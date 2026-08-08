"""Immutable public contracts for the G2.2 compiler boundary."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

Disposition = Literal["accept", "clarification_required", "quarantine"]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SentenceSource:
    source_id: str
    document_id: str
    session_id: str | None
    sentence_index: int
    text: str
    source_start: int
    source_end: int
    source_hash: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.document_id or not self.text:
            raise ValueError("sentence source identity and text are required")
        if self.source_start < 0 or self.source_end < self.source_start:
            raise ValueError("invalid source offsets")
        if len(self.source_hash) != 64:
            raise ValueError("source_hash must be sha256")


@dataclass(frozen=True, slots=True)
class SpanProposal:
    local_id: str
    text: str
    node_kind: str
    start: int
    end: int
    confidence: float

    def __post_init__(self) -> None:
        if not self.local_id or not self.text or self.start < 0 or self.end <= self.start:
            raise ValueError("invalid span proposal")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("span confidence must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class StructuredRelationCandidate:
    relation_type: str
    role_local_ids: tuple[tuple[str, tuple[str, ...]], ...]
    direction: str
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    confidence: float
    margin: float

    def __post_init__(self) -> None:
        if not self.relation_type or not self.role_local_ids:
            raise ValueError("relation type and role bindings are required")
        if not 0 <= self.confidence <= 1 or self.margin < 0:
            raise ValueError("invalid relation score")


@dataclass(frozen=True, slots=True)
class SentenceFragment:
    source: SentenceSource
    disposition: Disposition
    spans: tuple[SpanProposal, ...]
    relations: tuple[StructuredRelationCandidate, ...]
    ambiguity_reason: str | None
    quarantine_reason: str | None
    round_trip_text: str | None
    round_trip_cosine: float


@dataclass(frozen=True, slots=True)
class TopologyLinkCandidate:
    link_type: str
    source_local_id: str
    target_object_id: str
    session_id: str | None
    scope_id: str
    valid_at: int | None
    confidence: float
    margin: float


@dataclass(frozen=True, slots=True)
class TopologyDelta:
    source_id: str
    node_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    operation_ids: tuple[str, ...]
    topology_hash: str


@dataclass(frozen=True, slots=True)
class FieldHandoff:
    topology_hash: str
    factor_ids: tuple[str, ...]
    field_operators: tuple[str, ...]
    hard_obligation_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompilerResult:
    source_id: str
    fragment: SentenceFragment
    links: tuple[TopologyLinkCandidate, ...]
    delta: TopologyDelta | None
    field_handoff: FieldHandoff | None
    disposition: Disposition
    runtime_ms: float
    tokens: int


@dataclass(frozen=True, slots=True)
class GoldSentence:
    source: SentenceSource
    spans: tuple[SpanProposal, ...]
    relations: tuple[StructuredRelationCandidate, ...]
    disposition: Disposition
    paraphrase_group: str
    template_id: str


@dataclass(frozen=True, slots=True)
class GoldLink:
    source_id: str
    links: tuple[TopologyLinkCandidate, ...]
    disposition: Disposition
    paraphrase_group: str
    template_id: str
