"""G2.6 conversion from selected candidates to validated FieldIR programs."""

from __future__ import annotations

import hashlib

from topology_field_ir import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
    validate_program,
)
from topology_field_ir.validate import registry_digest

from .decoder import GoldenAtomInput, StructuredCandidate


def atom_input(atom: GoldenAtom) -> GoldenAtomInput:
    return GoldenAtomInput(atom.atom_id, atom.kind)


def build_program(
    *, program_id: str, atoms: tuple[GoldenAtom, ...], vector_spaces: tuple[VectorSpaceSpec, ...], candidate: StructuredCandidate,
    context: FieldContext, provenance_sha256: str, operator_vector: VectorRef | None = None,
) -> FieldProgram | None:
    """Build one atomic FieldIR program; null actions deliberately commit nothing."""
    if candidate.disposition != "accept" or candidate.relation_type is None:
        return None
    factor_id = "g26-factor-" + hashlib.sha256(
        repr((program_id, candidate.relation_type, candidate.role_bindings, provenance_sha256)).encode()
    ).hexdigest()[:24]
    program = FieldProgram(
        program_id,
        registry_digest(),
        vector_spaces,
        atoms,
        (TypedFactor(factor_id, candidate.relation_type, candidate.role_bindings, context, provenance_sha256, operator_vector=operator_vector),),
    )
    validate_program(program)
    return program
