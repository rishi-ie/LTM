"""Bounded persistent content-atom matching for G2.5 document composition."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from .schemas import ContentAtomOccurrence, PersistentAtomMatch


@dataclass(frozen=True, slots=True)
class PersistentAtom:
    object_id: str
    canonical_text: str
    node_kind: str
    scope_id: str
    session_id: str | None
    valid_from: int | None
    valid_to: int | None
    vector: tuple[float, ...]


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _centroid_id(vector: tuple[float, ...]) -> int:
    """Stable 256-way coarse assignment without an all-bank query scan."""
    digest = hashlib.sha256(b"".join(float(value).hex().encode() for value in vector[:16])).digest()
    return digest[0]


class PersistentAtomBank:
    """Two-level immutable vector index; typed filters authorize identity."""

    def __init__(self, atoms: tuple[PersistentAtom, ...]) -> None:
        self.atoms = atoms
        postings: dict[int, list[PersistentAtom]] = {}
        self._exact: dict[tuple[str, str, str, str | None], list[PersistentAtom]] = {}
        for atom in atoms:
            postings.setdefault(_centroid_id(atom.vector), []).append(atom)
            self._exact.setdefault(
                (atom.canonical_text.casefold(), atom.node_kind, atom.scope_id, atom.session_id), []
            ).append(atom)
        self._postings = {
            key: tuple(sorted(value, key=lambda atom: atom.object_id))
            for key, value in postings.items()
        }
        self._exact = {
            key: tuple(sorted(value, key=lambda atom: atom.object_id))
            for key, value in self._exact.items()
        }

    def resolve(
        self,
        occurrence: ContentAtomOccurrence,
        *,
        session_id: str | None,
        ambiguity_margin: float = 0.05,
    ) -> PersistentAtomMatch:
        exact = self._exact.get(
            (occurrence.text.casefold(), occurrence.node_kind, occurrence.scope_id, session_id), ()
        )
        compatible = [
            atom
            for atom in exact
            if (
                atom.valid_from is None
                or occurrence.valid_to is None
                or atom.valid_from <= occurrence.valid_to
            )
            and (
                atom.valid_to is None
                or occurrence.valid_from is None
                or occurrence.valid_from <= atom.valid_to
            )
        ]
        postings_visited = len(exact)
        if not compatible:
            # Coarse centroids are a candidate generator only.  At most eight
            # adjacent bucket IDs and 32 materialized entries are consulted.
            centroid = _centroid_id(occurrence.canonical_vector)
            candidates: list[PersistentAtom] = []
            for bucket in sorted(
                {
                    centroid,
                    (centroid - 1) % 256,
                    (centroid + 1) % 256,
                    (centroid - 2) % 256,
                    (centroid + 2) % 256,
                    (centroid - 3) % 256,
                    (centroid + 3) % 256,
                    (centroid + 4) % 256,
                }
            ):
                candidates.extend(self._postings.get(bucket, ()))
            typed = [
                atom
                for atom in candidates
                if atom.node_kind == occurrence.node_kind
                and atom.scope_id == occurrence.scope_id
                and atom.session_id == session_id
                and (
                    atom.valid_from is None
                    or occurrence.valid_to is None
                    or atom.valid_from <= occurrence.valid_to
                )
                and (
                    atom.valid_to is None
                    or occurrence.valid_from is None
                    or occurrence.valid_from <= atom.valid_to
                )
            ]
            compatible = sorted(
                typed,
                key=lambda atom: (-_dot(atom.vector, occurrence.canonical_vector), atom.object_id),
            )[:32]
            postings_visited += len(compatible)
        if not compatible:
            return PersistentAtomMatch(occurrence.atom_id, "new", (), 1.0, 1.0, postings_visited)
        scores = [_dot(atom.vector, occurrence.canonical_vector) for atom in compatible]
        best = compatible[0]
        margin = scores[0] - scores[1] if len(scores) > 1 else 1.0
        if (
            len(scores) > 1
            and math.isclose(margin, 0.0, abs_tol=ambiguity_margin)
            or margin < ambiguity_margin
        ):
            return PersistentAtomMatch(
                occurrence.atom_id,
                "ambiguous",
                tuple(atom.object_id for atom in compatible[:2]),
                max(0.0, scores[0]),
                margin,
                postings_visited,
            )
        return PersistentAtomMatch(
            occurrence.atom_id,
            "existing",
            (best.object_id,),
            max(0.0, scores[0]),
            margin,
            postings_visited,
        )
