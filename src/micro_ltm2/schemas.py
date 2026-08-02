from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from micro_ltm.schemas import Label, MicroProblem


@dataclass(frozen=True, slots=True)
class CausalStep:
    sweep: int
    max_delta: float
    fixed_residual: float
    active_count: int


@dataclass(frozen=True, slots=True)
class CausalOptimizationResult:
    initial_activations: np.ndarray
    final_activations: np.ndarray
    final_state: np.ndarray
    trace: tuple[CausalStep, ...]
    fixed_residual: float
    convergence_reason: str
    collision_count: int


@dataclass(frozen=True, slots=True)
class CompressionResult:
    state: np.ndarray
    positive_feature: float
    negative_feature: float


@dataclass(frozen=True, slots=True)
class V2Intervention:
    name: str
    expected: Label
    predicted: Label
    passed: bool


def public_case(problem: MicroProblem) -> dict[str, Any]:
    return {
        "problem_id": problem.problem_id,
        "codebook_seed": problem.codebook_seed,
        "facts": [{"proposition": x.proposition, "polarity": x.polarity} for x in problem.facts],
        "rules": [
            {
                "rule_id": rule.rule_id,
                "premises": [{"proposition": x.proposition, "polarity": x.polarity} for x in rule.premises],
                "conclusion": {"proposition": rule.conclusion.proposition, "polarity": rule.conclusion.polarity},
            }
            for rule in problem.rules
        ],
        "query_proposition": problem.query_proposition,
        "gold_label": problem.gold_label,
        "proof_depth": problem.proof_depth,
        "decisive_rule_id": problem.decisive_rule_id,
        "twin_id": problem.twin_id,
        "twin_operation": problem.twin_operation,
    }
