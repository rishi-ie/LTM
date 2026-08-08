from __future__ import annotations

import hashlib
from dataclasses import replace

from topology_field_ir import (
    FieldContext,
    FieldProgram,
    GoldenAtom,
    TypedFactor,
    VectorRef,
    VectorSpaceSpec,
)
from topology_field_ir.validate import registry_digest
from topology_field_r1 import (
    from_fieldir,
    numeric_digest,
    read_program,
    text_free_g1,
    to_fieldir,
    write_program,
)
from topology_g1.engine import execute
from topology_g1.schemas import ExecutionState


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _program() -> FieldProgram:
    context = FieldContext("global", "positive", "asserted", None, None, 1.0, 1.0)
    atoms = (
        GoldenAtom("a", "claim", "first", "first", "source", 0, 5, context, _sha("source")),
        GoldenAtom("b", "claim", "second", "second", "source", 6, 12, context, _sha("source")),
    )
    factor = TypedFactor("f", "implies", (("premise", ("a",)), ("conclusion", ("b",))), context, _sha("source"))
    return FieldProgram("program", registry_digest(), (), atoms, (factor,))


def test_numeric_round_trip_preserves_fieldir() -> None:
    original = _program()
    numeric, archive = from_fieldir(original)
    rebuilt = to_fieldir(numeric, archive)
    assert rebuilt == original
    assert numeric_digest(numeric)
    assert all("first" not in repr(item) and "second" not in repr(item) for item in numeric.atoms)


def test_text_free_g1_executes_without_archive() -> None:
    numeric, _archive = from_fieldir(_program())
    nodes, relations = text_free_g1(numeric)
    state = ExecutionState(frozenset({nodes[0].node_id}), scope_id=relations[0].scope_id)
    derivations, _contribution, _updated = execute(relations[0], {node.node_id: node for node in nodes}, state)
    assert derivations[0].conclusion_id == nodes[1].node_id


def test_role_swap_changes_numeric_digest() -> None:
    first, _archive = from_fieldir(_program())
    original = _program()
    changed_factor = TypedFactor("f", "implies", (("premise", ("b",)), ("conclusion", ("a",))), original.atoms[0].context, _sha("source"))
    second, _archive = from_fieldir(FieldProgram("program", registry_digest(), (), original.atoms, (changed_factor,)))
    assert numeric_digest(first) != numeric_digest(second)


def test_source_text_does_not_change_numeric_digest() -> None:
    original = _program()
    first, _archive = from_fieldir(original)
    changed = replace(
        original,
        atoms=tuple(replace(atom, canonical_text="different", occurrence_text="different") for atom in original.atoms),
    )
    second, _archive = from_fieldir(changed)
    assert numeric_digest(first) == numeric_digest(second)


def test_context_change_changes_numeric_digest() -> None:
    original = _program()
    first, _archive = from_fieldir(original)
    context = replace(original.factors[0].context, polarity="negative")
    changed = replace(original, factors=(replace(original.factors[0], context=context),))
    second, _archive = from_fieldir(changed)
    assert numeric_digest(first) != numeric_digest(second)


def test_active_serialization_does_not_contain_text(tmp_path) -> None:
    numeric, archive = from_fieldir(_program())
    path = tmp_path / "field.ltmf.json"
    write_program(path, numeric, archive)
    assert "first" not in path.read_text()
    restored, restored_archive = read_program(path)
    assert restored == numeric
    assert restored_archive == archive


def test_vector_references_survive_numeric_round_trip() -> None:
    original = _program()
    digest = _sha("sidecar"); row = _sha("row")
    ref = VectorRef("atom-vector", "semantic", digest, 3, row)
    program = FieldProgram(
        original.program_id,
        original.registry_sha256,
        (VectorSpaceSpec("semantic", "v1", _sha("encoder"), 2),),
        (replace(original.atoms[0], canonical_vector=ref), original.atoms[1]),
        original.factors,
    )
    numeric, archive = from_fieldir(program)
    assert to_fieldir(numeric, archive) == program
