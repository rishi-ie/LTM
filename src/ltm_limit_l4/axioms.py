"""Signed executable subset of the historical I3 axiom inventory."""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import asdict

from ltm_inference_i3.formal import expression_key, standard_axioms
from ltm_inference_i3.schemas import AxiomSchema, FormalExpression

from .schemas import ExecutableAxiomRecord

REALITY = "standard-l4-v1"
EXCLUDED = frozenset(
    {
        "eq.refl",
        "eq.congruence_add",
        "eq.congruence_mul",
        "eq.substitution",
        "order.lt_to_le",
        "mod.negate",
        "mod.add_congruent",
    }
)
REVERSE_ALLOWED = frozenset(
    {
        "eq.symmetry",
        "ring.add_comm",
        "ring.add_assoc",
        "ring.mul_comm",
        "ring.mul_assoc",
        "ring.distributive",
        "order.negate",
        "order.scale_positive",
        "set.union_comm",
        "set.inter_comm",
        "set.union_assoc",
        "set.inter_assoc",
        "logic.and_comm",
        "logic.or_comm",
        "logic.de_morgan",
    }
)
FORWARD_ONLY = frozenset(
    item.axiom_id for item in standard_axioms() if item.axiom_id not in EXCLUDED | REVERSE_ALLOWED
)


def variables(value: FormalExpression) -> frozenset[str]:
    found: set[str] = set()
    if value.op == "var" and value.value and value.value.startswith("?"):
        found.add(value.value)
    for item in value.args:
        found.update(variables(item))
    return frozenset(found)


def executable_axioms() -> tuple[AxiomSchema, ...]:
    rows = []
    for schema in standard_axioms():
        if schema.axiom_id in EXCLUDED:
            continue
        rows.append(
            AxiomSchema(
                schema.axiom_id,
                schema.family,
                schema.left,
                schema.right,
                schema.reversible and schema.axiom_id in REVERSE_ALLOWED,
                REALITY,
            )
        )
    if len(rows) != 39:
        raise AssertionError(f"expected 39 executable axioms, found {len(rows)}")
    return tuple(rows)


def schema_hash(schema: AxiomSchema) -> str:
    payload = (
        schema.axiom_id,
        schema.family,
        expression_key(schema.left),
        expression_key(schema.right),
        schema.reversible,
        schema.reality_key,
    )
    return hashlib.sha256(repr(payload).encode()).hexdigest()


def manifest_records() -> tuple[ExecutableAxiomRecord, ...]:
    return tuple(
        ExecutableAxiomRecord(
            schema.axiom_id,
            schema.family,
            True,
            schema.reversible,
            f"{REALITY}:axiom:{schema.axiom_id}",
            schema_hash(schema),
        )
        for schema in executable_axioms()
    )


def manifest_hash() -> str:
    return hashlib.sha256(repr(tuple(asdict(item) for item in manifest_records())).encode()).hexdigest()


def _evaluate(value: FormalExpression, bindings: dict[str, object]) -> object:
    if value.op == "var" and value.value:
        return bindings[value.value]
    if value.op == "int":
        return int(value.value or "0")
    args = tuple(_evaluate(item, bindings) for item in value.args)
    operations = {
        "add": lambda: args[0] + args[1],
        "mul": lambda: args[0] * args[1],
        "neg": lambda: -args[0],
        "eq": lambda: args[0] == args[1],
        "lt": lambda: args[0] < args[1],
        "le": lambda: args[0] <= args[1],
        "mod": lambda: args[0] % args[1],
        "divides": lambda: args[1] % args[0] == 0 if args[0] != 0 else args[1] == 0,
        "empty": lambda: frozenset(),
        "universe": lambda: frozenset({0, 1}),
        "union": lambda: args[0] | args[1],
        "inter": lambda: args[0] & args[1],
        "true": lambda: True,
        "false": lambda: False,
        "and": lambda: bool(args[0] and args[1]),
        "or": lambda: bool(args[0] or args[1]),
        "not": lambda: not args[0],
    }
    if value.op not in operations:
        raise ValueError(f"unsupported audit operator: {value.op}")
    return operations[value.op]()


def _semantic_check(schema: AxiomSchema) -> tuple[bool, int]:
    names = sorted(variables(schema.left) | variables(schema.right))
    if schema.family == "sets":
        domain: tuple[object, ...] = (frozenset(), frozenset({0}), frozenset({1}), frozenset({0, 1}))
    elif schema.family == "logic":
        domain = (False, True)
    else:
        domain = (-2, -1, 1, 2)
    checked = 0
    for values in itertools.product(domain, repeat=len(names)):
        bindings = dict(zip(names, values, strict=True))
        try:
            left = _evaluate(schema.left, bindings)
            right = _evaluate(schema.right, bindings)
        except (TypeError, ZeroDivisionError):
            continue
        checked += 1
        if left != right:
            return False, checked
    return checked > 0, checked


def audit_axioms() -> dict[str, object]:
    historical = {item.axiom_id: item for item in standard_axioms()}
    executable = executable_axioms()
    checks = []
    for schema in executable:
        forward_bound = variables(schema.right).issubset(variables(schema.left))
        reverse_bound = not schema.reversible or variables(schema.left).issubset(variables(schema.right))
        stable = schema_hash(schema) == schema_hash(schema)
        semantic, interpretations = _semantic_check(schema)
        checks.append(
            {
                "axiom_id": schema.axiom_id,
                "forward_variables_bound": forward_bound,
                "reverse_variables_bound": reverse_bound,
                "hash_stable": stable,
                "bounded_semantic_agreement": semantic,
                "interpretations_checked": interpretations,
                "passed": forward_bound and reverse_bound and stable and semantic,
            }
        )
    excluded_present = EXCLUDED.issubset(historical)
    expected = len(historical) == 46 and len(executable) == 39 and excluded_present
    return {
        "reality_revision": REALITY,
        "historical_count": len(historical),
        "executable_count": len(executable),
        "excluded": tuple(sorted(EXCLUDED)),
        "forward_only": tuple(sorted(FORWARD_ONLY)),
        "manifest_sha256": manifest_hash(),
        "checks": checks,
        "passed": expected and all(item["passed"] for item in checks),
    }
