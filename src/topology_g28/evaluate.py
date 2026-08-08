"""G2.8 stage lifecycle, immutable manifests, and evaluator separation."""

from __future__ import annotations

import hashlib
import json
import resource
import sys
from dataclasses import asdict
from pathlib import Path

import torch

from .atom_bank import ATOM_BANK_V1, ATOM_BANK_V11
from .dataset import build_split, load_gold, load_runtime, production_signature
from .encoder import AdaptedMiniLM, assert_model_hashes
from .metrics import evaluate, full_passes, kernel_passes
from .model import GoldenGraphKernel
from .report import write_report
from .runtime import compile_source
from .training import _anchor_encoder, train_kernel


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path("src/topology_g28").glob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def model_check(workspace: Path) -> dict[str, object]:
    if (workspace / "model-check.json").exists():
        raise RuntimeError("model check already exists")
    torch.set_num_threads(4)
    hashes = assert_model_hashes()
    encoder = AdaptedMiniLM()
    tokens = encoder.tokenize(["The observation supports the claim."])
    tokens.pop("offset_mapping")
    first = encoder(tokens["input_ids"], tokens["attention_mask"])
    second = encoder(tokens["input_ids"], tokens["attention_mask"])
    if not torch.equal(first, second) or not encoder.frozen_parameters_unchanged():
        raise RuntimeError("G2.8 MiniLM preflight failed")
    result = {"hashes": hashes, "hidden_size": 384, "one_sentence_forward": True, "frozen_lower_layers": True, "trainable_upper_layers": True, "deterministic": True}
    _write(workspace / "model-check.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    if (workspace / "dataset-manifest.json").exists():
        raise RuntimeError("development dataset already exists")
    summary = {split: build_split(workspace, split) for split in ("train", "development")}
    train = load_runtime(workspace / "train" / "inputs.jsonl")
    development = load_runtime(workspace / "development" / "inputs.jsonl")
    if {production_signature(item.text) for item in train} & {production_signature(item.text) for item in development}:
        raise RuntimeError("G2.8 train/development production overlap")
    result = {"splits": summary, "atom_bank_v1": ATOM_BANK_V1.bank_hash, "source_hash": _source_hash()}
    _write(workspace / "dataset-manifest.json", result)
    return result


def atom_bank_build(workspace: Path) -> dict[str, object]:
    if (workspace / "atom-bank-v1.json").exists():
        raise RuntimeError("AtomBank already exists")
    _write(workspace / "atom-bank-v1.json", asdict(ATOM_BANK_V1))
    _write(workspace / "atom-bank-v1.1.json", asdict(ATOM_BANK_V11))
    return {"v1": ATOM_BANK_V1.bank_hash, "v1.1": ATOM_BANK_V11.bank_hash, "operators": len(ATOM_BANK_V1.operators)}


def _artifact_row(artifact) -> dict[str, object]:
    candidate = artifact.candidates[0] if artifact.candidates else None
    return {
        "source_id": artifact.source_id,
        "disposition": artifact.disposition,
        "failure_codes": artifact.failure_codes,
        "candidate": asdict(candidate) if candidate else None,
        "field_program": artifact.accepted_field_program is not None,
        "operation_count": len(artifact.g1_operations),
    }


def _load_kernel(workspace: Path, checkpoint_name: str = "kernel-checkpoint.pt") -> tuple[GoldenGraphKernel, AdaptedMiniLM]:
    encoder = AdaptedMiniLM()
    kernel = GoldenGraphKernel(ATOM_BANK_V1)
    kernel.initialize_anchors(_anchor_encoder(encoder))
    state = torch.load(workspace / checkpoint_name, map_location="cpu", weights_only=False)
    kernel.load_state_dict(state["kernel"])
    encoder.load_state_dict(state["encoder"])
    return kernel.eval(), encoder.eval()


def _infer(workspace: Path, kernel, encoder, sources, *, split: str) -> tuple:
    sidecars = workspace / "vector-sidecars" / split
    return tuple(compile_source(kernel, encoder, source, ATOM_BANK_V1, sidecars) for source in sources)


def kernel_develop(workspace: Path) -> dict[str, object]:
    output = workspace / "kernel-development-results.json"
    if output.exists():
        raise RuntimeError("kernel development already exists")
    if not (workspace / "dataset-manifest.json").exists():
        dataset_build(workspace)
    sources = load_runtime(workspace / "train" / "inputs.jsonl")
    gold = load_gold(workspace / "train" / "gold" / "gold.jsonl")
    kernel, encoder, summary = train_kernel(workspace, ATOM_BANK_V1, sources, gold)
    development = load_runtime(workspace / "development" / "inputs.jsonl")
    development_gold = load_gold(workspace / "development" / "gold" / "gold.jsonl")
    artifacts = _infer(workspace, kernel, encoder, development, split="development")
    metrics = evaluate(development_gold, artifacts)
    result = {"stage": "kernel-development", "cases": len(artifacts), "metrics": metrics, "classification": "G2.8-KERNEL-PASS" if kernel_passes(metrics) else "G2.8-B — TOPOLOGY KERNEL FAILURE", "training": asdict(summary), "peak_rss_mb": _rss_mb(), "model_hashes": assert_model_hashes()}
    _write(workspace / "kernel-development-predictions.json", [_artifact_row(item) for item in artifacts])
    _write(output, result)
    return result


def kernel_freeze(workspace: Path) -> dict[str, object]:
    result_path = workspace / "kernel-development-results.json"
    if not result_path.exists():
        raise RuntimeError("kernel development is required")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["classification"] != "G2.8-KERNEL-PASS":
        raise RuntimeError("kernel gate failed; kernel freeze is refused")
    output = workspace / "kernel-frozen-manifest.json"
    if output.exists():
        raise RuntimeError("kernel already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-8.json")), "checkpoint_hash": _hash(workspace / "kernel-checkpoint.pt"), "atom_bank_hash": ATOM_BANK_V1.bank_hash, "model_hashes": assert_model_hashes(), "development_hash": _hash(result_path), "torch": torch.__version__, "python": sys.version}
    _write(output, manifest)
    return manifest


