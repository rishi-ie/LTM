from __future__ import annotations

import numpy as np

from .schemas import CompressionConfig, CompressionResult


def _flatten(activations: np.ndarray, codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return activations.reshape(-1).astype(np.float64), codes.reshape(-1, codes.shape[-1]).astype(np.float64)


def compress_equilibrium(activations: np.ndarray, codes: np.ndarray, config: CompressionConfig, compute_condition: bool = True) -> CompressionResult:
    y, matrix = _flatten(activations, codes)
    active = int(np.sum(y > 0.5))
    fallback = False
    condition = 0.0
    if config.method == "normalized_sum":
        raw = matrix.T @ y / np.sqrt(max(1.0, float(np.sum(y))))
        state = raw / max(1e-12, np.linalg.norm(raw))
    elif config.method == "raw_sum" or config.method == "orthogonal_sum":
        state = matrix.T @ y
    elif config.method == "active_dual" and active <= config.dimension:
        active_indices = np.flatnonzero(y > 0.5)
        active_matrix = matrix[active_indices]
        gram = active_matrix @ active_matrix.T + config.ridge * np.eye(len(active_indices))
        condition = float(np.linalg.cond(gram)) if (compute_condition and len(active_indices)) else 0.0
        state = active_matrix.T @ np.linalg.solve(gram, np.ones(len(active_indices))) if len(active_indices) else np.zeros(config.dimension)
    elif config.method in {"ridge", "active_dual"}:
        if config.method == "active_dual":
            fallback = True
        gram = matrix.T @ matrix + config.ridge * np.eye(config.dimension)
        condition = float(np.linalg.cond(gram)) if compute_condition else 0.0
        state = np.linalg.solve(gram, matrix.T @ y)
    else:
        raise ValueError(f"unsupported query-agnostic compression method: {config.method}")
    reconstruction = matrix @ state
    rmse = float(np.sqrt(np.mean((reconstruction - y) ** 2)))
    return CompressionResult(state.astype(np.float32), float(np.linalg.norm(state)), active, condition, rmse, fallback)
