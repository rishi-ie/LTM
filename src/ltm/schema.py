"""Small immutable contracts for the numeric LTM field program.

The experiment packages remain the historical evidence layer.  These records
are the first product-facing semantic representation and deliberately contain
no source text.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

SCHEMA_VERSION = "ltm-field/2"
ARCHIVE_VERSION = "ltm-archive/1"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hex_digest(value: str, name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be a lower-case sha256")


def _finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _unit(value: float, name: str) -> None:
    _finite(value, name)
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be in [0, 1]")


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
        if not self.space_id or not self.revision or self.dimension <= 0:
            raise ValueError("invalid vector-space identity")
        _hex_digest(self.encoder_sha256, "encoder_sha256")
        if self.metric != "cosine" or self.dtype != "float32":
            raise ValueError("unsupported vector-space contract")


@dataclass(frozen=True, slots=True)
class VectorRef:
    vector_id: str
    space_id: str
    sidecar_sha256: str
    row_index: int
    row_sha256: str

    def __post_init__(self) -> None:
        if not self.vector_id or not self.space_id or self.row_index < 0:
            raise ValueError("invalid vector reference")
        _hex_digest(self.sidecar_sha256, "sidecar_sha256")
        _hex_digest(self.row_sha256, "row_sha256")


@dataclass(frozen=True, slots=True)
class TopologyConfig:
    revision: str
    registry_sha256: str
    relation_codes: tuple[tuple[str, int], ...]
    role_codes: tuple[tuple[str, int], ...]
    node_kind_codes: tuple[tuple[str, int], ...]
    vector_spaces: tuple[VectorSpaceSpec, ...]
    factor_record_bytes: int = 64
    binding_record_bytes: int = 24

    def __post_init__(self) -> None:
        if not self.revision or self.factor_record_bytes != 64 or self.binding_record_bytes != 24:
            raise ValueError("unsupported LTM v1 packing policy")
        _hex_digest(self.registry_sha256, "registry_sha256")
        self._check_codes(self.relation_codes, "relation")
        self._check_codes(self.role_codes, "role")
        self._check_codes(self.node_kind_codes, "node kind")
        if len({space.space_id for space in self.vector_spaces}) != len(self.vector_spaces):
            raise ValueError("duplicate vector space")

    @staticmethod
    def _check_codes(items: tuple[tuple[str, int], ...], name: str) -> None:
        if not items or len({key for key, _ in items}) != len(items):
            raise ValueError(f"duplicate {name} code")
        codes = [code for _, code in items]
        if len(set(codes)) != len(codes) or any(code <= 0 for code in codes):
            raise ValueError(f"invalid {name} code")

    @property
    def relation_map(self) -> dict[str, int]:
        return dict(self.relation_codes)

    @property
    def role_map(self) -> dict[str, int]:
        return dict(self.role_codes)

    @property
    def node_kind_map(self) -> dict[str, int]:
        return dict(self.node_kind_codes)


@dataclass(frozen=True, slots=True)
class ContextRecord:
    scope_key: str
    polarity: str
    modality: str
    valid_from: int | None
    valid_to: int | None
    confidence: float
    authority: float
    priority: float = 1.0
    vector_ref: int | None = None

    def __post_init__(self) -> None:
        if not self.scope_key or self.polarity not in {"positive", "negative"}:
            raise ValueError("invalid context")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("invalid validity interval")
        _unit(self.confidence, "confidence")
        _unit(self.authority, "authority")
        _finite(self.priority, "priority")
        if self.priority < 0 or (self.vector_ref is not None and self.vector_ref < 0):
            raise ValueError("invalid context weight or vector reference")


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source_key: str
    source_start: int
    source_end: int
    source_sha256: str

    def __post_init__(self) -> None:
        if not self.source_key or self.source_start < 0 or self.source_end < self.source_start:
            raise ValueError("invalid provenance span")
        _hex_digest(self.source_sha256, "source_sha256")


@dataclass(frozen=True, slots=True)
class AtomRecord:
    atom_id: str
    kind_code: int
    context_index: int
    provenance_index: int
    source_key: str
    source_start: int
    source_end: int
    canonical_vector: int | None = None
    occurrence_vector: int | None = None

    def __post_init__(self) -> None:
        _hex_digest(self.atom_id, "atom_id")
        if self.kind_code <= 0 or self.context_index < 0 or self.provenance_index < 0:
            raise ValueError("invalid atom code or table index")
        if not self.source_key or self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError("invalid atom source span")
        for index in (self.canonical_vector, self.occurrence_vector):
            if index is not None and index < 0:
                raise ValueError("invalid atom vector reference")


@dataclass(frozen=True, slots=True)
class BindingRecord:
    factor_index: int
    role_code: int
    ordinal: int
    atom_index: int
    role_vector: int | None = None
    binding_vector: int | None = None

    def __post_init__(self) -> None:
        if min(self.factor_index, self.role_code, self.ordinal, self.atom_index) < 0:
            raise ValueError("invalid binding index")
        for index in (self.role_vector, self.binding_vector):
            if index is not None and index < 0:
                raise ValueError("invalid binding vector reference")


@dataclass(frozen=True, slots=True)
class FactorRecord:
    factor_id: str
    operator_code: int
    context_index: int
    provenance_index: int
    binding_start: int
    binding_count: int
    base_weight: float = 1.0
    operator_vector: int | None = None
    region_index: int = 0

    def __post_init__(self) -> None:
        _hex_digest(self.factor_id, "factor_id")
        if self.operator_code <= 0 or min(self.context_index, self.provenance_index, self.binding_start) < 0:
            raise ValueError("invalid factor index")
        if self.binding_count <= 0 or self.region_index < 0:
            raise ValueError("factor must have bindings and a valid region")
        _finite(self.base_weight, "base_weight")
        if self.base_weight < 0 or (self.operator_vector is not None and self.operator_vector < 0):
            raise ValueError("invalid factor weight or vector reference")


@dataclass(frozen=True, slots=True)
class SourceArchiveRecord:
    source_id: str
    text: str
    source_sha256: str
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id or not self.text:
            raise ValueError("source archive records require text")
        if _sha256(self.text) != self.source_sha256:
            raise ValueError("source archive hash mismatch")


@dataclass(frozen=True, slots=True)
class SurfaceClaimRecord:
    """Decoder-facing labels kept outside the numeric reasoning tables."""

    claim_atom_id: str
    entity_label: str
    predicate_label: str
    object_label: str

    def __post_init__(self) -> None:
        _hex_digest(self.claim_atom_id, "claim_atom_id")
        if not all((self.entity_label, self.predicate_label, self.object_label)):
            raise ValueError("surface claim labels are required")


@dataclass(frozen=True, slots=True)
class SourceArchive:
    records: tuple[SourceArchiveRecord, ...]
    node_attributes: tuple[tuple[str, tuple[tuple[str, object], ...]], ...] = ()
    surface_claims: tuple[SurfaceClaimRecord, ...] = ()
    revision: str = ARCHIVE_VERSION

    def __post_init__(self) -> None:
        if self.revision != ARCHIVE_VERSION or len({item.source_id for item in self.records}) != len(self.records):
            raise ValueError("invalid source archive")
        if len({node_id for node_id, _attributes in self.node_attributes}) != len(self.node_attributes):
            raise ValueError("duplicate archived node attributes")
        if len({item.claim_atom_id for item in self.surface_claims}) != len(self.surface_claims):
            raise ValueError("duplicate surface claim labels")


@dataclass(frozen=True, slots=True)
class FieldManifestV2:
    schema_version: str
    config_sha256: str
    semantic_sha256: str
    artifact_sha256: str
    archive_sha256: str | None
    table_hashes: tuple[tuple[str, str], ...]
    row_counts: tuple[tuple[str, int], ...]
    byte_lengths: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported field schema")
        for name, value in (("config_sha256", self.config_sha256), ("semantic_sha256", self.semantic_sha256), ("artifact_sha256", self.artifact_sha256)):
            _hex_digest(value, name)
        if self.archive_sha256 is not None:
            _hex_digest(self.archive_sha256, "archive_sha256")
        for _name, value in self.table_hashes:
            _hex_digest(value, "table hash")
        if any(count < 0 for _name, count in (*self.row_counts, *self.byte_lengths)):
            raise ValueError("negative table row count")


@dataclass(frozen=True, slots=True)
class FieldProgramV2:
    config: TopologyConfig
    atoms: tuple[AtomRecord, ...]
    factors: tuple[FactorRecord, ...]
    bindings: tuple[BindingRecord, ...]
    contexts: tuple[ContextRecord, ...]
    provenances: tuple[ProvenanceRecord, ...]
    vectors: tuple[VectorRef, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported field schema")
        if len({item.atom_id for item in self.atoms}) != len(self.atoms):
            raise ValueError("duplicate atom identity")
        if len({item.factor_id for item in self.factors}) != len(self.factors):
            raise ValueError("duplicate factor identity")
        if len({item.vector_id for item in self.vectors}) != len(self.vectors):
            raise ValueError("duplicate vector identity")
        for atom in self.atoms:
            if atom.context_index >= len(self.contexts) or atom.provenance_index >= len(self.provenances):
                raise ValueError("atom references missing table row")
        for factor_index, factor in enumerate(self.factors):
            if factor.context_index >= len(self.contexts) or factor.provenance_index >= len(self.provenances):
                raise ValueError("factor references missing table row")
            end = factor.binding_start + factor.binding_count
            if end > len(self.bindings):
                raise ValueError("factor binding range exceeds table")
            for binding in self.bindings[factor.binding_start:end]:
                if binding.factor_index != factor_index or binding.atom_index >= len(self.atoms):
                    raise ValueError("invalid factor binding row")
        for item in self.vectors:
            if item.space_id not in {space.space_id for space in self.config.vector_spaces}:
                raise ValueError("vector references unknown space")
        vector_count = len(self.vectors)
        for atom in self.atoms:
            for reference in (atom.canonical_vector, atom.occurrence_vector):
                if reference is not None and reference >= vector_count:
                    raise ValueError("atom vector reference exceeds vector table")
        for factor in self.factors:
            if factor.operator_vector is not None and factor.operator_vector >= vector_count:
                raise ValueError("factor vector reference exceeds vector table")
            context = self.contexts[factor.context_index]
            if context.vector_ref is not None and context.vector_ref >= vector_count:
                raise ValueError("context vector reference exceeds vector table")
            for binding in self.bindings[factor.binding_start : factor.binding_start + factor.binding_count]:
                for reference in (binding.role_vector, binding.binding_vector):
                    if reference is not None and reference >= vector_count:
                        raise ValueError("binding vector reference exceeds vector table")


@dataclass(frozen=True, slots=True)
class CommitResult:
    accepted: bool
    semantic_sha256: str | None
    artifact_sha256: str | None
    failure_codes: tuple[str, ...] = ()
