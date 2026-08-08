"""Leakage-resistant branching theorem generator for L4."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ltm_inference_i3.formal import at_path, expression_hash, expression_size, instantiate, match
from ltm_inference_i3.schemas import AxiomSchema, FormalExpression

from .axioms import REALITY, executable_axioms
from .codec import problem_to_obj, step_to_obj, write_jsonl
from .exact import proposal_count
from .schemas import ExactAxiomApplication, L4Problem, L4ProofStep

# Schemas with simple, independently local effects. More complex schemas remain
# executable distractors and are exercised by audit/attack tests.
FAMILY_SCHEMAS = {
    "equality": ("eq.symmetry",),
    "ring": ("ring.add_zero", "ring.zero_add", "ring.mul_one", "ring.one_mul", "ring.double_neg"),
    "order": ("order.negate", "order.scale_positive"),
    "modular": ("mod.add_zero", "mod.mul_one", "divides.negate"),
    "sets": ("set.union_empty", "set.empty_union", "set.inter_universe"),
    "logic": ("logic.and_true_right", "logic.and_true_left", "logic.or_false_right", "logic.double_not"),
}
FAMILIES = tuple(FAMILY_SCHEMAS)
BRANCHES = (2, 4, 8, 16, 32)


def _vars(value: FormalExpression) -> frozenset[str]:
    found: set[str] = set()
    if value.op == "var" and value.value:
        found.add(value.value)
    for item in value.args:
        found.update(_vars(item))
    return frozenset(found)


def _instance(schema: AxiomSchema, token: str) -> tuple[FormalExpression, FormalExpression]:
    bindings = {
        name: FormalExpression("symbol", value=f"s_{token}_{offset}")
        for offset, name in enumerate(sorted(_vars(schema.left) | _vars(schema.right)))
    }
    return instantiate(schema.left, bindings), instantiate(schema.right, bindings)


def _application(before: FormalExpression, after: FormalExpression, schema: AxiomSchema, path: tuple[int, ...]) -> ExactAxiomApplication:
    bindings = match(schema.left, at_path(before, path))
    if bindings is None:
        raise AssertionError("generated step does not match its schema")
    substitution_hash = hashlib.sha256(
        repr(tuple(sorted((key, expression_hash(value)) for key, value in bindings.items()))).encode()
    ).hexdigest()
    return ExactAxiomApplication(
        f"{REALITY}:axiom:{schema.axiom_id}",
        schema.axiom_id,
        path,
        False,
        substitution_hash,
        expression_hash(before),
        expression_hash(after),
    )


def _opaque_id(split: str, serial: int, seed: int) -> str:
    digest = hashlib.sha256(f"{split}|{serial}|{seed}".encode()).hexdigest()[:20]
    return f"l4:{split}:{digest}"


def _problem(
    split: str,
    serial: int,
    seed: int,
    *,
    depth: int,
    branching: int,
    family: str,
    status: str = "proved",
    detour: bool = False,
    pair_side: int | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    schemas = {item.axiom_id: item for item in executable_axioms()}
    problem_id = _opaque_id(split, serial, seed)
    token_base = _opaque_id(split, serial // 2, seed)[-8:] if pair_side is not None else problem_id[-8:]
    schema_serial = serial // 2 if pair_side is not None else serial
    if status == "unknown":
        source = FormalExpression("symbol", value=f"u_{problem_id[-8:]}")
        goal = FormalExpression("symbol", value=f"v_{problem_id[-8:]}")
        problem = L4Problem(problem_id, source, goal, REALITY)
        return problem_to_obj(problem), {
            "problem_id": problem_id,
            "status": "unknown",
            "depth": 0,
            "proof": [],
            "family": family,
            "branching": branching,
            "paired": False,
            "detour": False,
            "shortest_certified": True,
        }
    if status == "refuted":
        left = FormalExpression("symbol", value=f"r_{problem_id[-8:]}")
        right = FormalExpression("symbol", value=f"q_{problem_id[-8:]}")
        source = FormalExpression("neq", (left, right))
        goal = FormalExpression("eq", (left, right))
        problem = L4Problem(problem_id, source, goal, REALITY)
        return problem_to_obj(problem), {
            "problem_id": problem_id,
            "status": "refuted",
            "depth": 0,
            "proof": [],
            "family": family,
            "branching": branching,
            "paired": False,
            "detour": False,
            "shortest_certified": True,
        }

    names = FAMILY_SCHEMAS[family]
    target_count = depth * 2 if pair_side is not None else depth
    components: list[FormalExpression] = []
    replacements: list[FormalExpression] = []
    component_schemas: list[AxiomSchema] = []
    for index in range(target_count):
        axiom_id = names[(schema_serial + index) % len(names)]
        schema = schemas[axiom_id]
        left, right = _instance(schema, f"{token_base}_{index}")
        if detour and index == 0 and family == "ring":
            schema = schemas["ring.distributive"]
            left, right = _instance(schema, f"{token_base}_detour")
        components.append(left)
        replacements.append(right)
        component_schemas.append(schema)

    distractors = max(0, branching - target_count)
    for index in range(distractors):
        other_family = FAMILIES[(FAMILIES.index(family) + index + 1) % len(FAMILIES)]
        schema = schemas[FAMILY_SCHEMAS[other_family][index % len(FAMILY_SCHEMAS[other_family])]]
        left, _ = _instance(schema, f"{token_base}_d_{index}")
        components.append(left)

    source = FormalExpression("bundle", tuple(components))
    goal_parts = list(components)
    selected = range(depth) if pair_side in (None, 0) else range(depth, depth * 2)
    for index in selected:
        goal_parts[index] = replacements[index]
    goal = FormalExpression("bundle", tuple(goal_parts))
    current = source
    proof: list[L4ProofStep] = []
    for index in selected:
        next_parts = list(current.args)
        next_parts[index] = replacements[index]
        after = FormalExpression("bundle", tuple(next_parts))
        application = _application(current, after, component_schemas[index], (index,))
        proof.append(L4ProofStep(application, current, after))
        current = after
    legal = proposal_count(source)
    if legal > 128:
        raise RuntimeError(f"proposal budget exceeded for {problem_id}: {legal}")
    if current != goal or len(proof) != depth:
        raise AssertionError("invalid generated proof")
    problem = L4Problem(problem_id, source, goal, REALITY, min(64, max(depth + 4, 8)))
    gold = {
        "problem_id": problem_id,
        "status": "proved",
        "depth": depth,
        "proof": [step_to_obj(item) for item in proof],
        "family": family,
        "branching": branching,
        "paired": pair_side is not None,
        "pair_side": pair_side,
        "detour": detour,
        "shortest_certified": True,
        "source_goal_component_distance": sum(a != b for a, b in zip(source.args, goal.args, strict=True)),
        "source_legal_proposals": legal,
        "temporary_growth": any(expression_size(item.after) > expression_size(item.before) for item in proof),
    }
    return problem_to_obj(problem), gold


def build_split(path: Path, split: str, count: int, seed: int, *, locked: bool = False, stress: bool = False) -> dict[str, object]:
    public: list[dict[str, object]] = []
    gold: list[dict[str, object]] = []
    proved = count if not locked and not stress else int(count * (0.75 if locked else 1.0))
    refuted = 0 if not locked or stress else count // 8
    for index in range(count):
        status = "proved" if index < proved else "refuted" if index < proved + refuted else "unknown"
        paired = status == "proved" and index < min(800, proved)
        basis = index // 2 if paired else index
        family = FAMILIES[basis % len(FAMILIES)]
        branching = BRANCHES[(basis // len(FAMILIES)) % len(BRANCHES)]
        if stress:
            depth = 17 + basis % 29
        elif locked:
            band = basis % 4
            depth = (2 + basis % 3, 5 + basis % 4, 9 + basis % 4, 13 + basis % 4)[band]
        else:
            depth = 2 + basis % 15
        pair_side = index % 2 if paired else None
        detour = status == "proved" and family == "ring" and basis % 5 == 0
        row, expected = _problem(
            split,
            index,
            seed,
            depth=depth,
            branching=branching,
            family=family,
            status=status,
            detour=detour,
            pair_side=pair_side,
        )
        public.append(row)
        gold.append(expected)
    root = path / split
    write_jsonl(root / "public.jsonl", tuple(public))
    write_jsonl(root / "evaluator-gold.jsonl", tuple(gold))
    public_hash = hashlib.sha256((root / "public.jsonl").read_bytes()).hexdigest()
    gold_hash = hashlib.sha256((root / "evaluator-gold.jsonl").read_bytes()).hexdigest()
    return {"split": split, "cases": count, "public_sha256": public_hash, "gold_sha256": gold_hash}


def build_manifest(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    payload = tuple(tuple(sorted(row.items())) for row in rows)
    return {"splits": rows, "manifest_sha256": hashlib.sha256(repr(payload).encode()).hexdigest()}
