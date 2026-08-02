from __future__ import annotations

import numpy as np

from micro_ltm.schemas import SignedLiteral

from .schemas import CapacityCase


def index(literal: SignedLiteral) -> tuple[int, int]:
    return (0 if literal.polarity == 1 else 1, literal.proposition)


def fact_mask(case: CapacityCase) -> np.ndarray:
    mask = np.zeros((2, case.proposition_count), dtype=np.float32)
    for fact in case.problem.facts:
        p, i = index(fact)
        mask[p, i] = 1.0
    return mask


def forward_operator(activations: np.ndarray, case: CapacityCase) -> np.ndarray:
    proposals = np.zeros_like(activations, dtype=np.float64)
    for rule in case.problem.rules:
        if len(rule.premises) == 1:
            signal = float(activations[index(rule.premises[0])])
        else:
            signal = float(np.prod([activations[index(p)] for p in rule.premises]))
        p, i = index(rule.conclusion)
        proposals[p, i] = 1.0 - (1.0 - proposals[p, i]) * (1.0 - signal)
    state = 1.0 - (1.0 - activations.astype(np.float64)) * (1.0 - proposals)
    return np.maximum(state.astype(np.float32), fact_mask(case))


def relax(case: CapacityCase, max_sweeps: int = 16, tolerance: float = 1e-7) -> tuple[np.ndarray, list[np.ndarray], float]:
    state = fact_mask(case)
    trajectory = [state.copy()]
    for _ in range(max_sweeps):
        proposal = forward_operator(state, case)
        if np.any(proposal + 1e-8 < state):
            raise FloatingPointError("field activation decreased")
        state = proposal
        trajectory.append(state.copy())
        residual = float(np.max(np.abs(forward_operator(state, case) - state)))
        if residual <= tolerance:
            return state, trajectory, residual
    residual = float(np.max(np.abs(forward_operator(state, case) - state)))
    return state, trajectory, residual
