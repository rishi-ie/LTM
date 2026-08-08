"""Immutable G2.7 runtime and evaluator contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from topology_field_ir import FieldContext, FieldProgram, GoldenAtom


@dataclass(frozen=True, slots=True)
class ReasoningAtomSpec:
    relation_type: str
    family: str
    roles: tuple[str, ...]
    allowed_kinds: tuple[tuple[str, tuple[str, ...]], ...]
    hard_or_soft: str
    exact_operator: str
    field_operator: str
    structural_vector: tuple[float, ...]
    anchors: tuple[str, ...]
    contrasts: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.structural_vector) != 64 or self.hard_or_soft not in {"hard", "soft"}:
            raise ValueError("invalid reasoning atom specification")


@dataclass(frozen=True, slots=True)
class AtomCandidate:
    atom_id: str
    text: str
    start: int
    end: int
    node_kind: str
    vector: tuple[float, ...]
    probability: float

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start or len(self.vector) != 384:
            raise ValueError("invalid atom candidate")
        if not 0 <= self.probability <= 1 or not math.isfinite(self.probability):
            raise ValueError("invalid atom probability")


@dataclass(frozen=True, slots=True)
class ReasoningCoordinate:
    activations: tuple[float, ...]
    families: tuple[tuple[str, float], ...]
    active_atoms: tuple[str, ...]
    margins: tuple[tuple[str, float], ...]
    bank_hash: str

    def __post_init__(self) -> None:
        if len(self.activations) != 18 or not all(math.isfinite(x) for x in self.activations):
            raise ValueError("operator coordinate must contain 18 finite values")


@dataclass(frozen=True, slots=True)
class RoleBindingCoordinate:
    relation_type: str
    role: str
    atom_id: str
    probability: float
    role_vector: tuple[float, ...]
    binding_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.role_vector) != 64 or len(self.binding_vector) != 128:
            raise ValueError("role/binding dimensions are invalid")


@dataclass(frozen=True, slots=True)
class ContextCoordinate:
    polarity: str
    modality: str
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class CoordinateGraphCandidate:
    relation_type: str | None
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    relation_set: tuple[str, ...]
    context: ContextCoordinate
    score: float
    probability: float
    margin: float
    disposition: Literal["accept", "clarification_required", "quarantine"]


@dataclass(frozen=True, slots=True)
class SentenceCoordinateState:
    source_id: str
    atoms: tuple[AtomCandidate, ...]
    coordinate: ReasoningCoordinate
    bindings: tuple[RoleBindingCoordinate, ...]
    candidates: tuple[CoordinateGraphCandidate, ...]


@dataclass(frozen=True, slots=True)
class SentenceCompilation:
    source_id: str
    state: SentenceCoordinateState | None
    field_program: FieldProgram | None
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
    sentences: tuple[SentenceCompilation, ...]
    identities: tuple[IdentityDecision, ...]
    field_program: FieldProgram | None
    disposition: str


@dataclass(frozen=True, slots=True)
class GoldRecord:
    source_id: str
    relation_types: tuple[str, ...]
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    disposition: str
    polarity: str
    modality: str
    scope_id: str
    family: str
    atom_records: tuple[tuple[str, str, int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeExample:
    source_id: str
    document_id: str
    session_id: str
    text: str
    atoms: tuple[GoldenAtom, ...]
    context: FieldContext
