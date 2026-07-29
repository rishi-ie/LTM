"""Explicit device selection and deterministic-process helpers."""

import random
from typing import Literal

import numpy as np
import torch

ResolvedDevice = Literal["cpu", "mps"]


def mps_available() -> bool:
    mps_backend = getattr(torch.backends, "mps", None)
    return bool(mps_backend and mps_backend.is_available())


def resolve_device(requested: Literal["auto", "cpu", "mps"]) -> ResolvedDevice:
    if requested == "cpu":
        return "cpu"
    if requested == "mps" and not mps_available():
        raise RuntimeError("MPS was requested but is unavailable")
    return "mps" if requested == "mps" or mps_available() else "cpu"


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def device_report() -> dict[str, str | bool]:
    """Return JSON-safe capability information without loading a model."""
    return {
        "torch_version": torch.__version__,
        "mps_available": mps_available(),
        "auto_device": resolve_device("auto"),
        "field_device": "cpu",
        "field_dtype": "float64",
    }
