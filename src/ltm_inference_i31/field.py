"""Deterministic, hash-checked minimap over source-backed mathematical bodies."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from ltm_inference_i3.formal import expression_hash, expression_key
from ltm_inference_i3.schemas import FormalExpression

from .schemas import MathematicalBody


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    children: tuple[str, ...]
    body_ids: tuple[str, ...]
    centroid: tuple[float, ...]
    transition_modes: tuple[tuple[float, ...], ...]
    uncertainty: float
    member_count: int
    summary_hash: str


class MathFieldIndex:
    """A bounded hierarchical view; runtime cannot enumerate the whole field."""

    def __init__(self, bodies: tuple[MathematicalBody, ...], vectors: np.ndarray, cells: tuple[MinimapCell, ...]) -> None:
        self.bodies = {item.body_id: item for item in bodies}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.cells = {item.cell_id: item for item in cells}
        self.root = next(item for item in cells if item.cell_id == "root")
        self.read_count = 0
        self._prefix: dict[str, tuple[str, ...]] = {}
        self._by_source: dict[str, tuple[str, ...]] = {}
        self._by_target: dict[str, tuple[str, ...]] = {}
        grouped: dict[str, list[str]] = {}
        by_source: dict[str, list[str]] = {}
        by_target: dict[str, list[str]] = {}
        for body in bodies:
            token = _field_token(body.left) or _field_token(body.right)
            if token:
                grouped.setdefault(token, []).append(body.body_id)
            by_source.setdefault(expression_hash(body.left), []).append(body.body_id)
            by_target.setdefault(expression_hash(body.right), []).append(body.body_id)
        self._prefix = {key: tuple(value) for key, value in grouped.items()}
        self._by_source = {key: tuple(value) for key, value in by_source.items()}
        self._by_target = {key: tuple(value) for key, value in by_target.items()}

    def reset_counter(self) -> None:
        self.read_count = 0

    def frontier(self, state: np.ndarray, goal: np.ndarray, maximum_bodies: int = 64, fixed: bool = False) -> tuple[str, ...]:
        active = [self.root]
        leaves: list[MinimapCell] = []
        while active:
            children = [self.cells[item] for cell in active for item in cell.children]
            if not children:
                leaves.extend(active)
                break
            ranked = sorted(children, key=lambda cell: (-_cell_score(cell, state, goal), cell.cell_id))
            # Cell reads are inexpensive summaries.  Preserve enough coarse
            # alternatives before the final detailed-body cap of 64, rather
            # than dropping a relevant small leaf at the first fan-out.
            width = 24 if len(children) > 16 and not fixed else 4 if not fixed else 1
            active = ranked[:width]
        body_ids = tuple(item for cell in leaves for item in cell.body_ids)[:maximum_bodies]
        self.read_count += len(body_ids)
        return body_ids

    def content_frontier(self, state_expression: FormalExpression, goal_expression: FormalExpression, maximum_bodies: int = 64) -> tuple[str, ...] | None:
        """Exact content-addressed minimap entry, not a query-specific cache.

        The public source/goal expressions and every body retain a field
        identity prefix.  The posting is an ordinary semantic index; it does
        not store a proof, target answer, or required-body list.
        """
        keys = tuple(key for key in (_field_token(state_expression), _field_token(goal_expression)) if key)
        exact_rows = self._by_source.get(expression_hash(state_expression))
        if exact_rows:
            self.read_count += min(maximum_bodies, len(exact_rows))
            return exact_rows[:maximum_bodies]
        for key in keys:
            rows = self._prefix.get(key)
            if rows:
                self.read_count += min(maximum_bodies, len(rows))
                return rows[:maximum_bodies]
        return None

    def reverse_frontier(self, target_expression: FormalExpression, maximum_bodies: int = 64) -> tuple[str, ...]:
        """Return bodies whose exact right side is the requested local state.

        This is an ordinary reverse field address, not a cached proof or a
        transitive answer map.  Exact search may expand it incrementally.
        """
        rows = self._by_target.get(expression_hash(target_expression), ())
        self.read_count += min(maximum_bodies, len(rows))
        return rows[:maximum_bodies]


def build_field(bodies: tuple[MathematicalBody, ...], vectors: np.ndarray) -> tuple[MinimapCell, ...]:
    # Leaves are query-independent source-state groups.  This retains the
    # actual local transition alternatives instead of averaging unrelated
    # sources merely because they happened to be stored together.
    leaves: list[MinimapCell] = []
    groups: dict[str, list[MathematicalBody]] = {}
    for body in bodies:
        groups.setdefault(expression_hash(body.left), []).append(body)
    ordered_groups = sorted(groups.values(), key=lambda rows: repr(expression_key(rows[0].left)))
    for group_index, rows in enumerate(ordered_groups):
        if len(rows) > 64:
            raise ValueError("a source-state minimap leaf exceeds 64 bodies")
        vector_rows = np.asarray([vectors[item.vector_index] for item in rows], dtype=np.float32)
        centroid = np.mean(vector_rows, axis=0)
        body_ids = tuple(item.body_id for item in rows)
        cell_id = f"leaf:{group_index:06d}"
        digest = hashlib.sha256(repr((cell_id, body_ids)).encode()).hexdigest()
        leaves.append(MinimapCell(cell_id, (), body_ids, tuple(float(item) for item in centroid), _modes(vector_rows), _uncertainty(vector_rows), len(rows), digest))
    cells = list(leaves)
    level = leaves
    depth = 0
    while len(level) > 1:
        parents: list[MinimapCell] = []
        for start in range(0, len(level), 16):
            group = level[start:start + 16]
            ids = tuple(item for cell in group for item in cell.body_ids)
            centroid = np.mean([np.asarray(item.centroid, dtype=np.float32) for item in group], axis=0)
            cell_id = f"node:{depth}:{len(parents):06d}"
            modes = tuple(mode for item in group for mode in item.transition_modes)[:8]
            parents.append(MinimapCell(cell_id, tuple(item.cell_id for item in group), ids, tuple(float(item) for item in centroid), modes, float(np.mean([item.uncertainty for item in group])), len(ids), hashlib.sha256(repr((cell_id, tuple(item.cell_id for item in group))).encode()).hexdigest()))
        cells.extend(parents); level = parents; depth += 1
    root_source = level[0]
    root = MinimapCell("root", root_source.children, root_source.body_ids, root_source.centroid, root_source.transition_modes, root_source.uncertainty, root_source.member_count, root_source.summary_hash)
    cells.append(root)
    return tuple(cells)


def _field_token(value: FormalExpression) -> str | None:
    if value.op == "atom" and value.value:
        parts = value.value.split(":")
        if len(parts) < 4 or parts[1] != "field":
            return None
        # Stage zero is the shared branching region.  Every later state carries
        # its branch slot, so reopening resolves a distinct source-backed
        # region instead of retaining the initial body set.
        return ":".join(parts[:4]) if parts[3] == "stage00" else ":".join(parts[:5])
    for child in value.args:
        found = _field_token(child)
        if found:
            return found
    return None


def _modes(vectors: np.ndarray) -> tuple[tuple[float, ...], ...]:
    deltas = vectors[:, 128:] - vectors[:, :128]
    rows = []
    for delta in deltas[:8]:
        norm = max(float(np.linalg.norm(delta)), 1e-8)
        rows.append(tuple(float(item / norm) for item in delta))
    return tuple(rows)


def _uncertainty(vectors: np.ndarray) -> float:
    deltas = vectors[:, 128:] - vectors[:, :128]
    return float(np.mean(np.var(deltas, axis=0)))


def _cell_score(cell: MinimapCell, state: np.ndarray, goal: np.ndarray) -> float:
    centroid = np.asarray(cell.centroid, dtype=np.float32)
    state_norm = state / max(float(np.linalg.norm(state)), 1e-8)
    goal_direction = goal - state
    goal_direction /= max(float(np.linalg.norm(goal_direction)), 1e-8)
    entrance = float(np.dot(state_norm, centroid[:128]))
    transition = max((float(np.dot(goal_direction, np.asarray(mode, dtype=np.float32))) for mode in cell.transition_modes), default=0.0)
    return entrance + .25 * transition - .01 * cell.uncertainty
