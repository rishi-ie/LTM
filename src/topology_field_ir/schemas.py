"""Immutable FieldIR v1 contracts.

The semantic graph is intentionally separate from replaceable dense vector
artifacts.  Vector references can aid routing but cannot create a factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

SCHEMA_VERSION = "fieldir/1"


@dataclass(frozen=True, slots=True)
class VectorSpaceSpec:
    space_id: str
    revision: str
    encoder_sha256: str
    dimension: int
    metric: str = "cosine"
    normalized: bool = True
    dtype: str = "float32"

    def __post_init__(self) -> None:
        if not self.space_id or not self.revision or len(self.encoder_sha256) != 64:
            raise ValueError("vector space identity is invalid")
        if self.dimension <= 0 or self.metric != "cosine" or self.dtype != "float32":
            raise ValueError("unsupported vector space contract")


@dataclass(frozen=True, slots=True)
class VectorRef:
    vector_id: str
    space_id: str
    sidecar_sha256: str
    row_index: int
    row_sha256: str

    def __post_init__(self) -> None:
        if (
            not self.vector_id
            or not self.space_id
            or len(self.sidecar_sha256) != 64
            or len(self.row_sha256) != 64
            or self.row_index < 0
        ):
            raise ValueError("vector reference is invalid")


@dataclass(frozen=True, slots=True)
class FieldContext:
    scope_id: str
    polarity: str
    modality: str
    valid_from: int | None
    valid_to: int | None
    confidence: float
    authority: float
    priority: float = 1.0

    def __post_init__(self) -> None:
        if not self.scope_id or self.polarity not in {"positive", "negative"}:
            raise ValueError("invalid field context")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("invalid field validity interval")
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (self.confidence, self.authority)):
            raise ValueError("invalid confidence or authority")
        if not math.isfinite(self.priority) or self.priority < 0:
            raise ValueError("invalid priority")


@dataclass(frozen=True, slots=True)
class GoldenAtom:
    atom_id: str
    kind: str
    canonical_text: str
    occurrence_text: str
    source_id: str
    source_start: int
    source_end: int
    context: FieldContext
    provenance_sha256: str
    canonical_vector: VectorRef | None = None
    occurrence_vector: VectorRef | None = None

    def __post_init__(self) -> None:
        if (
            not self.atom_id
            or not self.kind
            or not self.canonical_text
            or not self.occurrence_text
            or not self.source_id
            or self.source_start < 0
            or self.source_end <= self.source_start
            or len(self.provenance_sha256) != 64
        ):
            raise ValueError("golden atom is invalid")


@dataclass(frozen=True, slots=True)
class TypedFactor:
    factor_id: str
    relation_type: str
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...]
    context: FieldContext
    provenance_sha256: str
    base_weight: float = 1.0
    operator_vector: VectorRef | None = None
    role_vectors: tuple[VectorRef, ...] = ()
    binding_vectors: tuple[VectorRef, ...] = ()

    def __post_init__(self) -> None:
        if not self.factor_id or not self.relation_type or len(self.provenance_sha256) != 64:
            raise ValueError("typed factor is invalid")
        if not self.role_bindings or not math.isfinite(self.base_weight) or self.base_weight < 0:
            raise ValueError("typed factor has no executable bindings")
        if len(self.role_vectors) not in {0, sum(len(ids) for _, ids in self.role_bindings)}:
            raise ValueError("role vector count differs from bindings")
        if len(self.binding_vectors) not in {0, sum(len(ids) for _, ids in self.role_bindings)}:
            raise ValueError("binding vector count differs from bindings")


@dataclass(frozen=True, slots=True)
class FieldProgram:
    program_id: str
    registry_sha256: str
    vector_spaces: tuple[VectorSpaceSpec, ...]
    atoms: tuple[GoldenAtom, ...]
    factors: tuple[TypedFactor, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.program_id or self.schema_version != SCHEMA_VERSION or len(self.registry_sha256) != 64:
            raise ValueError("field program identity is invalid")
        if len({item.space_id for item in self.vector_spaces}) != len(self.vector_spaces):
            raise ValueError("duplicate vector space")
        if len({item.atom_id for item in self.atoms}) != len(self.atoms):
            raise ValueError("duplicate atom")
        if len({item.factor_id for item in self.factors}) != len(self.factors):
            raise ValueError("duplicate factor")
