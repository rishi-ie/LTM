"""Numeric, text-free FieldIR v2 audit contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NumericAtom:
    atom_key: int
    kind_code: int
    context_index: int
    provenance_index: int
    source_key: int
    source_start: int
    source_end: int
    canonical_vector: int | None
    occurrence_vector: int | None


@dataclass(frozen=True, slots=True)
class NumericFactor:
    factor_key: int
    operator_code: int
    context_index: int
    provenance_index: int
    binding_start: int
    binding_count: int
    base_weight: float
    operator_vector: int | None


@dataclass(frozen=True, slots=True)
class NumericBinding:
    factor_index: int
    role_code: int
    ordinal: int
    atom_index: int
    role_vector: int | None
    binding_vector: int | None


@dataclass(frozen=True, slots=True)
class NumericContext:
    scope_key: int
    polarity_code: int
    modality_key: int
    valid_from: int | None
    valid_to: int | None
    confidence: float
    authority: float
    priority: float


@dataclass(frozen=True, slots=True)
class NumericProvenance:
    source_key: int
    source_start: int
    source_end: int
    source_sha256: str


@dataclass(frozen=True, slots=True)
class NumericVectorRef:
    vector_key: int
    space_key: int
    sidecar_sha256: str
    row_index: int
    row_sha256: str


@dataclass(frozen=True, slots=True)
class NumericFieldProgram:
    program_key: int
    registry_sha256: str
    atom_keys: tuple[str, ...]
    factor_keys: tuple[str, ...]
    id_keys: tuple[str, ...]
    vector_space_keys: tuple[str, ...]
    atoms: tuple[NumericAtom, ...]
    factors: tuple[NumericFactor, ...]
    bindings: tuple[NumericBinding, ...]
    contexts: tuple[NumericContext, ...]
    provenances: tuple[NumericProvenance, ...]
    vectors: tuple[NumericVectorRef, ...]


@dataclass(frozen=True, slots=True)
class SourceArchive:
    """Non-active display/audit data needed only for legacy reconstruction."""

    program_id: str
    atom_text: tuple[tuple[str, str, str], ...]
    ids: tuple[tuple[str, str], ...]
    modalities: tuple[tuple[str, str], ...]
    vector_ids: tuple[tuple[str, str], ...]
    vector_spaces: tuple[tuple[str, object], ...]
