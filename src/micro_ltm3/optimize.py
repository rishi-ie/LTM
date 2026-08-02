from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from micro_ltm.schemas import SignedLiteral

from .codebook import random_codes
from .schemas import CapacityCase


@dataclass(frozen=True, slots=True)
class OptimizerConfig:
    fact_weight: float = 32.0
    rule_weight: float = 16.0
    sparsity_weight: float = 0.01
    exclusion_weight: float = 8.0
    norm_weight: float = 0.001
    steps: int = 64
    learning_rate: float = 0.05
    tolerance: float = 1e-6
    max_evaluations: int = 320


DEFAULT_CONFIG = OptimizerConfig()


def _index(literal: SignedLiteral) -> tuple[int, int]:
    return (0 if literal.polarity == 1 else 1, literal.proposition)


def _supports(state: np.ndarray, codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    logits = 8.0 * (np.einsum("d,pd->p", state, codes[0]) - 0.37)
    neg_logits = 8.0 * (np.einsum("d,pd->p", state, codes[1]) - 0.37)
    return 1.0 / (1.0 + np.exp(-logits)), 1.0 / (1.0 + np.exp(-neg_logits))


def _support_grad(support: float, code: np.ndarray) -> np.ndarray:
    return 8.0 * support * (1.0 - support) * code


def energy_and_gradient(
    state: np.ndarray,
    case: CapacityCase,
    codes: np.ndarray,
    config: OptimizerConfig = DEFAULT_CONFIG,
) -> tuple[float, np.ndarray]:
    positive, negative = _supports(state, codes)
    supports = np.stack((positive, negative))
    gradients = np.empty_like(codes, dtype=np.float64)
    gradients[0] = np.stack([_support_grad(float(positive[i]), codes[0, i]) for i in range(case.proposition_count)])
    gradients[1] = np.stack([_support_grad(float(negative[i]), codes[1, i]) for i in range(case.proposition_count)])
    energy = 0.0
    grad = np.zeros_like(state, dtype=np.float64)

    def add(value: float, derivative: np.ndarray) -> None:
        nonlocal energy, grad
        energy += value
        grad += derivative

    for fact in case.problem.facts:
        p, i = _index(fact)
        residual = 1.0 - supports[p, i]
        add(config.fact_weight * residual * residual, -2.0 * config.fact_weight * residual * gradients[p, i])

    for rule in case.problem.rules:
        conclusion = _index(rule.conclusion)
        target = float(supports[conclusion])
        if len(rule.premises) == 1:
            premise = _index(rule.premises[0])
            antecedent = float(supports[premise])
            derivative = np.zeros_like(state, dtype=np.float64)
            if antecedent > target:
                residual = antecedent - target
                derivative = 2.0 * config.rule_weight * residual * (gradients[premise] - gradients[conclusion])
                add(config.rule_weight * residual * residual, derivative)
        else:
            first, second = (_index(rule.premises[0]), _index(rule.premises[1]))
            raw = float(supports[first] + supports[second] - 1.0)
            antecedent = max(0.0, raw)
            if antecedent > target:
                residual = antecedent - target
                derivative = 2.0 * 1.25 * config.rule_weight * residual * (gradients[first] + gradients[second] - gradients[conclusion])
                add(1.25 * config.rule_weight * residual * residual, derivative)

    for i in range(case.proposition_count):
        residual = max(0.0, float(supports[0, i] + supports[1, i] - 1.0))
        if residual:
            add(config.exclusion_weight * residual * residual, 2.0 * config.exclusion_weight * residual * (gradients[0, i] + gradients[1, i]))

    add(config.sparsity_weight * float(np.sum(supports * supports)), config.sparsity_weight * 2.0 * np.sum(supports[:, :, None] * gradients, axis=(0, 1)))
    add(config.norm_weight * float(state @ state), 2.0 * config.norm_weight * state)
    return float(energy), grad


def optimize_case(
    case: CapacityCase,
    codes: np.ndarray | None = None,
    config: OptimizerConfig = DEFAULT_CONFIG,
) -> tuple[np.ndarray, list[np.ndarray], float, dict[str, float]]:
    codes = random_codes(case) if codes is None else codes
    target = case.problem.query_proposition
    state = (0.05 * (codes[0, target] + codes[1, target])).astype(np.float64)
    energy, gradient = energy_and_gradient(state, case, codes, config)
    trajectory = [np.stack(_supports(state, codes)).astype(np.float32)]
    evaluations = 1
    reason = "step_limit"
    for _ in range(config.steps):
        norm = float(np.linalg.norm(gradient))
        if not np.isfinite(energy) or not np.isfinite(norm):
            reason = "numerical_failure"
            break
        if norm <= config.tolerance:
            reason = "gradient_tolerance"
            break
        accepted = False
        step = config.learning_rate
        for _retry in range(5):
            proposal = state - step * gradient
            proposal_norm = float(np.linalg.norm(proposal))
            if proposal_norm > 8.0:
                proposal *= 8.0 / proposal_norm
            proposal_energy, proposal_gradient = energy_and_gradient(proposal, case, codes, config)
            evaluations += 1
            if proposal_energy <= energy + 1e-8:
                state, energy, gradient = proposal, proposal_energy, proposal_gradient
                accepted = True
                break
            step *= 0.5
            if evaluations >= config.max_evaluations:
                break
        trajectory.append(np.stack(_supports(state, codes)).astype(np.float32))
        if evaluations >= config.max_evaluations:
            reason = "evaluation_limit"
            break
        if not accepted:
            reason = "backtracking_exhausted"
            break
        if len(trajectory) > 1 and float(np.max(np.abs(trajectory[-1] - trajectory[-2]))) <= config.tolerance:
            reason = "energy_tolerance"
            break
    final = trajectory[-1]
    residual = float(np.max(np.abs(final - np.stack(_supports(state, codes)))))
    return final, trajectory, residual, {"energy": float(energy), "evaluations": float(evaluations), "state_norm": float(np.linalg.norm(state)), "reason": reason}


__all__ = ["OptimizerConfig", "energy_and_gradient", "optimize_case"]
