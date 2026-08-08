"""Development/freeze/locked orchestration with single-use locked artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import resource
from dataclasses import asdict
from pathlib import Path

import torch

from .compiler import AtomTopologyCompiler
from .dataset import build_split, generate_examples
from .encoder import model_check
from .inference import compile_examples
from .metrics import classification, score
from .training import train_compiler


def _atomic(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def develop(workspace: Path, *, limit: int | None = None) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development is frozen")
    workspace.mkdir(parents=True, exist_ok=True)
    _atomic(workspace / "model-check.json", model_check())
    build_split("train", workspace)
    build_split("development", workspace)
    frozen, frozen_summary = train_compiler(encoder_trainable=False, limit=limit)
    tuned, tuned_summary = train_compiler(encoder_trainable=True, limit=limit)
    dev = generate_examples("development")
    if limit is not None:
        dev = dev[: max(64, min(len(dev), limit // 2))]
    frozen_results = compile_examples(frozen, dev)
    tuned_results = compile_examples(tuned, dev)
    frozen_metrics = score(dev, frozen_results)
    tuned_metrics = score(dev, tuned_results)
    winner = "tuned" if (tuned_metrics["all_case_exactness"], tuned_metrics["accepted_safe_coverage"]) >= (frozen_metrics["all_case_exactness"], frozen_metrics["accepted_safe_coverage"]) else "frozen"
    torch.save(frozen.state_dict(), workspace / "frozen-control.pt")
    torch.save(tuned.state_dict(), workspace / "tuned.pt")
    payload: dict[str, object] = {
        "training": {"frozen": asdict(frozen_summary), "tuned": asdict(tuned_summary)},
        "metrics": {"frozen": frozen_metrics, "tuned": tuned_metrics},
        "selected": winner,
        "development_cases": len(dev),
    }
    _atomic(workspace / "development-results.json", payload)
    return payload


def freeze(workspace: Path) -> dict[str, object]:
    result = workspace / "development-results.json"
    if not result.exists():
        raise RuntimeError("development must complete before freeze")
    manifest = {"workspace_hash": _hash_tree(workspace), "python": os.sys.version, "torch": torch.__version__}
    _atomic(workspace / "frozen-manifest.json", manifest)
    return manifest


def locked_suite_build(workspace: Path) -> dict[str, int]:
    if not (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("freeze required")
    if (workspace / "locked" / "sentence-inputs.jsonl").exists():
        raise RuntimeError("locked suite already exists")
    return build_split("locked", workspace)


def evaluate(workspace: Path, *, limit: int | None = None) -> dict[str, object]:
    if not (workspace / "frozen-manifest.json").exists() or not (workspace / "locked" / "sentence-inputs.jsonl").exists():
        raise RuntimeError("frozen locked suite required")
    output = workspace / "locked-results.json"
    if output.exists():
        raise RuntimeError("locked evaluation already exists")
    selected = json.loads((workspace / "development-results.json").read_text())["selected"]
    model = AtomTopologyCompiler(encoder_trainable=(selected == "tuned"))
    model.load_state_dict(torch.load(workspace / ("tuned.pt" if selected == "tuned" else "frozen-control.pt"), map_location="cpu", weights_only=True))
    cases = generate_examples("locked")
    if limit is not None:
        cases = cases[:limit]
    results = compile_examples(model, cases)
    measurements = score(cases, results)
    payload: dict[str, object] = {
        "selected": selected,
        "metrics": measurements,
        "classification": classification(measurements),
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "cases": len(cases),
    }
    _atomic(workspace / "locked-results.json", payload)
    _atomic(workspace / "locked-predictions.json", [{"source_id": value.source_id, "disposition": value.disposition} for value in results])
    return payload
