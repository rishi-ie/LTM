from __future__ import annotations

import numpy as np

from .field import energy_and_gradient, initial_state, make_codebook, supports
from .schemas import FieldConfig, MicroProblem, OptimizationResult, OptimizationStep


def optimize(
    problem: MicroProblem,
    config: FieldConfig,
    codes: np.ndarray | None = None,
    include_rules: bool = True,
    undirected: bool = False,
    steps: int = 64,
    learning_rate: float = 0.05,
    retries: int = 4,
    tolerance: float = 1e-6,
    max_evaluations: int = 320,
    max_norm: float = 8.0,
) -> OptimizationResult:
    codes = make_codebook(problem, config) if codes is None else codes
    state = initial_state(problem, codes).astype(np.float32)
    energy, gradient, _ = energy_and_gradient(state, problem, codes, config, include_rules, undirected)
    initial_energy = energy
    trace: list[OptimizationStep] = []
    evaluations = 1
    reason = "step_limit"
    for step in range(steps):
        grad_norm = float(np.linalg.norm(gradient))
        if grad_norm <= tolerance:
            reason = "gradient_tolerance"
            trace.append(OptimizationStep(step, energy, grad_norm, False, evaluations))
            break
        accepted = False
        trial_lr = learning_rate
        for _ in range(retries + 1):
            candidate = state - trial_lr * gradient
            norm = float(np.linalg.norm(candidate))
            if norm > max_norm:
                candidate = candidate * (max_norm / norm)
            trial_energy, trial_gradient, _ = energy_and_gradient(
                candidate, problem, codes, config, include_rules, undirected
            )
            evaluations += 1
            if trial_energy <= energy + 1e-8:
                previous = energy
                state, energy, gradient = candidate, trial_energy, trial_gradient
                accepted = True
                trace.append(OptimizationStep(step, energy, grad_norm, True, evaluations))
                if abs(previous - energy) <= tolerance:
                    reason = "energy_tolerance"
                break
            trial_lr *= 0.5
            if evaluations >= max_evaluations:
                break
        if reason == "energy_tolerance" or evaluations >= max_evaluations:
            if reason != "energy_tolerance":
                reason = "evaluation_limit"
            break
        if not accepted:
            reason = "backtracking_exhausted"
            trace.append(OptimizationStep(step, energy, grad_norm, False, evaluations))
            break
    final_support = supports(state, codes, config)
    return OptimizationResult(
        initial_state=initial_state(problem, codes),
        final_state=state,
        initial_energy=float(initial_energy),
        final_energy=float(energy),
        trace=tuple(trace),
        target_positive_support=float(final_support[0, problem.query_proposition]),
        target_negative_support=float(final_support[1, problem.query_proposition]),
        convergence_reason=reason,
    )
