from __future__ import annotations

import numpy as np


def build_features(statement: np.ndarray, arguments: np.ndarray, mask: np.ndarray, include_statement: bool = True) -> np.ndarray:
    if statement.ndim != 2 or arguments.shape[:2] != (len(statement), 3) or mask.shape != (len(statement), 3):
        raise ValueError("invalid embedding shapes")
    if include_statement:
        value = np.concatenate((statement, arguments.reshape(len(statement), -1), mask), axis=1)
    else:
        value = np.concatenate((arguments.reshape(len(statement), -1), mask), axis=1)
    return value.astype(np.float32, copy=False)
