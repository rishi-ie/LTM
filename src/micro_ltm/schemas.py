from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Label = Literal["entailed", "contradicted", "unknown"]


@dataclass(frozen=True, slots=True)
class SignedLiteral:
    proposition: int
    polarity: int

    def __post_init__(self) -> None:
        if self.polarity not in (-1, 1) or self.proposition < 0:
            raise ValueError("invalid signed literal")


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    premises: tuple[SignedLiteral, ...]
    conclusion: SignedLiteral

    def __post_init__(self) -> None:
        if len(self.premises) not in (1, 2):
            raise ValueError("rules require one or two premises")


@dataclass(frozen=True, slots=True)
class MicroProblem:
    problem_id: str
    codebook_seed: int
    facts: tuple[SignedLiteral, ...]
    rules: tuple[Rule, ...]
    query_proposition: int
    gold_label: Label
    proof_depth: int
    decisive_rule_id: str | None = None
    twin_id: str | None = None
    twin_operation: str | None = None


@dataclass(frozen=True, slots=True)
class FieldConfig:
    fact_weight: float = 32.0
    rule_weight: float = 16.0
    sparsity_weight: float = 0.01
    dimension: int = 128
    propositions: int = 24
    kappa: float = 8.0
    bias: float = 0.37
    exclusion_weight: float = 8.0
    norm_weight: float = 0.001


@dataclass(frozen=True, slots=True)
class OptimizationStep:
    step: int
    energy: float
    gradient_norm: float
    accepted: bool
    evaluations: int


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    initial_state: Any
    final_state: Any
    initial_energy: float
    final_energy: float
    trace: tuple[OptimizationStep, ...]
    target_positive_support: float
    target_negative_support: float
    convergence_reason: str


@dataclass(frozen=True, slots=True)
class DecoderResult:
    label: str
    probabilities: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class InterventionResult:
    intervention: str
    original_label: str
    intervened_label: str
    expected_label: str
    passed: bool


def problem_to_dict(problem: MicroProblem) -> dict[str, Any]:
    return asdict(problem)
