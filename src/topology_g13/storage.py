from __future__ import annotations

import fcntl
import hashlib
import math
import os
import platform
import resource
from pathlib import Path

import numpy as np

from .schemas import Scale


def rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024) if platform.system() == "Darwin" else value / 1024


def physical_block(logical: int, blocks: int, layout: str) -> int:
    if layout == "identity":
        return logical
    if layout == "reverse":
        return blocks - 1 - logical
    if layout == "affine":
        # 19 is coprime to all registered block counts; fall back deterministically if needed.
        multiplier = 19 if math.gcd(19, blocks) == 1 else 17
        return (multiplier * logical + 7) % blocks
    raise ValueError(f"unknown physical layout: {layout}")


def inverse_physical(physical: np.ndarray, blocks: int, layout: str) -> np.ndarray:
    if layout == "identity":
        return physical
    if layout == "reverse":
        return blocks - 1 - physical
    multiplier = 19 if math.gcd(19, blocks) == 1 else 17
    inverse = pow(multiplier, -1, blocks)
    return ((physical - 7) * inverse) % blocks


class Arena:
    """Fixed-width arena: no factor is represented as a resident Python object."""

    def __init__(self, root: Path, scale: Scale, settings: dict, layout: str = "identity"):
        self.root, self.scale, self.settings, self.layout = root, scale, settings, layout
        self.factor_bytes = settings["factor_bytes"]
        self.block_size = settings["factor_block_size"]
        self.block_bytes = self.factor_bytes * self.block_size
        self.cache: dict[int, bytes] = {}
        self.bytes_read = 0
        self.full_scan = False
        self.true_uncached = bool(settings.get("require_true_uncached_reads", False))

    @property
    def factor_path(self) -> Path:
        suffix = "identity" if self.layout == "identity" else self.layout
        return self.root / "arenas" / f"factors-{suffix}.bin"

    @property
    def token_path(self) -> Path:
        return self.root / "arenas" / "tokens-u32.bin"

    @staticmethod
    def _write_tokens(path: Path, tokens: int, seed: int) -> str:
        digest = hashlib.sha256(); chunk = 1_000_000; salt = np.uint32(seed & 0xFFFFFFFF)
        with path.open("wb") as handle:
            for start in range(0, tokens, chunk):
                size = min(chunk, tokens - start)
                values = np.arange(start, start + size, dtype=np.uint32) ^ salt
                raw = values.tobytes(); handle.write(raw); digest.update(raw)
        return digest.hexdigest()

    @staticmethod
    def _write_layout(path: Path, blocks: int, layout: str, seed: int) -> str:
        digest = hashlib.sha256(); per_batch = 128; items = 256 * 8
        with path.open("wb") as handle:
            for start in range(0, blocks, per_batch):
                physical = np.arange(start, min(start + per_batch, blocks), dtype=np.int64)
                logical = inverse_physical(physical, blocks, layout).astype(np.uint64)
                words = (logical[:, None] * np.uint64(items) + np.arange(items, dtype=np.uint64)[None, :]) ^ np.uint64(seed)
                raw = words.astype("<u8", copy=False).tobytes(); handle.write(raw); digest.update(raw)
        return digest.hexdigest()

    @classmethod
    def build(cls, root: Path, scale: Scale, settings: dict, seed: int, layouts: tuple[str, ...]) -> dict:
        arena_root = root / "arenas"; arena_root.mkdir(parents=True, exist_ok=True)
        token_path = arena_root / "tokens-u32.bin"
        if token_path.exists():
            raise FileExistsError(token_path)
        token_hash = cls._write_tokens(token_path, scale.tokens, seed)
        hashes = {}
        for layout in layouts:
            path = arena_root / f"factors-{layout}.bin"
            if path.exists(): raise FileExistsError(path)
            hashes[layout] = cls._write_layout(path, scale.blocks, layout, seed)
        return {"tokens": scale.tokens, "factors": scale.factors, "blocks": scale.blocks,
                "token_bytes": token_path.stat().st_size, "token_hash": token_hash,
                "factor_bytes": {layout: (arena_root / f"factors-{layout}.bin").stat().st_size for layout in layouts},
                "factor_hashes": hashes}

    def read_block(self, logical_block: int) -> bytes:
        if logical_block < 0 or logical_block >= self.scale.blocks: raise ValueError("block out of scale")
        if logical_block in self.cache: return self.cache[logical_block]
        offset = physical_block(logical_block, self.scale.blocks, self.layout) * self.block_bytes
        with self.factor_path.open("rb", buffering=0) as handle:
            if self.true_uncached:
                if platform.system() != "Darwin" or not hasattr(fcntl, "F_NOCACHE"):
                    raise RuntimeError("true uncached reads are unavailable on this runtime")
                fcntl.fcntl(handle.fileno(), fcntl.F_NOCACHE, 1)
            handle.seek(offset); data = handle.read(self.block_bytes)
        if len(data) != self.block_bytes: raise ValueError("truncated factor arena")
        first = int.from_bytes(data[:8], "little")
        expected = (logical_block * self.block_size * 8) ^ self.settings["locked_seed"]
        if first != expected: raise ValueError("factor layout checksum mismatch")
        self.cache[logical_block] = data; self.bytes_read += len(data)
        return data

    def scan_prefix(self) -> str:
        """The exhaustive physical control scans the complete selected scale once."""
        digest = hashlib.sha256(); self.full_scan = True
        remaining = self.scale.blocks * self.block_bytes
        with self.factor_path.open("rb", buffering=0) as handle:
            if self.true_uncached:
                if platform.system() != "Darwin" or not hasattr(fcntl, "F_NOCACHE"):
                    raise RuntimeError("true uncached reads are unavailable on this runtime")
                fcntl.fcntl(handle.fileno(), fcntl.F_NOCACHE, 1)
            while remaining:
                data = handle.read(min(16 * 1024 * 1024, remaining))
                if not data: raise ValueError("truncated exhaustive scan")
                digest.update(data); remaining -= len(data); self.bytes_read += len(data)
        return digest.hexdigest()

    def enforce_memory(self) -> None:
        if rss_mb() > self.settings["memory_abort_mb"]:
            raise MemoryError("G13 memory guard aborted before the 20 GB hard ceiling")


def preflight(root: Path, settings: dict) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    free = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
    uncached = platform.system() == "Darwin" and hasattr(fcntl, "F_NOCACHE")
    if settings.get("require_true_uncached_reads") and not uncached:
        raise RuntimeError("G13 requires macOS F_NOCACHE for its uncached measurements")
    return {"disk_free_bytes": free, "rss_mb": rss_mb(), "memory_abort_mb": settings["memory_abort_mb"],
            "platform": platform.platform(), "numpy": np.__version__, "network": False,
            "factor_record_bytes": settings["factor_bytes"], "token_record_bytes": 4,
            "true_uncached_reads": uncached}
