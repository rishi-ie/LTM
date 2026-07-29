"""Optimizer invariants and control comparison."""

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.field import LatentField
from ltm_poc.optimize import mean_shift, optimize
from tests.test_field import chunks


def test_optimizer_stays_on_sphere_and_does_not_raise_energy() -> None:
    vectors = np.zeros((2, 384), dtype=np.float32)
    vectors[0, 0] = 1
    vectors[1, 1] = 1
    config = WorkspaceConfig(
        embedding_model_path="embed",
        embedding_model_id="embed",
        embedding_revision="pin",
        decoder_model_path="decode",
        decoder_model_id="decode",
        decoder_revision="pin",
        active_candidates=2,
        evidence_limit=2,
    )
    field = LatentField.construct(vectors[0], vectors, chunks(), config)
    result = optimize(field, config)
    assert np.isclose(np.linalg.norm(result.final_state), 1.0)
    assert result.final_energy <= result.initial_energy + config.energy_tolerance
    assert result.field_evaluations <= config.optimizer_hard_evaluations
    assert np.isclose(np.linalg.norm(mean_shift(field)), 1.0)
