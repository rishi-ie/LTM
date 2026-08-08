from __future__ import annotations

from itertools import pairwise

import numpy as np

from ltm_limit_l6.dataset import build_case, reality_profile
from ltm_limit_l6.evaluator import verify_result
from ltm_limit_l6.optimizer import optimize


def test_field_has_no_exact_consumer_activation_path() -> None:
    case = build_case(3)
    assert not hasattr(case.field, "_consumer_body_ids")
    assert case.field.access["full_field_scans"] == 0


def test_prompt_anchor_is_immutable_and_factors_are_continuous() -> None:
    case = build_case(4)
    anchor = case.prompt.anchor_position
    result = optimize(case.field, case.prompt, reality_profile(), maximum_steps=8)
    assert case.prompt.anchor_position == anchor
    assert result.factual_operations == ()
    assert result.factor_states
    assert all(0.0 <= row.activation <= 1.0 for row in result.factor_states)
    assert any(0.0 < row.activation < 1.0 for row in result.factor_states)


def test_every_accepted_energy_step_is_nonincreasing() -> None:
    case = build_case(5)
    result = optimize(case.field, case.prompt, reality_profile())
    energies = [step.energy for step in result.trajectory]
    assert all(right <= left + 1e-7 for left, right in pairwise(energies))


def test_reality_isolation() -> None:
    case = build_case(2, reality_key="custom:one-plus-one-three")
    result = optimize(case.field, case.prompt, reality_profile(case.prompt.reality_key))
    assert result.factual_operations == ()
    assert all(body.reality_key == case.prompt.reality_key for body in case.field.bodies.values())


def test_independent_verifier_accepts_only_source_backed_candidates() -> None:
    case = build_case(1)
    result = optimize(case.field, case.prompt, reality_profile())
    assert verify_result(case, result)


def test_random_geometry_is_a_distinct_control() -> None:
    case = build_case(2)
    full = optimize(case.field, case.prompt, reality_profile())
    random = optimize(case.field, case.prompt, reality_profile(), random_geometry=True)
    assert full.trajectory and random.trajectory
    assert all(np.isfinite(step.energy) for step in random.trajectory)
