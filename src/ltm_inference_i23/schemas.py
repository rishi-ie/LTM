"""Public-only immutable contracts for I2.3."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AtomicMumbrane:
    unit_id: str
    body_id: str
    semantic_vector_ref: int
    local_index: int
    phase_index: int
    polarity: str
    modality: str
    scope_key: str
    identity_key: str
    provenance_id: str

    def __post_init__(self) -> None:
        if self.phase_index not in (0, 1) or self.semantic_vector_ref < 0:
            raise ValueError("invalid atomic Mumbrane")


@dataclass(frozen=True, slots=True)
class ReasoningBody:
    body_id: str
    unit_ids: tuple[str, ...]
    scope_key: str
    source_id: str
    body_hash: str

    def __post_init__(self) -> None:
        if len(self.unit_ids) < 2:
            raise ValueError("a body needs input and outcome Mumbranes")


@dataclass(frozen=True, slots=True)
class RuntimePrompt:
    prompt_id: str
    clamped_unit_ids: tuple[str, ...]
    scope_key: str
    maximum_bodies: int
    maximum_steps: int

    def __post_init__(self) -> None:
        if not self.clamped_unit_ids:
            raise ValueError("a prompt needs evidence")
        if not 1 <= self.maximum_bodies <= 64 or not 1 <= self.maximum_steps <= 32:
            raise ValueError("invalid bounded public prompt")


@dataclass(frozen=True, slots=True)
class OptimizationStep:
    step: int
    energy: float
    accepted: bool
    body_id: str | None
    opened_cell_ids: tuple[str, ...]
    state_hash: str


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    prompt_id: str
    disposition: str
    selected_candidate_id: str | None
    candidates: tuple[tuple[str, float], ...]
    supporting_body_ids: tuple[str, ...]
    trajectory: tuple[OptimizationStep, ...]
    coverage_disposition: str
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.factual_operations:
            raise ValueError("I2.3 can never emit factual operations")
