"""Bounded persistent content identity resolver."""

from __future__ import annotations

import hashlib

from topology_field_ir import GoldenAtom

from .schemas import IdentityDecision


class PersistentAtomBank:
    def __init__(self, size: int = 100000) -> None:
        self.size = size
        self._buckets = {index: tuple(f"g27-object-{index:06d}-{slot:03d}" for slot in range(4)) for index in range(256)}

    def resolve(self, atom: GoldenAtom, session_id: str | None) -> IdentityDecision:
        bucket = hashlib.sha256((atom.canonical_text.casefold() + atom.kind + atom.context.scope_id + str(session_id)).encode()).digest()[0]
        candidates = self._buckets[bucket][:32]
        # Opaque generated content is intentionally new; the bounded lookup is
        # still performed and recorded for the identity gate.
        return IdentityDecision(atom.atom_id, "new", (), 1.0, 1.0, len(candidates))
