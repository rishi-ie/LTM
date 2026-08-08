"""Fail-fast staged G2.6 execution with immutable freeze boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch

from .dataset import build_split, evaluator_gold, generate_examples, load_runtime
from .encoder import OnePassMiniLM, assert_model_hashes, model_check
from .inference import infer_examples, infer_runtime
from .metrics import evaluate, passes
from .model import JointCandidateScorer
from .report import write_report
from .training import train_kernel


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path("src/topology_g26").glob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024) if os.sys.platform == "darwin" else value / 1024


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _prediction_row(prediction: object) -> dict[str, object]:
    value = asdict(prediction)
    value["candidate"]["role_bindings"] = [list(item) for item in value["candidate"]["role_bindings"]]
    return value


def develop(workspace: Path, *, limit: int | None = None) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("G2.6 development is frozen")
    workspace.mkdir(parents=True, exist_ok=True)
    _json(workspace / "model-check.json", model_check())
    build_split("train", workspace)
    build_split("development", workspace)
    examples = generate_examples("train")
    if limit is not None:
        examples = examples[: max(32, limit)]
    model, encoder, summary = train_kernel(workspace, examples, max_steps=1200 if limit is None else min(20, max(4, limit)))
    development = generate_examples("development")
    if limit is not None:
        development = development[: max(32, limit)]
    runtime = load_runtime(workspace / "development" / "inputs.jsonl")[: len(development)]
    predictions = infer_examples(model, encoder, runtime)
    gold = evaluator_gold("development")[: len(predictions)]
    metrics = evaluate(gold, predictions)
    payload = {"stage": "kernel", "training": asdict(summary), "metrics": metrics, "cases": len(predictions), "limited": limit is not None, "peak_rss_mb": _rss_mb(), "classification": "G2.6-KERNEL-PASS" if passes(metrics) else "G2.6-B — JOINT ROUTING KERNEL FAILURE"}
    _json(workspace / "development-results.json", payload)
    _json(workspace / "development-predictions.json", [_prediction_row(item) for item in predictions])
    return payload


def freeze(workspace: Path) -> dict[str, object]:
    development = workspace / "development-results.json"
    checkpoint = workspace / "kernel-checkpoint.pt"
    if not development.exists() or not checkpoint.exists(): raise RuntimeError("complete development is required before freeze")
    result = json.loads(development.read_text(encoding="utf-8"))
    if result.get("limited"): raise RuntimeError("limited development cannot be frozen")
    if result.get("classification") != "G2.6-KERNEL-PASS":
        raise RuntimeError("G2.6 kernel failed; freeze and locked execution are refused")
    manifest_path = workspace / "frozen-manifest.json"
    if manifest_path.exists(): raise RuntimeError("G2.6 is already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(Path("configs/topology-g2-6.json")), "checkpoint_hash": _hash(checkpoint), "model_hashes": assert_model_hashes(), "development_hash": _hash(development), "python": sys.version, "torch": torch.__version__, "seeds": {"train": 1760, "development": 1761, "locked": 20260825}, "gates": {"accepted_precision": 0.95, "safe_coverage": 0.90}}
    _json(manifest_path, manifest)
    return manifest


def _verify_freeze(workspace: Path) -> dict[str, object]:
    path = workspace / "frozen-manifest.json"
    if not path.exists(): raise RuntimeError("freeze required")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["source_hash"] != _source_hash() or manifest["config_hash"] != _hash(Path("configs/topology-g2-6.json")) or manifest["checkpoint_hash"] != _hash(workspace / "kernel-checkpoint.pt"): raise RuntimeError("G2.6 frozen hash mismatch")
    assert_model_hashes()
    return manifest


def kernel_locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_freeze(workspace)
    if (workspace / "kernel_locked" / "inputs.jsonl").exists(): raise RuntimeError("kernel locked suite already exists")
    return build_split("kernel_locked", workspace)


def locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_freeze(workspace)
    if (workspace / "locked" / "inputs.jsonl").exists(): raise RuntimeError("locked suite already exists")
    return build_split("locked", workspace)


def _load_checkpoint(workspace: Path) -> tuple[JointCandidateScorer, OnePassMiniLM]:
    model = JointCandidateScorer()
    encoder = OnePassMiniLM(trainable=False)
    state = torch.load(workspace / "kernel-checkpoint.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(state["model"])
    encoder.load_state_dict(state["encoder"])
    model.eval(); encoder.eval()
    return model, encoder


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    _verify_freeze(workspace)
    output = workspace / "kernel-results.json"
    if output.exists(): raise RuntimeError("locked kernel evaluation already exists")
    runtime = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    model, encoder = _load_checkpoint(workspace)
    started = time.perf_counter()
    predictions = infer_runtime(model, encoder, runtime)
    metrics = evaluate(evaluator_gold("kernel_locked"), predictions)
    payload = {"cases": len(predictions), "metrics": metrics, "classification": "G2.6-KERNEL-PASS" if passes(metrics) else "G2.6-B — JOINT ROUTING KERNEL FAILURE", "kernel_passed": passes(metrics), "runtime_ms": (time.perf_counter() - started) * 1000, "peak_rss_mb": _rss_mb(), "offline": True}
    _json(workspace / "kernel-predictions.json", [_prediction_row(item) for item in predictions])
    _json(output, payload)
    return payload


def evaluate_locked(workspace: Path) -> dict[str, object]:
    kernel = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    if not kernel.get("kernel_passed", False):
        raise RuntimeError("G2.6 kernel failed; full compilation is intentionally not run")
    raise NotImplementedError("full span/document stages are gated behind a passing kernel")


def verify(workspace: Path) -> dict[str, object]:
    _verify_freeze(workspace)
    predictions = workspace / "kernel-predictions.json"
    if not predictions.exists(): raise RuntimeError("locked predictions missing")
    runtime = load_runtime(workspace / "kernel_locked" / "inputs.jsonl")
    model, encoder = _load_checkpoint(workspace)
    replay = [_prediction_row(item) for item in infer_runtime(model, encoder, runtime)]
    expected = json.loads(predictions.read_text(encoding="utf-8"))
    result = {"semantic_replay_equal": replay == expected, "predictions_hash": hashlib.sha256(json.dumps(replay, sort_keys=True).encode()).hexdigest()}
    _json(workspace / "verification.json", result)
    if not result["semantic_replay_equal"]: raise RuntimeError("G2.6 semantic replay differs")
    return result


def run_all(workspace: Path, *, limit: int | None = None) -> dict[str, object]:
    if not (workspace / "development-results.json").exists():
        development = develop(workspace, limit=limit)
    else:
        development = json.loads((workspace / "development-results.json").read_text(encoding="utf-8"))
    if development.get("classification") != "G2.6-KERNEL-PASS":
        write_report(workspace, Path("docs/experiments/gaps/g02-6/report.md"))
        return development
    if not (workspace / "frozen-manifest.json").exists(): freeze(workspace)
    if not (workspace / "kernel_locked" / "inputs.jsonl").exists(): kernel_locked_suite_build(workspace)
    if not (workspace / "kernel-results.json").exists(): result = kernel_evaluate(workspace)
    else: result = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    verify(workspace)
    _json(workspace / "locked-results.json", result)
    return result
