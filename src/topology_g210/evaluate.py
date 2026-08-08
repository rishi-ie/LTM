"""Frozen two-stage lifecycle for G2.10."""

from __future__ import annotations

import hashlib
import json
import resource
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import torch

from .dataset import build_split, load_gold, load_runtime, production_signature
from .encoder import AdaptedMiniLM, assert_model_hashes
from .metrics import passes, score
from .model import BehavioralCompiler
from .runtime import compile_source
from .topology import CELLS, SIGNATURE_WIDTH, signature, signature_digest
from .training import train

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-10.json"


def config() -> dict:
    return json.loads(CONFIG.read_text())


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "src" / "topology_g210").glob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name); json.dump(value, handle, indent=2, sort_keys=True, default=str); handle.write("\n")
    temporary.replace(path)


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def representation_check(workspace: Path) -> dict[str, object]:
    destination = workspace / "representation-check.json"
    if destination.exists(): raise RuntimeError("representation check already exists")
    rows = {cell.cell_id: signature(cell) for cell in CELLS}
    distances = [float(((rows[left.cell_id] - rows[right.cell_id]) ** 2).mean() ** .5) for index, left in enumerate(CELLS) for right in CELLS[index + 1 :]]
    result = {"cells": len(CELLS), "signature_width": SIGNATURE_WIDTH, "digests": {cell.cell_id: signature_digest(cell) for cell in CELLS}, "minimum_pairwise_rms": min(distances), "passed": min(distances) >= config()["gates"]["representation_distance"]}
    _write(destination, result)
    if not result["passed"]: raise RuntimeError("G2.10 behavioral cells are not separable")
    return result


def model_check(workspace: Path) -> dict[str, object]:
    output = workspace / "model-check.json"
    if output.exists(): raise RuntimeError("model check already exists")
    torch.set_num_threads(4); hashes = assert_model_hashes(); encoder = AdaptedMiniLM().eval(); head = BehavioralCompiler().eval()
    tokens = encoder.tokenize(["claim_A claim_B."]); tokens.pop("offset_mapping"); extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    first = encoder(tokens["input_ids"], tokens["attention_mask"], **extra); second = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    masks = torch.zeros((1, 2, first.shape[1]), dtype=torch.bool); masks[:, 0, 1] = True; masks[:, 1, 2] = True
    output_head = head(first, tokens["attention_mask"], masks)
    if not torch.equal(first, second) or first.shape[-1] != 384 or output_head["signature"].shape[-1] != SIGNATURE_WIDTH or not encoder.lower_layers_frozen(): raise RuntimeError("G2.10 model preflight failed")
    result = {"hashes": hashes, "hidden_size": 384, "one_sentence_forward": True, "lower_layers_frozen": True, "signature_width": SIGNATURE_WIDTH}
    _write(output, result); return result


def dataset_build(workspace: Path) -> dict[str, object]:
    output = workspace / "dataset-manifest.json"
    if output.exists(): raise RuntimeError("dataset already exists")
    summary = {split: build_split(workspace, split) for split in ("train", "development")}
    train_signatures = {production_signature(item.text) for item in load_runtime(workspace / "train" / "inputs.jsonl")}
    development_signatures = {production_signature(item.text) for item in load_runtime(workspace / "development" / "inputs.jsonl")}
    if train_signatures & development_signatures: raise RuntimeError("train/development production overlap")
    result = {"splits": summary, "source_hash": _source_hash(), "config_hash": _hash(CONFIG), "registry_cells": [cell.cell_id for cell in CELLS]}
    _write(output, result); return result


def _load(workspace: Path, checkpoint: str):
    encoder = AdaptedMiniLM(); model = BehavioralCompiler(); saved = torch.load(workspace / checkpoint, map_location="cpu", weights_only=False)
    encoder.load_state_dict(saved["encoder"]); model.load_state_dict(saved["model"])
    return model.eval(), encoder.eval()


