"""Deterministic factorized semantic vectors for the controlled suite."""

from __future__ import annotations

import hashlib

import numpy as np

DIMENSION = 384


def _seed(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "little") % (2**32)


def basis(value: str) -> np.ndarray:
    rng = np.random.default_rng(_seed(value))
    vector = rng.normal(0.0, 1.0, DIMENSION).astype(np.float32)
    vector /= max(1e-8, float(np.linalg.norm(vector)))
    return vector


def semantic_vector(entity: str, predicate: str, value: str, polarity: str = "positive") -> np.ndarray:
    vector = basis(f"entity:{entity}") + basis(f"predicate:{predicate}") + basis(f"value:{value}")
    vector += (0.15 if polarity == "positive" else -0.15) * basis("polarity")
    vector /= max(1e-8, float(np.linalg.norm(vector)))
    return vector.astype(np.float32)


def opaque_vector(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=DIMENSION).astype(np.float32)
    vector /= max(1e-8, float(np.linalg.norm(vector)))
    return vector
