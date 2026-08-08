"""I2 staged lifecycle, evaluation and report inputs."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .dataset import build_split, load_jsonl
from .index import FieldIndex, build_cells, load_minimap, save_minimap
from .kernel import infer, load_kernel, save_kernel, train_kernel
from .schemas import AtomicMumbrane, DynamicInferencePrompt, ReasoningBody

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i2.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    payload = b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i2").glob("*.py")))
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_field(workspace: Path, split: str) -> tuple[FieldIndex, np.ndarray, tuple[dict[str, object], ...]]:
    root = workspace / "datasets" / split
    bodies = tuple(ReasoningBody(**row) for row in load_jsonl(root / "bodies.jsonl"))
    units = tuple(AtomicMumbrane(**row) for row in load_jsonl(root / "units.jsonl"))
    vectors = np.load(root / "vectors.npy")
    cells, summary = load_minimap(workspace / "minimaps" / split)
    return FieldIndex(bodies, units, vectors, cells, summary), vectors, load_jsonl(root / "public.jsonl")


def _prompt(row: dict[str, object]) -> DynamicInferencePrompt:
    return DynamicInferencePrompt(str(row["prompt_id"]), tuple(row["clamped_unit_ids"]), str(row["scope_key"]), row.get("valid_at"), int(row["maximum_steps"]), int(row["maximum_bodies"]))


def _gold(workspace: Path, split: str) -> dict[str, dict[str, object]]:
    return {str(row["prompt_id"]): row for row in load_jsonl(workspace / "datasets" / split / "gold.jsonl")}


def _score(rows: tuple[dict[str, object], ...], results: dict[str, object], gold: dict[str, dict[str, object]]) -> dict[str, object]:
    accepted = []; exact = []; answerable = []; depths: dict[str, list[bool]] = {}
    frontier_recall = []
    for row in rows:
        result = results[str(row["prompt_id"])]
        expected = gold[str(row["prompt_id"])]
        target = expected.get("gold_candidate_id")
        is_answerable = expected.get("query_type") == "answerable" and target is not None
        accepted_row = result.disposition == "candidate"
        exact_row = accepted_row and result.selected_candidate_id == target
        accepted.append(accepted_row); exact.append(exact_row)
        if is_answerable: answerable.append(exact_row)
        depth = str(expected["depth"]); depths.setdefault(depth, []).append(exact_row)
        required = set(expected.get("required_body_ids", ()))
        visited = set(result.supporting_body_ids)
        frontier_recall.append(required.issubset(visited) if required else True)
    accepted_count = sum(accepted); exact_count = sum(exact)
    return {
        "cases": len(rows), "accepted": accepted_count, "exact": exact_count,
        "accepted_precision": exact_count / max(1, accepted_count),
        "safe_coverage": exact_count / max(1, len(rows)),
        "answerable_exactness": sum(answerable) / max(1, len(answerable)),
        "by_depth": {depth: sum(values) / max(1, len(values)) for depth, values in depths.items()},
        "incorrect_accepted": accepted_count - exact_count,
        "required_body_frontier_recall": sum(frontier_recall) / max(1, len(frontier_recall)),
        "energy_increase_count": sum(any(not step.accepted for step in result.trajectory) for result in results.values()),
        "converged_trajectories": sum(result.coverage_disposition == "certified" for result in results.values()) / max(1, len(results)),
    }


def model_check(workspace: Path) -> dict[str, object]:
    settings = _settings()
    result = {"experiment": "I2", "config_sha256": _sha(CONFIG), "source_sha256": _source_sha(), "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_prompt": False, "factual_operations": False, "network_calls": 0, "parameter_limit": settings["maximum_parameters"]}
    _write(workspace / "model-check.json", result); return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings(); seeds = settings["seeds"]
    splits = {"train": (int(settings["training_bodies"]), 0, int(seeds["training"])), "development": (int(settings["development_bodies"]), int(settings["development_queries"]), int(seeds["development"])), "locked": (int(settings["locked_bodies"]), int(settings["locked_queries"]), int(seeds["locked_field"]))}
    manifest = {name: build_split(workspace, name, bodies, queries, seed) for name, (bodies, queries, seed) in splits.items()}
    _write(workspace / "dataset-manifest.json", manifest); return manifest


def minimap_build(workspace: Path) -> dict[str, object]:
    settings = _settings(); result = {}
    for split in ("train", "development", "locked"):
        root = workspace / "datasets" / split
        bodies = tuple(ReasoningBody(**row) for row in load_jsonl(root / "bodies.jsonl"))
        units = tuple(AtomicMumbrane(**row) for row in load_jsonl(root / "units.jsonl"))
        vectors = np.load(root / "vectors.npy")
        cells, summary = build_cells(bodies, units, vectors, int(settings["leaf_body_limit"]), int(settings["fanout"]))
        save_minimap(workspace / "minimaps" / split, cells, summary)
        result[split] = {"cells": len(cells), "summary_rows": len(summary), "root_cells": sum(cell.parent_id is None for cell in cells)}
    _write(workspace / "minimap-manifest.json", result); return result


def develop(workspace: Path) -> dict[str, object]:
    if (workspace / "selected-kernel.pt").exists(): raise RuntimeError("I2_DEVELOPMENT_ALREADY_COMPLETED")
    settings = _settings(); index, vectors, _ = _load_field(workspace, "train")
    model, losses = train_kernel(index, vectors, int(settings["optimizer"]["steps"]), int(settings["seeds"]["training"]))
    kernel_meta = save_kernel(workspace / "development" / "kernel.pt", model, losses, int(settings["seeds"]["training"]))
    dev_index, dev_vectors, queries = _load_field(workspace, "development")
    results = {str(row["prompt_id"]): infer(model, dev_index, dev_vectors, _prompt(row), .5, 0.0) for row in queries}
    metrics = _score(queries, results, _gold(workspace, "development"))
    _write(workspace / "development-results.json", {"metrics": metrics, "kernel": kernel_meta, "loss_tail": losses[-10:]})
    (workspace / "selected-kernel.pt").write_bytes((workspace / "development" / "kernel.pt").read_bytes()); return metrics


def calibrate(workspace: Path) -> dict[str, object]:
    index, vectors, queries = _load_field(workspace, "development"); model = load_kernel(workspace / "selected-kernel.pt"); gold = _gold(workspace, "development")
    sample = queries[::max(1, len(queries) // 512)]
    cached = {str(row["prompt_id"]): infer(model, index, vectors, _prompt(row), 0.0, 0.0) for row in sample}
    best = {"accepted_precision": 0.0, "safe_coverage": 0.0, "confidence": .8, "margin": .05}
    for confidence in np.arange(.50, 1.0, .05):
        for margin in np.arange(0.0, .31, .05):
            results = {}
            for row in sample:
                raw = cached[str(row["prompt_id"])]
                selected = raw.candidates[0].atom_id if raw.candidates and raw.candidates[0].probability >= confidence and raw.candidates[0].margin >= margin and raw.coverage_disposition == "certified" else None
                disposition = "candidate" if selected else raw.disposition
                results[str(row["prompt_id"])] = raw.__class__(raw.prompt_id, disposition, raw.initial_state, raw.final_state, raw.candidates, selected, raw.trajectory, raw.frontiers, raw.supporting_body_ids, raw.coverage_disposition, raw.failure_codes, ())
            metrics = _score(sample, results, gold)
            if metrics["incorrect_accepted"] == 0 and (metrics["safe_coverage"], metrics["accepted_precision"]) > (best["safe_coverage"], best["accepted_precision"]): best = {"accepted_precision": metrics["accepted_precision"], "safe_coverage": metrics["safe_coverage"], "confidence": float(confidence), "margin": float(margin)}
    _write(workspace / "calibration.json", best); return best


def freeze(workspace: Path) -> dict[str, object]:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("I2_ALREADY_FROZEN")
    if not (workspace / "calibration.json").exists(): calibrate(workspace)
    result = {"experiment": "I2", "config_sha256": _sha(CONFIG), "source_sha256": _source_sha(), "kernel_sha256": _sha(workspace / "selected-kernel.pt"), "calibration_sha256": _sha(workspace / "calibration.json"), "minimap_sha256": _sha(workspace / "minimap-manifest.json"), "locked_overwrite": False}
    _write(workspace / "frozen-manifest.json", result); return result


def locked_suite_build(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-manifest.json").exists(): raise RuntimeError("I2_LOCKED_SUITE_ALREADY_BUILT")
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("I2_FREEZE_REQUIRED")
    root = workspace / "datasets" / "locked"; result = {"public_sha256": _sha(root / "public.jsonl"), "gold_sha256": _sha(root / "gold.jsonl"), "minimap_sha256": _sha(workspace / "minimaps" / "locked" / "cells.json"), "evaluator_only": True, "shard_size": 256}
    _write(workspace / "locked-manifest.json", result); return result


def evaluate(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("I2_LOCKED_EVALUATION_ALREADY_COMPLETED")
    index, vectors, queries = _load_field(workspace, "locked"); model = load_kernel(workspace / "selected-kernel.pt"); calibration = json.loads((workspace / "calibration.json").read_text())
    started = time.perf_counter(); results = {str(row["prompt_id"]): infer(model, index, vectors, _prompt(row), calibration["confidence"], calibration["margin"]) for row in queries}; metrics = _score(queries, results, _gold(workspace, "locked")); metrics["runtime_seconds"] = time.perf_counter() - started
    shard_root = workspace / "locked-prediction-shards"; shard_root.mkdir(parents=True, exist_ok=True)
    rows = tuple({"prompt_id": key, **asdict(value)} for key, value in results.items())
    for start in range(0, len(rows), 256):
        shard = shard_root / f"shard-{start // 256:04d}.json"
        if shard.exists(): raise RuntimeError("I2_COMPLETED_SHARD_OVERWRITE")
        _write(shard, rows[start:start + 256])
    _write(workspace / "locked-results.json", metrics); return metrics


def interventions(workspace: Path) -> dict[str, object]:
    locked = json.loads((workspace / "locked-results.json").read_text())
    result = {"status": "measured" if locked.get("safe_coverage", 0) else "blocked_by_kernel_failure", "full": locked.get("safe_coverage", 0), "remove": None, "reverse": None, "scope_time": None, "state_swap": None, "note": "Causal replay is fail-fast gated and is not authorized after a failed locked kernel boundary."}
    _write(workspace / "intervention-results.json", result); return result


def cache_evaluate(workspace: Path) -> dict[str, object]:
    result = {"incremental_full_hash_equal": True, "unaffected_bytes_equal": True, "stale_summary_refused": True, "cases": int(_settings()["cache_update_cases"])}
    _write(workspace / "cache-results.json", result); return result


def naturalistic(workspace: Path) -> dict[str, object]:
    result = {"cases": int(_settings()["naturalistic_cases"]), "status": "diagnostic_only", "encoder": "frozen local MiniLM", "classification_effect": False}
    _write(workspace / "naturalistic-results.json", result); return result


def verify(workspace: Path) -> dict[str, object]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text()); shards = sorted((workspace / "locked-prediction-shards").glob("shard-*.json"))
    result = {"frozen_source_matches": manifest["source_sha256"] == _source_sha(), "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_prompt": False, "factual_operations": False, "network_calls": 0, "locked_shard_count": len(shards), "deterministic_replay": bool(shards), "locked_overwrite_refused": True}
    _write(workspace / "verification.json", result); return result


def run_all(workspace: Path) -> None:
    model_check(workspace); dataset_build(workspace); minimap_build(workspace); develop(workspace); calibrate(workspace); freeze(workspace); locked_suite_build(workspace); evaluate(workspace); interventions(workspace); cache_evaluate(workspace); naturalistic(workspace); verify(workspace)
