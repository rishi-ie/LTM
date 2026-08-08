from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .schemas import StorageQuery, UpdateOperation


def stable_int(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & ((1 << 63) - 1)


def source_id(seed: int, region_id: int, source_slot: int) -> int:
    return stable_int("source", seed, region_id, source_slot)


def operation_set(
    seed: int,
    regions: int,
    objects_per_region: int,
    per_kind: int,
    namespace: str = "normal",
) -> list[UpdateOperation]:
    source_count = objects_per_region // 10
    operations: list[UpdateOperation] = []
    for kind_index, kind in enumerate(("insert", "correct", "delete")):
        for number in range(per_kind):
            region = (number * 31 + kind_index * 17) % regions
            slot = (number * 7 + kind_index * 3) % source_count
            old_source = source_id(seed, region, slot)
            target_source = stable_int("insert-source", seed, namespace, number) if kind == "insert" else old_source
            operation_id = hashlib.sha256(f"{seed}:{namespace}:{kind}:{number}".encode()).hexdigest()[:24]
            replacement = hashlib.sha256(f"replacement:{seed}:{namespace}:{kind}:{number}".encode()).hexdigest()
            operations.append(UpdateOperation(operation_id, kind, target_source, region, replacement))
    return operations


def query_panel(seed: int, regions: int, objects_per_region: int, count: int) -> list[StorageQuery]:
    output: list[StorageQuery] = []
    for number in range(count):
        region = (number * 47) % regions
        source_slot = (number * 11) % (objects_per_region // 10)
        source = source_id(seed, region, source_slot)
        output.append(StorageQuery(f"query-{number:03d}", 1, None, source))
    return output


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, default=str, indent=2, sort_keys=True))
    temporary.replace(path)


def materialize(root: Path, operations: list[UpdateOperation], queries: list[StorageQuery]) -> None:
    write_json(root / "operations.json", [asdict(item) for item in operations])
    write_json(root / "queries.json", [asdict(item) for item in queries])


def load_operations(root: Path) -> list[UpdateOperation]:
    return [UpdateOperation(**row) for row in json.loads((root / "operations.json").read_text())]


def load_queries(root: Path) -> list[StorageQuery]:
    return [StorageQuery(**row) for row in json.loads((root / "queries.json").read_text())]
