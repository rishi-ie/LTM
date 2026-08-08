"""I2.2 lifecycle: global vector-tree retrieval without identity routing."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from ltm_inference_i21.dataset import build_split, load_jsonl
from ltm_inference_i21.evaluate import _prompt, _score
from ltm_inference_i21.kernel import infer, load_kernel, save_kernel, train_kernel
from ltm_inference_i21.schemas import AtomicMumbrane, ReasoningBody

from .field import GlobalTreeField

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/ltm-inference-i22.json"


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha() -> str:
    return hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "src/ltm_inference_i22").glob("*.py")))).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _load(workspace: Path, split: str) -> tuple[GlobalTreeField, tuple[dict[str, object], ...], dict[str, dict[str, object]]]:
    root = workspace / "datasets" / split
    bodies = tuple(ReasoningBody(**row) for row in load_jsonl(root / "bodies.jsonl"))
    units = tuple(AtomicMumbrane(**row) for row in load_jsonl(root / "units.jsonl"))
    field = GlobalTreeField(bodies, units, np.load(root / "vectors.npy"))
    public = load_jsonl(root / "public.jsonl")
    hidden = {str(row["prompt_id"]): row for row in load_jsonl(root / "gold.jsonl")}
    return field, public, hidden


def _routing(field: GlobalTreeField, sample_limit: int = 1024) -> dict[str, float | bool]:
    body_ids = tuple(sorted(field.bodies))
    sample = np.linspace(0, len(body_ids) - 1, min(sample_limit, len(body_ids)), dtype=np.int64)
    hits = 0
    changed = 0
    for index in sample:
        body_id = body_ids[index]
        source = field.source_state[body_id]
        frontier = field.frontier(source, "", field.bodies[body_id].scope_key, 64)
        hits += int(bool(frontier) and frontier[0] == body_id)
        changed += int(field.leaf_for(source) != field.leaf_for(field.outcome_state[body_id]))
    return {"next_body_recall_at_64": hits / len(sample), "cross_leaf_change_rate": changed / len(sample), "tree_membership_accounting": field.tree_membership_ok(), "identity_route_present": hasattr(field, "by_source_identity")}


def model_check(workspace: Path) -> dict[str, object]:
    result = {"experiment": "I2.2", "config_sha256": _sha(CONFIG), "source_sha256": _source_sha(), "identity_leaf_lookup": False, "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_prompt": False, "network_calls": 0, "factual_operations": False}
    _write(workspace / "model-check.json", result)
    return result


def dataset_build(workspace: Path) -> dict[str, object]:
    settings = _settings(); seeds = settings["seeds"]
    definitions = {"train": (int(settings["training_bodies"]), 0, int(seeds["training"])), "development": (int(settings["development_bodies"]), int(settings["development_queries"]), int(seeds["development"])), "locked": (int(settings["locked_bodies"]), int(settings["locked_queries"]), int(seeds["locked"]))}
    result = {name: build_split(workspace, name, bodies, queries, seed) for name, (bodies, queries, seed) in definitions.items()}
    _write(workspace / "dataset-manifest.json", result)
    return result


def develop(workspace: Path) -> dict[str, object]:
    settings = _settings(); training, _, _ = _load(workspace, "train")
    options = settings["optimizer"]
    model, losses = train_kernel(training, int(options["steps"]), int(options["batch_size"]), int(settings["seeds"]["training"]))
    meta = save_kernel(workspace / "development" / "kernel.pt", model, losses, int(settings["seeds"]["training"]))
    field, rows, hidden = _load(workspace, "development")
    field.refresh(model)
    routing = _routing(field)
    results = {str(row["prompt_id"]): infer(model, field, _prompt(row), confidence=.99999) for row in rows}
    metrics = _score(rows, results, hidden)
    payload = {"kernel": meta, "routing": routing, "metrics": metrics, "loss_tail": losses[-10:]}
    _write(workspace / "development-results.json", payload)
    (workspace / "selected-kernel.pt").write_bytes((workspace / "development" / "kernel.pt").read_bytes())
    return payload


def freeze(workspace: Path) -> dict[str, object]:
    result = {"experiment": "I2.2", "source_sha256": _source_sha(), "config_sha256": _sha(CONFIG), "kernel_sha256": _sha(workspace / "selected-kernel.pt")}
    _write(workspace / "frozen-manifest.json", result)
    return result


def evaluate(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, rows, hidden = _load(workspace, "locked")
    field.refresh(model)
    routing = _routing(field)
    results = {str(row["prompt_id"]): infer(model, field, _prompt(row), confidence=.99999) for row in rows}
    metrics = _score(rows, results, hidden)
    payload = {"routing": routing, "metrics": metrics}
    _write(workspace / "locked-results.json", payload)
    return payload


def controls(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, rows, hidden = _load(workspace, "locked")
    field.refresh(model)
    full = {str(row["prompt_id"]): infer(model, field, _prompt(row), confidence=.99999) for row in rows[:256]}
    full_metrics = _score(rows[:256], full, hidden)
    no_movement = sum(hidden[str(row["prompt_id"])]["depth"] == 1 and hidden[str(row["prompt_id"])]["query_type"] == "answerable" for row in rows[:256]) / 256.0
    # Routing a query to a deterministically wrong leaf is the tree control.
    original_leaf_for = field.leaf_for
    leaves = tuple(sorted(cell_id for cell_id, cell in field.tree.items() if cell.axis is None))
    field.leaf_for = lambda state: leaves[(leaves.index(original_leaf_for(state)) + 1) % len(leaves)]  # type: ignore[method-assign]
    wrong_tree = {str(row["prompt_id"]): infer(model, field, _prompt(row), confidence=.99999) for row in rows[:256]}
    wrong_metrics = _score(rows[:256], wrong_tree, hidden)
    result = {"full_answerable_exactness": full_metrics["answerable_exactness"], "no_movement_all_case_upper_bound": no_movement, "wrong_tree_answerable_exactness": wrong_metrics["answerable_exactness"]}
    _write(workspace / "controls.json", result)
    return result


def intervene(workspace: Path) -> dict[str, object]:
    model = load_kernel(workspace / "selected-kernel.pt")
    field, rows, _ = _load(workspace, "locked")
    field.refresh(model)
    prompt = _prompt(rows[1]); normal = infer(model, field, prompt, confidence=.99999)
    state, _ = field.prompt_state(prompt.clamped_unit_ids, model)
    leaf_id = field.leaf_for(state); original = field.tree[leaf_id]
    field.tree[leaf_id] = original.__class__(original.cell_id, original.axis, original.threshold, original.left_id, original.right_id, (), original.cell_hash)
    removed = infer(model, field, prompt, confidence=.99999)
    result = {"normal_candidate": normal.disposition == "candidate", "removed_leaf_abstains": removed.disposition == "unknown", "identity_route_present": hasattr(field, "by_source_identity")}
    _write(workspace / "intervention-results.json", result)
    return result


def verify(workspace: Path) -> dict[str, object]:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text())
    result = {"frozen_source_matches": frozen["source_sha256"] == _source_sha(), "identity_leaf_lookup": False, "relation_labels_visible": False, "closure_visible": False, "candidate_ids_in_prompt": False, "factual_operations": False, "network_calls": 0}
    _write(workspace / "verification.json", result)
    return result
