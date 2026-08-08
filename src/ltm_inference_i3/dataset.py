"""Split-disjoint formal theorem generation for I3."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .formal import (
    apply_schema,
    c,
    e,
    expression_hash,
    expression_size,
    iter_paths,
    standard_axioms,
    v,
)
from .schemas import (
    AxiomSchema,
    FormalExpression,
    FormalProofStep,
    FormalProposition,
    MathRealityManifest,
    TheoremProblem,
)

DIMENSION = 384
_FAMILIES = ("ring", "sets", "logic", "modular", "order", "equality")
_SIMPLIFIERS = {
    "ring": ("ring.add_zero", "ring.zero_add", "ring.mul_one", "ring.one_mul", "ring.double_neg", "ring.mul_zero"),
    "sets": ("set.union_empty", "set.empty_union", "set.inter_universe"),
    "logic": ("logic.and_true_right", "logic.and_true_left", "logic.or_false_right", "logic.or_false_left", "logic.double_not"),
    "modular": ("mod.add_zero", "mod.mul_one"),
    "order": ("order.add_left", "order.add_right"),
    "equality": ("eq.substitution",),
}


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def expr_to_obj(value: FormalExpression) -> dict[str, object]:
    return {"op": value.op, "args": [expr_to_obj(item) for item in value.args], "value": value.value}


def expr_from_obj(value: dict[str, object]) -> FormalExpression:
    return FormalExpression(str(value["op"]), tuple(expr_from_obj(item) for item in value["args"]), value["value"] if value["value"] is None else str(value["value"]))


def proposition_to_obj(value: FormalProposition) -> dict[str, object]:
    return {"relation": value.relation, "left": expr_to_obj(value.left), "right": expr_to_obj(value.right)}


def proposition_from_obj(value: dict[str, object]) -> FormalProposition:
    return FormalProposition(str(value["relation"]), expr_from_obj(value["left"]), expr_from_obj(value["right"]))


def axiom_to_obj(value: AxiomSchema) -> dict[str, object]:
    return {"axiom_id": value.axiom_id, "family": value.family, "left": expr_to_obj(value.left), "right": expr_to_obj(value.right), "reversible": value.reversible, "reality_key": value.reality_key}


def axiom_from_obj(value: dict[str, object]) -> AxiomSchema:
    return AxiomSchema(str(value["axiom_id"]), str(value["family"]), expr_from_obj(value["left"]), expr_from_obj(value["right"]), bool(value["reversible"]), str(value["reality_key"]))


def _feature(value: FormalExpression) -> np.ndarray:
    """A deterministic structural coordinate without a target/proof channel."""
    vector = np.zeros(DIMENSION, dtype=np.float32)
    for path, item in iter_paths(value):
        digest = hashlib.sha256(repr((item.op, item.value, len(path), len(item.args))).encode()).digest()
        index = int.from_bytes(digest[:2], "little") % DIMENSION
        vector[index] += 1.0 / (1 + len(path))
    vector /= max(float(np.linalg.norm(vector)), 1e-8)
    return vector


def _base(family: str, token: str) -> FormalExpression:
    atom = v(token)
    if family == "modular":
        return e("mod", atom, c(7))
    if family == "order":
        return e("lt", atom, v(f"{token}b"))
    return atom


def _expand(goal: FormalExpression, family: str, depth: int, rng: random.Random, axioms: dict[str, AxiomSchema]) -> tuple[FormalExpression, tuple[FormalProofStep, ...]]:
    """Create a valid proof by applying simplifiers backward from a simple goal."""
    current = goal
    reverse_trace: list[FormalProofStep] = []
    choices = _SIMPLIFIERS[family]
    for step in range(depth):
        axiom_id = choices[step % len(choices)]
        schema = axioms[axiom_id]
        candidates = []
        for path, _ in iter_paths(current):
            changed = apply_schema(current, schema, path, True)
            if changed is not None and changed != current and expression_size(changed) <= 96:
                candidates.append((path, changed))
        if not candidates:
            continue
        path, changed = candidates[rng.randrange(len(candidates))]
        reverse_trace.append(FormalProofStep(axiom_id, path, True, current, changed))
        current = changed
    # Runtime starts with current and applies the inverse trace forward.
    forward = tuple(FormalProofStep(item.axiom_id, item.path, False, item.after, item.before) for item in reversed(reverse_trace))
    return current, forward


def _problem(split: str, index: int, depth: int, family: str, rng: random.Random, axioms: dict[str, AxiomSchema], category: str) -> tuple[dict[str, object], dict[str, object]]:
    goal_term = _base(family, f"{split}_v_{index}")
    start, trace = _expand(goal_term, family, depth, rng, axioms)
    proposition = FormalProposition("eq", start, goal_term)
    proof_status = "proved"
    if category == "unknown":
        proposition = FormalProposition("eq", start, _base(family, f"{split}_unknown_{index}"))
        trace = ()
        proof_status = "unknown"
    elif category == "refuted":
        # An exact negative premise is intentionally public and produces a
        # refutation, never an unsupported positive proof.
        proposition = FormalProposition("eq", start, _base(family, f"{split}_refuted_{index}"))
        trace = ()
        proof_status = "refuted"
    assumptions: tuple[FormalProposition, ...] = (FormalProposition("eq", start, start),)
    if category == "refuted":
        assumptions = assumptions + (FormalProposition("neq", proposition.left, proposition.right),)
    public = {
        "problem_id": f"{split}:theorem:{index:07d}",
        "assumptions": [proposition_to_obj(item) for item in assumptions],
        "goal": proposition_to_obj(proposition),
        "reality_key": "standard-v1",
        "maximum_bodies": 64,
        "maximum_steps": min(64, max(2, depth + 4)),
    }
    gold = {
        "problem_id": public["problem_id"],
        "status": proof_status,
        "proof": [{"axiom_id": item.axiom_id, "path": item.path, "reverse": item.reverse, "before": expr_to_obj(item.before), "after": expr_to_obj(item.after)} for item in trace],
        "required_axiom_ids": [item.axiom_id for item in trace],
        "depth": len(trace),
        "family": family,
        "goal_hash": expression_hash(proposition.right),
    }
    return public, gold


def _counts(total: int, locked: bool) -> tuple[str, ...]:
    if not locked:
        return tuple("proved" for _ in range(total))
    proved = int(total * .75)
    refuted = int(total * .125)
    return tuple(["proved"] * proved + ["refuted"] * refuted + ["unknown"] * (total - proved - refuted))


def build_axiom_bank(workspace: Path) -> dict[str, object]:
    axioms = standard_axioms()
    manifest = MathRealityManifest("standard-v1", "1", tuple(item.axiom_id for item in axioms), hashlib.sha256(repr(tuple(item.axiom_id for item in axioms)).encode()).hexdigest())
    root = workspace / "axiom-bank"
    root.mkdir(parents=True, exist_ok=True)
    (root / "standard-v1.json").write_text(json.dumps({"manifest": asdict(manifest), "axioms": [axiom_to_obj(item) for item in axioms]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"axioms": len(axioms), "manifest_hash": manifest.profile_hash}


def build_split(workspace: Path, split: str, count: int, seed: int, *, locked: bool = False, stress: bool = False) -> dict[str, object]:
    axioms = {item.axiom_id: item for item in standard_axioms()}
    rng = random.Random(seed)
    categories = _counts(count, locked)
    public_rows: list[dict[str, object]] = []
    gold_rows: list[dict[str, object]] = []
    for index, category in enumerate(categories):
        family = _FAMILIES[index % len(_FAMILIES)]
        if stress:
            depth = 17 + (index % 48)
        else:
            band = index % 20
            depth = 2 + (index % 3) if band < 8 else 5 + (index % 4) if band < 15 else 9 + (index % 8)
        public, gold = _problem(split, index, depth, family, rng, axioms, category)
        public_rows.append(public)
        gold_rows.append(gold)
    public_root = workspace / "public" / split
    gold_root = workspace / "evaluator-gold" / split
    _write_jsonl(public_root / "theorems.jsonl", tuple(public_rows))
    _write_jsonl(gold_root / "gold.jsonl", tuple(gold_rows))
    # The public field consists of neutral axiom bodies plus many opaque
    # duplicates/distractors; no body contains a theorem target or trace.
    bodies = []
    vectors = []
    for index in range(50_000):
        axiom = standard_axioms()[index % len(standard_axioms())]
        body_id = f"{split}:body:{index:07d}"
        bodies.append({"body_id": body_id, "axiom_id": axiom.axiom_id, "reality_key": "standard-v1", "vector_ref": index, "body_hash": hashlib.sha256(f"{body_id}|{axiom.axiom_id}".encode()).hexdigest()})
        vectors.append(_feature(axiom.left) + .1 * _feature(axiom.right))
    np.save(public_root / "body-vectors.npy", np.asarray(vectors, dtype=np.float32))
    _write_jsonl(public_root / "bodies.jsonl", tuple(bodies))
    return {"split": split, "theorems": count, "public_hash": hashlib.sha256((public_root / "theorems.jsonl").read_bytes()).hexdigest(), "gold_hash": hashlib.sha256((gold_root / "gold.jsonl").read_bytes()).hexdigest()}


def problem_from_obj(value: dict[str, object]) -> TheoremProblem:
    return TheoremProblem(str(value["problem_id"]), tuple(proposition_from_obj(item) for item in value["assumptions"]), proposition_from_obj(value["goal"]), str(value["reality_key"]), int(value["maximum_bodies"]), int(value["maximum_steps"]))


def expression_feature(value: FormalExpression) -> np.ndarray:
    return _feature(value)
