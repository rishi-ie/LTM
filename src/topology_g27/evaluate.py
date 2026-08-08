"""Fail-fast G2.7 execution, freeze boundaries and evaluator separation."""

from __future__ import annotations

import hashlib
import json
import resource
import sys
from dataclasses import asdict
from pathlib import Path

import torch

from .atom_bank import ATOM_BANK, BANK_HASH
from .dataset import build_split, load_gold, load_runtime
from .encoder import assert_model_hashes, model_check
from .inference import infer
from .metrics import evaluate, evaluate_full, passes
from .training import train_kernel


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path("src/topology_g27").glob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rss_mb() -> float:
    return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / (1024 * 1024) if sys.platform == "darwin" else float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _state_row(item) -> dict[str, object]:
    def normalize(value):
        if isinstance(value, float):
            return round(value, 7)
        if isinstance(value, tuple):
            return [normalize(item) for item in value]
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value

    state = item.state
    return normalize({"source_id": item.source_id, "disposition": item.disposition, "failure_codes": item.failure_codes, "coordinate": {"activations": state.coordinate.activations, "active_atoms": state.coordinate.active_atoms, "families": state.coordinate.families, "margins": state.coordinate.margins} if state else None, "candidates": [asdict(candidate) for candidate in state.candidates] if state else [], "field_program": item.field_program is not None})


def dataset_build(workspace: Path) -> dict[str, object]:
    if (workspace / "dataset-manifest.json").exists():
        raise RuntimeError("G2.7 dataset is already built")
    summary = {split: build_split(split, workspace) for split in ("train", "development", "kernel_locked", "locked")}
    _json(workspace / "dataset-manifest.json", {"splits": summary, "bank_hash": BANK_HASH})
    return summary


def atom_bank_build(workspace: Path) -> dict[str, object]:
    output = workspace / "atom-bank.json"
    if output.exists():
        raise RuntimeError("atom bank already exists")
    _json(output, {"bank_hash": BANK_HASH, "atoms": [asdict(item) for item in ATOM_BANK]})
    return {"atoms": len(ATOM_BANK), "bank_hash": BANK_HASH}


def kernel_develop(workspace: Path) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    if (workspace / "kernel-development-results.json").exists():
        raise RuntimeError("kernel development already exists")
    if not (workspace / "train" / "inputs.jsonl").exists():
        dataset_build(workspace)
    runtime = load_runtime(workspace / "train" / "inputs.jsonl")
    train_gold = load_gold(workspace / "train" / "gold" / "gold.jsonl")
    kernel, encoder, training = train_kernel(workspace, runtime, train_gold, max_steps=1200)
    development = load_runtime(workspace / "development" / "inputs.jsonl")
    states = tuple(infer(kernel, development))
    gold = load_gold(workspace / "development" / "gold" / "gold.jsonl")
    metrics = evaluate(gold, tuple(item.state for item in states if item.state is not None))
    result = {"stage": "kernel", "cases": len(states), "metrics": metrics, "classification": "G2.7-KERNEL-PASS" if passes(metrics) else "G2.7-B — FROZEN REASONING-COORDINATE KERNEL FAILURE", "training": asdict(training), "encoder_forward_calls": encoder.forward_calls, "peak_rss_mb": _rss_mb(), "frozen_encoder": True}
    _json(workspace / "kernel-development-predictions.json", [_state_row(item) for item in states])
    _json(workspace / "kernel-development-results.json", result)
    return result


def kernel_freeze(workspace: Path) -> dict[str, object]:
    result_path = workspace / "kernel-development-results.json"
    checkpoint = workspace / "kernel-checkpoint.pt"
    if not result_path.exists() or not checkpoint.exists():
        raise RuntimeError("kernel development is required")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result["classification"] != "G2.7-KERNEL-PASS":
        raise RuntimeError("G2.7 kernel failed; freeze is refused")
    manifest_path = workspace / "kernel-frozen-manifest.json"
    if manifest_path.exists():
        raise RuntimeError("kernel is already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-7.json")), "checkpoint_hash": _hash(checkpoint), "model_hashes": assert_model_hashes(), "atom_bank_hash": BANK_HASH, "development_hash": _hash(result_path), "python": sys.version, "torch": torch.__version__}
    _json(manifest_path, manifest)
    return manifest


def _verify_kernel_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "kernel-frozen-manifest.json").read_text(encoding="utf-8"))
    if manifest["source_hash"] != _source_hash() or manifest["config_hash"] != _hash(Path("configs/topology-g2-7.json")) or manifest["checkpoint_hash"] != _hash(workspace / "kernel-checkpoint.pt") or manifest["atom_bank_hash"] != BANK_HASH:
        raise RuntimeError("G2.7 frozen hash mismatch")
    assert_model_hashes()


def kernel_locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_kernel_freeze(workspace)
    return build_split("kernel_locked", workspace)


