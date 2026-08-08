from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: int
    source_hash: str
    region_id: int
    created_version: int
    deleted_version: int | None


@dataclass(frozen=True, slots=True)
class TopologyObject:
    object_id: int
    source_id: int
    target_id: int
    coordinates: tuple[float, ...]
    active: bool
    object_type: int


@dataclass(frozen=True, slots=True)
class RegionDescriptor:
    region_id: int
    block_hash: str
    object_count: int
    active_count: int
    byte_count: int
    summary_hash: str


@dataclass(frozen=True, slots=True)
class TopologyManifest:
    version_id: int
    parent_version_id: int | None
    schema_version: int
    regions: tuple[RegionDescriptor, ...]
    group_summary_hashes: tuple[str, ...]
    operation_log_hash: str
    root_hash: str


@dataclass(frozen=True, slots=True)
class UpdateOperation:
    operation_id: str
    operation_type: str
    source_id: int
    region_id: int
    replacement_hash: str | None


@dataclass(frozen=True, slots=True)
class UpdateReceipt:
    operation_id: str
    old_version: int
    new_version: int
    changed_region_ids: tuple[int, ...]
    changed_summary_ids: tuple[str, ...]
    created_object_ids: tuple[int, ...]
    invalidated_object_ids: tuple[int, ...]
    bytes_written: int


@dataclass(frozen=True, slots=True)
class StorageQuery:
    query_id: str
    version_id: int
    object_id: int | None
    source_id: int | None


@dataclass(frozen=True, slots=True)
class StorageQueryResult:
    found: bool
    objects: tuple[TopologyObject, ...]
    provenance_source_ids: tuple[int, ...]
    blocks_read: int
    bytes_read: int
    full_scan: bool


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    fault_stage: str
    prior_version: int
    attempted_version: int
    recovered_version: int
    complete_old_or_new: bool
