"""Numerical and deterministic checks for Phase 1.1."""

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.experiments.multi_state import (
    LatentSetField,
    SetOptimizerConfig,
    initialize_states,
    mmr_indices,
    optimize_set,
    resolve_set_evidence,
)
from ltm_poc.field import LatentField
from ltm_poc.schemas import ChunkRecord


def _chunks(count: int) -> list[ChunkRecord]:
    return [
        ChunkRecord(
            chunk_id=f"c{index}",
            record_id=f"r{index}",
            source_path=f"s{index}",
            source_kind="text",
            text=f"text {index}",
            char_start=0,
            char_end=6,
            token_start=0,
            token_end=1,
            token_count=1,
            content_hash=str(index),
            metadata={},
        )
        for index in range(count)
    ]


def _field() -> tuple[LatentField, list[ChunkRecord]]:
    chunks = _chunks(4)
    vectors = np.zeros((4, 384), dtype=np.float32)
    vectors[0, 0] = 1
    vectors[1, :2] = [0.8, 0.6]
    vectors[2, :2] = [0.6, -0.8]
    vectors[3, :2] = [0.2, 0.98]
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    config = WorkspaceConfig(
        embedding_model_path="embed",
        embedding_model_id="embed",
        embedding_revision="pin",
        decoder_model_path="decode",
        decoder_model_id="decode",
        decoder_revision="pin",
        active_candidates=4,
        evidence_limit=4,
    )
    return LatentField.construct(vectors[0], vectors, chunks, config), chunks


def test_mmr_and_resolution_are_deterministic_and_distinct() -> None:
    field, chunks = _field()
    selected = mmr_indices(field.query, field.vectors, chunks, 2, 4, 0.7)
    assert selected == mmr_indices(field.query, field.vectors, chunks, 2, 4, 0.7)
    config = SetOptimizerConfig(slots=2, seed_pool=4)
    states = initialize_states(field, chunks, config)
    evidence = resolve_set_evidence(field, states, 4)
    assert len({item.chunk_id for item in evidence}) == 4
    assert {item.slot for item in evidence} == {0, 1}
    four_slot_config = SetOptimizerConfig(slots=4, seed_pool=4)
    four_states = initialize_states(field, chunks, four_slot_config)
    four_evidence = resolve_set_evidence(field, four_states, 4)
    assert len(four_evidence) == 4


def test_set_gradient_matches_finite_difference_and_optimizer_is_bounded() -> None:
    base, chunks = _field()
    config = SetOptimizerConfig(slots=2, seed_pool=4)
    states = initialize_states(base, chunks, config)
    field = LatentSetField(base, config.diversity_weight, config.similarity_cap)
    energy, gradient = field.energy_and_gradient(states)
    direction = np.zeros_like(states)
    direction[0, 2] = 1
    epsilon = 1e-5
    plus = np.asarray(
        [vector / np.linalg.norm(vector) for vector in states + epsilon * direction]
    )
    minus = np.asarray(
        [vector / np.linalg.norm(vector) for vector in states - epsilon * direction]
    )
    finite = field.energy_and_gradient(plus)[0] - field.energy_and_gradient(minus)[0]
    finite /= 2 * epsilon
    tangent_direction = (
        direction - (direction * states).sum(axis=1, keepdims=True) * states
    )
    assert np.isclose(finite, float((gradient * tangent_direction).sum()), atol=1e-4)
    result = optimize_set(field, states, config)
    assert result.final_energy <= energy + config.energy_tolerance
    assert result.set_evaluations <= config.hard_set_evaluations
    assert np.allclose(np.linalg.norm(result.final_states, axis=1), 1.0)


def test_diversity_is_zero_below_cap_and_positive_above_cap() -> None:
    base, _ = _field()
    field = LatentSetField(base, diversity_weight=1.0, similarity_cap=0.75)
    orthogonal = np.stack([base.vectors[0], base.vectors[2]])
    identical = np.stack([base.vectors[0], base.vectors[0]])
    base_orthogonal = np.mean([base.energy_and_gradient(x)[0] for x in orthogonal])
    base_identical = np.mean([base.energy_and_gradient(x)[0] for x in identical])
    assert np.isclose(field.energy_and_gradient(orthogonal)[0], base_orthogonal)
    assert field.energy_and_gradient(identical)[0] > base_identical


def test_diversity_reduces_slot_collapse_on_two_modes() -> None:
    base, chunks = _field()
    plain = SetOptimizerConfig(
        slots=4, seed_pool=4, diversity_weight=0.0, similarity_cap=0.6
    )
    diverse = SetOptimizerConfig(
        slots=4, seed_pool=4, diversity_weight=1.5, similarity_cap=0.6
    )
    initial = initialize_states(base, chunks, plain)
    plain_result = optimize_set(LatentSetField(base, 0.0, 0.6), initial, plain)
    diverse_result = optimize_set(LatentSetField(base, 1.5, 0.6), initial, diverse)

    def maximum_pair_similarity(states) -> float:
        matrix = np.asarray(states) @ np.asarray(states).T
        return float(np.max(matrix - np.eye(len(matrix))))

    assert maximum_pair_similarity(
        diverse_result.final_states
    ) < maximum_pair_similarity(plain_result.final_states)
