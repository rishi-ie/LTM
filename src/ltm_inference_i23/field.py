"""Public-field index and learned-summary minimap for I2.3."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import torch

from .schemas import AtomicMumbrane, ReasoningBody


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    child_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    summary: tuple[float, ...]
    uncertainty: float
    member_count: int
    summary_hash: str


class PublicField:
    """A bounded public field. It has no evaluator-gold reference or loader."""

    def __init__(self, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], vectors: np.ndarray, *, leaf_limit: int = 64, fanout: int = 8) -> None:
        self.bodies = {body.body_id: body for body in bodies}
        self.units = {unit.unit_id: unit for unit in units}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.leaf_limit = leaf_limit
        self.fanout = fanout
        self.source_units = {body.body_id: next(self.units[unit_id] for unit_id in body.unit_ids if self.units[unit_id].phase_index == 0) for body in bodies}
        self.outcome_units = {body.body_id: next(self.units[unit_id] for unit_id in body.unit_ids if self.units[unit_id].phase_index == 1) for body in bodies}
        self.source_state: dict[str, np.ndarray] = {}
        self.outcome_state: dict[str, np.ndarray] = {}
        self.cells: dict[str, MinimapCell] = {}
        self.root_id: str | None = None

    @staticmethod
    def _normalise(value: np.ndarray) -> np.ndarray:
        return value / max(float(np.linalg.norm(value)), 1e-8)

    def refresh(self, model: torch.nn.Module) -> None:
        body_ids = tuple(sorted(self.bodies))
        source = np.asarray([self.vectors[self.source_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
        outcome = np.asarray([self.vectors[self.outcome_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
        with torch.no_grad():
            source_state = model.project(torch.from_numpy(source)).numpy()
            outcome_state = model.project(torch.from_numpy(outcome)).numpy()
        self.source_state = {body_id: source_state[index] for index, body_id in enumerate(body_ids)}
        self.outcome_state = {body_id: outcome_state[index] for index, body_id in enumerate(body_ids)}
        self.cells = {}
        self.root_id = self._build(model, body_ids, "root")

    def _summary(self, body_ids: tuple[str, ...]) -> np.ndarray:
        """A learned-coordinate centroid; it is the only child-routing signal."""
        return self._normalise(np.mean([self.source_state[item] for item in body_ids], axis=0))

    def _clusters(self, body_ids: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
        """Deterministic cosine k-means over learned states, with no ID route."""
        count = min(self.fanout, max(2, (len(body_ids) + self.leaf_limit - 1) // self.leaf_limit))
        points = np.asarray([self.source_state[item] for item in body_ids], dtype=np.float32)
        chosen = [0]
        for _ in range(1, count):
            similarity = points @ points[np.asarray(chosen)].T
            chosen.append(int(np.argmin(np.max(similarity, axis=1))))
        centroids = points[np.asarray(chosen)].copy()
        # Continue Lloyd updates to a stable assignment.  Child routing uses the
        # recomputed group centroids below, so stopping midway would make an
        # item's own learned state select a different child than the one that
        # contains it.  That is a minimap integrity error, not an inference
        # signal.
        previous_labels: np.ndarray | None = None
        for _ in range(32):
            labels = np.argmax(points @ centroids.T, axis=1)
            revised = []
            for index in range(count):
                selected = points[labels == index]
                revised.append(self._normalise(selected.mean(axis=0)) if len(selected) else centroids[index])
            centroids = np.asarray(revised, dtype=np.float32)
            updated_labels = np.argmax(points @ centroids.T, axis=1)
            if previous_labels is not None and np.array_equal(updated_labels, previous_labels):
                labels = updated_labels
                break
            previous_labels = updated_labels
            labels = updated_labels
        groups = tuple(tuple(body_ids[index] for index in np.flatnonzero(labels == group)) for group in range(count))
        nonempty = tuple(group for group in groups if group)
        if len(nonempty) <= 1:
            midpoint = len(body_ids) // 2
            return (body_ids[:midpoint], body_ids[midpoint:])
        return tuple(sorted(nonempty, key=lambda group: group[0]))

    def _build(self, model: torch.nn.Module, body_ids: tuple[str, ...], label: str) -> str:
        summary = self._summary(body_ids)
        cell_id = f"cell:{label}"
        if len(body_ids) <= self.leaf_limit:
            uncertainty = float(np.mean([1.0 - np.dot(summary, self.source_state[item]) for item in body_ids]))
            row = MinimapCell(cell_id, (), body_ids, tuple(float(item) for item in summary), uncertainty, len(body_ids), hashlib.sha256(repr((cell_id, body_ids, tuple(summary))).encode()).hexdigest())
            self.cells[cell_id] = row
            return cell_id
        groups = self._clusters(body_ids)
        child_ids = tuple(self._build(model, group, f"{label}:{index}") for index, group in enumerate(groups))
        uncertainty = float(np.mean([self.cells[child].uncertainty for child in child_ids]))
        self.cells[cell_id] = MinimapCell(cell_id, child_ids, (), tuple(float(item) for item in summary), uncertainty, len(body_ids), hashlib.sha256(repr((cell_id, child_ids, tuple(summary))).encode()).hexdigest())
        return cell_id

    def prompt_state(self, unit_ids: tuple[str, ...], model: torch.nn.Module) -> np.ndarray:
        values = np.asarray([self.vectors[self.units[item].semantic_vector_ref] for item in unit_ids], dtype=np.float32)
        with torch.no_grad():
            return model.project(torch.from_numpy(values.mean(axis=0, keepdims=True))).numpy()[0]

    def frontier_with_margin(self, state: np.ndarray, scope_key: str, maximum_bodies: int) -> tuple[tuple[str, ...], tuple[str, ...], float]:
        if not self.root_id:
            raise RuntimeError("field must be refreshed")
        active = [self.cells[self.root_id]]
        opened = [self.root_id]
        current = active[0]
        minimum_margin = 1.0
        while current.child_ids:
            scored = sorted(
                (
                    (float(np.dot(state, np.asarray(self.cells[item].summary, dtype=np.float32))), self.cells[item])
                    for item in current.child_ids
                ),
                key=lambda pair: (-pair[0], pair[1].cell_id),
            )
            minimum_margin = min(minimum_margin, scored[0][0] - scored[1][0] if len(scored) > 1 else 1.0)
            current = scored[0][1]
            opened.append(current.cell_id)
        ranked = tuple(sorted((item for item in current.body_ids if self.bodies[item].scope_key == scope_key), key=lambda item: (-float(np.dot(state, self.source_state[item])), item))[:maximum_bodies])
        return ranked, tuple(opened), minimum_margin

    def frontier(self, state: np.ndarray, scope_key: str, maximum_bodies: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
        ranked, opened, _ = self.frontier_with_margin(state, scope_key, maximum_bodies)
        return ranked, opened

    def membership_ok(self) -> bool:
        leaves = [cell for cell in self.cells.values() if not cell.child_ids]
        return sorted(item for cell in leaves for item in cell.body_ids) == sorted(self.bodies)
