from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from topology_g6.schemas import ProgramResult, ReasoningProblem


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class SoftVariable:
    variable_id: str
    variable_type: str
    lower: float
    upper: float
    initial: float
    group_id: str | None = None


@dataclass(frozen=True, slots=True)
class SoftFactor:
    factor_id: str
    factor_type: str
    variable_ids: tuple[str, ...]
    target_values: tuple[float, ...]
    base_weight: float
    authority: float
    confidence: float
    source_id: str
    alternative_id: str | None = None
    applicable: bool = True


@dataclass(frozen=True, slots=True)
class DiscreteAlternative:
    alternative_id: str
    alternative_type: str
    affected_ids: tuple[str, ...]
    incompatible_hard_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconciliationProblem:
    problem_id: str
    family: str
    g6_program: ReasoningProblem
    soft_variables: tuple[SoftVariable, ...]
    soft_factors: tuple[SoftFactor, ...]
    alternatives: tuple[DiscreteAlternative, ...]
    reference_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class StructuredState:
    confidence_values: tuple[tuple[str, float], ...]
    preference_values: tuple[tuple[str, float], ...]
    reference_values: tuple[tuple[str, float], ...]
    uncertainty: float
    selected_alternatives: tuple[str, ...]
    retained_alternatives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OptimizationStep:
    step: int
    energy: float
    gradient_norm: float
    accepted: bool
    learning_rate: float


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    problem_id: str
    hard_result: ProgramResult
    initial_state: StructuredState
    final_state: StructuredState
    selected_branch: str | None
    disposition: str
    initial_energy: float
    final_energy: float
    trace: tuple[OptimizationStep, ...]
    factor_residuals: tuple[tuple[str, float], ...]
    convergence_reason: str
    evaluations: int


def row(value: object) -> dict:
    return asdict(value)
