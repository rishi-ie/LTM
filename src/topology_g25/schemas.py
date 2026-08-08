"""Immutable typed-field contracts used by G2.5."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal

from topology_g1.schemas import TopologyOperation


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _vector(values: tuple[float, ...], dimension: int) -> None:
    if len(values) != dimension or not all(math.isfinite(value) for value in values):
        raise ValueError(f"expected finite vector with dimension {dimension}")


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
        if (
            not self.source_id
            or not self.document_id
            or not self.text
            or self.source_start < 0
            or self.source_end < self.source_start
        ):
            raise ValueError("source identity and text are required")
        if self.source_hash != sha256_text(self.text):
            raise ValueError("source hash mismatch")


@dataclass(frozen=True, slots=True)
class ContentAtomOccurrence:
    atom_id: str
    source_id: str
    node_kind: str
    text: str
    source_start: int
    source_end: int
    canonical_vector: tuple[float, ...]
    occurrence_vector: tuple[float, ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    polarity: str
    modality: str
    provenance_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.atom_id or not self.text or self.source_end <= self.source_start:
            raise ValueError("invalid content atom")
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("invalid atom interval")
        _vector(self.canonical_vector, 384)
        _vector(self.occurrence_vector, 384)


@dataclass(frozen=True, slots=True)
class OperatorActivation:
    relation_type: str
    prototype_scores: tuple[float, ...]
    probability: float

    def __post_init__(self) -> None:
        if len(self.prototype_scores) != 4 or not all(
            math.isfinite(value) for value in self.prototype_scores
        ):
            raise ValueError("operator activation requires four finite scores")
        if not math.isfinite(self.probability) or not 0 <= self.probability <= 1:
            raise ValueError("invalid operator probability")


@dataclass(frozen=True, slots=True)
class RolePlacement:
    relation_type: str
    role: str
    atom_id: str
    score: float
    role_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.role or not self.atom_id or not math.isfinite(self.score):
            raise ValueError("invalid role placement")
        _vector(self.role_vector, 64)


@dataclass(frozen=True, slots=True)
class ContextCoordinates:
    polarity: str
    modality: str
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    authority: float
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.authority) or not 0 <= self.authority <= 1:
            raise ValueError("invalid authority")
        if (
            self.valid_from is not None
            and self.valid_to is not None
            and self.valid_to < self.valid_from
        ):
            raise ValueError("invalid context interval")
        _vector(self.vector, 64)


@dataclass(frozen=True, slots=True)
class TopologyFactor:
    factor_id: str
    relation_type: str
    operator_vector: tuple[float, ...]
    role_placements: tuple[RolePlacement, ...]
    sparse_incidence: tuple[tuple[str, str], ...]
    binding_vectors: tuple[tuple[float, ...], ...]
    context: ContextCoordinates
    hard: bool
    field_operator: str
    confidence: float
    provenance_ids: tuple[str, ...]
    factor_hash: str

    def __post_init__(self) -> None:
        _vector(self.operator_vector, 128)
        if len(self.sparse_incidence) != len(self.role_placements) or len(
            self.binding_vectors
        ) != len(self.role_placements):
            raise ValueError("factor binding arrays differ")
        for vector in self.binding_vectors:
            _vector(vector, 256)
        if (
            len(self.factor_hash) != 64
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("invalid topology factor")


@dataclass(frozen=True, slots=True)
class PersistentAtomMatch:
    occurrence_atom_id: str
    disposition: Literal["existing", "new", "ambiguous"]
    candidate_object_ids: tuple[str, ...]
    confidence: float
    margin: float
    postings_visited: int


@dataclass(frozen=True, slots=True)
class StructuredFieldHandoff:
    content_atoms: tuple[ContentAtomOccurrence, ...]
    topology_factors: tuple[TopologyFactor, ...]
    g1_operations: tuple[TopologyOperation, ...]
    content_channel_hash: str
    operator_channel_hash: str
    role_channel_hash: str
    context_channel_hash: str
    binding_channel_hash: str
    exact_topology_hash: str
    field_hash: str


@dataclass(frozen=True, slots=True)
class KernelExample:
    source: SentenceSource
    atoms: tuple[ContentAtomOccurrence, ...]
    relation_type: str | None
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    family: str


@dataclass(frozen=True, slots=True)
class KernelRuntimeCase:
    """The gold-free subset passed to the kernel runtime process."""

    source: SentenceSource
    atoms: tuple[ContentAtomOccurrence, ...]


@dataclass(frozen=True, slots=True)
class KernelPrediction:
    source_id: str
    relation_type: str | None
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    confidence: float
    factor: TopologyFactor | None


@dataclass(frozen=True, slots=True)
class SentenceCompilationResult:
    """Gold-free compiler output; no temporary hypothesis is persisted."""

    source_id: str
    candidate_factors: tuple[TopologyFactor, ...]
    accepted_handoff: StructuredFieldHandoff | None
    disposition: str
    failure_codes: tuple[str, ...]
    runtime_ms: float


@dataclass(frozen=True, slots=True)
class DocumentCompilationResult:
    document_id: str
    sentence_results: tuple[SentenceCompilationResult, ...]
    persistent_matches: tuple[PersistentAtomMatch, ...]
    ordered_operations: tuple[TopologyOperation, ...]
    field_handoff: StructuredFieldHandoff | None
    disposition: str
