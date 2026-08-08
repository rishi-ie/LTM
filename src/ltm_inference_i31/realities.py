"""Signed, isolated mathematical-reality primitives.

These profiles define local truth conditions.  They are deliberately separate
from the learned field: a scorer can retrieve only bodies carrying the active
reality key, and exact finite operators are checked here.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MathRealityManifest:
    reality_key: str
    revision: str
    operation_name: str | None
    finite_table: tuple[tuple[int, int, int], ...]
    manifest_hash: str


def finite_reality(reality_key: str, operation_name: str, rows: tuple[tuple[int, int, int], ...], revision: str = "1") -> MathRealityManifest:
    canonical = tuple(sorted(rows))
    digest = hashlib.sha256(repr((reality_key, revision, operation_name, canonical)).encode()).hexdigest()
    return MathRealityManifest(reality_key, revision, operation_name, canonical, digest)


def apply_finite_operator(manifest: MathRealityManifest, left: int, right: int) -> int | None:
    for first, second, output in manifest.finite_table:
        if (first, second) == (left, right):
            return output
    return None


STANDARD = finite_reality("standard-v1", "add", ((1, 1, 2),))
COUNTERFACTUAL_SUM3 = finite_reality("sum3-v1", "oplus", ((1, 1, 3),))
