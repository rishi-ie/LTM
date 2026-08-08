"""Deterministic vector utilities used by tests, fixtures and atom banks."""

from __future__ import annotations

import hashlib
import math


def normalized_hash_vector(text: str, dimension: int = 384) -> tuple[float, ...]:
    """Create a deterministic unit vector without treating it as model output."""
    values = []
    counter = 0
    while len(values) < dimension:
        digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        values.extend((byte - 127.5) / 127.5 for byte in digest)
        counter += 1
    values = values[:dimension]
    norm = math.sqrt(sum(value * value for value in values))
    return tuple(value / norm for value in values)
