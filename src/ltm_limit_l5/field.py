"""Deterministic source-normalized field and hierarchical minimap for L5."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

from .schemas import EquilibriumBody, FieldMumbrane, MinimapCell

STATE_DIMENSION = 128


@dataclass(frozen=True, slots=True)
class FieldAccessAccounting:
    frontier_calls: int
    root_cell_reads: int
    minimap_cells_scored: int
    minimap_body_id_reads: int
    consumer_index_lookups: int
    body_records_read: int
    full_field_scans: int


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _unit(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    if value.shape != (STATE_DIMENSION,) or not np.isfinite(value).all():
        raise ValueError("field vectors must be finite 128D rows")
    norm = float(np.linalg.norm(value))
    return value / max(norm, 1e-8)


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right) / max(1e-8, float(np.linalg.norm(left) * np.linalg.norm(right))))


def _context_key(reality: str, scope: str) -> str:
    return f"{reality}\0{scope}"


def _scope_matches(body_scope: str, request_scope: str) -> bool:
    return body_scope == "global" or body_scope == request_scope


def _valid(valid_from: int | None, valid_to: int | None, valid_at: int | None) -> bool:
    if valid_at is None:
        return True
    return (valid_from is None or valid_from <= valid_at) and (valid_to is None or valid_at <= valid_to)


class EquilibriumFieldIndex:
    """Read-only indexed view over exact bodies, projected vectors, and minimap cells."""

    def __init__(
        self,
        bodies: tuple[EquilibriumBody, ...],
        units: tuple[FieldMumbrane, ...],
        vectors: np.ndarray,
        cells: tuple[MinimapCell, ...],
        summary_vectors: np.ndarray,
        *,
        source_mass_cap: float = 8.0,
    ) -> None:
        if source_mass_cap <= 0:
            raise ValueError("source mass cap must be positive")
        if len({body.body_id for body in bodies}) != len(bodies):
            raise ValueError("duplicate body id")
        if len({unit.unit_id for unit in units}) != len(units):
            raise ValueError("duplicate unit id")
        self.bodies = {body.body_id: body for body in bodies}
        self.units = {unit.unit_id: unit for unit in units}
        self.vectors = np.asarray(vectors, dtype=np.float32)
        if self.vectors.ndim != 2 or self.vectors.shape[1] != STATE_DIMENSION or not np.isfinite(self.vectors).all():
            raise ValueError("invalid field vector table")
        self.cells = {cell.cell_id: cell for cell in cells}
        self.summary_vectors = np.asarray(summary_vectors, dtype=np.float32)
        if self.summary_vectors.ndim != 2 or self.summary_vectors.shape[1] != STATE_DIMENSION * 3 or not np.isfinite(self.summary_vectors).all():
            raise ValueError("invalid minimap vector table")
        self.source_mass_cap = float(source_mass_cap)
        self._body_units: dict[str, tuple[FieldMumbrane, ...]] = {}
        self._inputs: dict[str, tuple[FieldMumbrane, ...]] = {}
        self._outcomes: dict[str, tuple[FieldMumbrane, ...]] = {}
        self._input_vectors: dict[str, np.ndarray] = {}
        self._outcome_vectors: dict[str, np.ndarray] = {}
        self._signatures: dict[str, tuple[object, ...]] = {}
        for body in bodies:
            expected = body.input_unit_ids + body.outcome_unit_ids
            if len(set(expected)) != len(expected) or any(item not in self.units for item in expected):
                raise ValueError(f"invalid units for body {body.body_id}")
            rows = tuple(self.units[item] for item in expected)
            inputs = tuple(self.units[item] for item in body.input_unit_ids)
            outcomes = tuple(self.units[item] for item in body.outcome_unit_ids)
            # A composed body may consume a prior body's outcome occurrence.
            if any(item.phase_index != 1 or item.body_id != body.body_id for item in outcomes):
                raise ValueError(f"phase mismatch in {body.body_id}")
            if any(item.semantic_vector_ref >= len(self.vectors) for item in rows):
                raise ValueError(f"vector reference outside table in {body.body_id}")
            if len({item.polarity for item in outcomes}) != 1:
                raise ValueError(f"mixed outcome polarity in {body.body_id}")
            self._body_units[body.body_id] = rows
            self._inputs[body.body_id] = inputs
            self._outcomes[body.body_id] = outcomes
            self._input_vectors[body.body_id] = _unit(np.mean([self.vectors[item.semantic_vector_ref] for item in inputs], axis=0))
            self._outcome_vectors[body.body_id] = _unit(np.mean([self.vectors[item.semantic_vector_ref] for item in outcomes], axis=0))
            self._signatures[body.body_id] = (
                tuple(sorted((item.semantic_key, item.polarity) for item in inputs)),
                tuple(sorted((item.semantic_key, item.polarity) for item in outcomes)),
                body.scope_key,
                body.reality_key,
                body.valid_from,
                body.valid_to,
            )
        duplicate_groups: dict[tuple[int, str, tuple[object, ...]], list[EquilibriumBody]] = {}
        for body in bodies:
            key = (self.body_polarity(body), body.independent_source_key, self._signatures[body.body_id])
            duplicate_groups.setdefault(key, []).append(body)
        self._canonical_body_ids = frozenset(
            min(
                group,
                key=lambda body: (-body.base_weight * body.authority * body.confidence, body.body_id),
            ).body_id
            for group in duplicate_groups.values()
        )
        if any(ref >= len(self.summary_vectors) for cell in cells for ref in cell.prototype_refs + cell.transition_refs):
            raise ValueError("minimap reference outside table")
        if len(self.cells) != len(cells):
            raise ValueError("duplicate minimap cell id")
        self._root_cell_ids = tuple(sorted(cell.cell_id for cell in cells if cell.parent_id is None))
        if not self._root_cell_ids:
            raise ValueError("minimap has no root")
        self._cell_input_keys = {
            cell.cell_id: frozenset(
                item.semantic_key
                for body_id in cell.body_ids
                for item in self._inputs[body_id]
            )
            for cell in cells
        }
        consumers: dict[str, set[str]] = {}
        for body in bodies:
            for item in self._inputs[body.body_id]:
                consumers.setdefault(item.semantic_key, set()).add(body.body_id)
        self._consumer_body_ids = {
            key: frozenset(values) for key, values in consumers.items()
        }
        self._access = {
            "frontier_calls": 0,
            "root_cell_reads": 0,
            "minimap_cells_scored": 0,
            "minimap_body_id_reads": 0,
            "consumer_index_lookups": 0,
            "body_records_read": 0,
            "full_field_scans": 0,
        }

    def access_accounting(self) -> FieldAccessAccounting:
        return FieldAccessAccounting(**self._access)

    def body_units(self, body: EquilibriumBody | str) -> tuple[FieldMumbrane, ...]:
        return self._body_units[body if isinstance(body, str) else body.body_id]

    def body_inputs(self, body: EquilibriumBody | str) -> tuple[FieldMumbrane, ...]:
        return self._inputs[body if isinstance(body, str) else body.body_id]

    def body_outcomes(self, body: EquilibriumBody | str) -> tuple[FieldMumbrane, ...]:
        return self._outcomes[body if isinstance(body, str) else body.body_id]

    def body_input(self, body: EquilibriumBody | str) -> np.ndarray:
        return self._input_vectors[body if isinstance(body, str) else body.body_id]

    def body_output(self, body: EquilibriumBody | str) -> np.ndarray:
        return self._outcome_vectors[body if isinstance(body, str) else body.body_id]

    def body_polarity(self, body: EquilibriumBody | str) -> int:
        return self.body_outcomes(body)[0].polarity

    def applicable(self, body: EquilibriumBody, scope_key: str, reality_key: str, valid_at: int | None) -> bool:
        if body.reality_key != reality_key or not _scope_matches(body.scope_key, scope_key):
            return False
        if not _valid(body.valid_from, body.valid_to, valid_at):
            return False
        return all(
            item.reality_key == reality_key
            and _scope_matches(item.scope_key, scope_key)
            and _valid(item.valid_from, item.valid_to, valid_at)
            for item in self.body_units(body)
        )

    def completeness(self, body: EquilibriumBody, active_semantic_keys: frozenset[str]) -> float:
        required = {item.semantic_key for item in self.body_inputs(body)}
        return len(required & active_semantic_keys) / max(1, len(required))

    def normalized_body_weights(self, scores: Mapping[str, float]) -> dict[str, float]:
        """Collapse exact same-source duplicates, then cap each polarity mass."""
        winners: dict[tuple[int, str, tuple[object, ...]], tuple[str, float]] = {}
        for body_id, relevance in scores.items():
            body = self.bodies[body_id]
            value = max(0.0, float(relevance)) * body.base_weight * body.authority * body.confidence
            if body_id not in self._canonical_body_ids:
                continue
            key = (self.body_polarity(body), body.independent_source_key, self._signatures[body_id])
            current = winners.get(key)
            if current is None or value > current[1] or (value == current[1] and body_id < current[0]):
                winners[key] = (body_id, value)
        result = {body_id: 0.0 for body_id in scores}
        by_polarity: dict[int, list[tuple[str, float]]] = {-1: [], 1: []}
        for (polarity, _, _), winner in winners.items():
            by_polarity[polarity].append(winner)
        for values in by_polarity.values():
            total = sum(value for _, value in values)
            scale = min(1.0, self.source_mass_cap / max(total, 1e-12))
            for body_id, value in values:
                result[body_id] = value * scale
        return result

    def _cell_score(self, cell: MinimapCell, position: np.ndarray, active_keys: frozenset[str]) -> float:
        score = max(_cosine(self.summary_vectors[row, :STATE_DIMENSION], position) for row in cell.prototype_refs)
        if active_keys & self._cell_input_keys[cell.cell_id]:
            score += 2.0
        return score

    def frontier(
        self,
        position: np.ndarray,
        scope_key: str,
        reality_key: str,
        valid_at: int | None,
        maximum_bodies: int = 128,
        active_semantic_keys: frozenset[str] = frozenset(),
        excluded_body_ids: frozenset[str] = frozenset(),
    ) -> tuple[tuple[MinimapCell, ...], tuple[EquilibriumBody, ...]]:
        if not 0 < maximum_bodies <= 128:
            raise ValueError("maximum bodies per frontier outside L5 bound")
        position = _unit(position)
        self._access["frontier_calls"] += 1
        self._access["root_cell_reads"] += len(self._root_cell_ids)
        roots = [self.cells[cell_id] for cell_id in self._root_cell_ids]
        selected: list[MinimapCell] = []
        frontier = roots
        leaves: list[MinimapCell] = []
        while frontier:
            compatible = [
                cell for cell in frontier
                if any(key in cell.context_keys for key in (_context_key(reality_key, scope_key), _context_key(reality_key, "global")))
            ]
            self._access["minimap_cells_scored"] += len(compatible)
            ranked = sorted(compatible, key=lambda cell: (-self._cell_score(cell, position, active_semantic_keys), cell.cell_id))[:4]
            selected.extend(ranked)
            children = [self.cells[child] for cell in ranked for child in cell.child_ids]
            if not children:
                leaves = ranked
                break
            frontier = children
        self._access["minimap_body_id_reads"] += sum(len(cell.body_ids) for cell in leaves)
        candidate_ids = {body_id for cell in leaves for body_id in cell.body_ids}
        # Exact semantic input indexes are profile-independent addresses, not
        # answer hints. They guarantee that a relevant body cannot be hidden by
        # approximate minimap descent in a large field.
        self._access["consumer_index_lookups"] += len(active_semantic_keys)
        candidate_ids.update(
            body_id
            for key in active_semantic_keys
            for body_id in self._consumer_body_ids.get(key, ())
        )
        self._access["body_records_read"] += len(candidate_ids)
        candidates = [
            self.bodies[body_id] for body_id in candidate_ids
            if body_id not in excluded_body_ids
            and self.applicable(self.bodies[body_id], scope_key, reality_key, valid_at)
        ]
        candidates.sort(
            key=lambda body: (
                -self.completeness(body, active_semantic_keys),
                -_cosine(self.body_input(body), position),
                body.body_id,
            )
        )
        return tuple(selected), tuple(candidates[:maximum_bodies])

    def coverage_bound(
        self,
        cells: tuple[MinimapCell, ...],
        bodies: tuple[EquilibriumBody, ...],
        accounted_body_ids: frozenset[str] = frozenset(),
        scope_key: str | None = None,
        reality_key: str | None = None,
        valid_at: int | None = None,
        active_semantic_keys: frozenset[str] = frozenset(),
    ) -> float:
        leaves = tuple(cell for cell in cells if not cell.child_ids)
        possible = {body_id for cell in leaves for body_id in cell.body_ids}
        if active_semantic_keys:
            possible = {
                body_id
                for key in active_semantic_keys
                for body_id in self._consumer_body_ids.get(key, ())
                if self.completeness(self.bodies[body_id], active_semantic_keys) >= 1.0
            }
        if scope_key is not None and reality_key is not None:
            possible = {
                body_id for body_id in possible
                if self.applicable(self.bodies[body_id], scope_key, reality_key, valid_at)
            }
        accounted = {body.body_id for body in bodies} | (possible & accounted_body_ids)
        return min(1.0, len(accounted) / max(1, len(possible)))


def _body_arrays(
    bodies: tuple[EquilibriumBody, ...],
    units: tuple[FieldMumbrane, ...],
    vectors: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    by_unit = {unit.unit_id: unit for unit in units}
    source: dict[str, np.ndarray] = {}
    outcome: dict[str, np.ndarray] = {}
    polarity: dict[str, int] = {}
    for body in bodies:
        inputs = [by_unit[item] for item in body.input_unit_ids]
        outputs = [by_unit[item] for item in body.outcome_unit_ids]
        source[body.body_id] = _unit(np.mean([vectors[item.semantic_vector_ref] for item in inputs], axis=0))
        outcome[body.body_id] = _unit(np.mean([vectors[item.semantic_vector_ref] for item in outputs], axis=0))
        polarity[body.body_id] = outputs[0].polarity
    return source, outcome, polarity


def _summary_modes(
    group: tuple[EquilibriumBody, ...],
    source: Mapping[str, np.ndarray],
    outcome: Mapping[str, np.ndarray],
    polarity: Mapping[str, int],
    limit: int,
) -> tuple[np.ndarray, ...]:
    # Separate signed outcomes first; deterministic farthest-first keeps multimodal cells useful.
    ordered = sorted(group, key=lambda body: (polarity[body.body_id], body.body_id))
    seeds: list[EquilibriumBody] = []
    for sign in (-1, 1):
        matches = [body for body in ordered if polarity[body.body_id] == sign]
        if matches:
            seeds.append(matches[0])
    while len(seeds) < min(limit, len(ordered)):
        remaining = [body for body in ordered if body not in seeds]
        if not remaining:
            break
        candidate = max(remaining, key=lambda body: (min(1.0 - _cosine(source[body.body_id], source[item.body_id]) for item in seeds), body.body_id))
        distance = min(1.0 - _cosine(source[candidate.body_id], source[item.body_id]) for item in seeds if polarity[item.body_id] == polarity[candidate.body_id])
        if distance <= 1e-6:
            break
        seeds.append(candidate)
    assignments: dict[str, list[EquilibriumBody]] = {seed.body_id: [] for seed in seeds}
    for body in ordered:
        compatible_seeds = [item for item in seeds if polarity[item.body_id] == polarity[body.body_id]]
        seed = max(compatible_seeds, key=lambda item: (_cosine(source[body.body_id], source[item.body_id]), item.body_id))
        assignments[seed.body_id].append(body)
    summaries = []
    for seed in seeds:
        members = assignments[seed.body_id]
        inp = _unit(np.mean([source[item.body_id] for item in members], axis=0))
        out = _unit(np.mean([outcome[item.body_id] for item in members], axis=0))
        delta = _unit(out - inp)
        summaries.append(np.concatenate((inp, out, delta)).astype(np.float32))
    return tuple(summaries)


def build_minimap(
    bodies: tuple[EquilibriumBody, ...],
    units: tuple[FieldMumbrane, ...],
    vectors: np.ndarray,
    *,
    leaf_limit: int = 64,
    fanout: int = 16,
    modes: int = 8,
    source_mass_cap: float = 8.0,
) -> tuple[tuple[MinimapCell, ...], np.ndarray]:
    if not bodies or not 0 < leaf_limit <= 64 or not 1 < fanout <= 16 or not 0 < modes <= 8:
        raise ValueError("invalid minimap bounds")
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[1] != STATE_DIMENSION or not np.isfinite(vectors).all():
        raise ValueError("invalid field vectors")
    source, outcome, polarity = _body_arrays(bodies, units, vectors)
    body_by_id = {body.body_id: body for body in bodies}
    by_unit = {unit.unit_id: unit for unit in units}
    signatures = {
        body.body_id: (
            tuple(sorted((by_unit[item].semantic_key, by_unit[item].polarity) for item in body.input_unit_ids)),
            tuple(sorted((by_unit[item].semantic_key, by_unit[item].polarity) for item in body.outcome_unit_ids)),
            body.scope_key,
            body.reality_key,
            body.valid_from,
            body.valid_to,
        )
        for body in bodies
    }
    ordered = sorted(bodies, key=lambda body: (tuple(np.round(source[body.body_id][:8], 6)), body.body_id))
    cells: list[MinimapCell] = []
    summaries: list[np.ndarray] = []

    def make_cell(group: tuple[EquilibriumBody, ...], level: int, child_ids: tuple[str, ...]) -> MinimapCell:
        refs = []
        for summary in _summary_modes(group, source, outcome, polarity, modes):
            refs.append(len(summaries))
            summaries.append(summary)
        source_winners: dict[tuple[int, str, tuple[object, ...]], float] = {}
        for body in group:
            key = (polarity[body.body_id], body.independent_source_key, signatures[body.body_id])
            source_winners[key] = max(source_winners.get(key, 0.0), body.base_weight * body.authority * body.confidence)
        positive = min(source_mass_cap, sum(value for (sign, _, _), value in source_winners.items() if sign == 1))
        negative = min(source_mass_cap, sum(value for (sign, _, _), value in source_winners.items() if sign == -1))
        contexts = tuple(sorted({_context_key(body.reality_key, body.scope_key) for body in group}))
        center = np.mean([source[body.body_id] for body in group], axis=0)
        radius = max(float(np.linalg.norm(source[body.body_id] - center)) for body in group)
        cell_id = f"cell:{level}:{len(cells):08d}"
        body_ids = tuple(sorted(body.body_id for body in group))
        summary_hash = hashlib.sha256(
            repr((cell_id, child_ids, body_ids, refs, positive, negative, contexts)).encode()
            + b"".join(summaries[row].tobytes() for row in refs)
        ).hexdigest()
        return MinimapCell(cell_id, level, None, child_ids, body_ids, tuple(refs), tuple(refs), positive, negative, contexts, len(group), radius, 0.0, summary_hash)

    level_cells = []
    for start in range(0, len(ordered), leaf_limit):
        cell = make_cell(tuple(ordered[start:start + leaf_limit]), 0, ())
        cells.append(cell)
        level_cells.append(cell)
    level = 1
    while len(level_cells) > 1:
        parents = []
        for start in range(0, len(level_cells), fanout):
            children = tuple(level_cells[start:start + fanout])
            group = tuple(
                sorted(
                    (body_by_id[body_id] for child in children for body_id in child.body_ids),
                    key=lambda body: body.body_id,
                )
            )
            parent = make_cell(group, level, tuple(child.cell_id for child in children))
            cells.append(parent)
            parents.append(parent)
            parent_id = parent.cell_id
            child_ids = {child.cell_id for child in children}
            cells[:] = [replace(item, parent_id=parent_id) if item.cell_id in child_ids else item for item in cells]
            level_cells = [replace(item, parent_id=parent_id) if item.cell_id in child_ids else item for item in level_cells]
        level_cells = parents
        level += 1
    return tuple(cells), np.asarray(summaries, dtype=np.float32)


def save_minimap(root: Path, cells: tuple[MinimapCell, ...], vectors: np.ndarray) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cells.json").write_text(json.dumps([asdict(cell) for cell in cells], sort_keys=True), encoding="utf-8")
    np.save(root / "summary-vectors.npy", np.asarray(vectors, dtype=np.float32))


def load_minimap(root: Path) -> tuple[tuple[MinimapCell, ...], np.ndarray]:
    rows = json.loads((root / "cells.json").read_text(encoding="utf-8"))
    tuple_fields = {"child_ids", "body_ids", "prototype_refs", "transition_refs", "context_keys"}
    cells = tuple(MinimapCell(**{key: tuple(value) if key in tuple_fields else value for key, value in row.items()}) for row in rows)
    return cells, np.load(root / "summary-vectors.npy")


__all__ = ["EquilibriumFieldIndex", "FieldAccessAccounting", "build_minimap", "load_minimap", "save_minimap"]
