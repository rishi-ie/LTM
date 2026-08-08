from __future__ import annotations

import hashlib
import json
import mmap
import os
import sqlite3
import struct
from dataclasses import asdict
from pathlib import Path

from .generator import source_id, stable_int
from .schemas import (
    RecoveryResult,
    RegionDescriptor,
    StorageQuery,
    StorageQueryResult,
    TopologyManifest,
    TopologyObject,
    UpdateOperation,
    UpdateReceipt,
)

RECORD = struct.Struct("<QQQ8fII")
ACTIVE = 1
GROUP_SIZE = 10


class SimulatedCrash(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _coords(*parts: object) -> tuple[float, ...]:
    raw = hashlib.sha256("\x1f".join(str(part) for part in parts).encode()).digest()
    return tuple((raw[index] / 255.0) * 2.0 - 1.0 for index in range(8))


def _pack(item: TopologyObject) -> bytes:
    return RECORD.pack(
        item.object_id,
        item.source_id,
        item.target_id,
        *item.coordinates,
        ACTIVE if item.active else 0,
        item.object_type,
    )


def _unpack(payload: bytes, offset: int) -> TopologyObject:
    row = RECORD.unpack_from(payload, offset)
    return TopologyObject(row[0], row[1], row[2], tuple(row[3:11]), bool(row[11] & ACTIVE), row[12])


def _summary(region_id: int, objects: list[TopologyObject]) -> tuple[dict, bytes]:
    active = [item for item in objects if item.active]
    coordinates = tuple(round(sum(item.coordinates[index] for item in active), 8) for index in range(8))
    object_xor = 0
    for item in active:
        object_xor ^= item.object_id
    body = {
        "region_id": region_id,
        "object_count": len(objects),
        "active_count": len(active),
        "object_xor": object_xor,
        "coordinates": coordinates,
        "source_digest": _digest("|".join(str(item.source_id) for item in active).encode()),
    }
    return body, _canonical(body)


class PersistentStore:
    """Content-addressed binary topology blocks plus transactional SQLite metadata."""

    def __init__(self, root: Path, schema_version: int = 1) -> None:
        self.root = root
        self.schema_version = schema_version
        self.blocks = root / "blobs"
        self.summaries = root / "summaries"
        self.manifests = root / "manifests"
        for directory in (self.blocks, self.summaries, self.manifests):
            directory.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "metadata.sqlite")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY, source_hash TEXT NOT NULL, region_id INTEGER NOT NULL,
                created_version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_events (
                event_id TEXT PRIMARY KEY, source_id INTEGER NOT NULL, event_type TEXT NOT NULL,
                version_id INTEGER NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS object_locations (
                object_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, region_id INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_objects (
                source_id INTEGER NOT NULL, object_id INTEGER NOT NULL,
                PRIMARY KEY (source_id, object_id)
            );
            CREATE TABLE IF NOT EXISTS versions (
                version_id INTEGER PRIMARY KEY, parent_version INTEGER, manifest_hash TEXT NOT NULL,
                manifest_file TEXT NOT NULL, operation_id TEXT
            );
            CREATE TABLE IF NOT EXISTS current_version (singleton INTEGER PRIMARY KEY CHECK(singleton=1), version_id INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS update_receipts (
                operation_id TEXT PRIMARY KEY, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS operation_log (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS object_source_index ON object_locations(source_id);
            CREATE INDEX IF NOT EXISTS source_object_index ON source_objects(source_id);
            """
        )
        self.db.commit()
        self.blocks_read = 0
        self.bytes_read = 0
        self.peak_resident_blocks = 0

    def close(self) -> None:
        self.db.close()

    def _atomic_blob(self, directory: Path, payload: bytes, suffix: str) -> tuple[str, Path]:
        digest = _digest(payload)
        path = directory / f"{digest}{suffix}"
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".tmp")
            with temporary.open("wb") as handle:
                handle.write(payload)
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        return digest, path

    def _write_block(self, objects: list[TopologyObject]) -> tuple[str, int]:
        payload = b"".join(_pack(item) for item in objects)
        digest, _ = self._atomic_blob(self.blocks, payload, ".bin")
        return digest, len(payload)

    def _write_summary(self, summary: dict) -> str:
        digest, _ = self._atomic_blob(self.summaries, _canonical(summary), ".json")
        return digest

    def _read_block(self, block_hash: str) -> list[TopologyObject]:
        path = self.blocks / f"{block_hash}.bin"
        payload = path.read_bytes()
        if _digest(payload) != block_hash or len(payload) % RECORD.size:
            raise ValueError("BLOCK_CHECKSUM_MISMATCH")
        with path.open("rb") as handle:
            mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                output = [_unpack(mapped, offset) for offset in range(0, len(mapped), RECORD.size)]
            finally:
                mapped.close()
        self.blocks_read += 1
        self.bytes_read += len(payload)
        self.peak_resident_blocks = max(self.peak_resident_blocks, 1)
        return output

    @staticmethod
    def validate_block_file(path: Path, expected_hash: str) -> None:
        payload = path.read_bytes()
        if _digest(payload) != expected_hash or len(payload) % RECORD.size:
            raise ValueError("BLOCK_CHECKSUM_MISMATCH")

    def validate_manifest_file(self, path: Path) -> None:
        data = json.loads(path.read_text())
        if data.get("schema_version") != self.schema_version:
            raise ValueError("SCHEMA_VERSION_MISMATCH")
        root = data.pop("root_hash", None)
        if root is None or _digest(_canonical(data)) != root:
            raise ValueError("MANIFEST_CHECKSUM_MISMATCH")

    def _manifest_path(self, version_id: int) -> Path:
        return self.manifests / f"v{version_id:06d}.json"

    def _manifest_dict(self, manifest: TopologyManifest) -> dict:
        return asdict(manifest)

    def _write_manifest(self, manifest: TopologyManifest) -> tuple[str, Path]:
        body = self._manifest_dict(manifest)
        expected = body.pop("root_hash")
        calculated = _digest(_canonical(body))
        if calculated != expected:
            raise ValueError("MANIFEST_ROOT_MISMATCH")
        path = self._manifest_path(manifest.version_id)
        payload = _canonical(self._manifest_dict(manifest))
        temporary = path.with_suffix(".json.tmp")
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        return _digest(payload), path

    def load_manifest(self, version_id: int | None = None) -> TopologyManifest:
        if version_id is None:
            row = self.db.execute("SELECT version_id FROM current_version WHERE singleton=1").fetchone()
            if row is None:
                raise ValueError("NO_PUBLISHED_VERSION")
            version_id = int(row[0])
        row = self.db.execute("SELECT manifest_file FROM versions WHERE version_id=?", (version_id,)).fetchone()
        if row is None:
            raise ValueError("UNKNOWN_VERSION")
        data = json.loads((self.root / row[0]).read_text())
        if data["schema_version"] != self.schema_version:
            raise ValueError("SCHEMA_VERSION_MISMATCH")
        regions = tuple(RegionDescriptor(**entry) for entry in data["regions"])
        manifest = TopologyManifest(
            data["version_id"],
            data["parent_version_id"],
            data["schema_version"],
            regions,
            tuple(data["group_summary_hashes"]),
            data["operation_log_hash"],
            data["root_hash"],
        )
        body = self._manifest_dict(manifest); root_hash = body.pop("root_hash")
        if _digest(_canonical(body)) != root_hash:
            raise ValueError("MANIFEST_CHECKSUM_MISMATCH")
        return manifest

    def _groups(self, descriptors: list[RegionDescriptor]) -> tuple[str, ...]:
        groups: list[str] = []
        for start in range(0, len(descriptors), GROUP_SIZE):
            children = descriptors[start : start + GROUP_SIZE]
            body = {"group": start // GROUP_SIZE, "children": [item.summary_hash for item in children]}
            groups.append(self._write_summary(body))
        return tuple(groups)

    def _build_manifest(
        self,
        version_id: int,
        parent: int | None,
        descriptors: list[RegionDescriptor],
        operation_hash: str,
    ) -> TopologyManifest:
        groups = self._groups(descriptors)
        base = {
            "version_id": version_id,
            "parent_version_id": parent,
            "schema_version": self.schema_version,
            "regions": [asdict(item) for item in descriptors],
            "group_summary_hashes": list(groups),
            "operation_log_hash": operation_hash,
        }
        return TopologyManifest(version_id, parent, self.schema_version, tuple(descriptors), groups, operation_hash, _digest(_canonical(base)))

    def _source_objects(self, source: int) -> list[int]:
        return [int(row[0]) for row in self.db.execute("SELECT object_id FROM source_objects WHERE source_id=? ORDER BY object_id", (source,))]

    def compile_initial(self, seed: int, regions: int, objects_per_region: int) -> TopologyManifest:
        if self.db.execute("SELECT 1 FROM current_version").fetchone() is not None:
            raise ValueError("STORE_ALREADY_COMPILED")
        if objects_per_region % 10:
            raise ValueError("OBJECTS_PER_REGION_NOT_DIVISIBLE_BY_TEN")
        descriptors: list[RegionDescriptor] = []
        sources_per_region = objects_per_region // 10
        with self.db:
            for region in range(regions):
                objects: list[TopologyObject] = []
                source_rows = []
                location_rows = []
                lineage_rows = []
                for source_slot in range(sources_per_region):
                    source = source_id(seed, region, source_slot)
                    source_hash = _digest(f"source:{seed}:{region}:{source_slot}".encode())
                    source_rows.append((source, source_hash, region, 1))
                    object_ids = [stable_int("object", source, ordinal, 0) for ordinal in range(10)]
                    for ordinal, object_id in enumerate(object_ids):
                        target = object_ids[(ordinal + 1) % len(object_ids)]
                        item = TopologyObject(object_id, source, target, _coords(seed, source, ordinal, 0), True, ordinal % 4)
                        objects.append(item)
                        location_rows.append((object_id, source, region))
                        lineage_rows.append((source, object_id))
                block_hash, byte_count = self._write_block(objects)
                summary, _ = _summary(region, objects)
                descriptors.append(RegionDescriptor(region, block_hash, len(objects), summary["active_count"], byte_count, self._write_summary(summary)))
                self.db.executemany("INSERT INTO sources VALUES (?, ?, ?, ?)", source_rows)
                self.db.executemany("INSERT INTO object_locations VALUES (?, ?, ?)", location_rows)
                self.db.executemany("INSERT INTO source_objects VALUES (?, ?)", lineage_rows)
        manifest = self._build_manifest(1, None, descriptors, _digest(b""))
        manifest_hash, path = self._write_manifest(manifest)
        with self.db:
            self.db.execute("INSERT INTO versions VALUES (?, ?, ?, ?, ?)", (1, None, manifest_hash, path.relative_to(self.root).as_posix(), None))
            self.db.execute("INSERT INTO current_version VALUES (1, 1)")
        return manifest

    def _objects_for_source(self, source: int, region: int, epoch: int) -> list[TopologyObject]:
        ids = [stable_int("object", source, ordinal, epoch) for ordinal in range(10)]
        return [TopologyObject(object_id, source, ids[(ordinal + 1) % 10], _coords(source, ordinal, epoch), True, ordinal % 4) for ordinal, object_id in enumerate(ids)]

    def _operation_log_hash(self) -> str:
        rows = [row[0] for row in self.db.execute("SELECT payload FROM operation_log ORDER BY sequence")]
        return _digest(_canonical(rows))

    def apply(self, operation: UpdateOperation, *, fault_stage: str | None = None) -> UpdateReceipt:
        old = self.load_manifest()
        old_version = old.version_id
        if fault_stage == "before_block":
            raise SimulatedCrash(fault_stage)
        descriptor = old.regions[operation.region_id]
        objects = self._read_block(descriptor.block_hash)
        source_objects = self._source_objects(operation.source_id)
        invalidated: list[int] = []
        created: list[int] = []
        if operation.operation_type == "insert":
            if source_objects:
                raise ValueError("INSERT_SOURCE_EXISTS")
            created_objects = self._objects_for_source(operation.source_id, operation.region_id, old_version)
            objects.extend(created_objects); created = [item.object_id for item in created_objects]
        elif operation.operation_type == "correct":
            if not source_objects:
                raise ValueError("CORRECT_SOURCE_UNKNOWN")
            for index, item in enumerate(objects):
                if item.source_id == operation.source_id and item.active:
                    objects[index] = TopologyObject(item.object_id, item.source_id, item.target_id, item.coordinates, False, item.object_type)
                    invalidated.append(item.object_id)
            created_objects = self._objects_for_source(operation.source_id, operation.region_id, old_version)
            objects.extend(created_objects); created = [item.object_id for item in created_objects]
        elif operation.operation_type == "delete":
            if not source_objects:
                raise ValueError("DELETE_SOURCE_UNKNOWN")
            for index, item in enumerate(objects):
                if item.source_id == operation.source_id and item.active:
                    objects[index] = TopologyObject(item.object_id, item.source_id, item.target_id, item.coordinates, False, item.object_type)
                    invalidated.append(item.object_id)
        else:
            raise ValueError("UNKNOWN_OPERATION")
        block_hash, byte_count = self._write_block(objects)
        if fault_stage == "after_block":
            raise SimulatedCrash(fault_stage)
        summary, _ = _summary(operation.region_id, objects)
        replacement = RegionDescriptor(operation.region_id, block_hash, len(objects), summary["active_count"], byte_count, self._write_summary(summary))
        descriptors = list(old.regions); descriptors[operation.region_id] = replacement
        new_version = old_version + 1
        manifest = self._build_manifest(new_version, old_version, descriptors, _digest(_canonical(asdict(operation))))
        manifest_hash, path = self._write_manifest(manifest)
        if fault_stage == "after_manifest":
            raise SimulatedCrash(fault_stage)
        receipt = UpdateReceipt(operation.operation_id, old_version, new_version, (operation.region_id,), (replacement.summary_hash, manifest.group_summary_hashes[operation.region_id // GROUP_SIZE]), tuple(created), tuple(invalidated), byte_count)
        try:
            self.db.execute("BEGIN IMMEDIATE")
            if operation.operation_type == "insert":
                self.db.execute("INSERT INTO sources VALUES (?, ?, ?, ?)", (operation.source_id, operation.replacement_hash, operation.region_id, new_version))
                self.db.executemany("INSERT INTO object_locations VALUES (?, ?, ?)", [(item, operation.source_id, operation.region_id) for item in created])
                self.db.executemany("INSERT INTO source_objects VALUES (?, ?)", [(operation.source_id, item) for item in created])
            self.db.execute("INSERT INTO source_events VALUES (?, ?, ?, ?, ?)", (operation.operation_id, operation.source_id, operation.operation_type, new_version, json.dumps(asdict(operation), sort_keys=True)))
            self.db.execute("INSERT INTO versions VALUES (?, ?, ?, ?, ?)", (new_version, old_version, manifest_hash, path.relative_to(self.root).as_posix(), operation.operation_id))
            self.db.execute("INSERT INTO update_receipts VALUES (?, ?)", (operation.operation_id, json.dumps(asdict(receipt), sort_keys=True)))
            self.db.execute("INSERT INTO operation_log(operation_id, payload) VALUES (?, ?)", (operation.operation_id, json.dumps(asdict(operation), sort_keys=True)))
            if fault_stage == "before_commit":
                raise SimulatedCrash(fault_stage)
            self.db.execute("UPDATE current_version SET version_id=? WHERE singleton=1", (new_version,))
            self.db.commit()
        except SimulatedCrash:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise
        if fault_stage == "after_commit":
            raise SimulatedCrash(fault_stage)
        return receipt

    def query(self, query: StorageQuery) -> StorageQueryResult:
        self.blocks_read = 0; self.bytes_read = 0; self.peak_resident_blocks = 0
        manifest = self.load_manifest(query.version_id)
        source = query.source_id
        if query.object_id is not None:
            row = self.db.execute("SELECT source_id, region_id FROM object_locations WHERE object_id=?", (query.object_id,)).fetchone()
            if row is None:
                return StorageQueryResult(False, (), (), 0, 0, False)
            source, region = int(row[0]), int(row[1])
        elif source is not None:
            row = self.db.execute("SELECT region_id FROM sources WHERE source_id=?", (source,)).fetchone()
            if row is None:
                return StorageQueryResult(False, (), (), 0, 0, False)
            region = int(row[0])
        else:
            raise ValueError("QUERY_REQUIRES_OBJECT_OR_SOURCE")
        objects = self._read_block(manifest.regions[region].block_hash)
        selected = [item for item in objects if item.active and ((query.object_id is not None and item.object_id == query.object_id) or (query.object_id is None and item.source_id == source))]
        return StorageQueryResult(bool(selected), tuple(selected), (source,) if selected else (), self.blocks_read, self.bytes_read, False)

    def current_version(self) -> int:
        return self.load_manifest().version_id

    def root_hash(self) -> str:
        return self.load_manifest().root_hash

    def store_bytes(self) -> int:
        return sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())

    def recovery(self, fault_stage: str, prior: int, attempted: int) -> RecoveryResult:
        self.close()
        reopened = PersistentStore(self.root, self.schema_version)
        try:
            recovered = reopened.current_version()
        finally:
            reopened.close()
        return RecoveryResult(fault_stage, prior, attempted, recovered, recovered in (prior, attempted))
