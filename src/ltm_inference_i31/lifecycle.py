"""Development lifecycle. Locked work is prohibited until controls pass."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .dataset import body_from_obj, build_split, expr_from_obj, feature, load_rows, problem_from_obj
from .evaluator import score
from .field import MathFieldIndex, build_field
from .kernel import SearchKernel, parameter_count, train_kernel
from .runtime import infer

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dataset_build(workspace: Path) -> dict[str, object]:
    result = {"train": build_split(workspace, "train", 2400, 1930), "development": build_split(workspace, "development", 600, 1931), "locked": build_split(workspace, "locked", 3600, 20270601, locked=True), "stress": build_split(workspace, "stress", 1200, 20270602, stress=True, locked=True)}
    _write(workspace / "dataset-manifest.json", result); return result


def _field(workspace: Path, split: str) -> MathFieldIndex:
    root = workspace / "public" / split
    bodies = tuple(body_from_obj(item) for item in load_rows(root / "bodies.jsonl"))
    vectors = np.load(root / "body-vectors.npy")
    return MathFieldIndex(bodies, vectors, build_field(bodies, vectors))


def _examples(workspace: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    field = _field(workspace, "train"); public = {str(item["problem_id"]): item for item in load_rows(workspace / "public/train/theorems.jsonl")}; gold = load_rows(workspace / "evaluator-gold/train/gold.jsonl")
    rng = np.random.default_rng(1930); states=[]; goals=[]; positives=[]; negatives=[]; distances=[]
    all_vectors = field.vectors
    for item in gold:
        problem = problem_from_obj(public[str(item["problem_id"])])
        for offset, step in enumerate(item["proof"]):
            states.append(feature(expr_from_obj(step["before"]))); goals.append(feature(problem.goal)); positives.append(all_vectors[field.bodies[str(step["body_id"])].vector_index]); negatives.append(all_vectors[int(rng.integers(len(all_vectors)))]); distances.append(float(len(item["proof"]) - offset))
    return tuple(np.asarray(item, dtype=np.float32) for item in (states, goals, positives, negatives, distances))


def develop(workspace: Path) -> dict[str, object]:
    model = train_kernel(_examples(workspace), steps=1800, seed=1930)
    path = workspace / "selected-kernel.pt"; path.parent.mkdir(parents=True, exist_ok=True); torch.save(model.state_dict(), path)
    metrics = evaluate_split(workspace, "development", model)
    payload = {"parameters": parameter_count(model), "metrics": metrics}; _write(workspace / "development-results.json", payload); return payload


def _load(workspace: Path) -> SearchKernel:
    model=SearchKernel(); model.load_state_dict(torch.load(workspace / "selected-kernel.pt", map_location="cpu", weights_only=True)); return model.eval()


def evaluate_split(workspace: Path, split: str, model: SearchKernel | None = None, **kwargs: bool) -> dict[str, object]:
    model = _load(workspace) if model is None else model; field = _field(workspace, split); public = load_rows(workspace / f"public/{split}/theorems.jsonl"); results = {str(row["problem_id"]): infer(problem_from_obj(row), field, model, **kwargs) for row in public}; return score(public, results, load_rows(workspace / f"evaluator-gold/{split}/gold.jsonl"), load_rows(workspace / f"public/{split}/bodies.jsonl"))


def controls(workspace: Path) -> dict[str, object]:
    model = _load(workspace); public = load_rows(workspace / "public/development/theorems.jsonl")[::3]; field = _field(workspace, "development"); gold = tuple(item for item in load_rows(workspace / "evaluator-gold/development/gold.jsonl") if str(item["problem_id"]) in {str(row["problem_id"]) for row in public}); bodies=load_rows(workspace / "public/development/bodies.jsonl")
    variants={"full":{},"no_goal":{"use_goal":False},"no_heuristic":{"use_heuristic":False},"random_scorer":{"use_scorer":False},"fixed_frontier":{"fixed_frontier":True},"minimap_only":{"use_content_index":False}}
    outcome={}
    for name, kwargs in variants.items():
        field.reset_counter(); rows={str(row["problem_id"]): infer(problem_from_obj(row), field, model, **kwargs) for row in public}; outcome[name]=score(public, rows, gold, bodies) | {"body_reads":field.read_count}
    full=float(outcome["full"]["all_case_exactness"]); deltas={name:full-float(outcome[name]["all_case_exactness"]) for name in variants if name != "full"}
    result={"controls":outcome,"deltas":deltas,"sensitive":deltas["no_goal"] >= .20 and deltas["random_scorer"] >= .20 and deltas["fixed_frontier"] >= .20, "remaining_cost_head_causal": deltas["no_heuristic"] >= .20}; _write(workspace / "development-controls.json",result);return result


def stress_develop(workspace: Path) -> dict[str, object]:
    """Run a fresh development-only length diagnostic; never touch locked data."""
    build_split(workspace, "development-stress", 200, 1932, stress=True)
    metrics = evaluate_split(workspace, "development-stress")
    _write(workspace / "development-stress-results.json", {"metrics": metrics, "classification": "diagnostic-only"})
    return metrics


def freeze(workspace: Path) -> dict[str, object]:
    """Refuse a locked boundary until every causal mechanism has passed."""
    controls_path = workspace / "development-controls.json"
    if not controls_path.exists():
        raise RuntimeError("development controls are required before freeze")
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    if not controls["sensitive"] or not controls["remaining_cost_head_causal"]:
        raise RuntimeError("locked execution is not authorized: causal search gates failed")
    result = {"status": "frozen", "kernel": hashlib.sha256((workspace / "selected-kernel.pt").read_bytes()).hexdigest()}
    _write(workspace / "frozen-manifest.json", result)
    return result
