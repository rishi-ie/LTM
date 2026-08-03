from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class TopologyAddress:
    address_id: str; object_id: str; object_kind: str; canonical_name: str
    aliases: tuple[str, ...]; predicate: str | None; relation_type: str | None
    scope_id: str; valid_from: int | None; valid_to: int | None; episode_id: str | None
    entity_type: str | None; provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PromptMention:
    text: str; normalized_text: str; expected_kind: str | None; source_start: int; source_end: int


@dataclass(frozen=True, slots=True)
class PromptSignature:
    prompt_id: str; goal_kind: str; entity_mentions: tuple[PromptMention, ...]
    predicate_phrases: tuple[str, ...]; relation_hints: tuple[str, ...]
    target_variables: tuple[str, ...]; scope_hints: tuple[str, ...]
    valid_at: int | None; valid_between: tuple[int, int] | None
    polarity: str; modality: str; conversation_references: tuple[str, ...]; ambiguity_policy: str


@dataclass(frozen=True, slots=True)
class AddressCandidate:
    address_id: str; score: float; channels: tuple[str, ...]; exact_matches: tuple[str, ...]; conflicts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AddressResult:
    prompt_id: str; candidates: tuple[AddressCandidate, ...]; resolved_addresses: tuple[str, ...]
    retained_ambiguities: tuple[tuple[str, ...], ...]; disposition: str; confidence: float
    indexes_consulted: tuple[str, ...]; postings_visited: int; objects_materialized: int; complete_scan: bool; runtime_us: int


def to_dict(value: object) -> dict:
    return asdict(value)
