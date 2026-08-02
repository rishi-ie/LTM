from __future__ import annotations

import numpy as np

from .schemas import CompressionResult


def compress(activations: np.ndarray, codes: np.ndarray, query: int, anchor: float = 0.05) -> CompressionResult:
    active = float(np.sum(activations))
    weighted = np.einsum("np,npd->d", activations, codes)
    raw = anchor * (codes[0, query] + codes[1, query]) + weighted / np.sqrt(max(1.0, active))
    norm = float(np.linalg.norm(raw))
    state = (raw / norm if norm else raw).astype(np.float32)
    return CompressionResult(state, float(state @ codes[0, query]), float(state @ codes[1, query]))
