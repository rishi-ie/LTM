"""Exact proposal construction used by L4 runtime, never by model authority."""

from __future__ import annotations

import hashlib

from ltm_inference_i3.formal import (
    at_path,
    expression_hash,
    expression_key,
    instantiate,
    iter_paths,
    match,
    replace_at,
)
from ltm_inference_i3.schemas import AxiomSchema, FormalExpression

from .axioms import REALITY, executable_axioms
from .schemas import Proposal

ARITIES = {
    "var": 0,
    "int": 0,
    "symbol": 0,
    "empty": 0,
    "universe": 0,
    "true": 0,
    "false": 0,
    "neg": 1,
    "not": 1,
    "substitute": 1,
    "add": 2,
    "mul": 2,
    "eq": 2,
    "neq": 2,
    "lt": 2,
    "le": 2,
    "mod": 2,
    "divides": 2,
    "union": 2,
    "inter": 2,
    "and": 2,
    "or": 2,
}


def well_formed(value: FormalExpression) -> bool:
    if value.op == "bundle":
        return bool(value.args) and all(well_formed(item) for item in value.args)
    expected = ARITIES.get(value.op)
    if expected is None or len(value.args) != expected:
        return False
    if expected == 0 and value.op in {"var", "int", "symbol"} and value.value is None:
        return False
    return all(well_formed(item) for item in value.args)


def _binding_hash(bindings: dict[str, FormalExpression]) -> str:
    payload = tuple(sorted((key, expression_key(value)) for key, value in bindings.items()))
    return hashlib.sha256(repr(payload).encode()).hexdigest()


def enumerate_proposals(
    value: FormalExpression,
    *,
    reality_key: str = REALITY,
    schemas: tuple[AxiomSchema, ...] | None = None,
) -> tuple[Proposal, ...]:
    if reality_key != REALITY or not well_formed(value):
        return ()
    rows: list[Proposal] = []
    for schema in schemas or executable_axioms():
        if schema.reality_key != reality_key:
            continue
        for path, _ in iter_paths(value):
            for reverse in ((False, True) if schema.reversible else (False,)):
                source, target = (schema.right, schema.left) if reverse else (schema.left, schema.right)
                bindings = match(source, at_path(value, path))
                if bindings is None:
                    continue
                after = replace_at(value, path, instantiate(target, bindings))
                if expression_key(after) == expression_key(value) or not well_formed(after):
                    continue
                rows.append(
                    Proposal(
                        schema.axiom_id,
                        f"{REALITY}:axiom:{schema.axiom_id}",
                        path,
                        reverse,
                        after,
                        _binding_hash(bindings),
                    )
                )
    unique = {
        (item.axiom_id, item.path, item.reverse, expression_hash(item.after)): item for item in rows
    }
    return tuple(unique[key] for key in sorted(unique))


def proposal_count(value: FormalExpression, *, reality_key: str = REALITY) -> int:
    """Count legal local applications without materializing whole-field successors."""
    if reality_key != REALITY or not well_formed(value):
        return 0
    count = 0
    for schema in executable_axioms():
        for _, local in iter_paths(value):
            for reverse in ((False, True) if schema.reversible else (False,)):
                source, target = (schema.right, schema.left) if reverse else (schema.left, schema.right)
                bindings = match(source, local)
                if bindings is None:
                    continue
                if expression_key(instantiate(target, bindings)) != expression_key(local):
                    count += 1
    return count


def explicit_refutation(source: FormalExpression, goal: FormalExpression) -> bool:
    return (
        source.op == "neq"
        and goal.op == "eq"
        and len(source.args) == 2
        and source.args == goal.args
    )
