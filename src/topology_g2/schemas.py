from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from topology_g1.schemas import RelationInstance, TopologyNode, TopologyOperation

Disposition = Literal["accept", "clarification_required", "quarantine"]
SourceKind = Literal["document", "conversation_turn"]


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    text: str
    source_kind: SourceKind
    speaker: str | None
    session_id: str | None
    turn_index: int | None
    source_hash: str

    @classmethod
    def make(
        cls,
        source_id: str,
        text: str,
        source_kind: SourceKind,
        speaker: str | None = None,
        session_id: str | None = None,
        turn_index: int | None = None,
    ) -> SourceRecord:
        return cls(
            source_id,
            text,
            source_kind,
            speaker,
            session_id,
            turn_index,
            hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class ContextEntity:
    entity_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    entity_type: str
    scope_id: str


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    entities: tuple[ContextEntity, ...]
    active_claims: tuple[TopologyNode, ...]
    scopes: tuple[TopologyNode, ...]
    recent_turns: tuple[SourceRecord, ...]
    reference_candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateObject:
    local_id: str
    node_kind: str
    subject: str | None
    predicate: str | None
    object: str | None
    polarity: str
    modality: str
    source_quote: str
    occurrence: int
    confidence: float


@dataclass(frozen=True, slots=True)
class CandidateRelation:
    relation_type: str
    arguments: tuple[tuple[str, tuple[str, ...]], ...]
    scope_name: str
    valid_from: int | None
    valid_to: int | None
    confidence: float


@dataclass(frozen=True, slots=True)
class CandidateReference:
    mention: str
    entity: str | None
    source_quote: str
    occurrence: int


@dataclass(frozen=True, slots=True)
class CandidateAmbiguity:
    kind: str
    source_quote: str
    occurrence: int
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateIR:
    disposition: Disposition
    speech_acts: tuple[str, ...]
    objects: tuple[CandidateObject, ...]
    relations: tuple[CandidateRelation, ...]
    references: tuple[CandidateReference, ...]
    ambiguities: tuple[CandidateAmbiguity, ...]


@dataclass(frozen=True, slots=True)
class ValidatedIR:
    disposition: Disposition
    nodes: tuple[TopologyNode, ...]
    relations: tuple[RelationInstance, ...]
    operations: tuple[TopologyOperation, ...]
    clarification_reason: str | None
    quarantine_reason: str | None


@dataclass(frozen=True, slots=True)
class CompilationResult:
    source_id: str
    first_generation: str
    first_error_codes: tuple[str, ...]
    repair_generation: str | None
    final_ir: ValidatedIR | None
    disposition: Disposition
    used_repair: bool
    runtime_ms: float
    generated_tokens: int


@dataclass(frozen=True, slots=True)
class GoldCase:
    source: SourceRecord
    context: ContextSnapshot
    gold_ir: CandidateIR
    topology_hash: str | None
    relation_types: tuple[str, ...]
    complexity: str
