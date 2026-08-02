from __future__ import annotations

import numpy as np

from .schemas import CapacityCase


def random_codes(case: CapacityCase, dimension: int = 128) -> np.ndarray:
    rng = np.random.default_rng(case.problem.codebook_seed)
    count = 2 * case.proposition_count
    for _ in range(100):
        raw = rng.normal(size=(count, dimension)).astype(np.float64)
        raw /= np.linalg.norm(raw, axis=1, keepdims=True)
        coherence = np.max(np.abs(raw @ raw.T - np.eye(count)))
        if coherence < 0.35:
            return raw.reshape(2, case.proposition_count, dimension).astype(np.float32)
    raise RuntimeError("could not construct incoherent codebook")


def orthogonal_codes(case: CapacityCase, dimension: int = 128) -> np.ndarray:
    count = 2 * case.proposition_count
    if count > dimension:
        raise ValueError("orthogonal codebook is unavailable above latent dimension")
    rng = np.random.default_rng(case.problem.codebook_seed)
    q, _ = np.linalg.qr(rng.normal(size=(dimension, count)))
    return q.T.reshape(2, case.proposition_count, dimension).astype(np.float32)
