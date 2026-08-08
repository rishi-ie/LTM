"""Atomic, fail-fast orchestration for the G2.5 representation kernel."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy
import torch

from .dataset import build_kernel_split, generate_kernel_examples, load_kernel_runtime_cases
from .encoder import assert_model_hashes, model_check
from .inference import infer_kernel
from .metrics import kernel_metrics, kernel_pass
from .model import TypedAtomKernel
from .schemas import KernelPrediction
from .training import train_kernel


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _hash_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def _source_hash() -> str:
    root = Path("src/topology_g25")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def _prediction_record(prediction: KernelPrediction) -> dict[str, Any]:
    return {
        "source_id": prediction.source_id,
        "relation_type": prediction.relation_type,
        "role_bindings": prediction.role_bindings,
        "polarity": prediction.polarity,
        "modality": prediction.modality,
        "scope_id": prediction.scope_id,
        "disposition": prediction.disposition,
        "confidence": prediction.confidence,
        "factor_hash": prediction.factor.factor_hash if prediction.factor else None,
        "sparse_incidence": prediction.factor.sparse_incidence if prediction.factor else (),
    }


def kernel_develop(workspace: Path, *, limit: int | None = None) -> dict[str, Any]:
    if (workspace / "kernel-frozen-manifest.json").exists():
        raise RuntimeError("kernel development is frozen")
    workspace.mkdir(parents=True, exist_ok=True)
    _atomic_json(workspace / "model-check.json", model_check())
    build_kernel_split("train", workspace)
    build_kernel_split("development", workspace)
    model, summary = train_kernel(workspace, limit=limit)
    development = generate_kernel_examples("development")
    if limit is not None:
        development = development[: min(len(development), max(32, limit // 4))]
    from .schemas import KernelRuntimeCase

    runtime = tuple(KernelRuntimeCase(item.source, item.atoms) for item in development)
    predictions = infer_kernel(model, runtime)
    metrics = kernel_metrics(development, predictions)
    payload: dict[str, Any] = {
        "training": asdict(summary),
        "metrics": metrics,
        "development_cases": len(development),
        "limited": limit is not None,
        "peak_rss_mb": _rss_mb(),
    }
    _atomic_json(workspace / "development-results.json", payload)
    _atomic_json(
        workspace / "development-predictions.json",
        [_prediction_record(item) for item in predictions],
    )
    return payload


def kernel_freeze(workspace: Path) -> dict[str, Any]:
    development = workspace / "development-results.json"
    checkpoint = workspace / "kernel-checkpoint.pt"
    if not development.exists() or not checkpoint.exists():
        raise RuntimeError("complete kernel development is required before freeze")
    result = json.loads(development.read_text(encoding="utf-8"))
    if result["limited"]:
        raise RuntimeError("a smoke-limited development run cannot be frozen")
    if (workspace / "kernel-frozen-manifest.json").exists():
        raise RuntimeError("kernel is already frozen")
    config = Path("configs/topology-g2-5.json")
    manifest = {
        "source_hash": _source_hash(),
        "config_hash": _hash_file(config),
        "checkpoint_hash": _hash_file(checkpoint),
        "model_hashes": assert_model_hashes(),
        "development_hash": _hash_file(development),
        "python": sys.version,
        "numpy": numpy.__version__,
        "torch": torch.__version__,
        "seeds": {"training": 1748, "development": 1749, "kernel_locked": 20260818},
    }
    _atomic_json(workspace / "kernel-frozen-manifest.json", manifest)
    return manifest


def _verify_kernel_freeze(workspace: Path) -> dict[str, Any]:
    manifest_path = workspace / "kernel-frozen-manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("kernel freeze required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "source_hash": _source_hash(),
        "config_hash": _hash_file(Path("configs/topology-g2-5.json")),
        "checkpoint_hash": _hash_file(workspace / "kernel-checkpoint.pt"),
    }
    if any(manifest[key] != value for key, value in checks.items()):
        raise RuntimeError("frozen kernel manifest no longer matches source, config, or checkpoint")
    assert_model_hashes()
    return manifest


def kernel_locked_suite_build(workspace: Path) -> dict[str, int]:
    _verify_kernel_freeze(workspace)
    public = workspace / "kernel_locked" / "kernel-inputs.jsonl"
    if public.exists():
        raise RuntimeError("kernel locked suite already exists")
    return build_kernel_split("kernel_locked", workspace)


def _load_kernel_model(workspace: Path) -> TypedAtomKernel:
    from .encoder import OnePassMiniLM

    model = TypedAtomKernel(OnePassMiniLM(trainable=False))
    state = torch.load(workspace / "kernel-checkpoint.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(state["model"])
    model.eval()
    return model


def kernel_evaluate(workspace: Path, *, batch_size: int = 16) -> dict[str, Any]:
    _verify_kernel_freeze(workspace)
    inputs = workspace / "kernel_locked" / "kernel-inputs.jsonl"
    output = workspace / "kernel-results.json"
    if not inputs.exists():
        raise RuntimeError("kernel locked suite must be generated before evaluation")
    if output.exists():
        raise RuntimeError("kernel locked evaluation already exists")
    # Runtime reads the public file only.  Gold is generated in a subsequent
    # evaluator-only phase; inference has no label-bearing argument.
    runtime = load_kernel_runtime_cases(inputs)
    predictions = infer_kernel(_load_kernel_model(workspace), runtime, batch_size=batch_size)
    _atomic_json(
        workspace / "kernel-predictions.json", [_prediction_record(item) for item in predictions]
    )
    evaluator_gold = generate_kernel_examples("kernel_locked")
    metrics = kernel_metrics(evaluator_gold, predictions)
    passed = kernel_pass(metrics)
    payload: dict[str, Any] = {
        "cases": len(predictions),
        "metrics": metrics,
        "classification": "G2.5-KERNEL-PASS"
        if passed
        else "G2.5-C — REPRESENTATION KERNEL FAILURE",
        "representation_kernel_passed": passed,
        "peak_rss_mb": _rss_mb(),
        "offline": True,
    }
    _atomic_json(output, payload)
    return payload


def verify_kernel(workspace: Path) -> dict[str, Any]:
    """Deterministic replay without rewriting locked outputs."""
    _verify_kernel_freeze(workspace)
    original = workspace / "kernel-predictions.json"
    if not original.exists():
        raise RuntimeError("kernel locked predictions are absent")
    replay = [
        _prediction_record(item)
        for item in infer_kernel(
            _load_kernel_model(workspace),
            load_kernel_runtime_cases(workspace / "kernel_locked" / "kernel-inputs.jsonl"),
        )
    ]
    expected = json.loads(original.read_text(encoding="utf-8"))
    # Persisted JSON turns tuples into lists.  The contract is semantic output,
    # not an implementation-specific Python container type.
    canonical_replay = json.loads(json.dumps(replay, sort_keys=True))
    payload = {
        "semantic_replay_equal": canonical_replay == expected,
        "predictions_hash": hashlib.sha256(
            json.dumps(canonical_replay, sort_keys=True).encode()
        ).hexdigest(),
    }
    _atomic_json(workspace / "kernel-verification.json", payload)
    if not payload["semantic_replay_equal"]:
        raise RuntimeError("kernel replay differs from frozen locked predictions")
    return payload


def run_kernel_all(workspace: Path) -> dict[str, Any]:
    """Resume only at the first uncompleted fail-fast stage."""
    if not (workspace / "development-results.json").exists():
        kernel_develop(workspace)
    if not (workspace / "kernel-frozen-manifest.json").exists():
        kernel_freeze(workspace)
    if not (workspace / "kernel_locked" / "kernel-inputs.jsonl").exists():
        kernel_locked_suite_build(workspace)
    if not (workspace / "kernel-results.json").exists():
        result = kernel_evaluate(workspace)
    else:
        result = json.loads((workspace / "kernel-results.json").read_text(encoding="utf-8"))
    verify_kernel(workspace)
    return result
