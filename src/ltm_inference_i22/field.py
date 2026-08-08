"""Global content-addressed minimap over frozen learned source states."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import torch

from ltm_inference_i21.field import AlignedField


@dataclass(frozen=True, slots=True)
class TreeCell:
    cell_id: str
    axis: int | None
    threshold: float | None
    left_id: str | None
    right_id: str | None
    body_ids: tuple[str, ...]
    cell_hash: str


class GlobalTreeField(AlignedField):
    """A vector-routed hierarchy; identity is intentionally unavailable to `frontier`."""

    def __init__(self, *args: object, leaf_limit: int = 64, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.leaf_limit = leaf_limit
        # Direct identity maps are not part of this experiment's runtime field.
        del self.by_source_identity
        del self.by_entity
        self.tree: dict[str, TreeCell] = {}
        self.root_id: str | None = None
        self.leaf_by_body: dict[str, str] = {}

    def refresh(self, model: torch.nn.Module) -> None:
        super().refresh(model)
        self.tree = {}
        self.leaf_by_body = {}
        body_ids = tuple(sorted(self.bodies))
        self.root_id = self._build(tuple(range(len(body_ids))), body_ids, "root")

    def _build(self, rows: tuple[int, ...], body_ids: tuple[str, ...], label: str) -> str:
        selected = tuple(body_ids[index] for index in rows)
        cell_id = f"tree:{label}"
        if len(rows) <= self.leaf_limit:
            cell = TreeCell(cell_id, None, None, None, None, selected, hashlib.sha256(repr((cell_id, selected)).encode()).hexdigest())
            self.tree[cell_id] = cell
            self.leaf_by_body.update({body_id: cell_id for body_id in selected})
            return cell_id
        values = np.asarray([self.source_state[body_ids[index]] for index in rows], dtype=np.float32)
        axis = int(np.argmax(np.var(values, axis=0)))
        ordered = tuple(sorted(rows, key=lambda index: (float(self.source_state[body_ids[index]][axis]), body_ids[index])))
        midpoint = len(ordered) // 2
        left_rows, right_rows = ordered[:midpoint], ordered[midpoint:]
        threshold = (float(self.source_state[body_ids[left_rows[-1]]][axis]) + float(self.source_state[body_ids[right_rows[0]]][axis])) / 2.0
        left_id = self._build(left_rows, body_ids, f"{label}:0")
        right_id = self._build(right_rows, body_ids, f"{label}:1")
        self.tree[cell_id] = TreeCell(cell_id, axis, threshold, left_id, right_id, (), hashlib.sha256(repr((cell_id, axis, threshold, left_id, right_id)).encode()).hexdigest())
        return cell_id

    def leaf_for(self, state: np.ndarray) -> str:
        if not self.root_id:
            raise RuntimeError("tree not refreshed")
        cell = self.tree[self.root_id]
        while cell.axis is not None:
            child_id = cell.left_id if float(state[cell.axis]) <= float(cell.threshold) else cell.right_id
            cell = self.tree[str(child_id)]
        return cell.cell_id

    def frontier(self, state: np.ndarray, entity: str, scope_key: str, maximum_bodies: int, identity_key: str | None = None) -> tuple[str, ...]:
        del entity, identity_key
        leaf = self.tree[self.leaf_for(state)]
        allowed = [body_id for body_id in leaf.body_ids if self.bodies[body_id].scope_key == scope_key]
        return tuple(sorted(allowed, key=lambda body_id: (-float(np.dot(state, self.source_state[body_id])), body_id))[:maximum_bodies])

    def tree_membership_ok(self) -> bool:
        leaves = [cell for cell in self.tree.values() if cell.axis is None]
        return len(self.leaf_by_body) == len(self.bodies) and sorted(body_id for cell in leaves for body_id in cell.body_ids) == sorted(self.bodies)
