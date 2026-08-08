from __future__ import annotations

from pathlib import Path

import pytest

from topology_g12.generator import operation_set, query_panel
from topology_g12.schemas import StorageQuery
from topology_g12.store import PersistentStore, SimulatedCrash


def _store(root: Path) -> PersistentStore:
    store = PersistentStore(root)
    store.compile_initial(1740, 4, 20)
    return store


def test_local_update_preserves_unrelated_blocks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    before = store.load_manifest()
    operation = operation_set(1740, 4, 20, 1)[0]
    receipt = store.apply(operation)
    after = store.load_manifest()
    changed = [index for index, pair in enumerate(zip(before.regions, after.regions)) if pair[0].block_hash != pair[1].block_hash]
    assert receipt.changed_region_ids == (operation.region_id,)
    assert changed == [operation.region_id]
    store.close()


def test_delete_removes_current_descendants_but_old_version_survives(tmp_path: Path) -> None:
    store = _store(tmp_path)
    deletion = next(item for item in operation_set(1740, 4, 20, 1) if item.operation_type == "delete")
    old = store.query(StorageQuery("old", 1, None, deletion.source_id))
    store.apply(deletion)
    current = store.query(StorageQuery("new", store.current_version(), None, deletion.source_id))
    assert old.found and not current.found
    store.close()


def test_fault_before_commit_keeps_old_version(tmp_path: Path) -> None:
    store = _store(tmp_path)
    operation = operation_set(1740, 4, 20, 1)[0]
    prior = store.current_version()
    with pytest.raises(SimulatedCrash):
        store.apply(operation, fault_stage="before_commit")
    recovery = store.recovery("before_commit", prior, prior + 1)
    assert recovery.recovered_version == prior


def test_checksum_rejects_corrupt_block(tmp_path: Path) -> None:
    store = _store(tmp_path)
    descriptor = store.load_manifest().regions[0]
    payload = bytearray((store.blocks / f"{descriptor.block_hash}.bin").read_bytes())
    payload[0] ^= 1
    corrupt = tmp_path / "corrupt.bin"; corrupt.write_bytes(payload)
    with pytest.raises(ValueError, match="CHECKSUM"):
        store.validate_block_file(corrupt, descriptor.block_hash)
    store.close()


def test_queries_map_exactly_one_block(tmp_path: Path) -> None:
    store = _store(tmp_path)
    query = query_panel(1740, 4, 20, 1)[0]
    result = store.query(query)
    assert result.found and result.blocks_read == 1 and not result.full_scan
    store.close()
