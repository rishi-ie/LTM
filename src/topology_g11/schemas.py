from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ConversationEvent:
    event_id: str
    session_id: str
    turn_index: int
    speaker: str
    event_type: str
    payload: tuple[tuple[str, str], ...]
    source_hash: str
    episode_id: str

    def value(self, name: str, default: str = "") -> str:
        return dict(self.payload).get(name, default)


@dataclass(frozen=True, slots=True)
class SessionClaim:
    claim_id: str
    session_id: str
    subject: str
    predicate: str
    object: str
    polarity: str
    scope_id: str
    valid_from_turn: int
    valid_to_turn: int | None
    source_event_id: str
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssistantEvent:
    event_id: str
    session_id: str
    text: str
    authorized_claim_ids: tuple[str, ...]
    decisive_provenance_ids: tuple[str, ...]
    independent_evidence: bool
    authority: float


@dataclass(frozen=True, slots=True)
class EpisodeSummary:
    summary_id: str
    session_id: str
    episode_id: str
    active_claim_ids: tuple[str, ...]
    supersession_ids: tuple[str, ...]
    preference_ids: tuple[str, ...]
    conflict_ids: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    exact_event_ids: tuple[str, ...]
    summary_hash: str


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    query_id: str
    session_id: str
    subject: str | None
    predicate: str
    scope_id: str
    episode_reference: str | None
    requested_style: str | None


@dataclass(frozen=True, slots=True)
class MemoryResult:
    query_id: str
    status: str
    claims: tuple[SessionClaim, ...]
    reference_bindings: tuple[tuple[str, str], ...]
    preferences: tuple[str, ...]
    conflicts: tuple[str, ...]
    decisive_provenance_ids: tuple[str, ...]
    reopened_episode_ids: tuple[str, ...]
    rows_read: int


@dataclass(frozen=True, slots=True)
class ConversationCase:
    conversation_id: str
    family: str
    session_id: str
    base_claim: SessionClaim
    events: tuple[ConversationEvent, ...]


def row(value: object) -> dict:
    return asdict(value)
