from __future__ import annotations

from dataclasses import asdict

import numpy as np

from topology_g8.engine import evaluate_batched, evaluate_reference
from topology_g8.generator import build_dataset, materialize


def settings() -> dict:
    return {
        "field_factors": 65_536,
        "physical_block_size": 256,
        "selected_blocks_per_request": 16,
        "maximum_steps": 48,
        "learning_rate": 0.05,
        "backtracking_retries": 4,
        "convergence_tolerance": 1e-7,
        "accepted_energy_tolerance": 1e-10,
        "maximum_evaluations": 240,
        "decision_margin": 0.05,
        "abstention_threshold": 0.75,
    }


def test_batched_reduction_matches_reference_and_honors_residency(tmp_path) -> None:
    config = settings()
    requests, blocks = build_dataset(1729, 1, config)
    materialize(tmp_path, requests, blocks)
    request = requests[0]
    reference = evaluate_reference(request, tmp_path / "field", config)

    for width in (1, 4, 16):
        for order in ("ascending", "descending", "random"):
            actual = evaluate_batched(request, tmp_path / "field", config, batch_width=width, order=order, seed=1729)
            assert asdict(actual.hard_result) == asdict(reference.hard_result)
            assert actual.final_state == reference.final_state
            assert actual.selected_branch == reference.selected_branch
            assert actual.disposition == reference.disposition
            assert actual.decisive_provenance_ids == reference.decisive_provenance_ids
            assert np.isclose(actual.final_energy, reference.final_energy, atol=1e-10)
            assert actual.memory_trace.peak_resident_blocks <= width
            assert not actual.memory_trace.complete_field_materialization
