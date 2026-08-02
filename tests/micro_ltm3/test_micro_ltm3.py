from __future__ import annotations

import inspect

import numpy as np

from micro_ltm.oracle import label_for
from micro_ltm3.codebook import orthogonal_codes, random_codes
from micro_ltm3.compress import compress_equilibrium
from micro_ltm3.field import relax
from micro_ltm3.generator import generate_split
from micro_ltm3.optimize import energy_and_gradient
from micro_ltm3.schemas import CompressionConfig


def test_generator_labels_and_twins_are_oracle_valid() -> None:
    cases = generate_split("test", 12, 901, 24, range(2, 6), True)
    assert len(cases) == 24
    assert all(label_for(case.problem) == case.problem.gold_label for case in cases)
    assert sum(case.problem.twin_id is not None for case in cases) == 12


def test_large_capacity_generation_is_sparse_and_valid() -> None:
    cases = generate_split("large", 12, 902, 96, range(6, 10), True)
    assert len(cases) == 24
    assert all(case.proposition_count == 96 for case in cases)
    assert all(case.density_bucket in {"low", "medium", "high", "dense"} for case in cases)


def test_codebooks_have_expected_shape_and_orthogonality() -> None:
    case = generate_split("codes", 3, 903, 24, range(2, 3), False)[0]
    codes = random_codes(case)
    assert codes.shape == (2, 24, 128)
    assert np.max(np.abs(np.linalg.norm(codes.reshape(-1, 128), axis=1) - 1)) < 1e-5
    orth = orthogonal_codes(case)
    gram = orth.reshape(-1, 128) @ orth.reshape(-1, 128).T
    assert np.max(np.abs(gram - np.eye(48))) < 1e-5


def test_query_agnostic_compressor_has_no_query_argument() -> None:
    signature = inspect.signature(compress_equilibrium)
    assert "query" not in signature.parameters


def test_field_reaches_fixed_point_and_ridge_is_deterministic() -> None:
    case = generate_split("field", 3, 904, 24, range(3, 4), False)[0]
    state_a, trajectory_a, residual_a = relax(case)
    state_b, trajectory_b, residual_b = relax(case)
    assert np.array_equal(state_a, state_b)
    assert len(trajectory_a) == len(trajectory_b)
    assert all(np.array_equal(left, right) for left, right in zip(trajectory_a, trajectory_b))
    assert residual_a == residual_b
    assert residual_a <= 1e-7
    codes = random_codes(case)
    result = compress_equilibrium(state_a, codes, CompressionConfig("ridge", 1e-3))
    assert np.isfinite(result.state).all()
    assert result.state_norm > 0


def test_differentiable_energy_gradient_matches_finite_difference() -> None:
    case = generate_split("gradient", 3, 905, 24, range(2, 3), False)[0]
    codes = random_codes(case)
    state = np.random.default_rng(7).normal(size=128).astype(np.float64) * 0.1
    energy, gradient = energy_and_gradient(state, case, codes)
    assert np.isfinite(energy)
    numeric = np.zeros(128)
    epsilon = 1e-5
    for index in range(128):
        plus = state.copy()
        plus[index] += epsilon
        minus = state.copy()
        minus[index] -= epsilon
        numeric[index] = (energy_and_gradient(plus, case, codes)[0] - energy_and_gradient(minus, case, codes)[0]) / (2 * epsilon)
    relative_error = np.max(np.abs(gradient - numeric) / np.maximum(1.0, np.abs(numeric)))
    assert relative_error < 1e-4
