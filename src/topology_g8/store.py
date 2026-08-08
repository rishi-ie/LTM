from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from topology_g6.schemas import Rule
from topology_g7.schemas import SoftFactor

from .schemas import MemoryTrace, StoredFactor


def _factor_from_row(row: dict) -> StoredFactor:
    rule = row["hard_rule"]
    soft = row["soft_factor"]
    return StoredFactor(
        row["factor_id"],
        row["factor_kind"],
        row["block_id"],
        tuple(row["query_keys"]),
        row["hard_literal"],
        Rule(**{**rule, "premises": tuple(rule["premises"])}) if rule else None,
        SoftFactor(**{**soft, "variable_ids": tuple(soft["variable_ids"]), "target_values": tuple(soft["target_values"])}) if soft else None,
        tuple(row["provenance_ids"]),
    )


class BlockStore:
    """Reads raw blocks only through bounded batches and records residency."""

    def __init__(self, root: Path, batch_width: int):
        self.root = root
        self.batch_width = batch_width
        self.manifest = json.loads((root / "manifest.json").read_text())
        self.blocks_opened = 0
        self.block_reads = 0
        self.resident_blocks = 0
        self.resident_factors = 0
        self.resident_bytes = 0
        self.peak_blocks = 0
        self.peak_factors = 0
        self.peak_bytes = 0
        self.complete_field_materialization = False

    def _open(self, block_id: str) -> tuple[StoredFactor, ...]:
        entry = self.manifest["blocks"][block_id]
        path = self.root / "blocks" / entry["file"]
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError("BLOCK_CHECKSUM_MISMATCH")
        rows = json.loads(payload)
        if len(rows) != entry["factor_count"]:
            raise ValueError("BLOCK_FACTOR_COUNT_MISMATCH")
        self.blocks_opened += 1
        self.block_reads += 1
        self.resident_blocks += 1
        self.resident_factors += len(rows)
        self.resident_bytes += len(payload)
        self.peak_blocks = max(self.peak_blocks, self.resident_blocks)
        self.peak_factors = max(self.peak_factors, self.resident_factors)
        self.peak_bytes = max(self.peak_bytes, self.resident_bytes)
        if self.resident_blocks > self.batch_width:
            raise MemoryError("BLOCK_RESIDENCY_CAP")
        if self.resident_factors == self.manifest["factor_count"]:
            self.complete_field_materialization = True
        return tuple(_factor_from_row(row) for row in rows)

    def iter_batches(self, block_ids: tuple[str, ...]) -> list[tuple[tuple[str, ...], tuple[StoredFactor, ...]]]:
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("DUPLICATE_BLOCK_ID")
        output = []
        for start in range(0, len(block_ids), self.batch_width):
            ids = block_ids[start : start + self.batch_width]
            loaded = tuple((block_id, self._open(block_id)) for block_id in ids)
            factors = tuple(factor for _, block in loaded for factor in block)
            output.append((ids, factors))
            self.resident_blocks -= len(loaded)
            self.resident_factors -= len(factors)
            self.resident_bytes -= sum(
                self.manifest["blocks"][block_id]["bytes"] for block_id, _ in loaded
            )
        return output

    def trace(self) -> MemoryTrace:
        return MemoryTrace(
            self.blocks_opened,
            self.block_reads,
            self.peak_blocks,
            self.peak_factors,
            self.peak_bytes,
            self.complete_field_materialization,
        )


def write_field(root: Path, blocks: dict[str, list[StoredFactor]]) -> None:
    block_dir = root / "blocks"; block_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"blocks": {}, "factor_count": 0}
    for block_id, factors in sorted(blocks.items()):
        rows = [asdict(item) for item in sorted(factors, key=lambda item: item.factor_id)]
        payload = json.dumps(rows, default=str, separators=(",", ":"), sort_keys=True).encode()
        filename = f"{block_id}.json"; (block_dir / filename).write_bytes(payload)
        manifest["blocks"][block_id] = {"file": filename, "factor_count": len(rows), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        manifest["factor_count"] += len(rows)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