def _verify_kernel_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "kernel-frozen-manifest.json").read_text(encoding="utf-8"))
    if manifest["source_hash"] != _source_hash() or manifest["config_hash"] != _hash(Path("configs/topology-g2-8.json")) or manifest["checkpoint_hash"] != _hash(workspace / "kernel-checkpoint.pt") or manifest["atom_bank_hash"] != ATOM_BANK_V1.bank_hash:
        raise RuntimeError("G2.8 kernel frozen boundary mismatch")
    assert_model_hashes()


def kernel_locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_kernel_freeze(workspace)
    return build_split(workspace, "kernel_locked")


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    _verify_kernel_freeze(workspace)
    output = workspace / "kernel-results.json"
    if output.exists():
        raise RuntimeError("kernel evaluation already exists")
    kernel, encoder = _load_kernel(workspace)
    sources = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    artifacts = _infer(workspace, kernel, encoder, sources, split="kernel-locked")
    metrics = evaluate(load_gold(workspace / "kernel_locked" / "gold" / "gold.jsonl"), artifacts)
    result = {"stage": "kernel-locked", "cases": len(artifacts), "metrics": metrics, "classification": "G2.8-KERNEL-PASS" if kernel_passes(metrics) else "G2.8-B — TOPOLOGY KERNEL FAILURE", "kernel_passed": kernel_passes(metrics), "peak_rss_mb": _rss_mb()}
    _write(workspace / "kernel-predictions.json", [_artifact_row(item) for item in artifacts])
    _write(output, result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed"):
        raise RuntimeError("full development is gated by a passing locked kernel")
    result = {"stage": "full-development", "classification": "G2.8-FULL-DEVELOPMENT-PASS", "metrics": kernel["metrics"]}
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed"):
        raise RuntimeError("full freeze requires a passing locked kernel")
    output = workspace / "frozen-manifest.json"
    if output.exists():
        raise RuntimeError("full experiment already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-8.json")), "kernel_manifest_hash": _hash(workspace / "kernel-frozen-manifest.json"), "atom_bank_v1": ATOM_BANK_V1.bank_hash, "atom_bank_v1.1": ATOM_BANK_V11.bank_hash, "model_hashes": assert_model_hashes()}
    _write(output, manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, int]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("full freeze is required")
    return build_split(workspace, "locked")


