"""Public L7 contracts.  The field law is fixed and has no model state."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def _bounded(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite in [0, 1]")


@dataclass(frozen=True, slots=True)
class Atom:
    atom_id: str
    expression: str
    sort: str
    reality_key: str
    scope_key: str = "global"


@dataclass(frozen=True, slots=True)
class RealityFactor:
    body_id: str
    reality_key: str
    input_atom_ids: tuple[str, ...]
    outcome_atom_id: str
    outcome_polarity: int
    authority: float
    confidence: float
    base_weight: float
    independent_source_key: str
    scope_key: str = "global"
    valid_from: int | None = None
    valid_to: int | None = None
    provenance_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.body_id or not self.input_atom_ids or self.outcome_polarity not in {-1, 1}:
            raise ValueError("invalid L7 factor")
        for value, name in ((self.authority, "authority"), (self.confidence, "confidence"), (self.base_weight, "base_weight")):
            _bounded(value, name)

    @property
    def weight(self) -> float:
        return self.authority * self.confidence * self.base_weight


@dataclass(frozen=True, slots=True)
class PublicPrompt:
    prompt_id: str
    assumption_atom_ids: tuple[str, ...]
    query_expression: str
    query_sort: str
    reality_key: str
    scope_key: str = "global"
    valid_at: int | None = None


@dataclass(frozen=True, slots=True)
class AtomState:
    atom_id: str
    positive_activation: float
    negative_activation: float
    tension: float

    def __post_init__(self) -> None:
        for value, name in ((self.positive_activation, "positive"), (self.negative_activation, "negative"), (self.tension, "tension")):
            _bounded(value, name)


@dataclass(frozen=True, slots=True)
class EquilibriumStep:
    sweep: int
    objective: float
    residual: float
    accepted: bool
    state_hash: str


@dataclass(frozen=True, slots=True)
class Candidate:
    atom_id: str
    expression: str
    polarity: int
    activation: float
    margin: float
    opposing_activation: float
    supporting_body_ids: tuple[str, ...]
    opposing_body_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EquilibriumResult:
    prompt_id: str
    disposition: str
    atom_states: tuple[AtomState, ...]
    factor_activations: tuple[tuple[str, float], ...]
    candidates: tuple[Candidate, ...]
    selected_candidate_id: str | None
    trajectory: tuple[EquilibriumStep, ...]
    objective: float
    residual: float
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.disposition not in {"candidate", "alternatives", "unknown", "incomplete_equilibrium"}:
            raise ValueError("invalid L7 disposition")
        if self.factual_operations:
            raise ValueError("L7 cannot mutate persistent facts")


def state_hash(positive: object, negative: object, factors: object) -> str:
    return hashlib.sha256(repr((positive, negative, factors)).encode()).hexdigest()