def _infer(workspace: Path, model, encoder, sources, *, supplied: bool, stage: str, thresholds: dict[str, float] | None = None):
    settings = thresholds or {"distance": .2, "margin": .01, "port": .5}
    return tuple(compile_source(model, encoder, source, workspace / "vector-sidecars" / stage, supplied=supplied, distance=settings["distance"], margin=settings["margin"], port=settings["port"]) for source in sources)


def _rows(items) -> list[dict]:
    return [{"source_id": item.source_id, "decision": asdict(item.decision), "scope_id": item.scope_id, "modality": item.modality, "atoms": [asdict(atom) for atom in item.atoms], "field_program": item.field_program is not None, "operations": len(item.operations), "numeric_digest": item.numeric_digest, "failure_codes": item.failure_codes} for item in items]


def kernel_develop(workspace: Path) -> dict[str, object]:
    output = workspace / "kernel-development-results.json"
    if output.exists(): raise RuntimeError("kernel development already exists")
    if not (workspace / "dataset-manifest.json").exists(): dataset_build(workspace)
    sources = load_runtime(workspace / "train" / "inputs.jsonl"); gold = load_gold(workspace / "train" / "gold" / "gold.jsonl")
    model, encoder, summary = train(workspace, sources, gold, stage="kernel", steps=config()["training"]["kernel_steps"], extraction=False)
    development = load_runtime(workspace / "development" / "inputs.jsonl"); predictions = _infer(workspace, model, encoder, development, supplied=True, stage="development-kernel")
    metrics = score(load_gold(workspace / "development" / "gold" / "gold.jsonl"), predictions); passed = passes(metrics, full=False)
    result = {"stage": "kernel-development", "metrics": metrics, "kernel_passed": passed, "classification": "G2.10-KERNEL-DEVELOPMENT-PASS" if passed else "G2.10-B — BEHAVIORAL COMPILER DEVELOPMENT FAILURE", "training": asdict(summary), "peak_rss_mb": _rss_mb(), "model_hashes": assert_model_hashes()}
    _write(workspace / "kernel-development-predictions.json", _rows(predictions)); _write(output, result); return result


def kernel_freeze(workspace: Path) -> dict[str, object]:
    development = json.loads((workspace / "kernel-development-results.json").read_text())
    if not development["kernel_passed"]: raise RuntimeError("kernel freeze refused after development failure")
    output = workspace / "kernel-frozen-manifest.json"
    if output.exists(): raise RuntimeError("kernel already frozen")
    result = {"source_hash": _source_hash(), "config_hash": _hash(CONFIG), "checkpoint_hash": _hash(workspace / "kernel-checkpoint.pt"), "development_hash": _hash(workspace / "kernel-development-results.json"), "representation_hash": _hash(workspace / "representation-check.json"), "model_hashes": assert_model_hashes(), "python": sys.version, "torch": torch.__version__}
    _write(output, result); return result


def _verify_kernel(workspace: Path) -> None:
    manifest = json.loads((workspace / "kernel-frozen-manifest.json").read_text())
    checks = {"source_hash": _source_hash(), "config_hash": _hash(CONFIG), "checkpoint_hash": _hash(workspace / "kernel-checkpoint.pt"), "representation_hash": _hash(workspace / "representation-check.json")}
    if any(manifest[key] != value for key, value in checks.items()): raise RuntimeError("frozen kernel boundary changed")


def kernel_locked_suite_build(workspace: Path) -> dict[str, object]:
    _verify_kernel(workspace); return build_split(workspace, "kernel_locked")


def kernel_evaluate(workspace: Path) -> dict[str, object]:
    _verify_kernel(workspace); output = workspace / "kernel-results.json"
    if output.exists(): raise RuntimeError("second kernel locked evaluation refused")
    model, encoder = _load(workspace, "kernel-checkpoint.pt"); predictions = _infer(workspace, model, encoder, load_runtime(workspace / "kernel_locked" / "inputs.jsonl"), supplied=True, stage="kernel-locked")
    metrics = score(load_gold(workspace / "kernel_locked" / "gold" / "gold.jsonl"), predictions); passed = passes(metrics, full=False)
    result = {"stage": "kernel-locked", "metrics": metrics, "kernel_passed": passed, "classification": "G2.10-KERNEL-PASS" if passed else "G2.10-C — BEHAVIORAL COMPILER LOCKED FAILURE", "failure_stage": None if passed else "kernel", "peak_rss_mb": _rss_mb()}
    _write(workspace / "kernel-predictions.json", _rows(predictions)); _write(output, result); return result


