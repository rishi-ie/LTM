"""Gold-separated runtime and evaluator contracts for G2.6."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from topology_field_ir import FieldContext, GoldenAtom

from .decoder import StructuredCandidate


@dataclass(frozen=True, slots=True)
class KernelCase:
    source_id: str
    text: str
    atoms: tuple[GoldenAtom, ...]
    context: FieldContext


@dataclass(frozen=True, slots=True)
class SemanticExample:
    source_id: str
    document_id: str
    session_id: str | None
    text: str
    atoms: tuple[GoldenAtom, ...]
    candidate: StructuredCandidate
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    family: str
    counterfactual_id: str | None = None


@dataclass(frozen=True, slots=True)
class KernelRuntimeCase:
    source_id: str
    text: str
    atoms: tuple[GoldenAtom, ...]
    context: FieldContext


@dataclass(frozen=True, slots=True)
class KernelGold:
    source_id: str
    candidate: StructuredCandidate
    polarity: str
    modality: str
    scope_id: str


@dataclass(frozen=True, slots=True)
class KernelPrediction:
    source_id: str
    candidate: StructuredCandidate
    polarity: str
    modality: str
    scope_id: str
    fieldir_valid: bool
    g1_valid: bool


@dataclass(frozen=True, slots=True)
class RelationCard:
    relation_type: str
    role_names: tuple[str, ...]
    allowed_kinds: tuple[tuple[str, tuple[str, ...]], ...]
    arities: tuple[int, ...]
    hard_or_soft: str
    exact_interpreter: str
    field_operator: str
    structural_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.relation_type or self.hard_or_soft not in {"hard", "soft"}:
            raise ValueError("invalid relation card")
        if len(self.role_names) != len(self.allowed_kinds) or len(self.role_names) != len(self.arities):
            raise ValueError("relation card role metadata differs")
        if len(self.structural_vector) != 64 or not all(math.isfinite(v) for v in self.structural_vector):
            raise ValueError("relation card structural vector must be 64 finite values")


@dataclass(frozen=True, slots=True)
class AtomCandidate:
    atom_id: str
    text: str
    start: int
    end: int
    node_kind: str
    probability: float
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.atom_id or self.start < 0 or self.end <= self.start:
            raise ValueError("invalid atom candidate span")
        if len(self.vector) != 384 or not all(math.isfinite(v) for v in self.vector):
            raise ValueError("atom candidate vector must be 384 finite values")
        if not 0 <= self.probability <= 1 or not math.isfinite(self.probability):
            raise ValueError("invalid atom probability")


@dataclass(frozen=True, slots=True)
class GraphCandidate:
    relation_type: str | None
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    polarity: str
    modality: str
    scope_id: str
    score: float
    probability: float
    margin: float
    disposition: Literal["accept", "clarification_required", "quarantine"]

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.score, self.probability, self.margin)):
            raise ValueError("graph scores must be finite")
        if not 0 <= self.probability <= 1:
            raise ValueError("invalid graph probability")


@dataclass(frozen=True, slots=True)
class SentenceCompilation:
    source_id: str
    candidates: tuple[GraphCandidate, ...]
    accepted_candidate: GraphCandidate | None
    field_program: object | None
    disposition: str
    failure_codes: tuple[str, ...]
    runtime_ms: float


@dataclass(frozen=True, slots=True)
class IdentityDecision:
    occurrence_atom_id: str
    disposition: Literal["existing", "new", "ambiguous"]
    candidate_object_ids: tuple[str, ...]
    confidence: float
    margin: float
    postings_visited: int


@dataclass(frozen=True, slots=True)
class DocumentCompilation:
    document_id: str
    sentence_results: tuple[SentenceCompilation, ...]
    identity_decisions: tuple[IdentityDecision, ...]
    field_program: object | None
    disposition: str
