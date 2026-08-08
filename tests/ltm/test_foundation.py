from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import torch

from ltm.adapters import config_from_g1, from_g1, to_g1
from ltm.codec import (
    artifact_hash,
    factor_record_size,
    pack_program,
    read_manifest,
    semantic_hash,
    verify_packed,
)
from ltm.schema import VectorRef
from topology_g1.codec import canonical_json
from topology_g1.fixtures import fixtures
from topology_g25.assembly import assemble_handoff
from topology_g25.dataset import generate_kernel_examples
from topology_g25.field import make_factor


def test_g1_round_trip_and_numeric_packing(tmp_path):
    fixture = fixtures("development")[0]
    program, archive = from_g1(fixture.nodes, (fixture.relation,))
    nodes, relations = to_g1(program, archive)
    assert canonical_json(nodes) == canonical_json(fixture.nodes)
    assert canonical_json(relations) == canonical_json((fixture.relation,))
    assert factor_record_size() == 64
    manifest = pack_program(tmp_path, program, archive)
    assert read_manifest(tmp_path) == manifest
    verify_packed(tmp_path, manifest)
    assert not any(fixture.nodes[0].node_id.encode() in (tmp_path / f"{name}.bin").read_bytes() for name in ("symbols", "atoms", "factors", "bindings", "contexts", "provenance"))


def test_semantic_hash_excludes_vector_artifacts_and_preserves_order():
    fixture = fixtures("development")[0]
    program, _archive = from_g1(fixture.nodes, (fixture.relation,))
    vector = VectorRef("content:0", "content", "0" * 64, 0, "1" * 64)
    with_vector = replace(program, vectors=(vector,))
    assert semantic_hash(with_vector) == semantic_hash(program)
    assert artifact_hash(with_vector) != artifact_hash(program)
    reversed_program, _ = from_g1(tuple(reversed(fixture.nodes)), (fixture.relation,), config_from_g1())
    assert semantic_hash(reversed_program) == semantic_hash(program)


def test_g25_handoff_is_accepted_into_numeric_field(tmp_path: Path):
    from ltm.adapters import from_g25_handoff

    example = next(item for item in generate_kernel_examples("train") if item.relation_type == "implies")
    slots = sum(len(atom_ids) for _, atom_ids in example.role_bindings)
    factor = make_factor(
        source_id=example.source.source_id,
        atoms=example.atoms,
        relation_type="implies",
        role_bindings=example.role_bindings,
        confidence=1.0,
        polarity=example.polarity,
        modality=example.modality,
        scope_id=example.scope_id,
        operator_vector=torch.ones(128),
        role_vectors=torch.ones((slots, 64)),
        binding_vectors=torch.ones((slots, 256)),
        role_scores=tuple(1.0 for _ in range(slots)),
        context_vector=torch.ones(64),
    )
    handoff = assemble_handoff(example.source, example.atoms, (factor,))
    assert handoff is not None
    program, _archive = from_g25_handoff(handoff, example.source.source_hash, tmp_path)
    assert len(program.vectors) == 10
    assert len(program.factors) == 1
    assert program.contexts[program.factors[0].context_index].vector_ref is not None