def develop(workspace: Path) -> dict[str, object]:
    if not json.loads((workspace / "kernel-results.json").read_text())["kernel_passed"]: raise RuntimeError("full development not authorized after kernel failure")
    output = workspace / "development-results.json"
    if output.exists(): raise RuntimeError("full development already exists")
    sources = load_runtime(workspace / "train" / "inputs.jsonl"); gold = load_gold(workspace / "train" / "gold" / "gold.jsonl")
    model, encoder, summary = train(workspace, sources, gold, stage="full", steps=config()["training"]["extraction_steps"], extraction=True)
    development = load_runtime(workspace / "development" / "inputs.jsonl"); predictions = _infer(workspace, model, encoder, development, supplied=False, stage="development-full")
    metrics = score(load_gold(workspace / "development" / "gold" / "gold.jsonl"), predictions); passed = passes(metrics, full=True)
    result = {"stage": "full-development", "metrics": metrics, "full_passed": passed, "classification": "G2.10-FULL-DEVELOPMENT-PASS" if passed else "G2.10-B — BEHAVIORAL COMPILER DEVELOPMENT FAILURE", "training": asdict(summary), "thresholds": {"distance": .2, "margin": .01, "port": .5}, "peak_rss_mb": _rss_mb()}
    _write(workspace / "development-predictions.json", _rows(predictions)); _write(output, result); return result


def freeze(workspace: Path) -> dict[str, object]:
    result = json.loads((workspace / "development-results.json").read_text())
    if not result["full_passed"]: raise RuntimeError("full freeze refused after development failure")
    output = workspace / "frozen-manifest.json"
    if output.exists(): raise RuntimeError("full boundary already frozen")
    manifest = {"source_hash": _source_hash(), "config_hash": _hash(CONFIG), "checkpoint_hash": _hash(workspace / "full-checkpoint.pt"), "kernel_result_hash": _hash(workspace / "kernel-results.json"), "development_hash": _hash(workspace / "development-results.json"), "model_hashes": assert_model_hashes()}
    _write(output, manifest); return manifest


def locked_suite_build(workspace: Path) -> dict[str, object]:
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("full freeze required")
    return build_split(workspace, "locked")


def evaluate_locked(workspace: Path) -> dict[str, object]:
    output = workspace / "locked-results.json"
    if output.exists(): raise RuntimeError("second locked evaluation refused")
    model, encoder = _load(workspace, "full-checkpoint.pt"); development = json.loads((workspace / "development-results.json").read_text())
    predictions = _infer(workspace, model, encoder, load_runtime(workspace / "locked" / "inputs.jsonl"), supplied=False, stage="locked", thresholds=development["thresholds"])
    metrics = score(load_gold(workspace / "locked" / "gold" / "gold.jsonl"), predictions); passed = passes(metrics, full=True)
    result = {"stage": "full-locked", "metrics": metrics, "classification": "G2.10-A — CONTROLLED BEHAVIORAL G2 PASS" if passed else "G2.10-C — BEHAVIORAL COMPILER LOCKED FAILURE", "failure_stage": None if passed else "extraction_or_compilation", "peak_rss_mb": _rss_mb(), "runtime_constraints": {"network_calls": 0, "rss_limit_mb": 12 * 1024}}
    _write(workspace / "locked-predictions.json", _rows(predictions)); _write(output, result); return result


def verify(workspace: Path) -> dict[str, object]:
    stored = json.loads((workspace / "kernel-predictions.json").read_text()); model, encoder = _load(workspace, "kernel-checkpoint.pt")
    replay = _rows(_infer(workspace, model, encoder, load_runtime(workspace / "kernel_locked" / "inputs.jsonl"), supplied=True, stage="verification"))
    result = {"semantic_replay_equal": stored == replay, "model_hashes": assert_model_hashes()}; _write(workspace / "verification.json", result); return result
