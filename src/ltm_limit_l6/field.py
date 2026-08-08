"""Query-independent L6 minimap and bounded frontier. No exact consumer map."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from .schemas import MathematicalRealityBody


def _unit(value: np.ndarray) -> np.ndarray:
    value = np.asarray(value, dtype=np.float32)
    norm = float(np.linalg.norm(value))
    return value / norm if norm else np.zeros_like(value)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(_unit(left), _unit(right)))


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    level: int
    parent_id: str | None
    child_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    prototype: tuple[float, ...]
    member_count: int
    radius: float
    context_keys: tuple[tuple[str, str], ...]
    summary_hash: str


class L6Field:
    """A field whose runtime retrieval is prototype/cell based only.

    Deliberately no semantic-key-to-consumer index exists here. Exact semantic
    matching belongs to the independent verifier, never to answer selection.
    """

    def __init__(self, bodies: tuple[MathematicalRealityBody, ...], vectors: np.ndarray, cells: dict[str, MinimapCell], roots: tuple[str, ...], body_vectors: dict[str, tuple[np.ndarray, np.ndarray]]) -> None:
        if vectors.ndim != 2 or vectors.shape[1] != 128:
            raise ValueError("L6 vectors must be [n,128]")
        self.bodies = {body.body_id: body for body in bodies}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.cells = cells
        self.roots = roots
        self.body_vectors = body_vectors
        self.access = {"cells": 0, "bodies": 0, "full_field_scans": 0}

    def _applicable(self, body: MathematicalRealityBody, reality: str, scope: str, valid_at: int | None) -> bool:
        if body.reality_key != reality or body.scope_key not in {scope, "global"}:
            return False
        return (valid_at is None or body.valid_from is None or body.valid_from <= valid_at) and (valid_at is None or body.valid_to is None or valid_at <= body.valid_to)

    def frontier(self, position: np.ndarray, reality: str, scope: str, valid_at: int | None, maximum_bodies: int = 128) -> tuple[tuple[MinimapCell, ...], tuple[MathematicalRealityBody, ...]]:
        if not 0 < maximum_bodies <= 128:
            raise ValueError("frontier exceeds L6 bound")
        candidates = [self.cells[cell_id] for cell_id in self.roots if any(key == (reality, scope) or key == (reality, "global") for key in self.cells[cell_id].context_keys)]
        self.access["cells"] += len(candidates)
        selected: list[MinimapCell] = []
        layer = candidates
        while layer:
            ranked = sorted(layer, key=lambda cell: (-_cosine(position, np.asarray(cell.prototype)), cell.cell_id))[:4]
            selected.extend(ranked)
            children = [self.cells[child] for cell in ranked for child in cell.child_ids]
            if not children:
                break
            self.access["cells"] += len(children)
            layer = children
        body_ids = {body_id for cell in selected if not cell.child_ids for body_id in cell.body_ids}
        rows = [self.bodies[body_id] for body_id in body_ids if self._applicable(self.bodies[body_id], reality, scope, valid_at)]
        rows.sort(key=lambda body: (-max(_cosine(position, vector) for vector in self.body_vectors[body.body_id]), body.body_id))
        self.access["bodies"] += min(maximum_bodies, len(rows))
        return tuple(selected), tuple(rows[:maximum_bodies])


def build_field(bodies: tuple[MathematicalRealityBody, ...], vectors: np.ndarray, *, leaf_limit: int = 64, fanout: int = 16) -> L6Field:
    if leaf_limit != 64 or fanout != 16:
        raise ValueError("L6 minimap limits are frozen at 64/16")
    if not bodies:
        raise ValueError("cannot build empty L6 field")
    body_vectors: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for body in bodies:
        input_vec = _unit(np.mean([vectors[index % len(vectors)] for index in range(body.transition_vector_ref, body.transition_vector_ref + len(body.input_expressions))], axis=0))
        output_vec = _unit(np.mean([vectors[(body.transition_vector_ref + len(body.input_expressions) + index) % len(vectors)] for index in range(len(body.outcome_expressions))], axis=0))
        body_vectors[body.body_id] = (input_vec, output_vec)
    cells: dict[str, MinimapCell] = {}
    leaves: list[str] = []
    ordered = sorted(bodies, key=lambda item: item.body_id)
    for offset in range(0, len(ordered), leaf_limit):
        rows = ordered[offset:offset + leaf_limit]
        proto = _unit(np.mean([body_vectors[row.body_id][0] for row in rows], axis=0))
        contexts = tuple(sorted({(row.reality_key, row.scope_key) for row in rows}))
        cell_id = f"l6:leaf:{offset // leaf_limit:06d}"
        payload = repr((cell_id, tuple(row.body_id for row in rows), tuple(contexts))).encode()
        cells[cell_id] = MinimapCell(cell_id, 0, None, (), tuple(row.body_id for row in rows), tuple(float(x) for x in proto), len(rows), 1.0, contexts, hashlib.sha256(payload).hexdigest())
        leaves.append(cell_id)
    level = leaves
    depth = 1
    while len(level) > 1:
        parents: list[str] = []
        for offset in range(0, len(level), fanout):
            child_ids = tuple(level[offset:offset + fanout])
            members = tuple(body_id for child in child_ids for body_id in cells[child].body_ids)
            proto = _unit(np.mean([np.asarray(cells[child].prototype) for child in child_ids], axis=0))
            contexts = tuple(sorted({key for child in child_ids for key in cells[child].context_keys}))
            cell_id = f"l6:level{depth}:{offset // fanout:06d}"
            cells[cell_id] = MinimapCell(cell_id, depth, None, child_ids, members, tuple(float(x) for x in proto), len(members), 1.0, contexts, hashlib.sha256(repr((cell_id, child_ids)).encode()).hexdigest())
            for child in child_ids:
                cells[child] = MinimapCell(cells[child].cell_id, cells[child].level, cell_id, cells[child].child_ids, cells[child].body_ids, cells[child].prototype, cells[child].member_count, cells[child].radius, cells[child].context_keys, cells[child].summary_hash)
            parents.append(cell_id)
        level = parents
        depth += 1
    return L6Field(bodies, vectors, cells, tuple(level), body_vectors)
