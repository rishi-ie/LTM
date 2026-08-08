"""Bounded persistent atom identity resolution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from topology_field_ir import GoldenAtom

from .schemas import IdentityDecision


@dataclass(frozen=True, slots=True)
class BankAtom:
    object_id: str
    canonical_text: str
    kind: str
    scope_id: str
    session_id: str | None
    vector: tuple[float, ...]


class BoundedAtomBank:
    def __init__(self, atoms: tuple[BankAtom, ...]) -> None:
        self._atoms = atoms
        self._buckets: dict[int, tuple[BankAtom, ...]] = {}
        buckets: dict[int, list[BankAtom]] = {}
        for atom in atoms:
            bucket = hashlib.sha256(atom.object_id.encode()).digest()[0]
            buckets.setdefault(bucket, []).append(atom)
        self._buckets = {key: tuple(sorted(value, key=lambda item: item.object_id)) for key, value in buckets.items()}

    def resolve(self, occurrence: GoldenAtom, *, session_id: str | None, margin: float = 0.05) -> IdentityDecision:
        bucket = hashlib.sha256(occurrence.canonical_text.casefold().encode()).digest()[0]
        candidates = [item for item in self._buckets.get(bucket, ()) if item.kind == occurrence.kind and item.scope_id == occurrence.context.scope_id and item.session_id == session_id][:32]
        if not candidates:
            return IdentityDecision(occurrence.atom_id, "new", (), 1.0, 1.0, min(32, len(self._buckets.get(bucket, ()))))
        scores = [sum(a * b for a, b in zip(item.vector, tuple(occurrence.context.priority for _ in item.vector))) for item in candidates]
        order = sorted(range(len(candidates)), key=lambda index: (-scores[index], candidates[index].object_id))
        best = order[0]
        gap = scores[best] - scores[order[1]] if len(order) > 1 else 1.0
        if len(order) > 1 and gap < margin:
            return IdentityDecision(occurrence.atom_id, "ambiguous", tuple(candidates[index].object_id for index in order[:2]), scores[best], gap, len(candidates))
        return IdentityDecision(occurrence.atom_id, "existing", (candidates[best].object_id,), max(0.0, min(1.0, scores[best])), gap, len(candidates))
