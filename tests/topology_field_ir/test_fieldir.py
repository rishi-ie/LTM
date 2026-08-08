from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from topology_field_ir import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
    artifact_digest,
    capability,
    semantic_digest,
    to_g1,
    validate_program,
    verify_vector_artifacts,
    write_vector_sidecar,
)
from topology_field_ir.validate import registry_digest


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _program() -> FieldProgram:
    context = FieldContext("global", "positive", "asserted", None, None, 1, 1)
    atoms = (
        GoldenAtom("a", "claim", "first", "first", "s", 0, 5, context, _sha("source")),
        GoldenAtom("b", "claim", "second", "second", "s", 6, 12, context, _sha("source")),
    )
    return FieldProgram("p", registry_digest(), (), atoms, (TypedFactor("f", "implies", (("premise", ("a",)), ("conclusion", ("b",))), context, _sha("source")),))


def test_typed_program_projects_to_g1() -> None:
    program = _program()
    validate_program(program)
    nodes, relations = to_g1(program)
    assert len(nodes) == 2
    assert relations[0].relation_type == "implies"
    assert capability(program.factors[0]).g6_rule is not None


def test_semantic_digest_ignores_vector_artifacts() -> None:
    program = _program()
    changed = FieldProgram(program.program_id, program.registry_sha256, (VectorSpaceSpec("semantic", "v2", _sha("encoder"), 2),), program.atoms, program.factors)
    assert semantic_digest(program) == semantic_digest(changed)
    assert artifact_digest(program) != artifact_digest(changed)


def test_vector_sidecar_checks_row_hash(tmp_path) -> None:
    path = tmp_path / "v.fvec"
    digest, rows = write_vector_sidecar(path, ((1.0, 0.0),), 2)
    from topology_field_ir import read_vector_sidecar

    assert read_vector_sidecar(path, digest, 0, rows[0]) == pytest.approx((1.0, 0.0))
    with pytest.raises(ValueError, match="row hash"):
        read_vector_sidecar(path, digest, 0, _sha("wrong"))


def test_program_verifies_referenced_normalized_sidecar(tmp_path) -> None:
    path = tmp_path / "v.fvec"
    digest, rows = write_vector_sidecar(path, ((1.0, 0.0),), 2)
    program = _program()
    atom = program.atoms[0]
    ref = VectorRef("a:semantic", "semantic", digest, 0, rows[0])
    program = FieldProgram(
        program.program_id,
        program.registry_sha256,
        (VectorSpaceSpec("semantic", "v1", _sha("encoder"), 2),),
        (replace(atom, canonical_vector=ref), program.atoms[1]),
        program.factors,
    )
    verify_vector_artifacts(program, {digest: path})
