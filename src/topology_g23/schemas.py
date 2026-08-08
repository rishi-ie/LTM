from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal

from topology_g1.schemas import RelationInstance, TopologyNode, TopologyOperation

Disposition = Literal["accept", "clarification_required", "quarantine"]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _probability(value: float) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("probability must be finite and in [0, 1]")


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
            raise ValueError("source identity and text are required")
        if self.source_start < 0 or self.source_end < self.source_start:
            raise ValueError("invalid source offsets")
        if self.source_hash != sha256_text(self.text) or len(self.source_hash) != 64:
            raise ValueError("source hash does not match text")


@dataclass(frozen=True, slots=True)
class TypedSpanCandidate:
    candidate_id: str
    text: str
    start: int
    end: int
    node_kind: str
    span_probability: float
    kind_probability: float

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.text or self.start < 0 or self.end <= self.start:
            raise ValueError("invalid span")
        _probability(self.span_probability); _probability(self.kind_probability)


@dataclass(frozen=True, slots=True)
class RelationHypothesis:
    hypothesis_id: str
    relation_type: str
    role_candidate_ids: tuple[tuple[str, tuple[str, ...]], ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    probability: float

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.relation_type or not self.role_candidate_ids:
            raise ValueError("relation hypothesis is incomplete")
        _probability(self.probability)


@dataclass(frozen=True, slots=True)
class TopologyHypothesis:
    hypothesis_id: str
    spans: tuple[TypedSpanCandidate, ...]
    relations: tuple[RelationHypothesis, ...]
    disposition: Disposition
    probability: float
    margin: float

    def __post_init__(self) -> None:
        _probability(self.probability)
        if self.margin < 0 or not math.isfinite(self.margin):
            raise ValueError("invalid hypothesis margin")


@dataclass(frozen=True, slots=True)
class ValidatedSentenceIR:
    source_id: str
    nodes: tuple[TopologyNode, ...]
    relations: tuple[RelationInstance, ...]
    operations: tuple[TopologyOperation, ...]
    topology_hash: str


@dataclass(frozen=True, slots=True)
class PublicTopologyCandidate:
    object_id: str
    object_kind: str
    canonical_text: str
    aliases: tuple[str, ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    session_id: str | None
    episode_id: str | None
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrossSentenceLink:
    relation_type: str
    source_node_id: str
    target_object_id: str
    role_bindings: tuple[tuple[str, str], ...]
    confidence: float
    margin: float


@dataclass(frozen=True, slots=True)
class SentenceCompilationResult:
    source_id: str
    hypotheses: tuple[TopologyHypothesis, ...]
    accepted_ir: ValidatedSentenceIR | None
    disposition: Disposition
    failure_codes: tuple[str, ...]
    runtime_ms: float
    token_count: int


@dataclass(frozen=True, slots=True)
class DocumentCompilationResult:
    document_id: str
    sentence_results: tuple[SentenceCompilationResult, ...]
    links: tuple[CrossSentenceLink, ...]
    ordered_operations: tuple[TopologyOperation, ...]
    topology_hash: str | None
    field_handoff: object | None
    disposition: Disposition


@dataclass(frozen=True, slots=True)
class FieldHandoff:
    topology_hash: str
    factor_ids: tuple[str, ...]
    field_operators: tuple[str, ...]
    hard_obligation_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GoldSentence:
    source: SentenceSource
    spans: tuple[TypedSpanCandidate, ...]
    relations: tuple[RelationHypothesis, ...]
    disposition: Disposition
    family: str
    template_id: str


@dataclass(frozen=True, slots=True)
class SentenceExample:
    source: SentenceSource
    gold: GoldSentence
    family: str


@dataclass(frozen=True, slots=True)
class GoldLink:
    source_id: str
    links: tuple[CrossSentenceLink, ...]
    disposition: Disposition
    family: str
    template_id: str


@dataclass(frozen=True, slots=True)
class LinkExample:
    source: SentenceSource
    fragment_spans: tuple[TypedSpanCandidate, ...]
    public_candidates: tuple[PublicTopologyCandidate, ...]
    gold: GoldLink
    family: str
