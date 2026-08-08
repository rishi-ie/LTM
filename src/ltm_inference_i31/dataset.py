"""Branching, goal-swapped equality fields for I3.1.

Bodies are public established equalities.  Paths and remaining costs are
evaluator-only; a public problem contains only source, goal, reality and
budgets.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ltm_inference_i3.schemas import FormalExpression

from .formal import body_hash
from .schemas import FormalProofStep, MathematicalBody, TheoremProblem

DIMENSION = 128


def atom(value: str) -> FormalExpression:
    return FormalExpression("atom", value=value)


def expr_obj(value: FormalExpression) -> dict[str, object]:
    return {"op": value.op, "value": value.value, "args": [expr_obj(item) for item in value.args]}


def expr_from_obj(value: dict[str, object]) -> FormalExpression:
    return FormalExpression(str(value["op"]), tuple(expr_from_obj(item) for item in value["args"]), None if value["value"] is None else str(value["value"]))


def feature(value: FormalExpression) -> np.ndarray:
    result = np.zeros(DIMENSION, dtype=np.float32)
    if value.op == "atom" and value.value:
        # Compositionally retain public semantic components (field, identity,
        # local context) instead of allowing a one-off full identifier to
        # dominate every minimap centroid.
        tokens = value.value.split(":")
    else:
        tokens = repr(value).split("'")
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        result[int.from_bytes(digest[:2], "little") % DIMENSION] += 1.0
    result /= max(float(np.linalg.norm(result)), 1e-8)
    return result


def _body_obj(body: MathematicalBody) -> dict[str, object]:
    return {"body_id": body.body_id, "reality_key": body.reality_key, "left": expr_obj(body.left), "right": expr_obj(body.right), "provenance_hash": body.provenance_hash, "vector_index": body.vector_index}


def body_from_obj(value: dict[str, object]) -> MathematicalBody:
    return MathematicalBody(str(value["body_id"]), str(value["reality_key"]), expr_from_obj(value["left"]), expr_from_obj(value["right"]), str(value["provenance_hash"]), int(value["vector_index"]))


def problem_from_obj(value: dict[str, object]) -> TheoremProblem:
    return TheoremProblem(str(value["problem_id"]), str(value["reality_key"]), expr_from_obj(value["source"]), expr_from_obj(value["goal"]), int(value["maximum_bodies"]), int(value["maximum_steps"]))


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def load_rows(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)


def _depth(index: int, stress: bool) -> int:
    if stress:
        return 17 + index % 48
    band = index % 20
    return 2 + index % 3 if band < 8 else 5 + index % 4 if band < 15 else 9 + index % 8


def build_split(workspace: Path, split: str, theorem_count: int, seed: int, *, stress: bool = False, locked: bool = False) -> dict[str, object]:
    if theorem_count % 2:
        raise ValueError("theorem_count must be even to retain goal-swapped pairs")
    rng = random.Random(seed)
    public: list[dict[str, object]] = []
    gold: list[dict[str, object]] = []
    bodies: list[MathematicalBody] = []
    vectors: list[np.ndarray] = []
    groups = theorem_count // 2
    for group in range(groups):
        reality = "standard-v1"
        prefix = f"{split}:field:{group:06d}"
        source = atom(prefix + ":stage00")
        branch_depth = _depth(group, stress)
        target_slots = rng.sample(range(32), 2)
        group_bodies: list[MathematicalBody] = []
        branch_steps: list[list[FormalProofStep]] = []
        for branch, slot in enumerate(target_slots):
            previous = source
            steps: list[FormalProofStep] = []
            for hop in range(branch_depth):
                current = atom(f"{prefix}:stage{hop + 1:02d}:slot{slot:02d}")
                body_id = f"{prefix}:lemma:stage{hop:02d}:slot{slot:02d}"
                body = MathematicalBody(body_id, reality, previous, current, "", len(bodies) + len(group_bodies))
                body = MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), body.vector_index)
                group_bodies.append(body)
                steps.append(FormalProofStep(body_id, (), False, previous, current))
                previous = current
            branch_steps.append(steps)
        # Thirty competing, applicable first steps create a real branching
        # decision; none reaches either requested terminal without the correct
        # body chain.
        for distractor in (slot for slot in range(32) if slot not in target_slots):
            target = atom(f"{prefix}:stage01:slot{distractor:02d}")
            body_id = f"{prefix}:distractor:stage00:slot{distractor:02d}"
            body = MathematicalBody(body_id, reality, source, target, "", len(bodies) + len(group_bodies))
            group_bodies.append(MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), body.vector_index))
        while len(group_bodies) < 64:
            left = atom(f"{prefix}:noise:{len(group_bodies):02d}:l")
            right = atom(f"{prefix}:noise:{len(group_bodies):02d}:r")
            body_id = f"{prefix}:noise:{len(group_bodies):02d}"
            body = MathematicalBody(body_id, reality, left, right, "", len(bodies) + len(group_bodies))
            group_bodies.append(MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), body.vector_index))
        for body in group_bodies:
            bodies.append(body)
            vectors.append(np.concatenate((feature(body.left), feature(body.right))).astype(np.float32))
        for branch, proof in enumerate(branch_steps):
            idx = group * 2 + branch
            category = "proved"
            if locked and idx % 8 == 6:
                category = "unknown"
            if locked and idx % 8 == 7:
                category = "refuted"
            goal = proof[-1].after if category == "proved" else atom(f"{prefix}:{category}:{branch}")
            public.append({"problem_id": f"{split}:theorem:{idx:07d}", "reality_key": reality, "source": expr_obj(source), "goal": expr_obj(goal), "maximum_bodies": 64, "maximum_steps": min(64, branch_depth + 6)})
            gold.append({"problem_id": public[-1]["problem_id"], "status": category, "proof": [asdict(item) | {"before": expr_obj(item.before), "after": expr_obj(item.after)} for item in (proof if category == "proved" else ())], "required_body_ids": [item.body_id for item in proof] if category == "proved" else [], "depth": len(proof), "branching": 26, "paired_goal_id": f"{split}:theorem:{group * 2 + (1 - branch):07d}"})
    public_root = workspace / "public" / split
    gold_root = workspace / "evaluator-gold" / split
    _write(public_root / "theorems.jsonl", public)
    _write(public_root / "bodies.jsonl", [_body_obj(item) for item in bodies])
    np.save(public_root / "body-vectors.npy", np.asarray(vectors, dtype=np.float32))
    _write(gold_root / "gold.jsonl", gold)
    return {"theorems": theorem_count, "bodies": len(bodies), "public_sha256": hashlib.sha256((public_root / "theorems.jsonl").read_bytes()).hexdigest()}
