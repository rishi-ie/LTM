"""Numerical and structural checks for the Phase 1.2 equilibrium field."""

import numpy as np

from ltm_poc.experiments.equilibrium import (
    EquilibriumConfig,
    EquilibriumField,
    SemanticFieldHierarchy,
    build_evidence_bundle,
    optimize_equilibrium,
    render_evidence_fallback,
)
from ltm_poc.schemas import ChunkRecord


def _vectors(count: int = 16) -> np.ndarray:
    rng = np.random.default_rng(1729)
    vectors = rng.normal(size=(count, 384))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors


def _chunks(count: int) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            chunk_id=f"c{index:03d}",
            record_id=f"r{index:03d}",
            source_path=f"source-{index}.txt",
            source_kind="text",
            text=f"constraint {index}",
            char_start=0,
            char_end=12,
            token_start=0,
            token_end=2,
            token_count=2,
            content_hash=str(index),
            metadata={"priority": 1.0},
        )
        for index in range(count)
    ]


def test_gradient_matches_finite_difference_and_optimizer_is_bounded() -> None:
    vectors = _vectors()
    query = vectors[0]
    hierarchy = SemanticFieldHierarchy.build(
        vectors, [{"priority": 1.0}] * len(vectors), leaf_size=4
    )
    field = EquilibriumField(hierarchy.exact_frontier(query), EquilibriumConfig())
    state = query.copy()
    energy, gradient = field.energy_and_gradient(state)
    direction = vectors[1] - float(vectors[1] @ state) * state
    direction /= np.linalg.norm(direction)
    epsilon = 1e-5
    plus = state + epsilon * direction
    plus /= np.linalg.norm(plus)
    minus = state - epsilon * direction
    minus /= np.linalg.norm(minus)
    finite = (
        field.energy_and_gradient(plus)[0] - field.energy_and_gradient(minus)[0]
    ) / (2 * epsilon)
    assert np.isclose(finite, gradient @ direction, atol=1e-4)
    result = optimize_equilibrium(field)
    energies = [energy] + [step.energy for step in result.trace]
    assert all(
        right <= left + field.config.energy_tolerance
        for left, right in zip(energies, energies[1:])
    )
    assert result.field_evaluations <= field.config.hard_evaluations
    assert np.isclose(np.linalg.norm(result.final_state), 1.0)


def test_barycenter_midpoint_prior_effect_and_zero_exclusion() -> None:
    vectors = np.zeros((3, 384))
    vectors[0, 0] = 1
    vectors[1, 1] = 1
    vectors[2, 2] = 1
    metadata = [
        {"priority": 1.0},
        {"priority": 1.0},
        {"priority": 0.0},
    ]
    hierarchy = SemanticFieldHierarchy.build(vectors, metadata)
    config = EquilibriumConfig(query_anchor=0.0, max_weight=0.0, relevance_floor=1.0)
    field = EquilibriumField(hierarchy.exact_frontier(vectors[0]), config)
    expected = (vectors[0] + vectors[1]) / np.sqrt(2)
    assert np.allclose(field.barycenter(), expected)
    assert set(field.frontier.represented_indices()) == {0, 1}

    stronger = SemanticFieldHierarchy.build(
        vectors[:2], [{"priority": 1.0}, {"priority": 10.0}]
    )
    stronger_field = EquilibriumField(stronger.exact_frontier(vectors[0]), config)
    assert stronger_field.barycenter() @ vectors[1] > field.barycenter() @ vectors[1]


def test_frontier_is_a_partition_and_hierarchy_tracks_exact() -> None:
    vectors = _vectors(200)
    hierarchy = SemanticFieldHierarchy.build(
        vectors, [{"priority": 1.0}] * len(vectors), leaf_size=16
    )
    frontier = hierarchy.compile_frontier(vectors[0], 64, 32)
    represented = frontier.represented_indices()
    assert len(represented) == len(set(represented)) == len(vectors)
    assert set(represented) == set(range(len(vectors)))
    assert frontier.exact_count <= 32
    assert len(frontier.elements) <= 64


def test_symmetric_conflict_and_irrelevant_floor_are_stable() -> None:
    vectors = np.zeros((3, 384))
    vectors[0, 0] = 1
    vectors[1, 1] = 1
    vectors[2, 1] = -1
    metadata = [{"priority": 1.0}] * 3
    hierarchy = SemanticFieldHierarchy.build(vectors, metadata)
    config = EquilibriumConfig(query_anchor=0.0)
    field = EquilibriumField(hierarchy.exact_frontier(vectors[0]), config)
    result = optimize_equilibrium(field)
    residuals = field.residuals(np.asarray(result.final_state))
    assert np.isclose(residuals[1], residuals[2], atol=1e-6)


def test_lambda_max_zero_matches_closed_form_and_bundle_is_bounded() -> None:
    vectors = _vectors(8)
    chunks = _chunks(8)
    hierarchy = SemanticFieldHierarchy.build(
        vectors, [chunk.metadata for chunk in chunks]
    )
    config = EquilibriumConfig(max_weight=0.0, steps=40, learning_rate=0.5)
    field = EquilibriumField(hierarchy.exact_frontier(vectors[0]), config)
    result = optimize_equilibrium(field)
    assert np.asarray(result.final_state) @ field.barycenter() > 0.999
    bundle = build_evidence_bundle(field, result, chunks)
    assert len(bundle["evidence"]) == 4
    assert len({item["chunk_id"] for item in bundle["evidence"]}) == 4
    assert "never claim" in bundle["instruction"]
    fallback = render_evidence_fallback(bundle)
    assert "not a logical proof" in fallback
    assert all(chunk.chunk_id in fallback for chunk in chunks[:1])


def test_invalid_metadata_is_rejected() -> None:
    vectors = _vectors(2)
    try:
        SemanticFieldHierarchy.build(vectors, [{"priority": 101}, {}])
    except ValueError as error:
        assert "priority" in str(error)
    else:
        raise AssertionError("invalid metadata was accepted")
