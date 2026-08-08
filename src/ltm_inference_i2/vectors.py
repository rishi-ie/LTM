"""Factorized semantic vectors with a compositional state axis."""

from __future__ import annotations

import hashlib

import numpy as np

DIMENSION = 384
STATE_DIMENSION = 128


def _seed(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "little") % (2**32)


def basis(value: str, dimension: int = DIMENSION) -> np.ndarray:
    rng = np.random.default_rng(_seed(value))
    vector = rng.normal(size=dimension).astype(np.float32)
    vector /= max(1e-8, float(np.linalg.norm(vector)))
    return vector


def semantic_vector(entity: str, state: int, *, polarity: str = "positive", scope: str = "global") -> np.ndarray:
    """A semantic occurrence vector; state coordinate is compositional, not a relation label."""
    vector = 0.55 * basis(f"entity:{entity}") + 0.35 * basis(f"state:{state}")
    vector[0] += float(state) / 64.0
    vector[1] += 0.12 if polarity == "positive" else -0.12
    vector[2] += 0.08 if scope == "global" else -0.08
    vector /= max(1e-8, float(np.linalg.norm(vector)))
    return vector.astype(np.float32)


def state_projection(vector: np.ndarray) -> np.ndarray:
    """Deterministic 384→128 projection used by the minimap before training."""
    value = np.asarray(vector, dtype=np.float32)
    if value.shape != (DIMENSION,):
        raise ValueError("expected 384D semantic vector")
    projected = value[:STATE_DIMENSION].copy()
    projected /= max(1e-8, float(np.linalg.norm(projected)))
    return projected.astype(np.float32)
