"""Fail-closed experiment lifecycle for L5.

The runtime phase reads only serialized public cases. Evaluator gold is opened
later by the scoring phase. Every result is written atomically and locked
outputs are write-once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import resource
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from .compiler import (
    DeterministicCoordinateEncoder,
    SharedCoordinateCompiler,
    controlled_source,
)
from .compiler_eval import (
    build_compiler_panel,
    compile_public_payloads,
    compiler_gold_payload,
    compiler_public_payload,
    encode_compiler_panel,
    encode_compiler_public_payloads,
    evaluate_compiler_panel,
    score_compiler_predictions,
)
from .dataset import (
    ExpectedCandidate,
    ExpectedOutcome,
    PublicFieldCase,
    build_case,
    build_dependency_case,
    expected_payload,
    public_payload,
)
from .decoder import authorize, realize
from .end_to_end import (
    build_raw_end_to_end_panel,
    compile_raw_chain,
    raw_chain_gold_payload,
    raw_chain_public_payload,
    score_raw_chains,
)
from .evaluator import score_results
from .experiment import run_control_panel, run_interventions
from .field import EquilibriumFieldIndex, build_minimap
from .kernel import (
    CachedCoordinateEncoder,
    MiniLMCoordinateEncoder,
    NumpyCompatibility,
    load_kernel,
    save_kernel,
)
from .optimizer import optimize
from .scale import (
    LazyDistractorCorpus,
    attach_distractors,
    build_shared_field,
    run_shared_query,
    verify_cache,
)
from .schemas import (
    CompiledPromptField,
    EquilibriumBody,
    EquilibriumCandidate,
    EquilibriumStep,
    FieldEquilibriumResult,
    FieldMumbrane,
    FrontierSnapshot,
    LatentModeState,
    PromptInfluenceRecord,
    SupportCertificate,
)
from .training import (
    alignment_arrays_from_rows,
    build_alignment_examples,
    encode_alignment_examples,
    train_alignment_kernel,
)
from .verifier import certify_result
from .writer import assemble_public_case

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPOSITORY_ROOT / "configs" / "ltm-limit-l5.json"
SEMANTIC_DEPENDENCY_PATHS = (
    REPOSITORY_ROOT / "src" / "ltm_inference_i3" / "formal.py",
    REPOSITORY_ROOT / "src" / "ltm_inference_i3" / "schemas.py",
    REPOSITORY_ROOT / "src" / "ltm_limit_l2" / "parser.py",
    REPOSITORY_ROOT / "src" / "ltm_limit_l3" / "parser.py",
    REPOSITORY_ROOT / "src" / "ltm_limit_l4" / "axioms.py",
    REPOSITORY_ROOT / "src" / "ltm_limit_l4" / "exact.py",
    REPOSITORY_ROOT / "src" / "ltm_limit_l4" / "schemas.py",
)
LOCKED_STAGE_FILES = {
    "evaluate": "locked-results.json",
    "stress-evaluate": "stress-results.json",
    "scale-evaluate": "scale-results.json",
    "intervene": "intervention-results.json",
    "controls": "controls.json",
}


class LifecycleError(RuntimeError):
    pass


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _code_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((REPOSITORY_ROOT / "src" / "ltm_limit_l5").glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _canonical_hash(value: object) -> str:
    return _sha_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    )


def _dependency_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(REPOSITORY_ROOT)): _sha_file(path)
        for path in SEMANTIC_DEPENDENCY_PATHS
    }


def _model_hashes(model_root: Path) -> dict[str, str]:
    if not model_root.is_dir():
        return {}
    return {
        str(path.relative_to(model_root)): _sha_file(path)
        for path in sorted(model_root.rglob("*"))
        if path.is_file()
    }


def _classification(
    stages: dict[str, dict[str, Any]],
    gates: dict[str, float],
    *,
    resource_failed: bool,
) -> str:
    failed = {name for name, row in stages.items() if row.get("passed") is False}
    if failed & {
        "model-check.json",
        "dataset-manifest.json",
        "frozen-manifest.json",
        "locked-suite-manifest.json",
        "stress-results.json",
        "verification.json",
    }:
        return "L5-G — INTEGRITY OR LEAKAGE FAILURE"
    if "compiler-development-results.json" in failed:
        return "L5-B — PROMPT OR SOURCE COMPILATION FAILURE"
    if failed & {"field-results.json", "scale-results.json"}:
        return "L5-D — MINIMAP OR DYNAMIC FRONTIER FAILURE"
    if "development-results.json" in failed:
        return "L5-C — SHARED COORDINATE OR LOCAL FIELD-LAW FAILURE"
    locked = stages.get("locked-results.json", {})
    codes = set(locked.get("failure_codes", ()))
    if "LOCKED_COMPILER_GATE_FAILED" in codes:
        return "L5-B — PROMPT OR SOURCE COMPILATION FAILURE"
    if "RAW_END_TO_END_GATE_FAILED" in codes:
        raw = locked.get("end_to_end_metrics", {})
        if raw.get("unknown_or_alternative_agreement", 1.0) < gates.get(
            "raw_unknown_or_alternative_agreement", 1.0
        ):
            return "L5-F — CONTRADICTION OR MULTI-HYPOTHESIS FAILURE"
        return "L5-H — VERIFICATION OR DECODER HANDOFF FAILURE"
    if "PRIMARY_EQUILIBRIUM_GATE_FAILED" in codes:
        metrics = locked.get("metrics", {})
        family = metrics.get("family_exactness", {})
        if min(
            (
                family.get("balanced_contradiction", 1.0),
                family.get("alternatives", 1.0),
                family.get("unknown", 1.0),
                family.get("weighted_contradiction", 1.0),
            )
        ) < min(
            gates.get("ambiguity_unknown_recall", 1.0),
            gates.get("weighted_contradiction", 1.0),
        ):
            return "L5-F — CONTRADICTION OR MULTI-HYPOTHESIS FAILURE"
        if (
            metrics.get("accepted_verified_precision", 0.0)
            >= gates.get("accepted_verified_precision", 1.0)
            and metrics.get("incorrect_accepted_candidates", 1) == 0
            and metrics.get("safe_coverage", 0.0) < gates.get("safe_coverage", 0.0)
        ):
            return "L5-S — SAFE BUT LOW COVERAGE"
        return "L5-E — LATENT EQUILIBRIUM FAILURE"
    if failed & {"controls.json", "intervention-results.json"}:
        return "L5-E — LATENT EQUILIBRIUM FAILURE"
    if resource_failed or "LOCKED_RESOURCE_GATE_FAILED" in codes:
        return "L5-COMPUTE"
    if stages.get("verification.json", {}).get("passed") and not failed:
        return "L5-A — COMPILED LATENT FIELD EQUILIBRIUM PASS"
    first = next(iter(failed), "INCOMPLETE")
    return f"L5 DEVELOPMENT STOP — {first}"


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _atomic_bytes(path: Path, payload: bytes, *, refuse_existing: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if refuse_existing and path.exists():
        raise LifecycleError(f"immutable artifact already exists: {path.name}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, payload: object, *, refuse_existing: bool = True) -> None:
    _atomic_bytes(
        path,
        (json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n").encode(),
        refuse_existing=refuse_existing,
    )


def _atomic_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    payload = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        for row in rows
    )
    _atomic_bytes(path, payload)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _deterministic_alignment_rows(texts: tuple[str, ...]) -> np.ndarray:
    """Semantic stand-in used only by focused lifecycle tests."""

    result = []
    for text in texts:
        match = re.search(r"\b(?:given|when)\s+([A-Za-z][A-Za-z0-9_.:-]*)", text, re.IGNORECASE)
        topic = match.group(1) if match else text
        topic_bytes = hashlib.shake_256(f"topic:{topic}".encode()).digest(384 * 2)
        text_bytes = hashlib.shake_256(f"text:{text}".encode()).digest(384 * 2)
        topic_row = np.asarray(
            [(int.from_bytes(topic_bytes[i : i + 2], "big") / 32767.5) - 1 for i in range(0, len(topic_bytes), 2)],
            dtype=np.float32,
        )
        text_row = np.asarray(
            [(int.from_bytes(text_bytes[i : i + 2], "big") / 32767.5) - 1 for i in range(0, len(text_bytes), 2)],
            dtype=np.float32,
        )
        row = topic_row + 0.05 * text_row
        result.append(row / max(1e-8, float(np.linalg.norm(row))))
    return np.asarray(result, dtype=np.float32)


def _raw_public_family(row: dict[str, object]) -> str:
    """Identify replay strata from public grammar, never opaque IDs or gold."""

    sources = row.get("sources")
    if not isinstance(sources, (list, tuple)):
        raise LifecycleError("invalid raw end-to-end public sources")
    parsed = []
    polarities = []
    for source in sources:
        if not isinstance(source, dict):
            raise LifecycleError("invalid raw end-to-end source")
        match = re.fullmatch(
            r"when\s+(.+?)\s+then\s+(.+?)\.?",
            str(source.get("text", "")).strip(),
            re.IGNORECASE,
        )
        if match is None:
            raise LifecycleError("invalid raw end-to-end grammar")
        inputs = tuple(
            item.strip().lower()
            for item in re.split(r"\s+and\s+", match.group(1), flags=re.IGNORECASE)
        )
        outcomes = tuple(
            item.strip().lower()
            for item in re.split(r"\s+and\s+", match.group(2), flags=re.IGNORECASE)
        )
        parsed.append((inputs, outcomes))
        polarities.append(int(source.get("polarity", 0)))
    if len(parsed) == 1 and len(parsed[0][0]) > 1:
        return "unknown"
    if len(parsed) == 2 and parsed[0][0] == parsed[1][0]:
        if parsed[0][1] == parsed[1][1] and set(polarities) == {-1, 1}:
            return "balanced_conflict"
        if parsed[0][1] != parsed[1][1]:
            return "alternatives"
    return "answerable"


def _public_case(row: dict[str, Any]) -> PublicFieldCase:
    prompt_row = row["prompt"]
    prompt = CompiledPromptField(
        prompt_row["prompt_id"],
        tuple(PromptInfluenceRecord(**item) for item in prompt_row["influences"]),
        tuple(prompt_row["anchor_position"]),
        prompt_row["disposition"],
        tuple(prompt_row["failure_codes"]),
        prompt_row["encoder_calls"],
        prompt_row["source_hash"],
    )
    units = tuple(FieldMumbrane(**item) for item in row["units"])
    tuple_fields = {"input_unit_ids", "outcome_unit_ids", "provenance_ids"}
    bodies = tuple(
        EquilibriumBody(
            **{key: tuple(value) if key in tuple_fields else value for key, value in item.items()}
        )
        for item in row["bodies"]
    )
    return PublicFieldCase(
        row["case_id"], prompt, units, bodies, tuple(tuple(item) for item in row["vector_table"])
    )


def _expected(row: dict[str, Any]) -> ExpectedOutcome:
    return ExpectedOutcome(
        row["case_id"],
        row["family"],
        row["domain"],
        row["dependency_count"],
        row["disposition"],
        tuple(ExpectedCandidate(**item) for item in row["candidates"]),
        tuple(row["selected"]) if row["selected"] is not None else None,
    )


def _result_payload(result: FieldEquilibriumResult) -> dict[str, object]:
    return asdict(result)


def _result(row: dict[str, Any]) -> FieldEquilibriumResult:
    modes = lambda values: tuple(
        LatentModeState(
            item["mode_id"],
            tuple(item["semantic_position"]),
            tuple(tuple(pair) for pair in item["unit_activations"]),
            item["confidence_mass"],
            item["polarity"],
            tuple(item["supporting_source_keys"]),
            item["state_hash"],
        )
        for item in values
    )
    candidates = tuple(
        EquilibriumCandidate(
            item["unit_id"], item["semantic_key"], item["polarity"], item["confidence"],
            item["margin"], tuple(item["supporting_body_ids"]),
            tuple(item["supporting_source_keys"]), tuple(item["provenance_ids"]),
        )
        for item in row["candidates"]
    )
    trajectory = tuple(
        EquilibriumStep(
            item["step"], item["energy"], item["residual"], item["accepted"],
            item["learning_rate"], tuple(item["mode_hashes"]), item["frontier_hash"],
        )
        for item in row["trajectory"]
    )
    frontiers = tuple(
        FrontierSnapshot(
            item["step"], tuple(item["cell_ids"]), tuple(item["body_ids"]),
            tuple(item["opened_body_ids"]), tuple(item["closed_body_ids"]),
            item["coverage_bound"], item["frontier_hash"],
        )
        for item in row["frontiers"]
    )
    certificates = tuple(
        SupportCertificate(
            item["candidate_unit_id"], tuple(item["body_ids"]), tuple(item["source_keys"]),
            tuple(item["provenance_ids"]), item["verifier_revision"], item["verified"],
            item["certificate_hash"],
        )
        for item in row["certificates"]
    )
    return FieldEquilibriumResult(
        row["prompt_id"], row["disposition"], modes(row["initial_modes"]),
        modes(row["final_modes"]), candidates, row["selected_candidate_id"], trajectory,
        frontiers, certificates, row["coverage_disposition"], tuple(row["failure_codes"]), (),
    )


@dataclass(slots=True)
class L5Lifecycle:
    workspace: Path
    config_path: Path = DEFAULT_CONFIG
    limits: dict[str, int | bool] | None = None
    config: dict[str, Any] = dataclass_field(init=False, repr=False)
    _compatibility_cache: NumpyCompatibility | None = dataclass_field(
        init=False, default=None, repr=False
    )
    _run_all_started: float | None = dataclass_field(
        init=False, default=None, repr=False
    )

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace)
        self.config_path = Path(self.config_path)
        self.config = _read_json(self.config_path)
        if self.config.get("experiment_id") != "L5":
            raise LifecycleError("wrong experiment configuration")
        self.limits = dict(self.limits or {})
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    def _value(self, key: str, *, section: str | None = None, default: int | None = None) -> int:
        if key in self.limits:
            return int(self.limits[key])
        source = self.config[section] if section else self.config
        if key in source:
            return int(source[key])
        if default is None:
            raise LifecycleError(f"missing lifecycle value: {key}")
        return default

    def _test_encoder(self) -> bool:
        return bool(self.limits.get("deterministic_encoder", False))

    def _effective_limits(self) -> dict[str, object]:
        top_level = (
            "decoder_cases",
            "development_compiler_items",
            "development_field_bodies",
            "inner_updates_per_step",
            "intervention_cases",
            "latent_modes",
            "leaf_body_limit",
            "locked_compiler_items",
            "locked_field_bodies",
            "maximum_bodies_per_step",
            "maximum_cumulative_bodies",
            "maximum_macro_steps",
            "minimap_fanout",
            "minimap_modes",
            "primary_locked_queries",
            "scale_field_bodies",
            "stress_queries",
            "training_compiler_items",
        )
        resolved = {key: self._value(key) for key in top_level}
        resolved["development_queries"] = self._value(
            "development_queries",
            default=min(4000, self._value("development_field_bodies")),
        )
        return {
            "resolved": resolved,
            "training": {
                key: self._value(key, section="training")
                for key in ("batch_size", "compiler_alignment_steps")
            },
            "deterministic_encoder": self._test_encoder(),
            "overrides": dict(sorted(self.limits.items())),
        }

    def _path(self, name: str) -> Path:
        return self.workspace / name

    def _require(self, name: str) -> dict[str, Any]:
        path = self._path(name)
        if not path.exists():
            raise LifecycleError(f"required stage artifact missing: {name}")
        result = _read_json(path)
        if result.get("passed") is False:
            raise LifecycleError(f"required stage failed: {name}")
        return result

    def _history(self, stage: str, status: str, artifact: str | None) -> None:
        path = self._path("execution-history.json")
        rows = _read_json(path).get("events", []) if path.exists() else []
        rows.append(
            {
                "sequence": len(rows),
                "stage": stage,
                "status": status,
                "artifact": artifact,
                "telemetry_utc": datetime.now(UTC).isoformat(),
            }
        )
        _atomic_json(path, {"events": rows}, refuse_existing=False)

    def _write(self, stage: str, filename: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = {
            "experiment_id": "L5",
            "stage": stage,
            "config_sha256": _sha_file(self.config_path),
            "code_sha256": _code_hash(),
            **payload,
        }
        _atomic_json(self._path(filename), result)
        self._history(stage, "passed" if result.get("passed") else "failed", filename)
        return result

    def model_check(self) -> dict[str, Any]:
        self.workspace.mkdir(parents=True, exist_ok=True)
        model = REPOSITORY_ROOT / self.config["model_path"]
        files = tuple(path for path in (model / "config.json", model / "model.safetensors", model / "tokenizer.json") if path.exists())
        passed = len(files) == 3 and platform.python_version_tuple()[:2] == ("3", "11")
        return self._write(
            "model-check",
            "model-check.json",
            {
                "passed": passed,
                "python": platform.python_version(),
                "offline": True,
                "network_calls": 0,
                "model_hashes": {path.name: _sha_file(path) for path in files},
                "failure_codes": [] if passed else ["MODEL_OR_PYTHON_BOUNDARY_MISMATCH"],
            },
        )

    def dataset_build(self) -> dict[str, Any]:
        self._require("model-check.json")
        sample_count = min(32, self._value("development_compiler_items"))
        samples = tuple(build_case(index, self.config["seeds"]["development"]) for index in range(sample_count))
        passed = all(item.public.case_id == item.expected.case_id for item in samples)
        return self._write(
            "dataset-build",
            "dataset-manifest.json",
            {
                "passed": passed,
                "generator": "ltm_limit_l5.dataset.build_case/1",
                "validated_cases": sample_count,
                "configured_counts": {
                    key: self._value(key)
                    for key in (
                        "development_field_bodies",
                        "locked_field_bodies", "scale_field_bodies",
                        "training_compiler_items", "development_compiler_items",
                        "locked_compiler_items", "primary_locked_queries", "stress_queries",
                    )
                },
                "seeds": self.config["seeds"],
                "failure_codes": [] if passed else ["DATASET_IDENTITY_MISMATCH"],
            },
        )

    def compiler_develop(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._require("dataset-manifest.json")
        training_count = max(2, self._value("training_compiler_items") // 3)
        training_examples = build_alignment_examples(training_count, self.config["seeds"]["training"])
        model_path = REPOSITORY_ROOT / self.config["model_path"]
        if self._test_encoder():
            training_texts = tuple(
                text for item in training_examples
                for text in (item.prompt_text, item.relevant_body_text, item.unrelated_body_text)
            )
            training_arrays = alignment_arrays_from_rows(
                training_examples, _deterministic_alignment_rows(training_texts)
            )
            encoder_name = "deterministic-test-control"
        else:
            batch_size = self._value("batch_size", section="training")
            training_arrays = encode_alignment_examples(training_examples, model_path, batch_size=batch_size)
            encoder_name = "local-all-MiniLM-L6-v2"
        steps = self._value("compiler_alignment_steps", section="training")
        model, losses = train_alignment_kernel(
            training_arrays,
            steps=steps,
            batch_size=min(self._value("batch_size", section="training"), training_count),
            seed=self.config["seeds"]["training"],
        )
        checkpoint = self._path("selected-kernel.pt")
        temporary = checkpoint.with_name(f".{checkpoint.name}.tmp")
        if checkpoint.exists() or temporary.exists():
            raise LifecycleError("compiler checkpoint already exists")
        checkpoint_metrics = save_kernel(temporary, model, losses, self.config["seeds"]["training"])
        os.replace(temporary, checkpoint)
        checkpoint_metrics["sha256"] = _sha_file(checkpoint)
        development_count = self._value("development_compiler_items")
        panel = build_compiler_panel(
            development_count,
            self.config["seeds"]["development"],
            split="development",
        )
        panel_rows = (
            {
                item.source.source_id: row
                for item, row in zip(
                    panel,
                    _deterministic_alignment_rows(
                        tuple(item.source.text for item in panel)
                    ),
                    strict=True,
                )
            }
            if self._test_encoder()
            else encode_compiler_panel(panel, model_path, batch_size=self._value("batch_size", section="training"))
        )
        compiler_metrics = evaluate_compiler_panel(
            panel, CachedCoordinateEncoder(panel_rows, model)
        )
        pair_count = min(32, sum(item.should_accept for item in panel) // 2)
        writer_compiler = SharedCoordinateCompiler(CachedCoordinateEncoder(panel_rows, model))
        writer_roundtrips = 0
        for index in range(pair_count):
            body_case, prompt_case = panel[2 * index], panel[2 * index + 1]
            body = writer_compiler.compile_source(body_case.source)
            prompt = writer_compiler.compile_prompt(prompt_case.source)
            artifact = assemble_public_case(prompt, (body,))
            writer_roundtrips += int(len(artifact.bodies) == 1 and not artifact.prompt.failure_codes)
        passed = (
            compiler_metrics["accepted_semantic_precision"] >= self.config["gates"]["compiler_precision"]
            and compiler_metrics["safe_coverage"] >= self.config["gates"]["compiler_safe_coverage"]
            and compiler_metrics["exact_content_agreement"] >= self.config["gates"]["compiler_exact_content"]
            and compiler_metrics["coordinate_recall_at_8"] >= self.config["gates"]["coordinate_recall_at_8"]
            and compiler_metrics["incorrect_accepted_compilations"] == 0
            and compiler_metrics["encoder_calls"] == compiler_metrics["expected_encoder_calls"]
            and writer_roundtrips == pair_count
            and int(checkpoint_metrics["parameters"])
            <= self.config["compute"]["maximum_new_parameters"]
            and int(checkpoint_metrics["weight_bytes"])
            <= self.config["compute"]["maximum_weight_bytes"]
            and _peak_rss_bytes()
            < self.config["compute"]["development_rss_gb"] * (1024**3)
        )
        return self._write(
            "compiler-develop",
            "compiler-development-results.json",
            {
                "passed": passed,
                **compiler_metrics,
                "coordinate_encoder": encoder_name,
                "training_rows": len(training_arrays.semantic_rows),
                "writer_roundtrip_agreement": writer_roundtrips / pair_count,
                "supplied_fixture_metrics_used_as_compiler_accuracy": False,
                "checkpoint": checkpoint_metrics,
                "runtime_seconds": time.perf_counter() - started,
                "peak_rss_bytes": _peak_rss_bytes(),
                "failure_codes": [] if passed else ["COMPILER_DEVELOPMENT_GATE_FAILED"],
            },
        )

    def field_build(self) -> dict[str, Any]:
        self._require("compiler-development-results.json")
        target = self._value("development_field_bodies")
        built = cases = 0
        seed = self.config["seeds"]["development"]
        while built < target:
            public = build_case(cases, seed).public
            vectors = np.asarray(public.vector_table, dtype=np.float32)
            cells, summaries = build_minimap(
                public.bodies, public.units, vectors,
                leaf_limit=self._value("leaf_body_limit"),
                fanout=self._value("minimap_fanout"),
                modes=self._value("minimap_modes"),
                source_mass_cap=float(self.config["source_mass_cap"]),
            )
            EquilibriumFieldIndex(public.bodies, public.units, vectors, cells, summaries)
            built += len(public.bodies)
            cases += 1
        return self._write(
            "field-build",
            "field-results.json",
            {
                "passed": built >= target,
                "target_bodies": target,
                "built_bodies": built,
                "cases": cases,
                "failure_codes": [],
            },
        )

    def _compatibility(
        self,
        *,
        use_kernel: bool | None = None,
    ) -> NumpyCompatibility | None:
        enabled = not self._test_encoder() if use_kernel is None else use_kernel
        if not enabled:
            return None
        if self._compatibility_cache is None:
            self._compatibility_cache = NumpyCompatibility(
                load_kernel(self._path("selected-kernel.pt")),
                minimum_multiplier=float(
                    self.config["minimum_compatibility_multiplier"]
                ),
            )
        return self._compatibility_cache

    def _run_case(self, case: PublicFieldCase, *, use_kernel: bool | None = None) -> FieldEquilibriumResult:
        vectors = np.asarray(case.vector_table, dtype=np.float32)
        cells, summaries = build_minimap(
            case.bodies, case.units, vectors,
            leaf_limit=self._value("leaf_body_limit"),
            fanout=self._value("minimap_fanout"),
            modes=self._value("minimap_modes"),
            source_mass_cap=float(self.config["source_mass_cap"]),
        )
        index = EquilibriumFieldIndex(
            case.bodies, case.units, vectors, cells, summaries,
            source_mass_cap=float(self.config["source_mass_cap"]),
        )
        compatibility = self._compatibility(use_kernel=use_kernel)
        result = optimize(
            index,
            case.prompt,
            compatibility=compatibility,
            maximum_steps=self._value("maximum_macro_steps"),
            maximum_bodies=self._value("maximum_bodies_per_step"),
            maximum_cumulative_bodies=self._value("maximum_cumulative_bodies"),
            maximum_modes=self._value("latent_modes"),
            inner_updates=self._value("inner_updates_per_step"),
            confidence_threshold=float(self.config["calibration"]["candidate_confidence_min"]),
            margin_threshold=float(self.config["calibration"]["candidate_margin_min"]),
            coverage_threshold=float(self.config["calibration"]["coverage_min"]),
            convergence_residual=float(self.config["calibration"]["convergence_residual"]),
        )
        certified = certify_result(case, result)
        view = authorize(certified)
        realization = realize(
            view,
            {item.semantic_key: item.semantic_key for item in case.units},
        )
        if realization.failure_codes:
            raise LifecycleError("strict decoder rejected a verified result")
        return certified

    def equilibrium_develop(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._require("field-results.json")
        count = self._value("development_queries", default=min(4000, self._value("development_field_bodies")))
        generated = tuple(build_case(index, self.config["seeds"]["development"]) for index in range(count))
        results = tuple(self._run_case(item.public) for item in generated)
        metrics = score_results(
            tuple(item.public for item in generated),
            tuple(item.expected for item in generated),
            results,
        )
        coordinate_encoder = (
            DeterministicCoordinateEncoder()
            if self._test_encoder()
            else MiniLMCoordinateEncoder(
                REPOSITORY_ROOT / self.config["model_path"],
                load_kernel(self._path("selected-kernel.pt")),
            )
        )
        compiler = SharedCoordinateCompiler(coordinate_encoder)
        context = {
            "scope_key": "session:writer-development",
            "reality_key": "reality:writer-development",
        }
        sources = (
            compiler.compile_source(
                controlled_source(
                    "when writer_start then writer_middle",
                    source_id="writer:source:1",
                    provenance_id="writer:document:1",
                    **context,
                )
            ),
            compiler.compile_source(
                controlled_source(
                    "when writer_middle then writer_finish",
                    source_id="writer:source:2",
                    provenance_id="writer:document:2",
                    **context,
                )
            ),
        )
        prompt = compiler.compile_prompt(
            controlled_source(
                "given writer_start, what follows?",
                source_id="writer:prompt",
                provenance_id="writer:prompt",
                **context,
            )
        )
        compiled_case = assemble_public_case(prompt, sources)
        compiled_result = self._run_case(compiled_case)
        writer_end_to_end = (
            compiled_result.disposition == "candidate"
            and bool(compiled_result.certificates)
            and len(compiled_result.certificates[0].body_ids) == 2
        )
        gates = self.config["gates"]
        dependency = metrics["dependency_exactness"]
        passed = (
            metrics["accepted_verified_precision"] >= gates["accepted_verified_precision"]
            and metrics["incorrect_accepted_candidates"] == 0
            and metrics["safe_coverage"] >= gates["safe_coverage"]
            and metrics["all_case_exactness"] >= gates["all_case_exactness"]
            and dependency.get("2_4", 1.0) >= gates["dependency_2_4"]
            and dependency.get("5_8", 1.0) >= gates["dependency_5_8"]
            and dependency.get("9_16", 1.0) >= gates["dependency_9_16"]
            and metrics["candidate_confidence_agreement"]
            >= gates["candidate_confidence_agreement"]
            and writer_end_to_end
            and _peak_rss_bytes()
            < self.config["compute"]["development_rss_gb"] * (1024**3)
        )
        return self._write(
            "equilibrium-develop",
            "development-results.json",
            {
                "passed": passed,
                "metrics": metrics,
                "learned_kernel_active": not self._test_encoder(),
                "raw_compiler_writer_optimizer_verifier_agreement": writer_end_to_end,
                "supplied_fixture_metrics_used_as_compiler_accuracy": False,
                "runtime_seconds": time.perf_counter() - started,
                "peak_rss_bytes": _peak_rss_bytes(),
                "failure_codes": [] if passed else ["EQUILIBRIUM_DEVELOPMENT_GATE_FAILED"],
            },
        )

    def calibrate(self) -> dict[str, Any]:
        development = self._require("development-results.json")
        return self._write(
            "calibrate",
            "calibration.json",
            {
                "passed": bool(development["passed"]),
                "selected": {
                    "compiler_confidence": self.config["calibration"]["compiler_confidence_max"],
                    "candidate_confidence": self.config["calibration"]["candidate_confidence_min"],
                    "candidate_margin": self.config["calibration"]["candidate_margin_min"],
                    "coverage": self.config["calibration"]["coverage_min"],
                    "convergence_residual": self.config["calibration"]["convergence_residual"],
                },
                "selection_source": "frozen-config-with-development-gate",
                "failure_codes": [],
            },
        )

    def freeze(self) -> dict[str, Any]:
        self._require("calibration.json")
        names = (
            "model-check.json", "dataset-manifest.json", "compiler-development-results.json",
            "field-results.json", "development-results.json", "calibration.json", "selected-kernel.pt",
        )
        return self._write(
            "freeze",
            "frozen-manifest.json",
            {
                "passed": True,
                "artifacts": {name: _sha_file(self._path(name)) for name in names},
                "source_sha256": _code_hash(),
                "configuration_sha256": _sha_file(self.config_path),
                "model_files": _model_hashes(
                    REPOSITORY_ROOT / self.config["model_path"]
                ),
                "semantic_dependencies": _dependency_hashes(),
                "effective_limits": self._effective_limits(),
                "effective_limits_sha256": _canonical_hash(
                    self._effective_limits()
                ),
                "failure_codes": [],
            },
        )

    def _verify_freeze(self) -> None:
        frozen = self._require("frozen-manifest.json")
        if frozen["source_sha256"] != _code_hash() or frozen["configuration_sha256"] != _sha_file(self.config_path):
            raise LifecycleError("frozen source or configuration changed")
        if any(_sha_file(self._path(name)) != digest for name, digest in frozen["artifacts"].items()):
            raise LifecycleError("frozen artifact hash mismatch")
        if frozen.get("model_files") != _model_hashes(
            REPOSITORY_ROOT / self.config["model_path"]
        ):
            raise LifecycleError("frozen MiniLM files changed")
        if frozen.get("semantic_dependencies") != _dependency_hashes():
            raise LifecycleError("frozen semantic dependency changed")
        effective = self._effective_limits()
        if (
            frozen.get("effective_limits") != effective
            or frozen.get("effective_limits_sha256") != _canonical_hash(effective)
        ):
            raise LifecycleError("frozen effective limits changed")

    def _verify_locked_suite(self) -> dict[str, Any]:
        self._verify_freeze()
        suite = self._require("locked-suite-manifest.json")
        checks = {
            "public_sha256": suite["public_path"],
            "evaluator_gold_sha256": suite["evaluator_path"],
            "compiler_public_sha256": suite["compiler_public_path"],
            "compiler_gold_sha256": suite["compiler_evaluator_path"],
            "end_to_end_public_sha256": suite["end_to_end_public_path"],
            "end_to_end_gold_sha256": suite["end_to_end_evaluator_path"],
        }
        if any(
            not self._path(relative).is_file()
            or _sha_file(self._path(relative)) != suite[digest_key]
            for digest_key, relative in checks.items()
        ):
            raise LifecycleError("locked suite hash mismatch")
        return suite

    def locked_suite_build(self) -> dict[str, Any]:
        self._verify_freeze()
        count = self._value("primary_locked_queries")
        public_path = self._path("locked/public/cases.jsonl")
        gold_path = self._path("locked/evaluator-gold/gold.jsonl")
        compiler_public_path = self._path("locked/compiler-public/cases.jsonl")
        compiler_gold_path = self._path("locked/compiler-evaluator-gold/gold.jsonl")
        end_to_end_public_path = self._path("locked/end-to-end-public/cases.jsonl")
        end_to_end_gold_path = self._path(
            "locked/end-to-end-evaluator-gold/gold.jsonl"
        )
        if any(
            path.exists()
            for path in (
                public_path,
                gold_path,
                compiler_public_path,
                compiler_gold_path,
                end_to_end_public_path,
                end_to_end_gold_path,
            )
        ):
            raise LifecycleError("locked suite already exists")
        generated = tuple(build_case(index, self.config["seeds"]["locked"], split="locked") for index in range(count))
        _atomic_jsonl(public_path, [public_payload(item.public) for item in generated])
        _atomic_jsonl(gold_path, [expected_payload(item.expected) for item in generated])
        compiler_panel = build_compiler_panel(
            self._value("locked_compiler_items"),
            self.config["seeds"]["locked"],
            split="locked",
        )
        _atomic_jsonl(
            compiler_public_path,
            [compiler_public_payload(item) for item in compiler_panel],
        )
        _atomic_jsonl(
            compiler_gold_path,
            [compiler_gold_payload(item) for item in compiler_panel],
        )
        end_to_end_panel = build_raw_end_to_end_panel(
            self._value("decoder_cases"),
            self.config["seeds"]["locked"],
            split="locked-end-to-end",
        )
        _atomic_jsonl(
            end_to_end_public_path,
            [raw_chain_public_payload(item) for item in end_to_end_panel],
        )
        _atomic_jsonl(
            end_to_end_gold_path,
            [raw_chain_gold_payload(item) for item in end_to_end_panel],
        )
        return self._write(
            "locked-suite-build",
            "locked-suite-manifest.json",
            {
                "passed": True,
                "cases": count,
                "public_sha256": _sha_file(public_path),
                "evaluator_gold_sha256": _sha_file(gold_path),
                "compiler_public_sha256": _sha_file(compiler_public_path),
                "compiler_gold_sha256": _sha_file(compiler_gold_path),
                "end_to_end_public_sha256": _sha_file(end_to_end_public_path),
                "end_to_end_gold_sha256": _sha_file(end_to_end_gold_path),
                "public_path": "locked/public/cases.jsonl",
                "evaluator_path": "locked/evaluator-gold/gold.jsonl",
                "compiler_public_path": "locked/compiler-public/cases.jsonl",
                "compiler_evaluator_path": "locked/compiler-evaluator-gold/gold.jsonl",
                "compiler_cases": len(compiler_panel),
                "end_to_end_public_path": "locked/end-to-end-public/cases.jsonl",
                "end_to_end_evaluator_path": (
                    "locked/end-to-end-evaluator-gold/gold.jsonl"
                ),
                "end_to_end_cases": len(end_to_end_panel),
                "failure_codes": [],
            },
        )

    @staticmethod
    def _validate_rows(
        prediction_path: Path,
        public_rows: tuple[dict[str, object], ...],
        *,
        predicted_id: str,
        public_id: str = "case_id",
    ) -> None:
        predictions = tuple(_rows(prediction_path))
        if len(predictions) != len(public_rows) or any(
            predicted.get(predicted_id) != public.get(public_id)
            for public, predicted in zip(public_rows, predictions, strict=True)
        ):
            raise LifecycleError(f"immutable prediction mismatch: {prediction_path.name}")

    def _run_public_locked(self, *, resume: bool = False) -> tuple[Path, ...]:
        suite = self._require("locked-suite-manifest.json")
        public_rows = tuple(_rows(self._path(suite["public_path"])))
        shard_root = self._path("locked-prediction-shards")
        if not resume and shard_root.exists() and any(shard_root.iterdir()):
            raise LifecycleError("locked predictions already exist")
        shard_root.mkdir(parents=True, exist_ok=True)
        expected_names = {
            f"shard-{index // 256:05d}.jsonl"
            for index in range(0, len(public_rows), 256)
        }
        existing_names = {path.name for path in shard_root.glob("*.jsonl")}
        if existing_names - expected_names:
            raise LifecycleError("unexpected immutable prediction shard")
        paths: list[Path] = []
        for start in range(0, len(public_rows), 256):
            chunk = public_rows[start : start + 256]
            path = shard_root / f"shard-{start // 256:05d}.jsonl"
            if path.exists():
                if not resume:
                    raise LifecycleError("locked predictions already exist")
                self._validate_rows(
                    path, chunk, predicted_id="prompt_id"
                )
            else:
                _atomic_jsonl(
                    path,
                    [
                        _result_payload(self._run_case(_public_case(row)))
                        for row in chunk
                    ],
                )
            paths.append(path)
        return tuple(paths)

    def _score_locked(self, shards: tuple[Path, ...]) -> dict[str, object]:
        public_iter = _rows(self._path("locked/public/cases.jsonl"))
        gold_iter = _rows(self._path("locked/evaluator-gold/gold.jsonl"))
        result_iter = (row for path in shards for row in _rows(path))
        totals = {
            "cases": 0,
            "answerable": 0,
            "unsupported": 0,
            "accepted": 0,
            "incorrect": 0,
            "energy_increases": 0,
        }
        metric_counts: dict[str, list[int]] = {}
        family_sum: dict[str, list[float]] = {}
        domain_sum: dict[str, list[float]] = {}
        dependency_sum: dict[str, list[float]] = {}
        depth_sum: dict[str, list[float]] = {}
        while True:
            public_rows, gold_rows, result_rows = [], [], []
            for _ in range(256):
                triple = tuple(next(iterator, None) for iterator in (public_iter, gold_iter, result_iter))
                if triple == (None, None, None):
                    break
                if any(item is None for item in triple):
                    raise LifecycleError("locked public/gold/prediction length mismatch")
                public_rows.append(_public_case(triple[0]))
                gold_rows.append(_expected(triple[1]))
                result_rows.append(_result(triple[2]))
            if not public_rows:
                break
            metrics = score_results(tuple(public_rows), tuple(gold_rows), tuple(result_rows))
            cases = len(public_rows)
            totals["cases"] += cases
            totals["answerable"] += int(metrics["answerable_cases"])
            totals["unsupported"] += int(metrics["unsupported_cases"])
            totals["accepted"] += int(metrics["accepted_cases"])
            totals["incorrect"] += metrics["incorrect_accepted_candidates"]
            totals["energy_increases"] += int(metrics["accepted_energy_increases"])
            for key, values in metrics["metric_counts"].items():
                aggregate = metric_counts.setdefault(key, [0, 0])
                aggregate[0] += int(values[0])
                aggregate[1] += int(values[1])
            family_counts: dict[str, int] = {}
            domain_counts: dict[str, int] = {}
            dependency_counts: dict[str, int] = {}
            depth_counts: dict[str, int] = {}
            for item in gold_rows:
                family_counts[item.family] = family_counts.get(item.family, 0) + 1
                domain_counts[item.domain] = domain_counts.get(item.domain, 0) + 1
                band = (
                    "1" if item.dependency_count == 1 else "2_4"
                    if item.dependency_count <= 4 else "5_8"
                    if item.dependency_count <= 8 else "9_16"
                )
                dependency_counts[band] = dependency_counts.get(band, 0) + 1
                depth_key = str(item.dependency_count)
                depth_counts[depth_key] = depth_counts.get(depth_key, 0) + 1
            for target, values, counts in (
                (family_sum, metrics["family_exactness"], family_counts),
                (domain_sum, metrics["domain_exactness"], domain_counts),
                (dependency_sum, metrics["dependency_exactness"], dependency_counts),
                (depth_sum, metrics["depth_exactness"], depth_counts),
            ):
                for key, value in values.items():
                    aggregate = target.setdefault(key, [0.0, 0.0])
                    aggregate[0] += float(value) * counts[key]
                    aggregate[1] += counts[key]
        cases = int(totals["cases"])

        def aggregate_rate(key: str, *, empty: float = 1.0) -> float:
            success, count = metric_counts[key]
            return success / count if count else empty

        return {
            "cases": cases,
            "answerable_cases": totals["answerable"],
            "unsupported_cases": totals["unsupported"],
            "accepted_cases": totals["accepted"],
            "corpus_oracle_agreement": aggregate_rate("corpus_oracle_agreement"),
            "accepted_verified_precision": aggregate_rate(
                "accepted_verified_precision"
            ),
            "incorrect_accepted_candidates": totals["incorrect"],
            "safe_coverage": aggregate_rate("all_case_exactness", empty=0.0),
            "all_case_exactness": aggregate_rate("all_case_exactness", empty=0.0),
            "answerable_case_exactness": aggregate_rate(
                "answerable_case_exactness"
            ),
            "answerable_exactness": aggregate_rate("answerable_case_exactness"),
            "unsupported_case_exactness": aggregate_rate(
                "unsupported_case_exactness"
            ),
            "global_optimum_oracle_agreement": aggregate_rate(
                "global_optimum_oracle_agreement"
            ),
            "global_optimum_agreement": aggregate_rate(
                "global_optimum_oracle_agreement"
            ),
            "oracle_disposition_agreement": aggregate_rate(
                "oracle_disposition_agreement"
            ),
            "candidate_set_exactness": aggregate_rate("candidate_set_exactness"),
            "selected_optimum_agreement": aggregate_rate(
                "selected_optimum_agreement"
            ),
            "energy_nonincrease": aggregate_rate("energy_nonincrease"),
            "accepted_energy_increases": totals["energy_increases"],
            "coverage_certification": aggregate_rate("coverage_certification"),
            "convergence_certification": aggregate_rate(
                "convergence_certification"
            ),
            "frontier_stability": aggregate_rate("frontier_stability"),
            "certificate_safety": aggregate_rate("certificate_safety"),
            "candidate_confidence_agreement": aggregate_rate(
                "candidate_confidence_agreement"
            ),
            "factual_operation_safety": aggregate_rate(
                "factual_operation_safety"
            ),
            "required_body_frontier_recall": aggregate_rate(
                "required_body_frontier_recall"
            ),
            "required_body_frontier_complete": aggregate_rate(
                "required_body_frontier_complete"
            ),
            "certified_all_case_exactness": aggregate_rate(
                "certified_all_case_exactness", empty=0.0
            ),
            "certified_answerable_case_exactness": aggregate_rate(
                "certified_answerable_case_exactness"
            ),
            "ambiguity_unknown_recall": aggregate_rate(
                "ambiguity_unknown_recall"
            ),
            "family_exactness": {
                key: values[0] / values[1]
                for key, values in sorted(family_sum.items())
            },
            "domain_exactness": {
                key: values[0] / values[1]
                for key, values in sorted(domain_sum.items())
            },
            "dependency_exactness": {
                key: values[0] / values[1]
                for key, values in sorted(dependency_sum.items())
            },
            "depth_exactness": {
                key: values[0] / values[1]
                for key, values in sorted(
                    depth_sum.items(), key=lambda item: int(item[0])
                )
            },
            "metric_counts": {
                key: tuple(values) for key, values in sorted(metric_counts.items())
            },
        }

    def _run_compiler_locked(self, *, resume: bool = False) -> Path:
        suite = self._require("locked-suite-manifest.json")
        public_path = self._path(suite["compiler_public_path"])
        prediction_path = self._path("locked-compiler-predictions.jsonl")
        if prediction_path.exists():
            if not resume:
                raise LifecycleError("locked compiler predictions already exist")
            self._validate_rows(
                prediction_path,
                tuple(_rows(public_path)),
                predicted_id="case_id",
            )
            return prediction_path
        public_rows = tuple(_rows(public_path))
        if self._test_encoder():
            semantic_rows = _deterministic_alignment_rows(
                tuple(str(row["source"]["text"]) for row in public_rows)
            )
            cached = {
                str(row["source"]["source_id"]): value
                for row, value in zip(public_rows, semantic_rows, strict=True)
            }
        else:
            cached = encode_compiler_public_payloads(
                public_rows,
                REPOSITORY_ROOT / self.config["model_path"],
                batch_size=self._value("batch_size", section="training"),
            )
        predictions = compile_public_payloads(
            public_rows,
            CachedCoordinateEncoder(cached, load_kernel(self._path("selected-kernel.pt"))),
        )
        _atomic_jsonl(prediction_path, list(predictions))
        return prediction_path

    def _score_compiler_locked(self, prediction_path: Path) -> dict[str, object]:
        suite = self._require("locked-suite-manifest.json")
        public_rows = tuple(_rows(self._path(suite["compiler_public_path"])))
        gold_rows = tuple(_rows(self._path(suite["compiler_evaluator_path"])))
        predictions = tuple(_rows(prediction_path))
        return score_compiler_predictions(public_rows, gold_rows, predictions)

    def _end_to_end_encoder(
        self, public_rows: tuple[dict[str, object], ...]
    ) -> DeterministicCoordinateEncoder | CachedCoordinateEncoder:
        flattened = tuple(
            {"source": source}
            for case in public_rows
            for source in (*case["sources"], case["prompt"])
        )
        rows = (
            {
                str(item["source"]["source_id"]): row
                for item, row in zip(
                    flattened,
                    _deterministic_alignment_rows(
                        tuple(str(item["source"]["text"]) for item in flattened)
                    ),
                    strict=True,
                )
            }
            if self._test_encoder()
            else encode_compiler_public_payloads(
                flattened,
                REPOSITORY_ROOT / self.config["model_path"],
                batch_size=self._value("batch_size", section="training"),
            )
        )
        return CachedCoordinateEncoder(
            rows,
            load_kernel(self._path("selected-kernel.pt")),
        )

    def _compile_raw_chain(
        self,
        row: dict[str, object],
        encoder: DeterministicCoordinateEncoder | CachedCoordinateEncoder,
    ) -> dict[str, object]:
        calibration = self.config["calibration"]
        return compile_raw_chain(
            row,
            encoder,
            compatibility=self._compatibility(),
            compiler_confidence_threshold=float(
                calibration["compiler_confidence_max"]
            ),
            confidence_threshold=float(calibration["candidate_confidence_min"]),
            margin_threshold=float(calibration["candidate_margin_min"]),
            coverage_threshold=float(calibration["coverage_min"]),
            convergence_residual=float(calibration["convergence_residual"]),
            maximum_steps=self._value("maximum_macro_steps"),
            maximum_bodies=self._value("maximum_bodies_per_step"),
            maximum_cumulative_bodies=self._value("maximum_cumulative_bodies"),
            maximum_modes=self._value("latent_modes"),
            inner_updates=self._value("inner_updates_per_step"),
        )

    def _run_end_to_end_locked(self, *, resume: bool = False) -> Path:
        suite = self._require("locked-suite-manifest.json")
        public_rows = tuple(_rows(self._path(suite["end_to_end_public_path"])))
        prediction_path = self._path("locked-end-to-end-predictions.jsonl")
        if prediction_path.exists():
            if not resume:
                raise LifecycleError("locked end-to-end predictions already exist")
            self._validate_rows(
                prediction_path, public_rows, predicted_id="case_id"
            )
            return prediction_path
        encoder = self._end_to_end_encoder(public_rows)
        predictions = tuple(
            self._compile_raw_chain(row, encoder) for row in public_rows
        )
        _atomic_jsonl(prediction_path, list(predictions))
        return prediction_path

    def _score_end_to_end_locked(self, prediction_path: Path) -> dict[str, object]:
        suite = self._require("locked-suite-manifest.json")
        public_rows = tuple(_rows(self._path(suite["end_to_end_public_path"])))
        gold_rows = tuple(_rows(self._path(suite["end_to_end_evaluator_path"])))
        predictions = tuple(_rows(prediction_path))
        return score_raw_chains(public_rows, gold_rows, predictions)

    def _locked_prediction_paths(self) -> tuple[Path, Path, tuple[Path, ...]]:
        suite = self._require("locked-suite-manifest.json")
        compiler = self._path("locked-compiler-predictions.jsonl")
        end_to_end = self._path("locked-end-to-end-predictions.jsonl")
        shard_root = self._path("locked-prediction-shards")
        expected_shards = (
            int(suite["cases"]) + 255
        ) // 256
        shards = tuple(
            shard_root / f"shard-{index:05d}.jsonl"
            for index in range(expected_shards)
        )
        if not compiler.is_file() or not end_to_end.is_file() or not all(
            path.is_file() for path in shards
        ):
            raise LifecycleError("locked runtime predictions incomplete")
        extras = {
            path.name for path in shard_root.glob("*.jsonl")
        } - {path.name for path in shards}
        if extras:
            raise LifecycleError("unexpected immutable prediction shard")
        self._validate_rows(
            compiler,
            tuple(_rows(self._path(suite["compiler_public_path"]))),
            predicted_id="case_id",
        )
        self._validate_rows(
            end_to_end,
            tuple(_rows(self._path(suite["end_to_end_public_path"]))),
            predicted_id="case_id",
        )
        public_rows = tuple(_rows(self._path(suite["public_path"])))
        for index, shard in enumerate(shards):
            self._validate_rows(
                shard,
                public_rows[index * 256 : (index + 1) * 256],
                predicted_id="prompt_id",
            )
        return compiler, end_to_end, shards

    def _run_locked_runtime_process(self, *, resume: bool) -> dict[str, Any]:
        audit_path = self._path("locked-runtime-access-audit.json")
        if audit_path.exists():
            if not resume:
                raise LifecycleError("locked runtime already executed")
            audit = _read_json(audit_path)
            if not audit.get("passed"):
                raise LifecycleError("locked runtime access audit failed")
            self._locked_prediction_paths()
            return audit
        forbidden = (
            self._path("locked/evaluator-gold"),
            self._path("locked/compiler-evaluator-gold"),
            self._path("locked/end-to-end-evaluator-gold"),
        )
        command = [
            sys.executable,
            "-m",
            "ltm_limit_l5.runtime_worker",
            "--workspace",
            str(self.workspace),
            "--config",
            str(self.config_path),
            "--limits-json",
            json.dumps(self.limits, sort_keys=True),
        ]
        if resume:
            command.append("--resume")
        for path in forbidden:
            command.extend(("--forbid", str(path)))
        environment = os.environ.copy()
        environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "PYTHONHASHSEED": "0",
            }
        )
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise LifecycleError(f"locked runtime process failed: {detail}")
        audit = _read_json(audit_path)
        if (
            not audit.get("passed")
            or audit.get("probe_denials") != len(forbidden)
            or audit.get("runtime_gold_reads") != 0
            or audit.get("unexpected_gold_access_denials") != 0
            or audit.get("network_probe_denials", 0) < 1
            or audit.get("network_calls") != 0
            or audit.get("lifecycle_import_guarded") is not True
        ):
            raise LifecycleError("locked runtime access audit failed")
        self._locked_prediction_paths()
        return audit

    def _evaluate(self, *, resume: bool) -> dict[str, Any]:
        started = time.perf_counter()
        self._verify_locked_suite()
        if self._path("locked-results.json").exists():
            if resume:
                return _read_json(self._path("locked-results.json"))
            raise LifecycleError("second locked evaluation refused")
        access_audit = self._run_locked_runtime_process(resume=resume)
        self._verify_locked_suite()
        compiler_predictions, end_to_end_predictions, shards = (
            self._locked_prediction_paths()
        )
        compiler_metrics = self._score_compiler_locked(compiler_predictions)
        end_to_end_metrics = self._score_end_to_end_locked(end_to_end_predictions)
        metrics = self._score_locked(shards)
        gates = self.config["gates"]
        compiler_passed = (
            compiler_metrics["accepted_semantic_precision"] >= gates["compiler_precision"]
            and compiler_metrics["safe_coverage"] >= gates["compiler_safe_coverage"]
            and compiler_metrics["exact_content_agreement"] >= gates["compiler_exact_content"]
            and compiler_metrics["coordinate_recall_at_8"] >= gates["coordinate_recall_at_8"]
            and compiler_metrics["incorrect_accepted_compilations"] == 0
        )
        end_to_end_passed = (
            end_to_end_metrics["accepted_precision"]
            >= gates["accepted_verified_precision"]
            and end_to_end_metrics["safe_coverage"] >= gates["safe_coverage"]
            and end_to_end_metrics["all_case_exactness"] >= gates["all_case_exactness"]
            and end_to_end_metrics["one_pass_per_item"] == 1.0
            and end_to_end_metrics["incorrect_accepted_predictions"] == 0
            and end_to_end_metrics["unknown_or_alternative_agreement"]
            >= gates["raw_unknown_or_alternative_agreement"]
        )
        family = metrics["family_exactness"]
        dependency = metrics["dependency_exactness"]
        equilibrium_passed = (
            metrics["accepted_verified_precision"] >= gates["accepted_verified_precision"]
            and metrics["incorrect_accepted_candidates"] == 0
            and metrics["safe_coverage"] >= gates["safe_coverage"]
            and metrics["all_case_exactness"] >= gates["all_case_exactness"]
            and metrics["answerable_case_exactness"] >= gates["answerable_exactness"]
            and dependency["2_4"] >= gates["dependency_2_4"]
            and dependency["5_8"] >= gates["dependency_5_8"]
            and dependency["9_16"] >= gates["dependency_9_16"]
            and family["one_body"] >= gates["one_body_completion"]
            and family["conjunction"] >= gates["multi_input_completeness"]
            and family["conjunction"] >= gates["conjunction"]
            and family["weighted_contradiction"]
            >= gates["weighted_contradiction"]
            and min(
                family["balanced_contradiction"],
                family["alternatives"],
                family["unknown"],
            )
            >= gates["ambiguity_unknown_recall"]
            and metrics["global_optimum_oracle_agreement"]
            >= gates["global_optimum_agreement"]
            and metrics["accepted_energy_increases"] == 0
            and metrics["energy_nonincrease"] == 1.0
            and metrics["coverage_certification"]
            >= gates["coverage_certification"]
            and metrics["convergence_certification"]
            >= gates["convergence_certification"]
            and metrics["frontier_stability"] >= gates["frontier_stability"]
            and metrics["required_body_frontier_recall"]
            >= gates["required_body_frontier_recall"]
            and metrics["certificate_safety"] >= gates["certificate_safety"]
            and metrics["candidate_confidence_agreement"]
            >= gates["candidate_confidence_agreement"]
            and metrics["factual_operation_safety"]
            >= gates["factual_operation_safety"]
            and metrics["corpus_oracle_agreement"] == 1.0
        )
        runtime_seconds = time.perf_counter() - started
        resource_passed = (
            _peak_rss_bytes()
            < self.config["compute"]["locked_rss_gb"] * (1024**3)
            and runtime_seconds < self.config["compute"]["maximum_active_seconds"]
        )
        passed = (
            compiler_passed
            and end_to_end_passed
            and equilibrium_passed
            and resource_passed
        )
        failures = []
        if not compiler_passed:
            failures.append("LOCKED_COMPILER_GATE_FAILED")
        if not end_to_end_passed:
            failures.append("RAW_END_TO_END_GATE_FAILED")
        if not equilibrium_passed:
            failures.append("PRIMARY_EQUILIBRIUM_GATE_FAILED")
        if not resource_passed:
            failures.append("LOCKED_RESOURCE_GATE_FAILED")
        return self._write(
            "evaluate",
            "locked-results.json",
            {
                "passed": passed,
                "metrics": metrics,
                "compiler_metrics": compiler_metrics,
                "end_to_end_metrics": end_to_end_metrics,
                "compiler_predictions_sha256": _sha_file(compiler_predictions),
                "end_to_end_predictions_sha256": _sha_file(end_to_end_predictions),
                "prediction_shards": {path.name: _sha_file(path) for path in shards},
                "runtime_access_audit_sha256": _sha_file(
                    self._path("locked-runtime-access-audit.json")
                ),
                "runtime_gold_reads": access_audit["runtime_gold_reads"],
                "runtime_gold_probe_denials": access_audit["probe_denials"],
                "runtime_network_probe_denials": access_audit[
                    "network_probe_denials"
                ],
                "network_calls": access_audit["network_calls"],
                "runtime_process_id": access_audit["runtime_process_id"],
                "evaluator_process_id": os.getpid(),
                "runtime_evaluator_process_separation": (
                    access_audit["runtime_process_id"] != os.getpid()
                ),
                "runtime_seconds": runtime_seconds,
                "peak_rss_bytes": _peak_rss_bytes(),
                "failure_codes": failures,
            },
        )

    def evaluate(self) -> dict[str, Any]:
        return self._evaluate(resume=False)

    def resume(self) -> dict[str, Any]:
        return self._evaluate(resume=True)

    def stress_evaluate(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._require("locked-results.json")
        count = self._value("stress_queries")
        generated = tuple(
            build_dependency_case(
                index,
                self.config["seeds"]["stress"],
                depth=17 + index % 48,
                split="stress",
                domain="math" if index % 2 == 0 else "abstract",
            )
            for index in range(count)
        )
        results = tuple(self._run_case(item.public) for item in generated)
        correct = []
        by_depth: dict[int, list[bool]] = {}
        accepted = accepted_correct = 0
        for item, result in zip(generated, results, strict=True):
            row = score_results((item.public,), (item.expected,), (result,))
            agrees = row["all_case_exactness"] == 1.0
            correct.append(agrees)
            by_depth.setdefault(item.expected.dependency_count, []).append(agrees)
            if result.disposition in {"candidate", "alternatives"}:
                accepted += 1
                accepted_correct += int(agrees)
        band_17_32 = [
            value
            for depth, values in by_depth.items()
            if 17 <= depth <= 32
            for value in values
        ]
        band_33_64 = [
            value
            for depth, values in by_depth.items()
            if 33 <= depth <= 64
            for value in values
        ]
        rate = lambda values: sum(values) / len(values) if values else 1.0
        precision = accepted_correct / accepted if accepted else 1.0
        integrity = precision == 1.0
        annotation = (
            rate(band_17_32) >= self.config["gates"]["depth_17_32_stress"]
            and rate(band_33_64) >= self.config["gates"]["depth_33_64_stress"]
        )
        return self._write(
            "stress-evaluate",
            "stress-results.json",
            {
                "passed": integrity,
                "diagnostic_annotation": (
                    "L5-17-64-AGGREGATE-STRESS-PASS"
                    if annotation
                    else "L5-STRESS-BOUNDARY-MEASURED"
                ),
                "cases": count,
                "accepted_precision": precision,
                "overall_exactness": rate(correct),
                "depth_17_32": rate(band_17_32),
                "depth_33_64": rate(band_33_64),
                "depth": {str(key): rate(values) for key, values in sorted(by_depth.items())},
                "deepest_verified_dependency": max(
                    (depth for depth, values in by_depth.items() if any(values)),
                    default=0,
                ),
                "incorrect_accepted_candidates": accepted - accepted_correct,
                "primary_classification_affected": False,
                "runtime_seconds": time.perf_counter() - started,
                "peak_rss_bytes": _peak_rss_bytes(),
                "failure_codes": [] if integrity else ["STRESS_INTEGRITY_FAILURE"],
            },
        )

    def scale_evaluate(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._require("stress-results.json")
        target = self._value("locked_field_bodies")
        query_count = min(self._value("decoder_cases"), target)
        seed = self.config["seeds"]["scale"]
        relevant = tuple(
            build_case(
                index,
                seed,
                split="scale-relevant",
                family="one_body",
                domain="math",
            ).public
            for index in range(query_count)
        )
        distractors = tuple(
            build_case(
                index + query_count,
                seed,
                split="scale-distractor-primary",
                family="one_body",
                domain="math",
            ).public
            for index in range(max(0, target - query_count))
        )
        shared = build_shared_field((*relevant, *distractors))
        cache_ok = verify_cache(shared)
        correct = []
        maximum_active = cumulative = full_scans = 0
        for case in relevant:
            observation = run_shared_query(
                shared,
                case.case_id,
                maximum_steps=self._value("maximum_macro_steps"),
                maximum_bodies=self._value("maximum_bodies_per_step"),
                maximum_cumulative_bodies=self._value("maximum_cumulative_bodies"),
                maximum_modes=self._value("latent_modes"),
            )
            units = {item.unit_id: item for item in case.units}
            expected = {
                units[unit_id].semantic_key
                for body in case.bodies
                for unit_id in body.outcome_unit_ids
            }
            selected = {
                item.semantic_key
                for item in observation.result.candidates
                if item.unit_id == observation.result.selected_candidate_id
            }
            correct.append(
                observation.result.disposition == "candidate" and selected == expected
            )
            maximum_active = max(maximum_active, observation.maximum_active_bodies)
            cumulative = max(cumulative, observation.cumulative_distinct_body_reads)
            full_scans += observation.full_field_scans
        corpus = LazyDistractorCorpus(
            self._value("scale_field_bodies"),
            seed,
        )
        overlay = attach_distractors(shared, corpus, materialize_limit=0)
        exactness = sum(correct) / len(correct) if correct else 1.0
        materialized = sum(len(partition.bodies) for partition in shared.partitions)
        runtime_seconds = time.perf_counter() - started
        passed = (
            cache_ok
            and materialized >= target
            and exactness == 1.0
            and maximum_active <= self._value("maximum_bodies_per_step")
            and cumulative <= self._value("maximum_cumulative_bodies")
            and full_scans == 0
            and _peak_rss_bytes()
            < self.config["compute"]["locked_rss_gb"] * (1024**3)
            and runtime_seconds < self.config["compute"]["maximum_active_seconds"]
        )
        return self._write(
            "scale-evaluate",
            "scale-results.json",
            {
                "passed": passed,
                "primary_materialized_bodies": materialized,
                "query_cases": len(relevant),
                "shared_field_exactness": exactness,
                "partition_count": len(shared.partitions),
                "field_manifest_sha256": shared.manifest.manifest_sha256,
                "cache_verification": cache_ok,
                "maximum_active_bodies": maximum_active,
                "maximum_cumulative_body_reads": cumulative,
                "full_field_scans": full_scans,
                "million_body_diagnostic": asdict(overlay.metrics),
                "million_body_is_lazy_commitment_not_materialized_runtime": True,
                "runtime_seconds": runtime_seconds,
                "peak_rss_bytes": _peak_rss_bytes(),
                "failure_codes": [] if passed else ["SHARED_FIELD_SCALE_GATE_FAILED"],
            },
        )

    def intervene(self) -> dict[str, Any]:
        self._require("scale-results.json")
        count = min(
            self._value("intervention_cases"),
            max(20, self._value("primary_locked_queries")),
        )
        generated = tuple(
            build_case(index, self.config["seeds"]["interventions"], split="intervention")
            for index in range(count)
        )
        metrics = run_interventions(
            generated,
            compatibility=self._compatibility(),
        )
        passed = all(
            value["rate"]
            >= (
                self.config["gates"]["force_direction"]
                if key == "direction_reversal_accuracy"
                else 0.95
            )
            for key, value in metrics.items()
            if value["cases"]
        )
        return self._write(
            "intervene",
            "intervention-results.json",
            {
                "passed": passed,
                "metrics": metrics,
                "failure_codes": [] if passed else ["CAUSAL_INTERVENTION_GATE_FAILED"],
            },
        )

    def controls(self) -> dict[str, Any]:
        self._require("intervention-results.json")
        count = min(
            1000,
            self._value("intervention_cases"),
            max(20, self._value("primary_locked_queries")),
        )
        generated = tuple(
            build_case(index, self.config["seeds"]["interventions"], split="controls")
            for index in range(count)
        )
        metrics = run_control_panel(
            generated,
            compatibility=self._compatibility(),
            minimum_geometry_gain=float(
                self.config["gates"]["minimum_geometry_gain"]
            ),
        )
        effects = metrics["effects"]
        mechanism_passed = bool(metrics.get("mechanism_gates", {}).get("passed"))
        passed = (
            effects["full_minus_no_optimization"] >= self.config["gates"]["full_minus_no_optimization"]
            and effects["full_minus_fixed_frontier_deep"] >= self.config["gates"]["full_minus_fixed_frontier"]
            and effects["multi_minus_single_mode_conflicts"] >= self.config["gates"]["multi_minus_single_mode"]
            and effects["context_gate_drop"] >= self.config["gates"]["context_control_drop"]
            and effects["raw_duplicate_semantic_changes"] == 0
            and (mechanism_passed or self._test_encoder())
        )
        return self._write(
            "controls",
            "controls.json",
            {
                "passed": passed,
                "metrics": metrics,
                "mechanism_gate_enforced": not self._test_encoder(),
                "mechanism_gate_passed": mechanism_passed,
                "failure_codes": [] if passed else ["CAUSAL_CONTROL_GATE_FAILED"],
            },
        )

    def verify(self) -> dict[str, Any]:
        suite = self._verify_locked_suite()
        locked = self._require("locked-results.json")
        stress = self._require("stress-results.json")
        scale = self._require("scale-results.json")
        interventions = self._require("intervention-results.json")
        controls_path = self._path("controls.json")
        if not controls_path.is_file():
            raise LifecycleError("required stage artifact missing: controls.json")
        controls = _read_json(controls_path)
        public = self._path(suite["public_path"])
        gold = self._path(suite["evaluator_path"])
        compiler_public = self._path(suite["compiler_public_path"])
        compiler_gold = self._path(suite["compiler_evaluator_path"])
        compiler_predictions, end_to_end_predictions, shard_paths = (
            self._locked_prediction_paths()
        )
        end_to_end_public = self._path(suite["end_to_end_public_path"])
        end_to_end_gold = self._path(suite["end_to_end_evaluator_path"])
        access_audit_path = self._path("locked-runtime-access-audit.json")
        access_audit = _read_json(access_audit_path)
        public_rows = tuple(_rows(public))
        stored_results = tuple(
            row
            for path in shard_paths
            for row in _rows(path)
        )
        replay_count = min(32, len(public_rows))
        replay_equal = all(
            json.loads(
                json.dumps(
                    _result_payload(self._run_case(_public_case(public_rows[index]))),
                    sort_keys=True,
                )
            )
            == stored_results[index]
            for index in range(replay_count)
        )
        end_to_end_public_rows = tuple(_rows(end_to_end_public))
        stored_end_to_end = tuple(_rows(end_to_end_predictions))
        answerable_indices = [
            index for index, row in enumerate(end_to_end_public_rows)
            if _raw_public_family(row) == "answerable"
        ][:8]
        safety_indices = [
            index
            for family in ("unknown", "balanced_conflict", "alternatives")
            for index in [
                item_index for item_index, row in enumerate(end_to_end_public_rows)
                if _raw_public_family(row) == family
            ][:2]
        ]
        replay_indices = tuple(dict.fromkeys((*answerable_indices, *safety_indices)))
        replay_public = tuple(end_to_end_public_rows[index] for index in replay_indices)
        replay_encoder = self._end_to_end_encoder(replay_public)
        end_to_end_replay = tuple(
            self._compile_raw_chain(row, replay_encoder) for row in replay_public
        )
        end_to_end_replay_equal = all(
            json.loads(json.dumps(prediction, sort_keys=True))
            == stored_end_to_end[stored_index]
            for stored_index, prediction in zip(
                replay_indices, end_to_end_replay, strict=True
            )
        )
        end_to_end_public_is_gold_free = all(
            not {
                "expected_semantic_key",
                "expected_disposition",
                "expected_candidates",
                "expected_certificate_body_counts",
                "depth",
                "family",
            }
            & row.keys()
            for row in end_to_end_public_rows
        )
        rescored = {
            "compiler": self._score_compiler_locked(compiler_predictions),
            "end_to_end": self._score_end_to_end_locked(end_to_end_predictions),
            "equilibrium": self._score_locked(shard_paths),
        }
        evaluator_replay_equal = _canonical_hash(rescored) == _canonical_hash(
            {
                "compiler": locked["compiler_metrics"],
                "end_to_end": locked["end_to_end_metrics"],
                "equilibrium": locked["metrics"],
            }
        )
        passed = (
            _sha_file(public) == suite["public_sha256"]
            and _sha_file(gold) == suite["evaluator_gold_sha256"]
            and _sha_file(compiler_public) == suite["compiler_public_sha256"]
            and _sha_file(compiler_gold) == suite["compiler_gold_sha256"]
            and _sha_file(compiler_predictions) == locked["compiler_predictions_sha256"]
            and _sha_file(end_to_end_public) == suite["end_to_end_public_sha256"]
            and _sha_file(end_to_end_gold) == suite["end_to_end_gold_sha256"]
            and _sha_file(end_to_end_predictions)
            == locked["end_to_end_predictions_sha256"]
            and _sha_file(access_audit_path)
            == locked["runtime_access_audit_sha256"]
            and access_audit.get("passed") is True
            and access_audit.get("probe_denials") == 3
            and access_audit.get("runtime_gold_reads") == 0
            and access_audit.get("unexpected_gold_access_denials") == 0
            and access_audit.get("network_probe_denials", 0) >= 1
            and access_audit.get("network_calls") == 0
            and access_audit.get("lifecycle_import_guarded") is True
            and locked["runtime_gold_reads"] == 0
            and locked.get("runtime_evaluator_process_separation") is True
            and locked.get("runtime_process_id")
            != locked.get("evaluator_process_id")
            and stress["incorrect_accepted_candidates"] == 0
            and scale["full_field_scans"] == 0
            and interventions["passed"]
            and isinstance(controls.get("mechanism_gate_passed"), bool)
            and replay_equal
            and end_to_end_replay_equal
            and end_to_end_public_is_gold_free
            and evaluator_replay_equal
            and all(_sha_file(self._path("locked-prediction-shards") / name) == digest for name, digest in locked["prediction_shards"].items())
        )
        return self._write(
            "verify", "verification.json",
            {
                "passed": passed,
                "deterministic_artifact_replay": replay_equal,
                "replayed_cases": replay_count,
                "end_to_end_deterministic_replay": end_to_end_replay_equal,
                "end_to_end_replayed_cases": len(replay_indices),
                "end_to_end_replayed_safety_cases": len(safety_indices),
                "end_to_end_public_is_gold_free": end_to_end_public_is_gold_free,
                "evaluator_metric_replay": evaluator_replay_equal,
                "runtime_gold_guard_passed": access_audit.get("passed") is True,
                "runtime_evaluator_process_separation": locked.get(
                    "runtime_evaluator_process_separation"
                ),
                "runtime_gold_probe_denials": access_audit.get("probe_denials"),
                "runtime_gold_reads": access_audit.get("runtime_gold_reads"),
                "network_probe_denials": access_audit.get(
                    "network_probe_denials"
                ),
                "network_calls": access_audit.get("network_calls"),
                "failure_codes": (
                    []
                    if passed
                    else ["ARTIFACT_OR_EVALUATOR_REPLAY_FAILED"]
                ),
            },
        )

    def report(self) -> dict[str, Any]:
        stages = {}
        for name in (
            "model-check.json", "dataset-manifest.json",
            "compiler-development-results.json", "field-results.json",
            "development-results.json", "calibration.json", "frozen-manifest.json",
            "locked-suite-manifest.json", "locked-results.json", "stress-results.json",
            "scale-results.json", "intervention-results.json", "controls.json",
            "verification.json",
        ):
            if self._path(name).exists():
                stages[name] = _read_json(self._path(name))
        active_seconds = (
            time.perf_counter() - self._run_all_started
            if self._run_all_started is not None
            else None
        )
        resource_failed = (
            _peak_rss_bytes()
            >= self.config["compute"]["machine_ceiling_gb"] * (1024**3)
            or active_seconds is not None
            and active_seconds >= self.config["compute"]["maximum_active_seconds"]
        )
        mechanical = _classification(
            stages,
            self.config["gates"],
            resource_failed=resource_failed,
        )
        payload = {
            "passed": mechanical.startswith("L5-A"),
            "classification": mechanical,
            "measured_stages": tuple(stages),
            "locked_raw_end_to_end_metrics": stages.get(
                "locked-results.json", {}
            ).get("end_to_end_metrics"),
            "current_run_all_active_seconds": active_seconds,
            "process_peak_rss_bytes": _peak_rss_bytes(),
            "failure_codes": (
                []
                if mechanical.startswith("L5-A")
                else [mechanical.split(" — ", 1)[0]]
            ),
        }
        result = self._write("report", "report.json", payload)
        lines = [
            "# L5 measured report",
            "",
            f"Classification: `{mechanical}`",
            "",
            "Only stages listed below were measured:",
            "",
        ]
        lines.extend(f"- `{name}`: {'pass' if value.get('passed') else 'fail'}" for name, value in stages.items())
        raw_metrics = payload["locked_raw_end_to_end_metrics"]
        if raw_metrics is not None:
            lines.extend(
                (
                    "",
                    "Locked raw compiler → writer → optimizer → verifier → decoder:",
                    "",
                    f"- accepted precision: `{raw_metrics['accepted_precision']:.6f}`",
                    f"- safe coverage: `{raw_metrics['safe_coverage']:.6f}`",
                    f"- all-case exactness: `{raw_metrics['all_case_exactness']:.6f}`",
                    (
                        "- unknown/conflict/alternative agreement: "
                        f"`{raw_metrics['unknown_or_alternative_agreement']:.6f}`"
                    ),
                    f"- incorrect accepted predictions: `{raw_metrics['incorrect_accepted_predictions']}`",
                )
            )
        _atomic_bytes(self._path("report.md"), ("\n".join(lines) + "\n").encode())
        return result

    def run_all(self) -> dict[str, Any]:
        self._run_all_started = time.perf_counter()
        stages = (
            ("model-check.json", self.model_check),
            ("dataset-manifest.json", self.dataset_build),
            ("compiler-development-results.json", self.compiler_develop),
            ("field-results.json", self.field_build),
            ("development-results.json", self.equilibrium_develop),
            ("calibration.json", self.calibrate),
            ("frozen-manifest.json", self.freeze),
            ("locked-suite-manifest.json", self.locked_suite_build),
            ("locked-results.json", self.evaluate),
            ("stress-results.json", self.stress_evaluate),
            ("scale-results.json", self.scale_evaluate),
            ("intervention-results.json", self.intervene),
            ("controls.json", self.controls),
            ("verification.json", self.verify),
        )
        for filename, action in stages:
            if self._path(filename).exists():
                result = _read_json(self._path(filename))
            else:
                result = action()
            if result.get("passed") is False:
                if filename == "controls.json":
                    verification = self.verify()
                    if verification.get("passed") is False:
                        return self.report()
                return self.report()
        return self.report()


COMMANDS = {
    "model-check": "model_check",
    "dataset-build": "dataset_build",
    "compiler-develop": "compiler_develop",
    "field-build": "field_build",
    "equilibrium-develop": "equilibrium_develop",
    "calibrate": "calibrate",
    "freeze": "freeze",
    "locked-suite-build": "locked_suite_build",
    "evaluate": "evaluate",
    "resume": "resume",
    "stress-evaluate": "stress_evaluate",
    "scale-evaluate": "scale_evaluate",
    "intervene": "intervene",
    "controls": "controls",
    "verify": "verify",
    "report": "report",
    "run-all": "run_all",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l5")
    parser.add_argument("command", choices=tuple(COMMANDS))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    del args.offline
    lifecycle = L5Lifecycle(args.workspace, args.config)
    try:
        result = getattr(lifecycle, COMMANDS[args.command])()
    except LifecycleError as error:
        print(json.dumps({"experiment_id": "L5", "command": args.command, "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed") else 1


__all__ = ["COMMANDS", "L5Lifecycle", "LifecycleError", "main"]
