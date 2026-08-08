"""Deterministic behavioral topology cells for G2.10."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

CHANNELS = ("activation", "support", "opposition", "uncertainty", "live", "time")
STATE_WIDTH = len(CHANNELS) * 2
RESPONSE_WIDTH = 35
SIGNATURE_WIDTH = 1704
ETA = 0.25


@dataclass(frozen=True, slots=True)
class Cell:
    cell_id: str
    relation_type: str
    roles: tuple[str, str]
    symmetric: bool
    write: tuple[int, ...]


CELLS = (
    Cell("transfer.derive", "implies", ("premise", "conclusion"), False, (6,)),
    Cell("transfer.oblige", "requires", ("dependent", "prerequisite"), False, ()),
    Cell("evidence.support", "supports", ("evidence", "claim"), False, (7,)),
    Cell("evidence.opposition", "opposes", ("evidence", "claim"), False, (8,)),
    Cell("evidence.uncertainty", "uncertainty", ("source", "claim"), False, (9,)),
    Cell("constraint.equal", "equals", ("left", "right"), True, (0, 6)),
    Cell("constraint.exclude", "excludes", ("left", "right"), True, (0, 6)),
    Cell("precedes", "before", ("first", "second"), False, ()),
    Cell("replace", "supersedes", ("older", "newer"), False, (4,)),
)
CELL_BY_ID = {cell.cell_id: cell for cell in CELLS}


@dataclass(frozen=True, slots=True)
class Probe:
    name: str
    values: tuple[float, ...]
    scope_ok: bool = True
    time_ok: bool = True
    modality_ok: bool = True
    polarity_ok: bool = True


def _state(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    return left + right


def probes() -> tuple[Probe, ...]:
    neutral = (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    values: list[Probe] = []
    for index, (left, right) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1), (.25, .75), (.75, .25))):
        values.append(Probe(f"activation-{index}", _state((left, *neutral[1:]), (right, *neutral[1:]))))
    for source in (0.0, 1.0):
        for base in (.25, .75):
            values.append(Probe(f"evidence-{source}-{base}", _state((source, 0, 0, 0, 1, 0), (0, base, base, base, 1, 0))))
    for index, (left, right) in enumerate(((0, 1), (1, 0), (.5, .5), (.25, .75), (.75, .25))):
        values.append(Probe(f"time-{index}", _state((0, 0, 0, 0, 1, left), (0, 0, 0, 0, 1, right))))
    values.append(Probe("time-missing-left", _state((0, 0, 0, 0, 1, 0), (0, 0, 0, 0, 1, 1)), time_ok=False))
    values.append(Probe("time-missing-right", _state((0, 0, 0, 0, 1, 1), (0, 0, 0, 0, 1, 0)), time_ok=False))
    for live in (0.0, 1.0):
        for active in (0.0, 1.0):
            values.append(Probe(f"lifecycle-{live}-{active}", _state((0, 0, 0, 0, live, 0), (active, 0, 0, 0, 1, 0))))
    values.append(Probe("scope-closed", _state(neutral, neutral), scope_ok=False))
    values.append(Probe("modality-closed", _state(neutral, neutral), modality_ok=False))
    values.append(Probe("polarity-closed", _state(neutral, neutral), polarity_ok=False))
    if len(values) != 24:
        raise AssertionError("G2.10 probe contract changed")
    return tuple(values)


def _diagnostics(probe: Probe) -> np.ndarray:
    return np.array((float(probe.scope_ok and probe.time_ok and probe.modality_ok and probe.polarity_ok), float(not probe.scope_ok), float(not probe.time_ok), float(not probe.modality_ok), float(not probe.polarity_ok)), dtype=np.float64)


def response(cell: Cell, probe: Probe, *, swapped: bool = False) -> np.ndarray:
    state = np.array(probe.values, dtype=np.float64)
    if swapped:
        state = np.concatenate((state[6:], state[:6]))
    diagnostics = _diagnostics(probe)
    gradient = np.zeros(STATE_WIDTH, dtype=np.float64)
    exact = np.zeros(5, dtype=np.float64)
    energy = 0.0
    if diagnostics[0]:
        left, right = state[:6], state[6:]
        if cell.cell_id.startswith("transfer"):
            residual = max(0.0, left[0] - right[0])
            energy = residual * residual
            if residual:
                gradient[0], gradient[6] = 2 * residual, -2 * residual
            exact[0 if cell.cell_id.endswith("derive") else 1] = residual
        elif cell.cell_id.startswith("evidence"):
            channel = {"evidence.support": 1, "evidence.opposition": 2, "evidence.uncertainty": 3}[cell.cell_id]
            strength = left[0]
            energy = strength * (1 - right[channel]) ** 2
            gradient[6 + channel] = -2 * strength * (1 - right[channel])
        elif cell.cell_id == "constraint.equal":
            residual = left[0] - right[0]
            energy = residual * residual
            gradient[0], gradient[6] = 2 * residual, -2 * residual
        elif cell.cell_id == "constraint.exclude":
            residual = max(0.0, left[0] + right[0] - 1)
            energy = residual * residual
            if residual:
                gradient[0] = gradient[6] = 2 * residual
            exact[2] = residual
        elif cell.cell_id == "precedes":
            residual = max(0.0, left[5] - right[5])
            energy = residual * residual
            gradient[5], gradient[11] = 2 * residual, -2 * residual
            exact[3] = residual
        elif cell.cell_id == "replace":
            energy = (left[4] * right[0]) ** 2
            gradient[4] = 2 * left[4] * right[0] ** 2
            exact[4] = left[4] * right[0]
    write = np.zeros(STATE_WIDTH, dtype=np.float64)
    write[list(cell.write)] = 1.0
    delta = np.clip(state - ETA * write * gradient, 0.0, 1.0) - state
    return np.concatenate((diagnostics, np.array((energy,)), gradient, delta, exact))


def canonical_response(value: np.ndarray, *, swapped: bool) -> np.ndarray:
    """Return a response to canonical port order for symmetry comparisons."""
    if not swapped:
        return value
    output = value.copy()
    output[6:18] = np.concatenate((value[12:18], value[6:12]))
    output[18:30] = np.concatenate((value[24:30], value[18:24]))
    return output


def signature(cell: Cell) -> np.ndarray:
    write = np.zeros(STATE_WIDTH, dtype=np.float64)
    write[list(cell.write)] = 1.0
    read = np.ones(STATE_WIDTH, dtype=np.float64)
    rows = [read, write]
    for probe in probes():
        rows.extend((response(cell, probe), response(cell, probe, swapped=True)))
    value = np.concatenate(rows)
    if value.shape != (SIGNATURE_WIDTH,):
        raise AssertionError(value.shape)
    return np.round(value, 8)


def signature_digest(cell: Cell) -> str:
    return hashlib.sha256(json.dumps(signature(cell).tolist(), separators=(",", ":")).encode()).hexdigest()


def signature_distance(value: np.ndarray, cell: Cell) -> float:
    """RMS over coordinates that distinguish registered cell behavior."""
    bank = np.stack(tuple(signature(item) for item in CELLS))
    variance = bank.var(axis=0)
    weights = np.where(variance > 1e-10, variance / variance[variance > 1e-10].mean(), 0.0)
    return float(np.sqrt(np.sum((value - signature(cell)) ** 2 * weights) / max(weights.sum(), 1.0)))


def canonical_order(cell: Cell, atom_ids: tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted(atom_ids)) if cell.symmetric else atom_ids
