"""Bounded body indexes and hierarchical minimap summaries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .schemas import AtomicMumbrane, MinimapCell, ReasoningBody
from .vectors import state_projection


def _hash(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


class FieldIndex:
    def __init__(self, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], vectors: np.ndarray, cells: tuple[MinimapCell, ...], summary_vectors: np.ndarray) -> None:
        self.bodies = {body.body_id: body for body in bodies}
        self.units = {unit.unit_id: unit for unit in units}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.cells = {cell.cell_id: cell for cell in cells}
        self.summary_vectors = np.asarray(summary_vectors, dtype=np.float32)
        self._by_body = {body.body_id: body.unit_ids for body in bodies}
        self._by_identity: dict[str, list[str]] = {}
        for unit in units:
            self._by_identity.setdefault(unit.identity_key, []).append(unit.body_id)
        self._body_input: dict[str, np.ndarray] = {}
        self._body_output: dict[str, np.ndarray] = {}
        for body in bodies:
            rows = self.body_units(body)
            inputs = [state_projection(self.vectors[item.semantic_vector_ref]) for item in rows if item.phase_index == 0]
            outputs = [state_projection(self.vectors[item.semantic_vector_ref]) for item in rows if item.phase_index == 1]
            self._body_input[body.body_id] = np.mean(inputs, axis=0)
            self._body_output[body.body_id] = np.mean(outputs, axis=0)

    def body_units(self, body: ReasoningBody) -> tuple[AtomicMumbrane, ...]:
        return tuple(self.units[item] for item in body.unit_ids)

    def body_for_identity(self, identity_key: str) -> tuple[ReasoningBody, ...]:
        return tuple(self.bodies[item] for item in self._by_identity.get(identity_key, ()))

    def _cell_score(self, cell: MinimapCell, position: np.ndarray) -> float:
        row = cell.semantic_prototype_refs[0]
        centroid = self.summary_vectors[row, :128]
        return float(np.dot(centroid, position) / (np.linalg.norm(centroid) * max(1e-8, np.linalg.norm(position))))

    def frontier(self, position: np.ndarray, maximum_bodies: int = 64) -> tuple[tuple[MinimapCell, ...], tuple[ReasoningBody, ...]]:
        roots = [cell for cell in self.cells.values() if cell.parent_id is None]
        selected_cells: list[MinimapCell] = []
        frontier = roots
        while frontier:
            ranked = sorted(frontier, key=lambda cell: (-self._cell_score(cell, position), cell.cell_id))[:4]
            selected_cells.extend(ranked)
            children = [self.cells[child] for cell in ranked for child in cell.child_ids]
            frontier = [child for child in children if child.child_ids]
            if not frontier:
                leaves = ranked
                break
        else:
            leaves = selected_cells[-4:]
        body_ids = [body_id for cell in leaves for body_id in cell.body_ids]
        body_ids = sorted(set(body_ids), key=lambda item: (-float(np.dot(self._body_input[item], position)), item))[:maximum_bodies]
        return tuple(selected_cells), tuple(self.bodies[item] for item in body_ids)

    def body_input(self, body_id: str) -> np.ndarray:
        return self._body_input[body_id]

    def body_output(self, body_id: str) -> np.ndarray:
        return self._body_output[body_id]


def build_cells(bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], vectors: np.ndarray, leaf_limit: int = 64, fanout: int = 16) -> tuple[tuple[MinimapCell, ...], np.ndarray]:
    by_id = {unit.unit_id: unit for unit in units}
    body_in: dict[str, np.ndarray] = {}
    body_out: dict[str, np.ndarray] = {}
    for body in bodies:
        rows = [by_id[item] for item in body.unit_ids]
        body_in[body.body_id] = np.mean([state_projection(vectors[item.semantic_vector_ref]) for item in rows if item.phase_index == 0], axis=0)
        body_out[body.body_id] = np.mean([state_projection(vectors[item.semantic_vector_ref]) for item in rows if item.phase_index == 1], axis=0)
    ordered = sorted(bodies, key=lambda body: (float(body_in[body.body_id][0]), body.body_id))
    cells: list[MinimapCell] = []
    summaries: list[np.ndarray] = []
    current: list[MinimapCell] = []
    for start in range(0, len(ordered), leaf_limit):
        group = ordered[start:start + leaf_limit]
        inp = np.mean([body_in[item.body_id] for item in group], axis=0)
        out = np.mean([body_out[item.body_id] for item in group], axis=0)
        delta = out - inp
        delta /= max(1e-8, float(np.linalg.norm(delta)))
        row = len(summaries); summaries.append(np.concatenate((inp, out, delta)).astype(np.float32))
        cell_id = f"cell:0:{len(current):06d}"
        cell = MinimapCell(cell_id, 0, None, (), tuple(item.body_id for item in group), (row,), (row,), 1, float(np.max(np.linalg.norm(np.asarray([body_in[item.body_id] for item in group]) - inp, axis=1))), 0.0, len(group), _hash((cell_id, tuple(item.body_id for item in group), row)))
        cells.append(cell); current.append(cell)
    level_cells = current
    level = 1
    while len(level_cells) > 1:
        parents: list[MinimapCell] = []
        for start in range(0, len(level_cells), fanout):
            group = level_cells[start:start + fanout]
            row = len(summaries)
            inp = np.mean([summaries[item.semantic_prototype_refs[0]][:128] for item in group], axis=0)
            out = np.mean([summaries[item.semantic_prototype_refs[0]][128:256] for item in group], axis=0)
            delta = np.mean([summaries[item.semantic_prototype_refs[0]][256:] for item in group], axis=0)
            delta /= max(1e-8, float(np.linalg.norm(delta)))
            summaries.append(np.concatenate((inp, out, delta)).astype(np.float32))
            cell_id = f"cell:{level}:{len(parents):06d}"
            child_ids = tuple(item.cell_id for item in group)
            body_ids = tuple(item for child in group for item in child.body_ids)
            parents.append(MinimapCell(cell_id, level, None, child_ids, body_ids, (row,), (row,), 1, 0.0, 0.0, len(body_ids), _hash((cell_id, child_ids))))
        parent_by_child = {child.cell_id: parent for parent in parents for child in level_cells if child.cell_id in parent.child_ids}
        for i, cell in enumerate(cells):
            parent = parent_by_child.get(cell.cell_id)
            if parent:
                cells[i] = MinimapCell(cell.cell_id, cell.level, parent.cell_id, cell.child_ids, cell.body_ids, cell.semantic_prototype_refs, cell.transition_basis_refs, cell.context_mask, cell.radius, cell.uncertainty, cell.member_count, cell.summary_hash)
        cells.extend(parents)
        level_cells = parents; level += 1
    return tuple(cells), np.asarray(summaries, dtype=np.float32)


def save_minimap(root: Path, cells: tuple[MinimapCell, ...], vectors: np.ndarray) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cells.json").write_text(json.dumps([asdict(cell) for cell in cells], sort_keys=True), encoding="utf-8")
    np.save(root / "summary_vectors.npy", vectors)


def load_minimap(root: Path) -> tuple[tuple[MinimapCell, ...], np.ndarray]:
    rows = json.loads((root / "cells.json").read_text(encoding="utf-8"))
    return tuple(MinimapCell(**row) for row in rows), np.load(root / "summary_vectors.npy")
