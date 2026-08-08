"""Deterministic projection of a learned coordinate into a legal cell."""
from __future__ import annotations

import numpy as np

from .schemas import ProjectionDecision
from .topology import CELLS, canonical_order, signature_distance


def project(vector: np.ndarray, atom_ids: tuple[str, str], kinds: tuple[str, str], port_probability: float = 1.0, *, distance_limit: float = 0.2, margin_limit: float = 0.01) -> ProjectionDecision:
    legal = [cell for cell in CELLS if not (cell.cell_id == "precedes" and kinds != ("event", "event")) and not (cell.cell_id == "constraint.equal" and kinds != ("value", "value"))]
    costs = sorted(((signature_distance(vector, cell), cell) for cell in legal), key=lambda item: (item[0], item[1].cell_id))
    distance, cell = costs[0]; margin = costs[1][0] - distance if len(costs) > 1 else 1.0
    if distance > distance_limit: return ProjectionDecision(None, (), "quarantine", distance, margin, port_probability, ("OUTSIDE_CELL",))
    if margin < margin_limit or port_probability < .5: return ProjectionDecision(None, (), "clarification_required", distance, margin, port_probability, ("AMBIGUOUS_CELL",))
    return ProjectionDecision(cell.cell_id, canonical_order(cell, atom_ids), "accept", distance, margin, port_probability, ())
