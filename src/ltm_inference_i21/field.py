"""Aligned body state index and deterministic hierarchical minimap."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from .dataset import load_jsonl
from .schemas import AtomicMumbrane, ReasoningBody


def _entity(identity_key: str) -> str:
    return identity_key.split("|", 1)[0]


@dataclass(frozen=True, slots=True)
class MinimapCell:
    cell_id: str
    level: int
    parent_id: str | None
    child_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    member_count: int
    summary_hash: str


class AlignedField:
    def __init__(self, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], vectors: np.ndarray) -> None:
        self.bodies = {body.body_id: body for body in bodies}
        self.units = {unit.unit_id: unit for unit in units}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.body_source_units = {body.body_id: next(self.units[item] for item in body.unit_ids if self.units[item].phase_index == 0) for body in bodies}
        self.body_outcome_units = {body.body_id: next(self.units[item] for item in body.unit_ids if self.units[item].phase_index == 1) for body in bodies}
        self.by_source_identity: dict[str, tuple[str, ...]] = {}
        source_rows: dict[str, list[str]] = {}
        for body_id, source in self.body_source_units.items():
            source_rows.setdefault(source.identity_key, []).append(body_id)
        self.by_source_identity = {key: tuple(sorted(value)) for key, value in source_rows.items()}
        self.by_entity: dict[str, tuple[str, ...]] = {}
        for body_id, source in self.body_source_units.items():
            self.by_entity.setdefault(_entity(source.identity_key), []).append(body_id)  # type: ignore[arg-type]
        self.by_entity = {key: tuple(sorted(value)) for key, value in self.by_entity.items()}
        self.cells = self._build_cells()
        self.source_state: dict[str, np.ndarray] = {}
        self.outcome_state: dict[str, np.ndarray] = {}
        self.transition_state: dict[str, np.ndarray] = {}

    def _build_cells(self) -> tuple[MinimapCell, ...]:
        leaves: list[MinimapCell] = []
        for index, (entity, body_ids) in enumerate(sorted(self.by_entity.items())):
            cell_id = f"leaf:{index:06d}"
            leaves.append(MinimapCell(cell_id, 0, None, (), body_ids, len(body_ids), hashlib.sha256(repr((entity, body_ids)).encode()).hexdigest()))
        cells: list[MinimapCell] = list(leaves)
        level = leaves
        level_number = 1
        while len(level) > 1:
            parents: list[MinimapCell] = []
            for index in range(0, len(level), 16):
                children = level[index:index + 16]
                cell_id = f"cell:{level_number}:{index // 16:06d}"
                body_ids = tuple(body_id for child in children for body_id in child.body_ids)
                parents.append(MinimapCell(cell_id, level_number, None, tuple(child.cell_id for child in children), body_ids, len(body_ids), hashlib.sha256(repr((cell_id, tuple(child.cell_id for child in children))).encode()).hexdigest()))
            parent_of = {child_id: parent.cell_id for parent in parents for child_id in parent.child_ids}
            for position, cell in enumerate(cells):
                if cell.cell_id in parent_of:
                    cells[position] = MinimapCell(cell.cell_id, cell.level, parent_of[cell.cell_id], cell.child_ids, cell.body_ids, cell.member_count, cell.summary_hash)
            cells.extend(parents)
            level = parents
            level_number += 1
        return tuple(cells)

    def refresh(self, model: torch.nn.Module) -> None:
        """Project every runtime comparison through the one learned transform."""
        body_ids = tuple(sorted(self.bodies))
        source = np.asarray([self.vectors[self.body_source_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
        outcome = np.asarray([self.vectors[self.body_outcome_units[item].semantic_vector_ref] for item in body_ids], dtype=np.float32)
        with torch.no_grad():
            source_state = model.project(torch.from_numpy(source)).numpy()
            outcome_state = model.project(torch.from_numpy(outcome)).numpy()
        self.source_state = {body_id: source_state[index] for index, body_id in enumerate(body_ids)}
        self.outcome_state = {body_id: outcome_state[index] for index, body_id in enumerate(body_ids)}
        self.transition_state = {body_id: self._normalize(self.outcome_state[body_id] - self.source_state[body_id]) for body_id in body_ids}

    @staticmethod
    def _normalize(value: np.ndarray) -> np.ndarray:
        return value / max(1e-8, float(np.linalg.norm(value)))

    def prompt_state(self, unit_ids: tuple[str, ...], model: torch.nn.Module) -> tuple[np.ndarray, str]:
        values = np.asarray([self.vectors[self.units[item].semantic_vector_ref] for item in unit_ids], dtype=np.float32)
        with torch.no_grad():
            state = model.project(torch.from_numpy(np.mean(values, axis=0, keepdims=True))).numpy()[0]
        return state, _entity(self.units[unit_ids[0]].identity_key)

    def frontier(self, state: np.ndarray, entity: str, scope_key: str, maximum_bodies: int, identity_key: str | None = None) -> tuple[str, ...]:
        """Open an identity-addressed minimap leaf and rank its transitions in learned space."""
        candidate_rows = self.by_source_identity.get(identity_key, ()) if identity_key else self.by_entity.get(entity, ())
        allowed = [body_id for body_id in candidate_rows if self.bodies[body_id].scope_key == scope_key]
        ranked = sorted(allowed, key=lambda body_id: (-float(np.dot(state, self.source_state[body_id])), body_id))
        return tuple(ranked[:maximum_bodies])

    def membership_ok(self) -> bool:
        leaves = [cell for cell in self.cells if cell.level == 0]
        return sorted(body_id for cell in leaves for body_id in cell.body_ids) == sorted(self.bodies)

    def save_minimap(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "cells.json").write_text(json.dumps([asdict(cell) for cell in self.cells], sort_keys=True), encoding="utf-8")


def load_field(workspace: Path, split: str) -> tuple[AlignedField, tuple[dict[str, object], ...]]:
    root = workspace / "datasets" / split
    bodies = tuple(ReasoningBody(**row) for row in load_jsonl(root / "bodies.jsonl"))
    units = tuple(AtomicMumbrane(**row) for row in load_jsonl(root / "units.jsonl"))
    return AlignedField(bodies, units, np.load(root / "vectors.npy")), load_jsonl(root / "public.jsonl")


def gold(workspace: Path, split: str) -> dict[str, dict[str, object]]:
    return {str(row["prompt_id"]): row for row in load_jsonl(workspace / "datasets" / split / "gold.jsonl")}
