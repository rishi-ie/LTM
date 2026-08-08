from __future__ import annotations

import numpy as np
import pytest

from ltm_limit_l5.compiler import (
    DeterministicCoordinateEncoder,
    SharedCoordinateCompiler,
    controlled_source,
)
from ltm_limit_l5.decoder import authorize, realize
from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.optimizer import optimize
from ltm_limit_l5.verifier import certify_result
from ltm_limit_l5.writer import assemble_public_case, assemble_sources


def _compiled_chain():
    compiler = SharedCoordinateCompiler(DeterministicCoordinateEncoder())
    sources = (
        compiler.compile_source(
            controlled_source(
                "when metal_hot then chamber_expands",
                source_id="source:1",
                reality_key="reality:lab",
            )
        ),
        compiler.compile_source(
            controlled_source(
                "when chamber_expands then gauge_rises",
                source_id="source:2",
                reality_key="reality:lab",
            )
        ),
    )
    prompt = compiler.compile_prompt(
        controlled_source(
            "given metal_hot, what follows?",
            source_id="prompt:1",
            reality_key="reality:lab",
        )
    )
    return sources, prompt


def test_atomic_writer_builds_source_backed_field_and_round_trip() -> None:
    sources, prompt = _compiled_chain()
    case = assemble_public_case(prompt, sources)
    cells, summaries = build_minimap(
        case.bodies, case.units, np.asarray(case.vector_table, dtype=np.float32)
    )
    index = EquilibriumFieldIndex(
        case.bodies,
        case.units,
        np.asarray(case.vector_table, dtype=np.float32),
        cells,
        summaries,
    )
    result = certify_result(case, optimize(index, prompt, confidence_threshold=0.50))
    view = authorize(result)
    output = realize(view, {item.semantic_key: item.semantic_key for item in case.units})

    assert result.disposition == "candidate"
    assert len(result.trajectory) > 1
    assert len(result.certificates[0].body_ids) == 2
    assert output.authorized_unit_ids == (result.selected_candidate_id,)
    assert result.factual_operations == ()


def test_writer_refuses_unaccepted_or_duplicate_source_transactions() -> None:
    compiler = SharedCoordinateCompiler(DeterministicCoordinateEncoder())
    accepted = compiler.compile_source(controlled_source("when a then b"))
    rejected = compiler.compile_source(controlled_source("given a, what follows?"))

    with pytest.raises(ValueError, match="unaccepted"):
        assemble_sources((rejected,))
    with pytest.raises(ValueError, match="duplicate"):
        assemble_sources((accepted, accepted))


def test_writer_preserves_exact_context_and_provenance() -> None:
    compiler = SharedCoordinateCompiler(DeterministicCoordinateEncoder())
    source = compiler.compile_source(
        controlled_source(
            "when a and b then c",
            source_id="source:context",
            scope_key="session:7",
            reality_key="reality:blue",
            valid_at=42,
            polarity=-1,
            modality="hypothetical",
            provenance_id="document:9",
        )
    )
    artifact = assemble_sources((source,))
    body = artifact.bodies[0]

    assert body.scope_key == "session:7"
    assert body.reality_key == "reality:blue"
    assert body.valid_from == 42
    assert body.independent_source_key == "document:9"
    assert all(item.provenance_id == "document:9" for item in artifact.units)
    assert {item.polarity for item in artifact.units if item.phase_index == 1} == {-1}
    assert artifact.factual_operations == ()
