from __future__ import annotations

import numpy as np

from micro_ltm.field import make_codebook
from micro_ltm.schemas import FieldConfig, MicroProblem, SignedLiteral

from .compress import compress
from .schemas import CausalOptimizationResult, CausalStep


def _index(literal: SignedLiteral) -> tuple[int, int]:
    return (0 if literal.polarity == 1 else 1, literal.proposition)


def fact_mask(problem: MicroProblem) -> np.ndarray:
    mask = np.zeros((2, 24), dtype=np.float32)
    for fact in problem.facts:
        polarity, proposition = _index(fact)
        mask[polarity, proposition] = 1.0
    return mask


def forward_operator(
    activations: np.ndarray,
    problem: MicroProblem,
    mode: str = "forward",
) -> tuple[np.ndarray, np.ndarray]:
    """Apply one local topology-field update without using gold labels.

    The product conjunction and probabilistic-OR aggregation are smooth in the
    interior. Hard facts are applied at the boundary of the state manifold.
    """
    messages: list[tuple[SignedLiteral, float]] = []
    for rule in problem.rules:
        if mode == "reverse":
            signal = activations[_index(rule.conclusion)]
            for premise in rule.premises:
                messages.append((premise, float(signal)))
        else:
            if len(rule.premises) == 1:
                signal = activations[_index(rule.premises[0])]
            else:
                signal = float(np.prod([activations[_index(p)] for p in rule.premises]))
            messages.append((rule.conclusion, float(signal)))
            if mode == "undirected":
                signal = activations[_index(rule.conclusion)]
                for premise in rule.premises:
                    messages.append((premise, float(signal)))
    proposal = np.zeros_like(activations, dtype=np.float64)
    for literal, signal in messages:
        polarity, proposition = _index(literal)
        proposal[polarity, proposition] = 1.0 - (1.0 - proposal[polarity, proposition]) * (1.0 - signal)
    next_state = 1.0 - (1.0 - activations.astype(np.float64)) * (1.0 - proposal)
    next_state = np.clip(next_state, 0.0, 1.0).astype(np.float32)
    next_state = np.maximum(next_state, fact_mask(problem))
    return next_state, np.asarray(messages, dtype=object)


def relax(
    problem: MicroProblem,
    codes: np.ndarray,
    max_sweeps: int = 16,
    tolerance: float = 1e-7,
    mode: str = "forward",
) -> CausalOptimizationResult:
    facts = fact_mask(problem)
    state = facts.copy()
    initial = state.copy()
    trace: list[CausalStep] = []
    collision_count = 0
    reason = "sweep_limit"
    for sweep in range(max_sweeps):
        proposal, _ = forward_operator(state, problem, mode)
        delta = float(np.max(np.abs(proposal - state)))
        residual = float(np.max(np.abs(forward_operator(proposal, problem, mode)[0] - proposal)))
        target = problem.query_proposition
        if proposal[0, target] > 0.5 and proposal[1, target] > 0.5:
            collision_count += 1
        trace.append(CausalStep(sweep, delta, residual, int(np.sum(proposal > 0.5))))
        if np.any(proposal + 1e-8 < state):
            raise FloatingPointError("causal relaxation was not monotonic")
        state = proposal
        if residual <= tolerance:
            reason = "fixed_point"
            break
    final_residual = float(np.max(np.abs(forward_operator(state, problem, mode)[0] - state)))
    if not np.all(np.isfinite(state)):
        reason = "numerical_failure"
    compressed = compress(state, codes, problem.query_proposition)
    return CausalOptimizationResult(initial, state, compressed.state, tuple(trace), final_residual, reason, collision_count)


def codebook(problem: MicroProblem) -> np.ndarray:
    return make_codebook(problem, FieldConfig(32.0, 8.0, 0.01, propositions=24))
