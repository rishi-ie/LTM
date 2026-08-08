"""Frozen runtime contracts. No relation labels or evaluator data are allowed."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def _hash(value: object) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def _finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


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
    valid_from: int | None
    valid_to: int | None
    identity_key: str
    provenance_id: str

    def __post_init__(self) -> None:
        if not self.unit_id or not self.body_id or self.semantic_vector_ref < 0:
            raise ValueError("invalid atomic Mumbrane")
        if self.local_index < 0 or self.phase_index < 0:
            raise ValueError("invalid Mumbrane position")
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("invalid Mumbrane validity")


@dataclass(frozen=True, slots=True)
class ReasoningBody:
    body_id: str
    unit_ids: tuple[str, ...]
    phase_count: int
    region_id: str
    source_id: str
    body_hash: str

    def __post_init__(self) -> None:
        if not self.body_id or not self.unit_ids or self.phase_count < 2:
            raise ValueError("invalid reasoning body")
        if len(self.body_hash) != 64:
            raise ValueError("invalid body hash")


@dataclass(frozen=True, slots=True)
class InferencePrompt:
    prompt_id: str
    clamped_unit_ids: tuple[str, ...]
    scope_key: str
    valid_at: int | None
    candidate_atom_ids: tuple[str, ...]
    maximum_bodies: int

    def __post_init__(self) -> None:
        if not self.prompt_id or not self.clamped_unit_ids:
            raise ValueError("empty inference prompt")
        if len(self.candidate_atom_ids) > 64 or not 0 < self.maximum_bodies <= 32:
            raise ValueError("inference bounds exceeded")


@dataclass(frozen=True, slots=True)
class LatentCandidate:
    atom_id: str
    probability: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in ((self.probability, "probability"), (self.margin, "margin")):
            _finite(value, label)


@dataclass(frozen=True, slots=True)
class OptimizationStep:
    step: int
    energy: float
    residual: float
    active_candidate_count: int
    state_hash: str


@dataclass(frozen=True, slots=True)
class LatentInferenceResult:
    prompt_id: str
    disposition: str
    candidates: tuple[LatentCandidate, ...]
    selected_candidate_id: str | None
    trajectory: tuple[OptimizationStep, ...]
    bodies_visited: int
    units_visited: int
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()]

    def __post_init__(self) -> None:
        if self.disposition not in {"candidate", "ambiguous", "unknown", "quarantine"}:
            raise ValueError("invalid latent disposition")
        if self.factual_operations:
            raise ValueError("I1 cannot emit factual operations")


def body_hash(unit_ids: tuple[str, ...], phase_count: int, region_id: str) -> str:
    return _hash((unit_ids, phase_count, region_id))
