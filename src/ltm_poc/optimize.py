"""Bounded spherical optimization and mean-shift control."""

import numpy as np

from ltm_poc.config import WorkspaceConfig
from ltm_poc.field import LatentField
from ltm_poc.schemas import OptimizationResult, OptimizationStep


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("cannot normalize non-finite or zero vector")
    return vector / norm


def optimize(field: LatentField, config: WorkspaceConfig) -> OptimizationResult:
    state = field.query.copy()
    initial_energy, gradient = field.energy_and_gradient(state)
    evaluations = 1
    trace: list[OptimizationStep] = []
    termination = "max_steps"
    energy = initial_energy
    for step in range(1, config.optimizer_max_steps + 1):
        if evaluations >= config.optimizer_hard_evaluations:
            termination = "hard_budget"
            break
        tangent = gradient - float(gradient @ state) * state
        learning_rate = config.optimizer_learning_rate
        accepted = False
        for _ in range(3):
            candidate = _unit(state - learning_rate * tangent)
            candidate_energy, candidate_gradient = field.energy_and_gradient(candidate)
            evaluations += 1
            if candidate_energy <= energy + config.energy_tolerance:
                accepted = True
                break
            learning_rate *= 0.5
        if not accepted:
            termination = (
                "hard_budget"
                if evaluations >= config.optimizer_hard_evaluations
                else "max_steps"
            )
            break
        delta = float(np.linalg.norm(candidate - state))
        state, energy, gradient = candidate, candidate_energy, candidate_gradient
        trace.append(
            OptimizationStep(
                step=step,
                field_evaluations=evaluations,
                energy=energy,
                gradient_norm=float(np.linalg.norm(tangent)),
                query_cosine=float(state @ field.query),
                state_delta=delta,
                nearest_chunk_ids=[item.chunk_id for item in field.evidence[:4]],
            )
        )
        if delta <= config.state_tolerance:
            termination = "converged_state"
            break
    return OptimizationResult(
        termination=termination,
        update_steps=len(trace),
        field_evaluations=evaluations,
        initial_energy=initial_energy,
        final_energy=energy,
        final_state=state.tolist(),
        trace=trace,
    )


def mean_shift(field: LatentField, steps: int = 8) -> np.ndarray:
    state = field.query.copy()
    for _ in range(steps):
        logits = field.log_weights + (field.vectors @ state) / field.field_temperature
        weights = np.exp(logits - np.max(logits))
        state = _unit(weights @ field.vectors)
    return state
