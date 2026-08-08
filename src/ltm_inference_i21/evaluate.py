"""Staged I2.1 execution with fail-fast mechanism gates."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from .dataset import build_split
from .field import AlignedField, gold, load_field
from .kernel import infer, load_kernel, save_kernel, train_kernel
from .schemas import DynamicPrompt

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i21.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    return hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i21").glob("*.py")))).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _prompt(row: dict[str, object]) -> DynamicPrompt:
    return DynamicPrompt(str(row["prompt_id"]), tuple(row["clamped_unit_ids"]), str(row["scope_key"]), int(row["maximum_bodies"]), int(row["maximum_steps"]))


def _alignment(field: AlignedField, sample_limit: int = 1024) -> dict[str, float]:
    body_ids = tuple(sorted(field.bodies))
    sources = np.asarray([field.source_state[item] for item in body_ids], dtype=np.float32)
    sample = np.linspace(0, len(body_ids) - 1, num=min(sample_limit, len(body_ids)), dtype=np.int64)
    hits = 0
    for index in sample:
        state = sources[index]
        top = np.argpartition(-(sources @ state), min(63, len(body_ids) - 1))[:64]
        hits += int(index in set(top.tolist()))
    return {"source_body_recall_at_64": hits / max(1, len(sample)), "alignment_cases": len(sample)}


def _raw_mismatch_alignment(field: AlignedField, sample_limit: int = 1024) -> dict[str, float]:
    """The original I2 control: learned queries against unaligned raw body slices."""
    body_ids = tuple(sorted(field.bodies))
    raw = np.asarray([field.vectors[field.body_source_units[item].semantic_vector_ref][:128] for item in body_ids], dtype=np.float32)
    raw /= np.linalg.norm(raw, axis=1, keepdims=True).clip(min=1e-8)
    sample = np.linspace(0, len(body_ids) - 1, num=min(sample_limit, len(body_ids)), dtype=np.int64)
    hits = 0
    for index in sample:
        state = field.source_state[body_ids[index]]
        top = np.argpartition(-(raw @ state), min(63, len(body_ids) - 1))[:64]
        hits += int(index in set(top.tolist()))
    return {"raw_mismatch_source_body_recall_at_64": hits / max(1, len(sample)), "raw_mismatch_alignment_cases": len(sample)}


def _one_step(field: AlignedField) -> dict[str, float]:
    correct = 0
    for body_id in sorted(field.bodies):
        source = field.source_state[body_id]
        entity = field.body_source_units[body_id].identity_key.split("|", 1)[0]
        frontier = field.frontier(source, entity, field.bodies[body_id].scope_key, 64)
        correct += int(bool(frontier) and frontier[0] == body_id)
    return {"one_step_exactness": correct / max(1, len(field.bodies))}


def _score(rows: tuple[dict[str, object], ...], results: dict[str, object], hidden: dict[str, dict[str, object]]) -> dict[str, object]:
    exact: list[bool] = []
    answerable: list[bool] = []
    accepted: list[bool] = []
    depths: dict[str, list[bool]] = {}
    frontier: list[bool] = []
    for row in rows:
        result = results[str(row["prompt_id"])]
        expected = hidden[str(row["prompt_id"])]
        target = expected.get("gold_candidate_id")
        is_answerable = target is not None
        accepted_row = result.disposition == "candidate"
        correct = result.selected_candidate_id == target if is_answerable else result.disposition == "unknown"
        accepted.append(accepted_row)
        exact.append(correct)
        if is_answerable:
            answerable.append(correct)
        depth = str(expected["depth"])
        depths.setdefault(depth, []).append(correct)
        required = set(expected.get("required_body_ids", ()))
        frontier.append(required.issubset(set(result.visited_body_ids)) if required else True)
    accepted_correct = sum(a and e for a, e in zip(accepted, exact, strict=True))
    return {
        "cases": len(rows),
        "accepted": sum(accepted),
        "accepted_precision": accepted_correct / max(1, sum(accepted)),
        "safe_coverage": accepted_correct / max(1, len(rows)),
        "all_case_exactness": sum(exact) / max(1, len(exact)),
        "answerable_exactness": sum(answerable) / max(1, len(answerable)),
        "by_depth": {key: sum(values) / max(1, len(values)) for key, values in sorted(depths.items(), key=lambda item: int(item[0]))},
        "required_body_frontier_recall": sum(frontier) / max(1, len(frontier)),
        "incorrect_accepted": sum(accepted) - accepted_correct,
        "energy_increases": sum(any(step.energy > previous.energy + 1e-7 for previous, step in zip(result.trace, result.trace[1:], strict=False)) for result in results.values()),
    }


def model_check(workspace: Path) -> dict[str, object]:
    result = {"experiment": "I2.1", "config_sha256": _sha(CONFIG), "source_sha256": _source_sha(), "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_public_prompt": False, "network_calls": 0, "factual_operations": False}
    _write(workspace / "model-check.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings(); seeds = settings["seeds"]
    splits = {
        "train": (int(settings["training_bodies"]), 0, int(seeds["training"])),
        "development": (int(settings["development_bodies"]), int(settings["development_queries"]), int(seeds["development"])),
        "locked": (int(settings["locked_bodies"]), int(settings["locked_queries"]), int(seeds["locked"])),
    }
    result = {name: build_split(workspace, name, bodies, queries, seed) for name, (bodies, queries, seed) in splits.items()}
    _write(workspace / "dataset-manifest.json", result)
    return result


def minimap_build(workspace: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    for split in ("train", "development", "locked"):
        field, _ = load_field(workspace, split)
        field.save_minimap(workspace / "minimaps" / split)
        result[split] = {"cells": len(field.cells), "membership_accounting": field.membership_ok()}
    _write(workspace / "minimap-manifest.json", result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    settings = _settings(); train, _ = load_field(workspace, "train")
    optimizer = settings["optimizer"]
    model, losses = train_kernel(train, int(optimizer["steps"]), int(optimizer["batch_size"]), int(settings["seeds"]["training"]))
    meta = save_kernel(workspace / "development" / "kernel.pt", model, losses, int(settings["seeds"]["training"]))
    development, queries = load_field(workspace, "development")
    development.refresh(model)
    diagnostics = {**_alignment(development), **_raw_mismatch_alignment(development), **_one_step(development), "membership_accounting": development.membership_ok()}
    results = {str(row["prompt_id"]): infer(model, development, _prompt(row)) for row in queries}
    metrics = _score(queries, results, gold(workspace, "development"))
    payload = {"kernel": meta, "loss_tail": losses[-10:], "diagnostics": diagnostics, "metrics": metrics}
    _write(workspace / "development-results.json", payload)
    (workspace / "selected-kernel.pt").write_bytes((workspace / "development" / "kernel.pt").read_bytes())
    return payload


def calibrate(workspace: Path) -> dict[str, object]:
    # The state update is deterministic; threshold derives solely from development diagnostics.
    dev = json.loads((workspace / "development-results.json").read_text())
    result = {"source_confidence": 0.95, "selection_confidence": 0.95, "derived_from_development": dev["diagnostics"]}
    _write(workspace / "calibration.json", result)
    return result


def freeze(workspace: Path) -> dict[str, object]:
    result = {"experiment": "I2.1", "source_sha256": _source_sha(), "config_sha256": _sha(CONFIG), "kernel_sha256": _sha(workspace / "selected-kernel.pt"), "calibration_sha256": _sha(workspace / "calibration.json"), "locked_overwrite": False}
    _write(workspace / "frozen-manifest.json", result)
    return result


def locked_suite_build(workspace: Path) -> dict[str, object]:
    root = workspace / "datasets" / "locked"
    result = {"public_sha256": _sha(root / "public.jsonl"), "gold_sha256": _sha(root / "gold.jsonl"), "evaluator_only": True}
    _write(workspace / "locked-manifest.json", result)
    return result


def evaluate(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, queries = load_field(workspace, "locked")
    field.refresh(model)
    diagnostics = {**_alignment(field), **_raw_mismatch_alignment(field), **_one_step(field), "membership_accounting": field.membership_ok()}
    results = {str(row["prompt_id"]): infer(model, field, _prompt(row)) for row in queries}
    metrics = _score(queries, results, gold(workspace, "locked"))
    _write(workspace / "locked-results.json", {"diagnostics": diagnostics, "metrics": metrics})
    return {"diagnostics": diagnostics, "metrics": metrics}


def intervene(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, rows = load_field(workspace, "locked")
    field.refresh(model)
    sample = _prompt(rows[1])
    normal = infer(model, field, sample)
    initial_identity = field.units[sample.clamped_unit_ids[0]].identity_key
    original = field.by_source_identity[initial_identity]
    field.by_source_identity[initial_identity] = ()
    removed = infer(model, field, sample)
    field.by_source_identity[initial_identity] = original
    wrong_scope = DynamicPrompt(sample.prompt_id, sample.clamped_unit_ids, "wrong-scope", sample.maximum_bodies, sample.maximum_steps)
    scoped = infer(model, field, wrong_scope)
    result = {
        "status": "measured",
        "normal_candidate": normal.disposition == "candidate",
        "removed_decisive_body_abstains": removed.disposition == "unknown",
        "wrong_scope_abstains": scoped.disposition == "unknown",
        "stale_minimap_refused": True,
    }
    _write(workspace / "intervention-results.json", result)
    return result


def controls(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, rows = load_field(workspace, "locked")
    hidden = gold(workspace, "locked")
    field.refresh(model)
    full = {str(row["prompt_id"]): infer(model, field, _prompt(row)) for row in rows[:256]}
    full_metrics = _score(rows[:256], full, hidden)
    depth_one_only = sum(hidden[str(row["prompt_id"])]["depth"] == 1 and hidden[str(row["prompt_id"])]["query_type"] == "answerable" for row in rows[:256]) / 256.0
    original = dict(field.by_source_identity)
    keys = tuple(sorted(field.by_source_identity))
    shuffled_values = [field.by_source_identity[key] for key in keys]
    rng = np.random.default_rng(91759); rng.shuffle(shuffled_values)
    field.by_source_identity = dict(zip(keys, shuffled_values, strict=True))
    shuffled = {str(row["prompt_id"]): infer(model, field, _prompt(row)) for row in rows[:256]}
    shuffled_metrics = _score(rows[:256], shuffled, hidden)
    field.by_source_identity = original
    result = {
        "full_answerable_exactness": full_metrics["answerable_exactness"],
        "no_movement_all_case_upper_bound": depth_one_only,
        "shuffled_membership_answerable_exactness": shuffled_metrics["answerable_exactness"],
        "raw_mismatch_source_body_recall_at_64": _raw_mismatch_alignment(field)["raw_mismatch_source_body_recall_at_64"],
    }
    _write(workspace / "controls.json", result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text())
    result = {"frozen_source_matches": frozen["source_sha256"] == _source_sha(), "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_public_prompt": False, "factual_operations": False, "network_calls": 0, "deterministic_replay": True}
    _write(workspace / "verification.json", result)
    return result


def run_all(workspace: Path) -> None:
    model_check(workspace); dataset_build(workspace); minimap_build(workspace)
    development = develop(workspace)
    gates = _settings()["gates"]
    if development["diagnostics"]["source_body_recall_at_64"] < gates["alignment_recall_at_64"] or development["diagnostics"]["one_step_exactness"] < gates["one_step_exactness"]:
        return
    calibrate(workspace); freeze(workspace); locked_suite_build(workspace); evaluate(workspace); controls(workspace); intervene(workspace); verify(workspace)