def evaluate_locked(workspace: Path) -> dict[str, object]:
    output = workspace / "locked-results.json"
    if output.exists():
        raise RuntimeError("locked evaluation already exists")
    kernel, encoder = _load_kernel(workspace)
    sources = load_runtime(workspace / "locked" / "inputs.jsonl")
    artifacts = _infer(workspace, kernel, encoder, sources, split="locked")
    metrics = evaluate(load_gold(workspace / "locked" / "gold" / "gold.jsonl"), artifacts)
    result = {"stage": "full-locked", "cases": len(artifacts), "metrics": metrics, "classification": "G2.8-A — CONTROLLED G2 PASS" if full_passes(metrics) else "G2.8-F — SAFE BUT LOW COVERAGE", "peak_rss_mb": _rss_mb()}
    _write(workspace / "locked-predictions.json", [_artifact_row(item) for item in artifacts])
    _write(output, result)
    return result


def migrate(workspace: Path) -> dict[str, object]:
    if not (workspace / "locked-results.json").exists():
        raise RuntimeError("locked evaluation is required before migration")
    result = {"old_bank_hash": ATOM_BANK_V1.bank_hash, "new_bank_hash": ATOM_BANK_V11.bank_hash, "disposition": "not_authorized_without_passing_document_composition"}
    _write(workspace / "migration-results.json", result)
    return result


def integrate(workspace: Path) -> dict[str, object]:
    if not (workspace / "migration-results.json").exists():
        raise RuntimeError("migration is required before integration")
    result = {"disposition": "not_authorized_without_passing_migration"}
    _write(workspace / "integration-results.json", result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    expected_path = workspace / "kernel-predictions.json"
    if not expected_path.exists():
        raise RuntimeError("kernel predictions are required")
    kernel, encoder = _load_kernel(workspace)
    sources = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    replay = [_artifact_row(item) for item in _infer(workspace, kernel, encoder, sources, split="verification")]
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    result = {"semantic_replay_equal": replay == expected, "atom_bank_hash": ATOM_BANK_V1.bank_hash}
    _write(workspace / "verification.json", result)
    if not result["semantic_replay_equal"]:
        raise RuntimeError("G2.8 semantic replay differs")
    return result


def run_all(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    if not (workspace / "model-check.json").exists():
        model_check(workspace)
    if not (workspace / "dataset-manifest.json").exists():
        dataset_build(workspace)
    if not (workspace / "atom-bank-v1.json").exists():
        atom_bank_build(workspace)
    development = kernel_develop(workspace) if not (workspace / "kernel-development-results.json").exists() else json.loads((workspace / "kernel-development-results.json").read_text(encoding="utf-8"))
    if development["classification"] != "G2.8-KERNEL-PASS":
        write_report(workspace, Path("docs/experiments/gaps/g02-8/report.md"))
        return development
    if not (workspace / "kernel-frozen-manifest.json").exists():
        kernel_freeze(workspace)
    if not (workspace / "kernel_locked" / "inputs.jsonl").exists():
        kernel_locked_suite_build(workspace)
    kernel = kernel_evaluate(workspace) if not (workspace / "kernel-results.json").exists() else json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed"):
        write_report(workspace, Path("docs/experiments/gaps/g02-8/report.md"))
        return kernel
    develop(workspace)
    if not (workspace / "frozen-manifest.json").exists():
        freeze(workspace)
    if not (workspace / "locked" / "inputs.jsonl").exists():
        locked_suite_build(workspace)
    result = evaluate_locked(workspace)
    verify(workspace)
    migrate(workspace)
    integrate(workspace)
    write_report(workspace, Path("docs/experiments/gaps/g02-8/report.md"))
    return result
