"""Immutable public contracts for the representation-first compiler."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal

from topology_g1.schemas import RelationInstance, TopologyNode, TopologyOperation

Disposition = Literal["accept", "clarification_required", "quarantine"]
MatchDisposition = Literal["existing", "new", "ambiguous"]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unit_vector(values: tuple[float, ...], dimension: int) -> None:
    if len(values) != dimension or not all(math.isfinite(value) for value in values):
        raise ValueError(f"expected a finite {dimension}-dimensional vector")
    norm = math.sqrt(sum(value * value for value in values))
    if not 0.999 <= norm <= 1.001:
        raise ValueError("semantic vectors must be normalized")


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
        if self.source_start < 0 or self.source_end != self.source_start + len(self.text):
            raise ValueError("sentence offsets must cover exact text")
        if self.source_hash != sha256_text(self.text):
            raise ValueError("source hash does not match source text")


@dataclass(frozen=True, slots=True)
class AtomPrototype:
    prototype_id: str
    node_kind: str
    working_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.prototype_id or not self.node_kind:
            raise ValueError("atom prototype identity is required")
        _unit_vector(self.working_vector, 128)


@dataclass(frozen=True, slots=True)
class GroundedAtom:
    local_id: str
    node_kind: str
    text: str
    source_start: int
    source_end: int
    semantic_vector: tuple[float, ...]
    working_vector: tuple[float, ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    polarity: str
    modality: str
    probability: float

    def __post_init__(self) -> None:
        if not self.local_id or not self.node_kind or not self.text or not self.scope_id:
            raise ValueError("grounded atom identity is incomplete")
        if self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError("invalid atom offsets")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("invalid atom validity interval")
        if not math.isfinite(self.probability) or not 0 <= self.probability <= 1:
            raise ValueError("atom probability must be in [0, 1]")
        _unit_vector(self.semantic_vector, 384)
        _unit_vector(self.working_vector, 128)


@dataclass(frozen=True, slots=True)
class MemoryAtom:
    object_id: str
    node_kind: str
    canonical_text: str
    aliases: tuple[str, ...]
    semantic_vector: tuple[float, ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    session_id: str | None
    provenance_ids: tuple[str, ...]
    encoder_hash: str

    def __post_init__(self) -> None:
        if not self.object_id or not self.node_kind or not self.canonical_text or not self.scope_id:
            raise ValueError("memory atom identity is incomplete")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("invalid memory atom validity")
        if len(self.encoder_hash) != 64:
            raise ValueError("memory atom requires an encoder hash")
        _unit_vector(self.semantic_vector, 384)


@dataclass(frozen=True, slots=True)
class AtomMatch:
    local_atom_id: str
    target_object_ids: tuple[str, ...]
    disposition: MatchDisposition
    confidence: float
    margin: float

    def __post_init__(self) -> None:
        if not self.local_atom_id or not math.isfinite(self.confidence) or not math.isfinite(self.margin):
            raise ValueError("invalid atom match")
        if not 0 <= self.confidence <= 1 or self.margin < 0:
            raise ValueError("invalid atom match confidence or margin")
        if self.disposition == "existing" and len(self.target_object_ids) != 1:
            raise ValueError("existing match requires exactly one target")
        if self.disposition == "new" and self.target_object_ids:
            raise ValueError("new atom match cannot name an existing target")
        if self.disposition == "ambiguous" and len(self.target_object_ids) < 2:
            raise ValueError("ambiguous match requires alternatives")


@dataclass(frozen=True, slots=True)
class OperatorHypothesis:
    hypothesis_id: str
    relation_type: str
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None
    probability: float

    def __post_init__(self) -> None:
        if not self.hypothesis_id or not self.relation_type or not self.role_bindings or not self.scope_id:
            raise ValueError("operator hypothesis is incomplete")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("invalid operator validity")
        if not math.isfinite(self.probability) or not 0 <= self.probability <= 1:
            raise ValueError("invalid operator probability")


@dataclass(frozen=True, slots=True)
class TopologyProgram:
    source_id: str
    atoms: tuple[GroundedAtom, ...]
    atom_matches: tuple[AtomMatch, ...]
    operators: tuple[OperatorHypothesis, ...]
    disposition: Disposition
    probability: float
    margin: float

    def __post_init__(self) -> None:
        if not self.source_id or not math.isfinite(self.probability) or not math.isfinite(self.margin):
            raise ValueError("invalid topology program")
        if not 0 <= self.probability <= 1 or self.margin < 0:
            raise ValueError("invalid topology program confidence")
        local_ids = [atom.local_id for atom in self.atoms]
        if len(local_ids) != len(set(local_ids)):
            raise ValueError("topology program has duplicate atom IDs")
        if self.disposition == "accept" and (not self.atoms or not self.operators):
            raise ValueError("accepted topology program requires atoms and operators")


@dataclass(frozen=True, slots=True)
class TensorTopologyIR:
    node_ids: tuple[str, ...]
    node_type_ids: tuple[int, ...]
    semantic_vectors: tuple[tuple[float, ...], ...]
    relation_operator_ids: tuple[int, ...]
    role_incidence: tuple[tuple[tuple[str, int], ...], ...]
    hard_mask: tuple[bool, ...]
    field_operator_ids: tuple[str, ...]
    atom_signatures: tuple[tuple[str, int, int, str, str], ...]
    relation_signatures: tuple[tuple, ...]
    provenance_ids: tuple[str, ...]
    ir_hash: str

    def __post_init__(self) -> None:
        count = len(self.node_ids)
        if count != len(self.node_type_ids) or count != len(self.semantic_vectors) or count != len(self.atom_signatures):
            raise ValueError("tensor IR node arrays differ in length")
        relation_count = len(self.relation_operator_ids)
        if (
            relation_count != len(self.role_incidence)
            or relation_count != len(self.hard_mask)
            or relation_count != len(self.field_operator_ids)
            or relation_count != len(self.relation_signatures)
        ):
            raise ValueError("tensor IR relation arrays differ in length")
        if len(self.ir_hash) != 64:
            raise ValueError("tensor IR requires a stable hash")
        for vector in self.semantic_vectors:
            _unit_vector(vector, 384)


@dataclass(frozen=True, slots=True)
class ValidatedProgram:
    program: TopologyProgram
    g1_nodes: tuple[TopologyNode, ...]
    g1_relations: tuple[RelationInstance, ...]
    g1_operations: tuple[TopologyOperation, ...]
    tensor_ir: TensorTopologyIR
    topology_hash: str


@dataclass(frozen=True, slots=True)
class SentenceCompilationResult:
    source_id: str
    hypotheses: tuple[TopologyProgram, ...]
    accepted_program: ValidatedProgram | None
    disposition: Disposition
    failure_codes: tuple[str, ...]
    runtime_ms: float
    token_count: int


@dataclass(frozen=True, slots=True)
class DocumentCompilationResult:
    document_id: str
    sentence_results: tuple[SentenceCompilationResult, ...]
    cross_sentence_links: tuple[OperatorHypothesis, ...]
    ordered_operations: tuple[TopologyOperation, ...]
    topology_hash: str | None
    field_handoff: tuple[str, ...] | None
    disposition: Disposition


@dataclass(frozen=True, slots=True)
class ProgramExample:
    source: SentenceSource
    gold: TopologyProgram
    public_memory: tuple[MemoryAtom, ...]
    family: str
    template_id: str
