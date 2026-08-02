from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from micro_ltm.schemas import Label, MicroProblem


@dataclass(frozen=True, slots=True)
class CapacityCase:
    problem: MicroProblem
    proposition_count: int
    density_bucket: str


@dataclass(frozen=True, slots=True)
class CompressionConfig:
    method: Literal["normalized_sum", "raw_sum", "ridge", "active_dual", "orthogonal_sum", "legacy"]
    ridge: float = 1e-6
    dimension: int = 128


@dataclass(frozen=True, slots=True)
class CompressionResult:
    state: np.ndarray
    state_norm: float
    active_count: int
    condition_number: float
    reconstruction_rmse: float
    fallback_used: bool


@dataclass(frozen=True, slots=True)
class LatentReadout:
    positive_projection: float
    negative_projection: float
    label: Label
    probabilities: tuple[float, float, float]
