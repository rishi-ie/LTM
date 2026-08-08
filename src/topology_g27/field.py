"""Exact G1 and FieldIR handoff for coordinate graph candidates."""

from __future__ import annotations

import hashlib

from topology_field_ir import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorSpaceSpec,
    validate_program,
)
from topology_field_ir.validate import registry_digest

from .schemas import CoordinateGraphCandidate


def build_program(program_id: str, atoms: tuple[GoldenAtom, ...], candidate: CoordinateGraphCandidate, provenance: str, operator_coordinate: tuple[float, ...] = ()) -> FieldProgram | None:
    if candidate.disposition != "accept" or not candidate.relation_set:
        return None
    spaces = (
        VectorSpaceSpec("g27-content", "1", hashlib.sha256(b"g27-content").hexdigest(), 384),
        VectorSpaceSpec("g27-operator-coordinate", "1", hashlib.sha256(b"g27-operator-coordinate").hexdigest(), 18, normalized=False),
        VectorSpaceSpec("g27-role", "1", hashlib.sha256(b"g27-role").hexdigest(), 64),
        VectorSpaceSpec("g27-binding", "1", hashlib.sha256(b"g27-binding").hexdigest(), 128),
    )
    by_relation: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for role, ids in candidate.role_bindings:
        relation, plain_role = role.split(":", 1) if ":" in role else (candidate.relation_set[0], role)
        by_relation.setdefault(relation, []).append((plain_role, ids))
    factors = []
    for relation in candidate.relation_set:
        bindings = tuple(by_relation.get(relation, ()))
        if not bindings:
            return None
        factors.append(TypedFactor("g27-" + hashlib.sha256(f"{program_id}:{relation}:{bindings}".encode()).hexdigest()[:24], relation, bindings, FieldContext(candidate.context.scope_id, candidate.context.polarity, candidate.context.modality, candidate.context.valid_from, candidate.context.valid_to, candidate.probability, 1.0), provenance))
    program = FieldProgram(program_id, registry_digest(), spaces, atoms, tuple(factors))
    validate_program(program)
    return program
