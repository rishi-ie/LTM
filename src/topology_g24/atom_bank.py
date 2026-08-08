"""Deterministic coarse semantic index for stored content atoms."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .schemas import AtomMatch, GroundedAtom, MemoryAtom


def _applicable(atom: GroundedAtom, candidate: MemoryAtom, session_id: str | None) -> bool:
    if atom.node_kind != candidate.node_kind:
        return False
    if candidate.scope_id not in {"global", atom.scope_id}:
        return False
    if candidate.session_id is not None and candidate.session_id != session_id:
        return False
    if atom.valid_from is not None and candidate.valid_to is not None and candidate.valid_to < atom.valid_from:
        return False
    return not (
        atom.valid_to is not None
        and candidate.valid_from is not None
        and candidate.valid_from > atom.valid_to
    )


@dataclass(frozen=True, slots=True)
class AtomBankIndex:
    atoms: tuple[MemoryAtom, ...]
    centroids: np.ndarray
    assignments: tuple[int, ...]
    postings: tuple[tuple[int, ...], ...]
    index_hash: str

    def query(
        self,
        atom: GroundedAtom,
        *,
        session_id: str | None,
        centroid_count: int = 4,
        maximum: int = 32,
    ) -> tuple[tuple[MemoryAtom, float], ...]:
        vector = np.asarray(atom.semantic_vector, dtype=np.float32)
        centroid_scores = self.centroids @ vector
        selected = np.argsort(-centroid_scores, kind="stable")[: min(centroid_count, len(self.postings))]
        materialized = tuple(index for centroid in selected for index in self.postings[int(centroid)])
        scored = [
            (self.atoms[index], float(np.dot(vector, np.asarray(self.atoms[index].semantic_vector, dtype=np.float32))))
            for index in materialized
            if _applicable(atom, self.atoms[index], session_id)
        ]
        scored.sort(key=lambda item: (-item[1], item[0].object_id))
        return tuple(scored[:maximum])

    def resolve(self, atom: GroundedAtom, *, session_id: str | None) -> AtomMatch:
        candidates = self.query(atom, session_id=session_id)
        if not candidates or candidates[0][1] < 0.75:
            return AtomMatch(atom.local_id, (), "new", max(0.0, candidates[0][1] if candidates else 0.0), 1.0)
        best, best_score = candidates[0]
        next_score = candidates[1][1] if len(candidates) > 1 else -1.0
        margin = best_score - next_score
        if margin < 0.05:
            alternatives = tuple(item.object_id for item, score in candidates if best_score - score < 0.05)
            return AtomMatch(atom.local_id, alternatives, "ambiguous", best_score, margin)
        return AtomMatch(atom.local_id, (best.object_id,), "existing", best_score, margin)


def build_atom_bank(atoms: tuple[MemoryAtom, ...], clusters: int = 128, iterations: int = 6) -> AtomBankIndex:
    if not atoms:
        raise ValueError("atom bank cannot be empty")
    vectors = np.asarray([item.semantic_vector for item in atoms], dtype=np.float32)
    count = min(clusters, len(atoms))
    initial = np.linspace(0, len(atoms) - 1, num=count, dtype=np.int64)
    centroids = vectors[initial].copy()
    for _ in range(iterations):
        assignments = np.argmax(vectors @ centroids.T, axis=1)
        updated = centroids.copy()
        for index in range(count):
            members = vectors[assignments == index]
            if len(members):
                value = members.mean(axis=0)
                updated[index] = value / max(1e-12, float(np.linalg.norm(value)))
        if np.array_equal(updated, centroids):
            break
        centroids = updated
    assignments = np.argmax(vectors @ centroids.T, axis=1)
    postings = tuple(tuple(np.flatnonzero(assignments == index).tolist()) for index in range(count))
    from topology_g1.codec import digest

    index_hash = digest(
        {
            "atoms": tuple(item.object_id for item in atoms),
            "assignments": tuple(int(value) for value in assignments),
            "centroids": centroids.round(8).tolist(),
        }
    )
    return AtomBankIndex(atoms, centroids, tuple(int(value) for value in assignments), postings, index_hash)
