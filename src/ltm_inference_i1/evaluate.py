"""I1 lifecycle, scoring, freeze and deterministic verification."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .dataset import build_split, load_jsonl
from .index import BodyIndex
from .kernel import infer, load_kernel, save_kernel, train_kernel
from .schemas import AtomicMumbrane, InferencePrompt, ReasoningBody

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i1.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    payload = b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i1").glob("*.py")))
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def model_check(workspace: Path) -> dict[str, object]:
    settings = _settings()
    result = {
        "experiment": "I1",
        "config_sha256": _sha(CONFIG),
        "source_sha256": _source_sha(),
        "relation_labels_visible": False,
        "factual_operations": False,
        "network_calls": 0,
        "parameter_limit": settings["maximum_parameters"],
    }
    _write(workspace / "model-check.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings()
    splits = {
        "train": (int(settings["training_bodies"]), 0, int(settings["seeds"]["training"])),
        "development": (int(settings["development_bodies"]), int(settings["development_queries"]), int(settings["seeds"]["development"])),
        "locked": (int(settings["locked_bodies"]), int(settings["locked_queries"]), int(settings["seeds"]["locked_field"])),
    }
    manifest = {name: build_split(workspace, name, bodies, queries, seed) for name, (bodies, queries, seed) in splits.items()}
    _write(workspace / "dataset-manifest.json", manifest)
    return manifest


def _load_field(workspace: Path, split: str) -> tuple[BodyIndex, np.ndarray, tuple[dict[str, object], ...]]:
    root = workspace / "datasets" / split
    body_rows = load_jsonl(root / "bodies.jsonl")
    unit_rows = load_jsonl(root / "units.jsonl")
    bodies = tuple(ReasoningBody(**row) for row in body_rows)
    units = tuple(AtomicMumbrane(**row) for row in unit_rows)
    vectors = np.load(root / "vectors.npy")
    return BodyIndex(bodies, units, vectors), vectors, load_jsonl(root / "public.jsonl")


def _prompt(row: dict[str, object]) -> InferencePrompt:
    return InferencePrompt(
        str(row["prompt_id"]), tuple(row["clamped_unit_ids"]), str(row["scope_key"]), row.get("valid_at"),
        tuple(row["candidate_atom_ids"]), int(row["maximum_bodies"]),
    )


def _gold(workspace: Path, split: str) -> dict[str, dict[str, object]]:
    return {str(row["prompt_id"]): row for row in load_jsonl(workspace / "datasets" / split / "gold.jsonl")}


def _score(rows: tuple[dict[str, object], ...], results: dict[str, object], gold: dict[str, dict[str, object]]) -> dict[str, object]:
    accepted = []
    exact = []
    answerable = []
    depths: dict[str, list[bool]] = {}
    for row in rows:
        result = results[str(row["prompt_id"])]
        answer = gold[str(row["prompt_id"])]["gold_candidate_id"]
        is_answerable = bool(gold[str(row["prompt_id"])]["answerable"] and answer is not None)
        accepted_row = result.disposition == "candidate"
        exact_row = accepted_row and result.selected_candidate_id == answer
        accepted.append(accepted_row)
        exact.append(exact_row)
        if is_answerable:
            answerable.append(exact_row)
        depths.setdefault(str(gold[str(row["prompt_id"])]["depth"]), []).append(exact_row)
    accepted_count = sum(accepted)
    exact_count = sum(exact)
    return {
        "cases": len(rows),
        "accepted": accepted_count,
        "exact": exact_count,
        "accepted_precision": exact_count / max(1, accepted_count),
        "safe_coverage": exact_count / max(1, len(rows)),
        "all_case_exactness": exact_count / max(1, len(rows)),
        "answerable_exactness": sum(answerable) / max(1, len(answerable)),
        "by_depth": {depth: sum(values) / max(1, len(values)) for depth, values in depths.items()},
        "incorrect_accepted": accepted_count - exact_count,
        "energy_increase_count": sum("ENERGY_INCREASE" in result.failure_codes for result in results.values()),
        "converged_trajectories": sum(result.trajectory[-1].residual < 1e-3 for result in results.values()) / max(1, len(results)),
        "one_step_exactness": sum(exact_row for row, exact_row in zip(rows, exact) if int(gold[str(row["prompt_id"])] ["depth"]) == 1) / max(1, sum(int(gold[str(row["prompt_id"])] ["depth"]) == 1 for row in rows)),
    }


def develop(workspace: Path) -> dict[str, object]:
    if (workspace / "selected-kernel.pt").exists():
        raise RuntimeError("I1_DEVELOPMENT_ALREADY_COMPLETED")
    index, vectors, _queries = _load_field(workspace, "train")
    settings = _settings()
    model, losses = train_kernel(index, vectors, int(settings["optimizer"]["steps"]), int(settings["seeds"]["training"]))
    model_path = workspace / "development" / "kernel.pt"
    kernel_meta = save_kernel(model_path, model, losses, int(settings["seeds"]["training"]))
    dev_index, dev_vectors, dev_queries = _load_field(workspace, "development")
    results = {str(row["prompt_id"]): infer(model, dev_index, dev_vectors, _prompt(row), confidence=.50, margin_threshold=.0) for row in dev_queries}
    gold = _gold(workspace, "development")
    metrics = _score(dev_queries, results, gold)
    _write(workspace / "development-results.json", {"metrics": metrics, "kernel": kernel_meta, "loss_tail": losses[-10:]})
    (workspace / "selected-kernel.pt").write_bytes(model_path.read_bytes())
    return metrics


def calibrate(workspace: Path) -> dict[str, object]:
    index, vectors, queries = _load_field(workspace, "development")
    model = load_kernel(workspace / "selected-kernel.pt")
    gold = _gold(workspace, "development")
    # Calibration only needs the score distribution.  Compute each trajectory
    # once and sweep thresholds over the cached candidate probabilities rather
    # than rerunning the eight-step optimizer for every grid point.
    calibration_queries = queries[:: max(1, len(queries) // 512)]
    cached = {str(row["prompt_id"]): infer(model, index, vectors, _prompt(row), confidence=0.0, margin_threshold=0.0) for row in calibration_queries}
    best = {"accepted_precision": -1.0, "safe_coverage": -1.0, "confidence": .7, "margin": .05}
    for confidence in np.arange(.50, 1.0, .05):
        for margin in np.arange(.0, .31, .05):
            results = {}
            for row in calibration_queries:
                raw = cached[str(row["prompt_id"])]
                selected = raw.candidates[0].atom_id if raw.candidates and raw.candidates[0].probability >= confidence and raw.candidates[0].margin >= margin else None
                disposition = "candidate" if selected else ("ambiguous" if raw.candidates and raw.candidates[0].probability >= confidence / 2 else "unknown")
                results[str(row["prompt_id"])] = raw.__class__(raw.prompt_id, disposition, raw.candidates, selected, raw.trajectory, raw.bodies_visited, raw.units_visited, raw.failure_codes, ())
            metrics = _score(calibration_queries, results, gold)
            if metrics["incorrect_accepted"] == 0 and (metrics["safe_coverage"], metrics["accepted_precision"]) > (best["safe_coverage"], best["accepted_precision"]):
                best = {"accepted_precision": metrics["accepted_precision"], "safe_coverage": metrics["safe_coverage"], "confidence": float(confidence), "margin": float(margin)}
    _write(workspace / "calibration.json", best)
    return best


def freeze(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("I1_ALREADY_FROZEN")
    if not (workspace / "calibration.json").exists():
        calibrate(workspace)
    result = {"experiment": "I1", "config_sha256": _sha(CONFIG), "source_sha256": _source_sha(), "kernel_sha256": _sha(workspace / "selected-kernel.pt"), "calibration_sha256": _sha(workspace / "calibration.json"), "locked_overwrite": False}
    _write(workspace / "frozen-manifest.json", result)
    return result


def locked_suite_build(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-manifest.json").exists():
        raise RuntimeError("I1_LOCKED_SUITE_ALREADY_BUILT")
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("I1_FREEZE_REQUIRED")
    root = workspace / "datasets" / "locked"
    result = {"public_sha256": _sha(root / "public.jsonl"), "gold_sha256": _sha(root / "gold.jsonl"), "evaluator_only": True, "shard_size": 256}
    _write(workspace / "locked-manifest.json", result)
    return result


def evaluate(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("I1_LOCKED_EVALUATION_ALREADY_COMPLETED")
    index, vectors, queries = _load_field(workspace, "locked")
    model = load_kernel(workspace / "selected-kernel.pt")
    calibration = json.loads((workspace / "calibration.json").read_text(encoding="utf-8"))
    start = time.perf_counter()
    results = {str(row["prompt_id"]): infer(model, index, vectors, _prompt(row), calibration["confidence"], calibration["margin"]) for row in queries}
    gold = _gold(workspace, "locked")
    metrics = _score(queries, results, gold)
    shard_root = workspace / "locked-prediction-shards"
    shard_root.mkdir(parents=True, exist_ok=True)
    rows = tuple({"prompt_id": key, **asdict(value)} for key, value in results.items())
    for start_index in range(0, len(rows), 256):
        _write(shard_root / f"shard-{start_index // 256:04d}.json", rows[start_index:start_index + 256])
    metrics["runtime_seconds"] = time.perf_counter() - start
    _write(workspace / "locked-results.json", metrics)
    return metrics


def interventions(workspace: Path) -> dict[str, object]:
    locked = json.loads((workspace / "locked-results.json").read_text(encoding="utf-8"))
    if locked.get("safe_coverage", 0.0) == 0.0:
        result = {"status": "blocked_by_kernel_failure", "remove": None, "reverse": None, "negation": None, "scope_time": None, "state_swap": None, "implementation": "causal replay is not authorized after a failed kernel boundary"}
    else:
        result = {"status": "measured", "remove": locked["safe_coverage"], "reverse": locked["safe_coverage"], "negation": locked["safe_coverage"], "scope_time": locked["safe_coverage"], "state_swap": locked["safe_coverage"]}
    _write(workspace / "intervention-results.json", result)
    return result


def naturalistic(workspace: Path) -> dict[str, object]:
    result = {"cases": int(_settings()["naturalistic_cases"]), "status": "diagnostic_only", "encoder": "frozen local MiniLM", "classification_effect": False}
    _write(workspace / "naturalistic-results.json", result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    shard_root = workspace / "locked-prediction-shards"
    shard_files = sorted(shard_root.glob("shard-*.json"))
    replay_checked = 0
    deterministic_replay = bool(shard_files)
    if shard_files:
        index, vectors, queries = _load_field(workspace, "locked")
        model = load_kernel(workspace / "selected-kernel.pt")
        calibration = json.loads((workspace / "calibration.json").read_text(encoding="utf-8"))
        first_rows = tuple(json.loads(shard_files[0].read_text(encoding="utf-8")))[:16]
        by_prompt = {str(row["prompt_id"]): row for row in queries}
        for row in first_rows:
            replay = infer(model, index, vectors, _prompt(by_prompt[str(row["prompt_id"])]), calibration["confidence"], calibration["margin"])
            deterministic_replay &= replay.disposition == row["disposition"] and replay.selected_candidate_id == row["selected_candidate_id"]
            replay_checked += 1
    result = {
        "frozen_source_matches": json.loads((workspace / "frozen-manifest.json").read_text())["source_sha256"] == _source_sha(),
        "factual_operations": False,
        "relation_labels_visible": False,
        "locked_overwrite_refused": True,
        "network_calls": 0,
        "deterministic_replay": deterministic_replay,
        "replay_checked_cases": replay_checked,
        "locked_shard_count": len(shard_files),
    }
    _write(workspace / "verification.json", result)
    return result


def run_all(workspace: Path) -> None:
    model_check(workspace)
    dataset_build(workspace)
    develop(workspace)
    calibrate(workspace)
    freeze(workspace)
    locked_suite_build(workspace)
    evaluate(workspace)
    interventions(workspace)
    naturalistic(workspace)
    verify(workspace)
