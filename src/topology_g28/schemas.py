"""Immutable public and evaluator contracts for G2.8."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from topology_field_ir import FieldContext, FieldProgram
from topology_g1.schemas import TopologyOperation


@dataclass(frozen=True, slots=True)
class GoldenRoleDefinition:
    role_name: str
    allowed_node_kinds: tuple[str, ...]
    minimum: int
    maximum: int
    semantic_anchors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GoldenOperatorDefinition:
    operator_id: str
    relation_type: str
    reasoning_family: str
    semantic_anchors: tuple[str, ...]
    contrast_operator_ids: tuple[str, ...]
    roles: tuple[GoldenRoleDefinition, ...]
    hard_or_soft: str
    exact_operator: str
    field_operator: str
    allowed_contexts: tuple[str, ...]
    base_field_weight: float

    def __post_init__(self) -> None:
        if self.hard_or_soft not in {"hard", "soft"} or not self.roles:
            raise ValueError("invalid golden operator")
        if not math.isfinite(self.base_field_weight) or self.base_field_weight < 0:
            raise ValueError("invalid field weight")


@dataclass(frozen=True, slots=True)
class AtomBankManifest:
    revision: str
    g1_registry_sha256: str
    operators: tuple[GoldenOperatorDefinition, ...]
    compiler_policy_hash: str
    bank_hash: str


@dataclass(frozen=True, slots=True)
class ContentCandidate:
    candidate_id: str
    text: str
    source_start: int
    source_end: int
    node_kind_probabilities: tuple[tuple[str, float], ...]
    content_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError("invalid content offsets")
        if len(self.content_vector) != 384:
            raise ValueError("content vectors are 384-dimensional")


@dataclass(frozen=True, slots=True)
class OperatorCoordinate:
    relation_type: str
    activation: float
    clause_index: int
    delta_vector: tuple[float, ...]
    margin: float

    def __post_init__(self) -> None:
        if len(self.delta_vector) != 192 or not math.isfinite(self.activation):
            raise ValueError("invalid operator coordinate")


@dataclass(frozen=True, slots=True)
class RoleBindingHypothesis:
    relation_type: str
    role_name: str
    content_candidate_id: str
    probability: float
    role_vector: tuple[float, ...]
    binding_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.role_vector) != 64 or len(self.binding_vector) != 128:
            raise ValueError("invalid role binding vectors")


@dataclass(frozen=True, slots=True)
class CompleteGraphHypothesis:
    hypothesis_id: str
    relation_types: tuple[str, ...]
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    context: FieldContext
    operator_coordinates: tuple[OperatorCoordinate, ...]
    score: float
    probability: float
    margin: float
    disposition: Literal["accept", "clarification_required", "quarantine"]


@dataclass(frozen=True, slots=True)
class IdentityDecision:
    candidate_id: str
    disposition: Literal["existing", "new", "ambiguous"]
    object_ids: tuple[str, ...]
    confidence: float
    margin: float
    postings_visited: int


@dataclass(frozen=True, slots=True)
class CompiledSentenceArtifact:
    source_id: str
    atom_bank_revision: str
    candidates: tuple[CompleteGraphHypothesis, ...]
    accepted_field_program: FieldProgram | None
    g1_operations: tuple[TopologyOperation, ...]
    vector_sidecar_manifest_hash: str | None
    disposition: str
    failure_codes: tuple[str, ...]
    runtime_ms: float


@dataclass(frozen=True, slots=True)
class CompiledDocumentArtifact:
    document_id: str
    atom_bank_revision: str
    sentence_artifacts: tuple[CompiledSentenceArtifact, ...]
    identity_decisions: tuple[IdentityDecision, ...]
    accepted_operations: tuple[TopologyOperation, ...]
    field_program: FieldProgram | None
    unresolved_source_ids: tuple[str, ...]
    topology_hash: str | None
    field_hash: str | None
    disposition: str


@dataclass(frozen=True, slots=True)
class MigrationRecord:
    source_id: str
    old_bank_revision: str
    new_bank_revision: str
    old_factor_ids: tuple[str, ...]
    new_factor_ids: tuple[str, ...]
    invalidated_factor_ids: tuple[str, ...]
    old_topology_hash: str
    new_topology_hash: str
    old_field_hash: str
    new_field_hash: str
    disposition: str


@dataclass(frozen=True, slots=True)
class SourceExample:
    source_id: str
    document_id: str
    session_id: str
    text: str
    context: FieldContext
    atoms: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class GoldExample:
    source_id: str
    relation_types: tuple[str, ...]
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    disposition: str
    polarity: str
    modality: str
    scope_id: str
    atom_records: tuple[tuple[str, str, int, int], ...]
