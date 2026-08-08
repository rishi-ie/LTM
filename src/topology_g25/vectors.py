"""Deterministic fixture vectors; model outputs replace these at runtime."""

from __future__ import annotations

import hashlib
import math


def unit_hash_vector(text: str, dimension: int) -> tuple[float, ...]:
    values: list[float] = []
    counter = 0
    while len(values) < dimension:
        block = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        values.extend((byte - 127.5) / 127.5 for byte in block)
        counter += 1
    values = values[:dimension]
    norm = math.sqrt(sum(value * value for value in values))
    return tuple(value / norm for value in values)
