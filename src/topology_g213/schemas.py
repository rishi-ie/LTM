from __future__ import annotations

import hashlib
from dataclasses import dataclass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ConversationSpan:
    span_id: str
    text: str
    start: int
    end: int
    slot_type: str = "content"


@dataclass(frozen=True, slots=True)
class ConversationTurnSource:
    source_id: str
    session_id: str
    episode_id: str
    turn_index: int
    speaker: str
    text: str
    source_hash: str


@dataclass(frozen=True, slots=True)
class ConversationCandidate:
    object_id: str
    object_kind: str
    label: str
    session_id: str
    episode_id: str
    active: bool
    superseded: bool
    scope_id: str
    recency: int


@dataclass(frozen=True, slots=True)
class DiscourseDecision:
    act: str
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class MemoryActionDecision:
    action: str
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class ReferenceDecision:
    state: str
    candidate_id: str | None
    candidate_ids: tuple[str, ...]
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class CorrectionDecision:
    target_id: str | None
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class PreferenceDecision:
    key: str | None
    value: str | None
    probability: float


@dataclass(frozen=True, slots=True)
class ConversationContext:
    polarity: str
    modality: str
    scope_id: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ConversationCase:
    source: ConversationTurnSource
    spans: tuple[ConversationSpan, ...]
    act: str
    action: str
    reference_state: str
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    preference_key: str | None = None
    preference_value: str | None = None
    target_id: str | None = None


@dataclass(frozen=True, slots=True)
class CompiledConversationTurn:
    source_id: str
    discourse: DiscourseDecision
    memory_action: MemoryActionDecision
    content_spans: tuple[ConversationSpan, ...]
    reference: ReferenceDecision
    correction: CorrectionDecision
    preference: PreferenceDecision
    context: ConversationContext
    disposition: str
    failure_codes: tuple[str, ...]
    runtime_ms: float
    conversation_event: object | None = None
    g1_operations: tuple[object, ...] = ()
    field_program: object | None = None
    mumbrane_program: object | None = None


@dataclass(frozen=True, slots=True)
class CompiledConversation:
    conversation_id: str
    turns: tuple[CompiledConversationTurn, ...]
    disposition: str
    lifecycle_metrics: tuple[tuple[str, float], ...] = ()

