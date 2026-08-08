"""Immutable contracts for the universal Mumbrane candidate representation."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .codebook import ALL_FEATURES_MASK

MUMBRANE_SCHEMA = "mumbrane/1"
NONE_INDEX = 0xFFFFFFFF


def _digest(value: str, label: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{label} must be a lower-case sha256")


def _finite(value: float | None, label: str) -> None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{label} must be finite")


@dataclass(frozen=True, slots=True)
class MumbraneUnit:
    unit_id: str
    schema_revision: str
    unit_class_code: int
    semantic_code: int
    feature_mask: int
    port_start: int
    port_count: int
    coordinate_start: int
    coordinate_count: int
    vector_bundle_index: int | None
    base_weight: float
    flags: int
    semantic_sha256: str

    def __post_init__(self) -> None:
        if not self.unit_id or self.schema_revision != MUMBRANE_SCHEMA:
            raise ValueError("invalid Mumbrane unit identity")
        if self.unit_class_code <= 0 or self.semantic_code <= 0:
            raise ValueError("invalid Mumbrane unit codes")
        if not 0 <= self.feature_mask <= ALL_FEATURES_MASK:
            raise ValueError("invalid Mumbrane feature mask")
        if min(self.port_start, self.port_count, self.coordinate_start, self.coordinate_count, self.flags) < 0:
            raise ValueError("invalid Mumbrane ranges")
        if self.vector_bundle_index is not None and self.vector_bundle_index < 0:
            raise ValueError("invalid vector bundle reference")
        _finite(self.base_weight, "base_weight")
        if self.base_weight < 0:
            raise ValueError("base_weight must be non-negative")
        _digest(self.semantic_sha256, "semantic_sha256")


@dataclass(frozen=True, slots=True)
class MumbranePort:
    source_unit_index: int
    role_code: int
    ordinal: int
    target_unit_index: int
    role_vector_index: int | None = None
    binding_vector_index: int | None = None
    flags: int = 0

    def __post_init__(self) -> None:
        if min(self.source_unit_index, self.role_code, self.ordinal, self.target_unit_index, self.flags) < 0:
            raise ValueError("invalid Mumbrane port")
        for index in (self.role_vector_index, self.binding_vector_index):
            if index is not None and index < 0:
                raise ValueError("invalid Mumbrane port vector")


@dataclass(frozen=True, slots=True)
class MumbraneCoordinate:
    unit_index: int
    axis_code: int
    value_code: int
    scalar_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self) -> None:
        if min(self.unit_index, self.axis_code, self.value_code) < 0:
            raise ValueError("invalid Mumbrane coordinate")
        for name, value in (("scalar", self.scalar_value), ("lower", self.lower_bound), ("upper", self.upper_bound)):
            _finite(value, name)
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValueError("invalid Mumbrane coordinate interval")


@dataclass(frozen=True, slots=True)
class MumbraneVectorBundle:
    content_vector: int | None
    operator_vector: int | None
    role_vector: int | None
    context_vector: int | None
    binding_vector: int | None

    def __post_init__(self) -> None:
        for index in (self.content_vector, self.operator_vector, self.role_vector, self.context_vector, self.binding_vector):
            if index is not None and index < 0:
                raise ValueError("invalid Mumbrane vector bundle")


@dataclass(frozen=True, slots=True)
class MumbraneProgram:
    schema_revision: str
    units: tuple[MumbraneUnit, ...]
    ports: tuple[MumbranePort, ...]
    coordinates: tuple[MumbraneCoordinate, ...]
    vector_bundles: tuple[MumbraneVectorBundle, ...]
    vectors: tuple[tuple[float, ...], ...]
    symbols: tuple[str, ...]
    source_archive: tuple[tuple[str, str], ...]
    substrate_sha256: str
    artifact_sha256: str
    archive_sha256: str

    def __post_init__(self) -> None:
        if self.schema_revision != MUMBRANE_SCHEMA:
            raise ValueError("unsupported Mumbrane schema")
        for name, value in (("substrate_sha256", self.substrate_sha256), ("artifact_sha256", self.artifact_sha256), ("archive_sha256", self.archive_sha256)):
            _digest(value, name)
        if len({item.unit_id for item in self.units}) != len(self.units):
            raise ValueError("duplicate Mumbrane unit identity")
        if any(unit.port_start + unit.port_count > len(self.ports) for unit in self.units):
            raise ValueError("Mumbrane unit port range exceeds table")
        if any(unit.coordinate_start + unit.coordinate_count > len(self.coordinates) for unit in self.units):
            raise ValueError("Mumbrane unit coordinate range exceeds table")
        if any(unit.vector_bundle_index is not None and unit.vector_bundle_index >= len(self.vector_bundles) for unit in self.units):
            raise ValueError("Mumbrane bundle reference exceeds table")
        if any(port.source_unit_index >= len(self.units) or port.target_unit_index >= len(self.units) for port in self.ports):
            raise ValueError("Mumbrane port unit reference exceeds table")
        if any(coordinate.unit_index >= len(self.units) for coordinate in self.coordinates):
            raise ValueError("Mumbrane coordinate unit reference exceeds table")
        for bundle in self.vector_bundles:
            for index in (bundle.content_vector, bundle.operator_vector, bundle.role_vector, bundle.context_vector, bundle.binding_vector):
                if index is not None and index >= len(self.vectors):
                    raise ValueError("Mumbrane vector bundle exceeds vector table")
        for vector in self.vectors:
            if not vector or not all(math.isfinite(value) for value in vector):
                raise ValueError("invalid Mumbrane vector")
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("duplicate Mumbrane symbol")


@dataclass(frozen=True, slots=True)
class TopologyProfile:
    profile_id: str
    revision: str
    mumbrane_schema_revision: str
    operator_bank_revision: str
    active_operator_ids: tuple[str, ...]
    exact_opcodes: tuple[tuple[str, str], ...]
    soft_opcodes: tuple[tuple[str, str], ...]
    required_feature_mask: int
    dynamics_weight: float
    profile_sha256: str

    def __post_init__(self) -> None:
        if not self.profile_id or not self.revision or self.mumbrane_schema_revision != MUMBRANE_SCHEMA:
            raise ValueError("invalid topology profile")
        if not self.active_operator_ids or not math.isfinite(self.dynamics_weight) or self.dynamics_weight < 0:
            raise ValueError("invalid topology profile policy")
        _digest(self.profile_sha256, "profile_sha256")


@dataclass(frozen=True, slots=True)
class CompiledTopologyProfile:
    profile: TopologyProfile
    operator_codes: tuple[int, ...]
    opcode_codes: tuple[tuple[int, int, int], ...]
    execution_sha256: str


@dataclass(frozen=True, slots=True)
class ProfileExecution:
    profile_id: str
    substrate_sha256: str
    execution_sha256: str
    hard_signature: str
    soft_state: tuple[tuple[str, float], ...]
    disposition: str
    active_unit_ids: tuple[str, ...]
    vector_rows_read: int


@dataclass(frozen=True, slots=True)
class MigrationResult:
    tier: int
    disposition: str
    affected_unit_ids: tuple[str, ...]
    unchanged_unit_ids: tuple[str, ...]
    old_execution_sha256: str
    new_execution_sha256: str
    rollback_sha256: str | None = None


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
