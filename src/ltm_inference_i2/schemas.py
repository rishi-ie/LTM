from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


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
        if not self.unit_id or not self.body_id or self.semantic_vector_ref < 0 or self.local_index < 0 or self.phase_index < 0:
            raise ValueError("invalid atomic Mumbrane")
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("invalid validity interval")


@dataclass(frozen=True, slots=True)
class ReasoningBody:
    body_id: str
    unit_ids: tuple[str, ...]
    phase_count: int
    region_id: str
    source_id: str
    body_hash: str

    def __post_init__(self) -> None:
        if not self.body_id or not self.unit_ids or self.phase_count < 2 or len(self.body_hash) != 64:
            raise ValueError("invalid reasoning body")


@dataclass(frozen=True, slots=True)
class TransitionSketch:
    sketch_id: str
    input_centroid_ref: int
    outcome_centroid_ref: int
    displacement_ref: int
    conjunction_signature_ref: int | None
    context_mask: int
    confidence: float
    sketch_hash: str

    def __post_init__(self) -> None:
        if min(self.input_centroid_ref, self.outcome_centroid_ref, self.displacement_ref, self.context_mask) < 0:
            raise ValueError("invalid transition sketch")
        _finite(self.confidence, "confidence")
        if len(self.sketch_hash) != 64:
            raise ValueError("invalid sketch hash")


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    level: int
    parent_id: str | None
    child_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    semantic_prototype_refs: tuple[int, ...]
    transition_basis_refs: tuple[int, ...]
    context_mask: int
    radius: float
    uncertainty: float
    member_count: int
    summary_hash: str

    def __post_init__(self) -> None:
        if self.level < 0 or self.radius < 0 or self.uncertainty < 0 or self.member_count < 0:
            raise ValueError("invalid minimap cell")
        if len(self.summary_hash) != 64:
            raise ValueError("invalid minimap hash")


@dataclass(frozen=True, slots=True)
class DynamicInferencePrompt:
    prompt_id: str
    clamped_unit_ids: tuple[str, ...]
    scope_key: str
    valid_at: int | None
    maximum_steps: int
    maximum_bodies: int

    def __post_init__(self) -> None:
        if not self.prompt_id or not self.clamped_unit_ids or not 0 < self.maximum_steps <= 32 or not 0 < self.maximum_bodies <= 64:
            raise ValueError("invalid inference prompt")


@dataclass(frozen=True, slots=True)
class LatentFieldState:
    semantic_position: tuple[float, ...]
    candidate_activations: tuple[tuple[str, float], ...]
    frontier_activations: tuple[tuple[str, float], ...]
    state_hash: str

    def __post_init__(self) -> None:
        if len(self.semantic_position) != 128 or any(not math.isfinite(v) for v in self.semantic_position):
            raise ValueError("invalid latent position")


@dataclass(frozen=True, slots=True)
class FrontierSnapshot:
    step: int
    minimap_cell_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    unit_ids: tuple[str, ...]
    opened_ids: tuple[str, ...]
    closed_ids: tuple[str, ...]
    coverage_bound: float
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class DynamicOptimizationStep:
    step: int
    energy: float
    gradient_norm: float
    accepted: bool
    learning_rate: float
    state_hash: str
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class LatentCandidate:
    atom_id: str
    probability: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DynamicInferenceResult:
    prompt_id: str
    disposition: str
    initial_state: LatentFieldState
    final_state: LatentFieldState
    candidates: tuple[LatentCandidate, ...]
    selected_candidate_id: str | None
    trajectory: tuple[DynamicOptimizationStep, ...]
    frontiers: tuple[FrontierSnapshot, ...]
    supporting_body_ids: tuple[str, ...]
    coverage_disposition: str
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()]

    def __post_init__(self) -> None:
        if self.disposition not in {"candidate", "ambiguous", "unknown", "incomplete_frontier", "quarantine"}:
            raise ValueError("invalid disposition")
        if self.factual_operations:
            raise ValueError("I2 cannot emit factual operations")


def body_hash(unit_ids: tuple[str, ...], phase_count: int, region_id: str) -> str:
    return _digest((unit_ids, phase_count, region_id))
