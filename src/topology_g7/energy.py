from __future__ import annotations

import numpy as np

from .schemas import ReconciliationProblem, SoftFactor


def weight(factor: SoftFactor) -> float:
    return min(8.0, max(0.0001, factor.base_weight * factor.authority * factor.confidence))


def index(problem: ReconciliationProblem) -> dict[str, int]:
    return {item.variable_id: position for position, item in enumerate(problem.soft_variables)}


def factors_for(problem: ReconciliationProblem, alternative_id: str | None) -> tuple[SoftFactor, ...]:
    return tuple(
        factor
        for factor in problem.soft_factors
        if factor.applicable and (factor.alternative_id is None or factor.alternative_id == alternative_id)
    )


def energy_and_gradient(
    values: np.ndarray, problem: ReconciliationProblem, alternative_id: str | None
) -> tuple[float, np.ndarray, tuple[tuple[str, float], ...]]:
    """Registered piecewise-quadratic laws; coupling is supported for unit tests.

    Locked problems make the reference member in a coupling fixed by the selected
    alternative, preserving a quadratic oracle for the decisive experiment.
    """
    positions = index(problem)
    gradient = np.zeros_like(values)
    energy = 0.0
    residuals: list[tuple[str, float]] = []
    for factor in factors_for(problem, alternative_id):
        ids = factor.variable_ids
        targets = factor.target_values
        w = weight(factor)
        if factor.factor_type in {"evidence", "preference", "reference", "branch"}:
            pos = positions[ids[0]]; residual = values[pos] - targets[0]
            term = w * residual * residual; gradient[pos] += 2.0 * w * residual
        elif factor.factor_type == "coupling":
            left, right = positions[ids[0]], positions[ids[1]]
            residual = values[left] * values[right] - targets[0]
            term = w * residual * residual
            gradient[left] += 2.0 * w * residual * values[right]
            gradient[right] += 2.0 * w * residual * values[left]
        elif factor.factor_type == "uncertainty":
            pos = positions[ids[0]]; residual = values[pos] - targets[0]
            term = w * residual * residual; gradient[pos] += 2.0 * w * residual
        elif factor.factor_type == "certainty":
            pos = positions[ids[0]]; residual = max(0.0, values[pos] - targets[0])
            term = w * residual * residual
            if residual > 0: gradient[pos] += 2.0 * w * residual
        else:
            raise ValueError(f"unknown soft factor {factor.factor_type}")
        energy += term; residuals.append((factor.factor_id, float(term)))
    return float(energy), gradient, tuple(sorted(residuals))


def finite_difference(values: np.ndarray, problem: ReconciliationProblem, alternative_id: str | None) -> np.ndarray:
    result = np.zeros_like(values); delta = 1e-6
    for position in range(len(values)):
        plus = values.copy(); minus = values.copy(); plus[position] += delta; minus[position] -= delta
        result[position] = (energy_and_gradient(plus, problem, alternative_id)[0] - energy_and_gradient(minus, problem, alternative_id)[0]) / (2 * delta)
    return result
