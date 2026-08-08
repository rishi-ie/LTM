"""Immutable G2.9 compiler contracts; evaluator gold is intentionally absent."""

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
    base_field_weight: float


@dataclass(frozen=True, slots=True)
class AtomBankManifest:
    revision: str
    g1_registry_sha256: str
    operators: tuple[GoldenOperatorDefinition, ...]
    compiler_policy_hash: str
    bank_hash: str


@dataclass(frozen=True, slots=True)
class GoldenQueryBank:
    revision: str
    encoder_checkpoint_hash: str
    query_hash: str
    operator_query_count: int
    role_query_count: int


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
            raise ValueError("invalid content source offsets")
        if len(self.content_vector) != 384:
            raise ValueError("content vector must be 384-dimensional")


@dataclass(frozen=True, slots=True)
class OperatorQueryMatch:
    relation_type: str
    instance_slot: int
    activation: float
    margin: float
    attended_offsets: tuple[tuple[int, int], ...]
    delta_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.delta_vector) != 192 or self.instance_slot not in {0, 1, 2}:
            raise ValueError("invalid operator query match")


@dataclass(frozen=True, slots=True)
class RoleQueryMatch:
    relation_type: str
    instance_slot: int
    role_name: str
    candidate_id: str
    probability: float
    margin: float
    role_vector: tuple[float, ...]
    binding_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.role_vector) != 64 or len(self.binding_vector) != 128:
            raise ValueError("invalid role query vector")


@dataclass(frozen=True, slots=True)
class RelationSetPrediction:
    relation_types: tuple[str, ...]
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
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
    operator_matches: tuple[OperatorQueryMatch, ...]
    role_matches: tuple[RoleQueryMatch, ...]
    prediction: RelationSetPrediction | None
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


def finite_probability(value: float) -> float:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("invalid probability")
    return value
