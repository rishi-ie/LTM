from __future__ import annotations

import hashlib

import numpy as np

DIMENSION = 32


def anchor(request_id: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(("anchor:" + request_id).encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 0.05, DIMENSION).astype(np.float64)


def force_for(factor_id: str, weight: float) -> tuple[float, ...]:
    seed = int.from_bytes(hashlib.sha256(("force:" + factor_id).encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=DIMENSION)
    vector /= np.linalg.norm(vector)
    return tuple((vector * weight).astype(np.float64))


def equilibrium(request_id: str, forces: list[np.ndarray] | tuple[np.ndarray, ...]) -> np.ndarray:
    total = anchor(request_id)
    for force in forces:
        total = total + force
    return total


def l2(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right))


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    return 1.0 if denom == 0.0 else float(np.dot(left, right) / denom)