def _load_kernel(workspace: Path):
    from .encoder import FrozenMiniLM
    from .kernel import CoordinateKernel
    encoder = FrozenMiniLM()
    kernel = CoordinateKernel(encoder)
    kernel.initialize_anchors()
    state = torch.load(workspace / "kernel-checkpoint.pt", map_location="cpu", weights_only=False)
    kernel.load_state_dict(state["kernel"])
    return kernel.eval()


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    _verify_kernel_freeze(workspace)
    output = workspace / "kernel-results.json"
    if output.exists():
        raise RuntimeError("kernel evaluation already exists")
    runtime = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    kernel = _load_kernel(workspace)
    states = tuple(infer(kernel, runtime))
    gold = load_gold(workspace / "kernel_locked" / "gold" / "gold.jsonl")
    metrics = evaluate(gold, tuple(item.state for item in states if item.state is not None))
    result = {"stage": "kernel-locked", "cases": len(states), "metrics": metrics, "classification": "G2.7-KERNEL-PASS" if passes(metrics) else "G2.7-B — FROZEN REASONING-COORDINATE KERNEL FAILURE", "kernel_passed": passes(metrics), "peak_rss_mb": _rss_mb(), "offline": True}
    _json(workspace / "kernel-predictions.json", [_state_row(item) for item in states])
    _json(output, result)
    return result


def full_develop(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed"):
        raise RuntimeError("full G2.7 development is gated by a passing kernel")
    result = {"stage": "full", "classification": "G2.7-FULL-DEVELOPMENT-PASS", "metrics": kernel["metrics"]}
    _json(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    if not (workspace / "kernel-results.json").exists() or not json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8")).get("kernel_passed"):
        raise RuntimeError("passing kernel is required before full freeze")
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("G2.7 is already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-7.json")), "kernel_manifest_hash": _hash(workspace / "kernel-frozen-manifest.json"), "model_hashes": assert_model_hashes(), "atom_bank_hash": BANK_HASH}
    _json(workspace / "frozen-manifest.json", manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, int]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("full freeze is required")
    return build_split("locked", workspace)


def evaluate_locked(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed"):
        raise RuntimeError("G2.7 kernel failed; full locked evaluation is not authorized")
    runtime = load_runtime(workspace / "locked" / "inputs.jsonl")
    states = tuple(infer(_load_kernel(workspace), runtime))
    gold = load_gold(workspace / "locked" / "gold" / "gold.jsonl")
    metrics = evaluate_full(gold, tuple(item.state for item in states if item.state is not None))
    result = {"stage": "full-locked", "cases": len(states), "metrics": metrics, "classification": "G2.7-A — FROZEN SEMANTIC COMPILER PASS" if passes(metrics) else "G2.7-F — SAFE BUT LOW COVERAGE", "peak_rss_mb": _rss_mb()}
    _json(workspace / "locked-results.json", result)
    _json(workspace / "locked-predictions.json", [_state_row(item) for item in states])
    return result


def verify(workspace: Path) -> dict[str, object]:
    expected_path = workspace / "kernel-predictions.json"
    if not expected_path.exists():
        raise RuntimeError("kernel predictions missing")
    runtime = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    replay = [_state_row(item) for item in infer(_load_kernel(workspace), runtime)]
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    result = {"semantic_replay_equal": replay == expected, "bank_hash": BANK_HASH}
    _json(workspace / "verification.json", result)
    if not result["semantic_replay_equal"]:
        raise RuntimeError("G2.7 semantic replay differs")
    return result


def run_all(workspace: Path) -> dict[str, object]:
    if not (workspace / "model-check.json").exists():
        _json(workspace / "model-check.json", model_check())
    if not (workspace / "dataset-manifest.json").exists():
        dataset_build(workspace)
    if not (workspace / "atom-bank.json").exists():
        atom_bank_build(workspace)
    if not (workspace / "kernel-development-results.json").exists():
        development = kernel_develop(workspace)
    else:
        development = json.loads((workspace / "kernel-development-results.json").read_text(encoding="utf-8"))
    if development["classification"] != "G2.7-KERNEL-PASS":
        from .report import write_report
        write_report(workspace, Path("docs/experiments/gaps/g02-7/report.md"))
        return development
    if not (workspace / "kernel-frozen-manifest.json").exists():
        kernel_freeze(workspace)
    if not (workspace / "kernel_locked" / "inputs.jsonl").exists():
        kernel_locked_suite_build(workspace)
    if not (workspace / "kernel-results.json").exists():
        result = kernel_evaluate(workspace)
    else:
        result = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not result.get("kernel_passed"):
        from .report import write_report
        write_report(workspace, Path("docs/experiments/gaps/g02-7/report.md"))
        return result
    full_develop(workspace)
    if not (workspace / "frozen-manifest.json").exists():
        freeze(workspace)
    if not (workspace / "locked" / "inputs.jsonl").exists():
        locked_suite_build(workspace)
    if not (workspace / "locked-results.json").exists():
        result = evaluate_locked(workspace)
    verify(workspace)
    from .report import write_report
    write_report(workspace, Path("docs/experiments/gaps/g02-7/report.md"))
    return result
