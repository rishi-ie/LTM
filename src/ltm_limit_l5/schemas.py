"""Immutable contracts for L5 compiled latent-field equilibrium."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class FieldMumbrane:
    unit_id: str
    body_id: str
    semantic_key: str
    semantic_vector_ref: int
    local_index: int
    phase_index: int
    polarity: int
    modality: str
    scope_key: str
    reality_key: str
    valid_from: int | None
    valid_to: int | None
    identity_key: str
    provenance_id: str
    independent_source_key: str

    def __post_init__(self) -> None:
        if not self.unit_id or not self.body_id or not self.semantic_key:
            raise ValueError("invalid field Mumbrane identity")
        if self.semantic_vector_ref < 0 or self.local_index < 0 or self.phase_index not in {0, 1}:
            raise ValueError("invalid field Mumbrane coordinate")
        if self.polarity not in {-1, 1}:
            raise ValueError("invalid field Mumbrane polarity")
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("invalid validity interval")


@dataclass(frozen=True, slots=True)
class EquilibriumBody:
    body_id: str
    input_unit_ids: tuple[str, ...]
    outcome_unit_ids: tuple[str, ...]
    base_weight: float
    authority: float
    confidence: float
    scope_key: str
    reality_key: str
    valid_from: int | None
    valid_to: int | None
    independent_source_key: str
    provenance_ids: tuple[str, ...]
    body_hash: str

    def __post_init__(self) -> None:
        if not self.input_unit_ids or not self.outcome_unit_ids or len(self.body_hash) != 64:
            raise ValueError("invalid equilibrium body")
        for value, name in ((self.base_weight, "base_weight"), (self.authority, "authority"), (self.confidence, "confidence")):
            _finite(value, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} outside [0,1]")


@dataclass(frozen=True, slots=True)
class PromptInfluenceRecord:
    unit_id: str
    semantic_key: str
    semantic_position: tuple[float, ...]
    clamp_strength: float
    query_relevance_weight: float
    polarity_sign: int
    modality_weight: float
    scope_key: str
    reality_key: str
    valid_at: int | None
    compiler_confidence: float
    provenance_id: str

    def __post_init__(self) -> None:
        if len(self.semantic_position) != 128 or any(not math.isfinite(item) for item in self.semantic_position):
            raise ValueError("invalid prompt semantic position")
        for value, name in ((self.clamp_strength, "clamp_strength"), (self.query_relevance_weight, "query_relevance_weight"), (self.modality_weight, "modality_weight"), (self.compiler_confidence, "compiler_confidence")):
            _finite(value, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} outside [0,1]")
        if self.polarity_sign not in {-1, 1}:
            raise ValueError("invalid prompt polarity")


@dataclass(frozen=True, slots=True)
class CompiledPromptField:
    prompt_id: str
    influences: tuple[PromptInfluenceRecord, ...]
    anchor_position: tuple[float, ...]
    disposition: str
    failure_codes: tuple[str, ...]
    encoder_calls: int
    source_hash: str

    def __post_init__(self) -> None:
        if len(self.anchor_position) != 128 or self.encoder_calls != 1:
            raise ValueError("invalid prompt compilation boundary")
        if self.disposition not in {"accept", "clarification_required", "quarantine"}:
            raise ValueError("invalid compiler disposition")


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    level: int
    parent_id: str | None
    child_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    prototype_refs: tuple[int, ...]
    transition_refs: tuple[int, ...]
    positive_source_mass: float
    negative_source_mass: float
    context_keys: tuple[str, ...]
    member_count: int
    radius: float
    uncertainty: float
    summary_hash: str

    def __post_init__(self) -> None:
        if self.level < 0 or len(self.prototype_refs) > 8 or len(self.transition_refs) > 8:
            raise ValueError("invalid minimap cell")
        if self.member_count < 0 or len(self.summary_hash) != 64:
            raise ValueError("invalid minimap accounting")


@dataclass(frozen=True, slots=True)
class LatentModeState:
    mode_id: str
    semantic_position: tuple[float, ...]
    unit_activations: tuple[tuple[str, float], ...]
    confidence_mass: float
    polarity: int
    supporting_source_keys: tuple[str, ...]
    state_hash: str

    def __post_init__(self) -> None:
        if len(self.semantic_position) != 128 or any(not math.isfinite(item) for item in self.semantic_position):
            raise ValueError("invalid latent mode")
        if self.polarity not in {-1, 1}:
            raise ValueError("invalid latent-mode polarity")


@dataclass(frozen=True, slots=True)
class EquilibriumStep:
    step: int
    energy: float
    residual: float
    accepted: bool
    learning_rate: float
    mode_hashes: tuple[str, ...]
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class FrontierSnapshot:
    step: int
    cell_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    opened_body_ids: tuple[str, ...]
    closed_body_ids: tuple[str, ...]
    coverage_bound: float
    frontier_hash: str


@dataclass(frozen=True, slots=True)
class EquilibriumCandidate:
    unit_id: str
    semantic_key: str
    polarity: int
    confidence: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    supporting_source_keys: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SupportCertificate:
    candidate_unit_id: str
    body_ids: tuple[str, ...]
    source_keys: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    verifier_revision: str
    verified: bool
    certificate_hash: str


@dataclass(frozen=True, slots=True)
class FieldEquilibriumResult:
    prompt_id: str
    disposition: str
    initial_modes: tuple[LatentModeState, ...]
    final_modes: tuple[LatentModeState, ...]
    candidates: tuple[EquilibriumCandidate, ...]
    selected_candidate_id: str | None
    trajectory: tuple[EquilibriumStep, ...]
    frontiers: tuple[FrontierSnapshot, ...]
    certificates: tuple[SupportCertificate, ...]
    coverage_disposition: str
    failure_codes: tuple[str, ...]
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        allowed = {"candidate", "alternatives", "ambiguous", "unknown", "incomplete_frontier", "quarantine"}
        if self.disposition not in allowed:
            raise ValueError("invalid equilibrium disposition")
        if self.factual_operations:
            raise ValueError("L5 cannot mutate factual topology")


FORBIDDEN_PUBLIC_FIELDS = frozenset(
    {
        "answer_id",
        "answer_candidates",
        "expected_disposition",
        "expected_depth",
        "required_body_ids",
        "route_identifier",
        "proof",
        "evaluator_path",
    }
)
