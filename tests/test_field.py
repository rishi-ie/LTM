"""Analytic field behavior checks."""

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.field import LatentField
from ltm_poc.schemas import ChunkRecord


def config() -> WorkspaceConfig:
    return WorkspaceConfig(
        embedding_model_path="embed",
        embedding_model_id="embed",
        embedding_revision="pin",
        decoder_model_path="decode",
        decoder_model_id="decode",
        decoder_revision="pin",
        active_candidates=2,
        evidence_limit=2,
    )


def chunks() -> list[ChunkRecord]:
    return [
        ChunkRecord(
            chunk_id=f"c{index}",
            record_id="r",
            source_path="s",
            source_kind="text",
            text=str(index),
            char_start=0,
            char_end=1,
            token_start=0,
            token_end=1,
            token_count=1,
            content_hash=str(index),
            metadata={},
        )
        for index in range(2)
    ]


def test_field_gradient_matches_directional_finite_difference() -> None:
    vectors = np.zeros((2, 384), dtype=np.float32)
    vectors[0, 0] = 1
    vectors[1, 1] = 1
    query = vectors[0].copy()
    field = LatentField.construct(query, vectors, chunks(), config())
    state = query.astype(np.float64)
    energy, gradient = field.energy_and_gradient(state)
    direction = np.zeros(384)
    direction[1] = 1
    epsilon = 1e-5
    plus = state + epsilon * direction
    plus /= np.linalg.norm(plus)
    minus = state - epsilon * direction
    minus /= np.linalg.norm(minus)
    finite_difference = (
        field.energy_and_gradient(plus)[0] - field.energy_and_gradient(minus)[0]
    ) / (2 * epsilon)
    assert energy == field.energy_and_gradient(state)[0]
    assert np.isclose(finite_difference, gradient @ direction, atol=1e-4)
