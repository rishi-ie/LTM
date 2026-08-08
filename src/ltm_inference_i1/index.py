"""Bounded content-addressable body index."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .schemas import AtomicMumbrane, ReasoningBody


class BodyIndex:
    def __init__(self, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], vectors: np.ndarray) -> None:
        self.bodies = {body.body_id: body for body in bodies}
        self.units = {unit.unit_id: unit for unit in units}
        self.vectors = vectors
        self._postings: dict[str, list[str]] = defaultdict(list)
        self._by_body: dict[str, tuple[str, ...]] = {body.body_id: body.unit_ids for body in bodies}
        for unit in units:
            self._postings[unit.identity_key].append(unit.body_id)

    def retrieve(self, active_ids: tuple[str, ...], maximum: int = 32) -> tuple[ReasoningBody, ...]:
        selected: list[str] = []
        for unit_id in active_ids:
            unit = self.units[unit_id]
            for body_id in self._postings.get(unit.identity_key, ()):
                if body_id not in selected:
                    selected.append(body_id)
                if len(selected) >= maximum:
                    break
            if len(selected) >= maximum:
                break
        return tuple(self.bodies[body_id] for body_id in selected[:maximum])

    def body_units(self, body: ReasoningBody) -> tuple[AtomicMumbrane, ...]:
        return tuple(self.units[unit_id] for unit_id in body.unit_ids)
