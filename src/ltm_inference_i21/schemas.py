"""Immutable runtime contracts for I2.1."""

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
        if self.phase_index not in (0, 1):
            raise ValueError("invalid phase")
        if self.semantic_vector_ref < 0:
            raise ValueError("invalid semantic vector reference")


@dataclass(frozen=True, slots=True)
class ReasoningBody:
    body_id: str
    unit_ids: tuple[str, ...]
    scope_key: str
    source_id: str
    body_hash: str


@dataclass(frozen=True, slots=True)
class DynamicPrompt:
    prompt_id: str
    clamped_unit_ids: tuple[str, ...]
    scope_key: str
    maximum_bodies: int
    maximum_steps: int

    def __post_init__(self) -> None:
        if not self.clamped_unit_ids or self.maximum_bodies > 64 or self.maximum_steps > 64:
            raise ValueError("invalid bounded prompt")


@dataclass(frozen=True, slots=True)
class TraceStep:
    step: int
    energy: float
    accepted: bool
    body_id: str | None
    state_hash: str


@dataclass(frozen=True, slots=True)
class InferenceResult:
    prompt_id: str
    disposition: str
    selected_candidate_id: str | None
    candidates: tuple[tuple[str, float], ...]
    visited_body_ids: tuple[str, ...]
    trace: tuple[TraceStep, ...]
    coverage_disposition: str
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if self.factual_operations:
            raise ValueError("I2.1 cannot emit factual operations")
