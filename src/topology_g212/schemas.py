"""Immutable public contracts for G2.12."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SpanCandidate:
    span_id: str
    node_kind: str
    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class OperatorDecision:
    relation_type: str
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    relation_type: str
    role_name: str
    span_id: str
    probability: float


@dataclass(frozen=True, slots=True)
class DirectionDecision:
    relation_type: str
    forward_score: float
    reverse_score: float
    margin: float
    accepted_order: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class ContextDecision:
    polarity: str
    modality: str
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    confidence: float


@dataclass(frozen=True, slots=True)
class CompleteFactorCandidate:
    relation_type: str
    role_assignments: tuple[RoleAssignment, ...]
    direction: DirectionDecision
    context: ContextDecision
    probability: float
    margin: float


@dataclass(frozen=True, slots=True)
class AtomicCase:
    source_id: str
    text: str
    source_hash: str
    spans: tuple[SpanCandidate, ...]
    relations: tuple[str, ...]
    role_bindings: tuple[tuple[str, str, tuple[str, ...]], ...]
    polarity: str
    modality: str
    scope_id: str
    disposition: str


@dataclass(frozen=True, slots=True)
class SentenceCompilation:
    source_id: str
    candidates: tuple[CompleteFactorCandidate, ...]
    disposition: str
    failure_codes: tuple[str, ...]
    g1_operations: tuple[object, ...] = ()
    field_program: object | None = None
    mumbrane_program: object | None = None


@dataclass(frozen=True, slots=True)
class DocumentCompilation:
    document_id: str
    sentence_results: tuple[SentenceCompilation, ...]
    identity_decisions: tuple[object, ...]
    ordered_operations: tuple[object, ...]
    disposition: str


def finite_probability(value: float) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("probability must be finite and in [0, 1]")
