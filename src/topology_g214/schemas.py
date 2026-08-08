from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from topology_g213.schemas import ConversationCase


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class GateCandidate:
    object_id: str
    object_kind: str
    alias: str
    session_id: str
    episode_id: str
    scope_id: str
    active: bool
    expired: bool
    superseded: bool
    deleted: bool
    recency: int


@dataclass(frozen=True, slots=True)
class HeadConfidence:
    head_name: str
    selected_label: str
    probability: float
    margin: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.probability) or not math.isfinite(self.margin):
            raise ValueError("nonfinite head confidence")


@dataclass(frozen=True, slots=True)
class CandidateResolution:
    operation: str
    disposition: str
    selected_object_id: str | None
    alternative_object_ids: tuple[str, ...]
    confidence: float
    margin: float
    candidates_visited: int


@dataclass(frozen=True, slots=True)
class AcceptanceEvidence:
    source_id: str
    head_confidences: tuple[HeadConfidence, ...]
    resolutions: tuple[CandidateResolution, ...]
    minimum_probability: float
    minimum_margin: float
    passed_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]
    gate_revision: str
    evidence_hash: str


@dataclass(frozen=True, slots=True)
class GatedConversationPrediction:
    source_id: str
    original_prediction: object
    acceptance_evidence: AcceptanceEvidence
    final_disposition: str
    authorized_target_ids: tuple[str, ...]
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateCase:
    case: ConversationCase
    candidates: tuple[GateCandidate, ...]

