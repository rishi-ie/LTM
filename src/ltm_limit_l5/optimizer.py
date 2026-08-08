"""Source-normalized multi-hypothesis equilibrium optimization for L5."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .field import EquilibriumFieldIndex
from .schemas import (
    CompiledPromptField,
    EquilibriumBody,
    EquilibriumCandidate,
    EquilibriumStep,
    FieldEquilibriumResult,
    FrontierSnapshot,
    LatentModeState,
)

Compatibility = Callable[[np.ndarray, np.ndarray, np.ndarray, EquilibriumBody], float]


def _unit(value: np.ndarray) -> np.ndarray:
    row = np.asarray(value, dtype=np.float32)
    return row / max(1e-8, float(np.linalg.norm(row)))


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right) / max(1e-8, float(np.linalg.norm(left) * np.linalg.norm(right))))


def _hash(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        if isinstance(value, np.ndarray):
            digest.update(value.astype(np.float32).tobytes())
        else:
            digest.update(repr(value).encode())
    return digest.hexdigest()


def _modality_weight(name: str) -> float:
    return {
        "asserted": 1.0,
        "observed": 1.0,
        "user_reported": 0.75,
        "conditional": 0.70,
        "hypothetical": 0.50,
        "uncertain": 0.40,
    }.get(name, 0.50)


@dataclass(slots=True)
class _Mode:
    mode_id: str
    position: np.ndarray
    polarity: int
    active_keys: set[str]
    activations: dict[str, float]
    applied_body_ids: set[str] = field(default_factory=set)
    supporting_body_ids: set[str] = field(default_factory=set)
    supporting_source_keys: set[str] = field(default_factory=set)
    provenance_ids: set[str] = field(default_factory=set)
    support_weights: dict[str, float] = field(default_factory=dict)
    opposition_weights: dict[str, float] = field(default_factory=dict)
    focus_unit_ids: tuple[str, ...] = ()
    confidence: float = 1.0
    stable_steps: int = 0
    last_energy: float = 0.0

    def clone(self, suffix: str) -> _Mode:
        return _Mode(
            f"{self.mode_id}:{suffix}",
            self.position.copy(),
            self.polarity,
            set(self.active_keys),
            dict(self.activations),
            set(self.applied_body_ids),
            set(self.supporting_body_ids),
            set(self.supporting_source_keys),
            set(self.provenance_ids),
            dict(self.support_weights),
            dict(self.opposition_weights),
            self.focus_unit_ids,
            self.confidence,
            self.stable_steps,
            self.last_energy,
        )


def _public_mode(mode: _Mode) -> LatentModeState:
    activations = tuple(sorted((key, float(value)) for key, value in mode.activations.items()))
    sources = tuple(sorted(mode.supporting_source_keys))
    state_hash = _hash(mode.position, activations, mode.polarity, sources)
    return LatentModeState(
        mode.mode_id,
        tuple(float(value) for value in mode.position),
        activations,
        float(mode.confidence),
        mode.polarity,
        sources,
        state_hash,
    )


def _context(prompt: CompiledPromptField) -> tuple[str, str, int | None]:
    if not prompt.influences:
        raise ValueError("compiled prompt contains no influences")
    scopes = {item.scope_key for item in prompt.influences}
    realities = {item.reality_key for item in prompt.influences}
    times = {item.valid_at for item in prompt.influences}
    if len(scopes) != 1 or len(realities) != 1 or len(times) != 1:
        raise ValueError("compiled prompt context is inconsistent")
    return next(iter(scopes)), next(iter(realities)), next(iter(times))


def _initial_modes(index: EquilibriumFieldIndex, prompt: CompiledPromptField, max_modes: int) -> list[_Mode]:
    active = {item.semantic_key for item in prompt.influences}
    activations = {item.unit_id: item.clamp_strength * item.compiler_confidence for item in prompt.influences}
    roots = tuple(cell for cell in index.cells.values() if cell.parent_id is None)
    signs = []
    if any(cell.positive_source_mass > 0 for cell in roots):
        signs.append(1)
    if any(cell.negative_source_mass > 0 for cell in roots):
        signs.append(-1)
    if not signs:
        signs = sorted({item.polarity_sign for item in prompt.influences})
    return [
        _Mode(f"mode:{ordinal}", np.asarray(prompt.anchor_position, dtype=np.float32).copy(), sign, set(active), dict(activations))
        for ordinal, sign in enumerate(signs[:max_modes])
    ]


def _energy(index: EquilibriumFieldIndex, mode: _Mode, anchor: np.ndarray, clamp: float) -> float:
    position = mode.position
    value = clamp * float(np.dot(position - anchor, position - anchor))
    # Subtract the maximum possible distance so adding newly opened support cannot
    # manufacture an energy increase merely by refining the frontier.
    for body_id, weight in mode.support_weights.items():
        distance = index.body_output(body_id) - position
        value += weight * (float(np.dot(distance, distance)) - 4.0)
    for body_id, weight in mode.opposition_weights.items():
        value += weight * 0.5 * (_cosine(position, index.body_output(body_id)) - 1.0)
    return float(value)


def _relax(
    index: EquilibriumFieldIndex,
    mode: _Mode,
    anchor: np.ndarray,
    clamp: float,
    inner_updates: int,
) -> tuple[float, float, float]:
    before = mode.position.copy()
    current = _energy(index, mode, anchor, clamp)
    step_size = 0.40
    for _ in range(inner_updates):
        gradient = 2.0 * clamp * (mode.position - anchor)
        for body_id, weight in mode.support_weights.items():
            gradient += 2.0 * weight * (mode.position - index.body_output(body_id))
        for body_id, weight in mode.opposition_weights.items():
            gradient += 0.5 * weight * index.body_output(body_id)
        if float(np.linalg.norm(gradient)) < 1e-8:
            break
        accepted = False
        local_rate = step_size
        for _ in range(16):
            proposal = _unit(mode.position - local_rate * gradient)
            candidate = mode.position.copy()
            mode.position = proposal
            proposal_energy = _energy(index, mode, anchor, clamp)
            if proposal_energy <= current + 1e-9:
                current = proposal_energy
                step_size = local_rate
                accepted = True
                break
            mode.position = candidate
            local_rate *= 0.5
        if not accepted:
            step_size = 0.0
            break
    # The objective is cumulative; newly added normalized factors are non-positive.
    if current > mode.last_energy + 1e-7:
        mode.position = before
        current = min(mode.last_energy, _energy(index, mode, anchor, clamp))
        step_size = 0.0
    mode.last_energy = current
    return current, float(np.linalg.norm(mode.position - before)), step_size


def _kernel_callable(kernel: object | None, compatibility: Compatibility | None) -> Compatibility | None:
    if compatibility is not None:
        return compatibility
    if kernel is None:
        return None
    if callable(kernel):
        return kernel  # type: ignore[return-value]
    callback = getattr(kernel, "compatibility", None)
    if not callable(callback):
        raise TypeError("kernel must be callable or expose compatibility")
    return callback  # type: ignore[return-value]


def _body_scores(
    index: EquilibriumFieldIndex,
    mode: _Mode,
    bodies: tuple[EquilibriumBody, ...],
    query_weight: float,
    compatibility: Compatibility | None,
) -> tuple[dict[str, float], dict[str, float]]:
    authority_scores = {}
    geometry_multipliers = {}
    for body in bodies:
        if body.body_id in mode.applied_body_ids or index.completeness(body, frozenset(mode.active_keys)) < 1.0:
            continue
        inp = index.body_input(body)
        out = index.body_output(body)
        score = query_weight * min(
            _modality_weight(item.modality) for item in index.body_outcomes(body)
        )
        geometry = max(0.05, 0.5 + 0.5 * _cosine(mode.position, inp))
        if compatibility is not None:
            geometry *= float(
                np.clip(
                    compatibility(
                        mode.position.copy(), inp.copy(), out.copy(), body
                    ),
                    0.0,
                    1.0,
                )
            )
        authority_scores[body.body_id] = score
        geometry_multipliers[body.body_id] = geometry
    authority = index.normalized_body_weights(authority_scores)
    geometry = {
        body_id: weight * geometry_multipliers[body_id]
        for body_id, weight in authority.items()
    }
    return authority, geometry


def _expand_mode(
    index: EquilibriumFieldIndex,
    mode: _Mode,
    bodies: tuple[EquilibriumBody, ...],
    authority_weights: dict[str, float],
    geometry_weights: dict[str, float],
) -> list[_Mode]:
    groups: dict[tuple[int, tuple[str, ...]], list[EquilibriumBody]] = {}
    for body in bodies:
        if body.body_id not in authority_weights or body.body_id in mode.applied_body_ids:
            continue
        outcomes = index.body_outcomes(body)
        key = (outcomes[0].polarity, tuple(sorted(item.semantic_key for item in outcomes)))
        groups.setdefault(key, []).append(body)
    compatible = [(key, rows) for key, rows in groups.items() if key[0] == mode.polarity]
    if not compatible:
        mode.stable_steps += 1
        return [mode]
    children = []
    sibling_ids = {body.body_id for rows in groups.values() for body in rows}
    for ordinal, (key, rows) in enumerate(sorted(compatible, key=lambda item: item[0])):
        child = mode.clone(str(ordinal))
        total = sum(authority_weights[body.body_id] for body in rows)
        child.confidence = min(child.confidence, 1.0 - math.exp(-2.0 * total))
        focus = []
        child.applied_body_ids.update(sibling_ids)
        for body in rows:
            authority_weight = authority_weights[body.body_id]
            if authority_weight <= 0:
                continue
            child.support_weights[body.body_id] = geometry_weights[body.body_id]
            child.supporting_body_ids.add(body.body_id)
            child.supporting_source_keys.add(body.independent_source_key)
            child.provenance_ids.update(body.provenance_ids)
            for item in index.body_outcomes(body):
                child.active_keys.add(item.semantic_key)
                child.activations[item.unit_id] = max(child.activations.get(item.unit_id, 0.0), 1.0 - math.exp(-2.0 * total))
                focus.append(item.unit_id)
        for body_id, authority_weight in authority_weights.items():
            if authority_weight > 0 and index.body_polarity(body_id) != child.polarity:
                child.opposition_weights[body_id] = geometry_weights[body_id]
        child.focus_unit_ids = tuple(sorted(set(focus)))
        child.stable_steps = 0
        children.append(child)
    return children


def _mode_rank(mode: _Mode, anchor: np.ndarray) -> tuple[float, str]:
    # Confidence remains authoritative; geometry only breaks otherwise equal soft modes.
    return mode.confidence + 0.01 * _cosine(mode.position, anchor), mode.mode_id


def _deduplicate_modes(modes: list[_Mode], anchor: np.ndarray, limit: int) -> list[_Mode]:
    unique: dict[tuple[int, tuple[str, ...], tuple[str, ...]], _Mode] = {}
    for mode in modes:
        key = (mode.polarity, tuple(sorted(mode.active_keys)), mode.focus_unit_ids)
        current = unique.get(key)
        if current is None or _mode_rank(mode, anchor) > _mode_rank(current, anchor):
            unique[key] = mode
    return sorted(unique.values(), key=lambda item: (-_mode_rank(item, anchor)[0], _mode_rank(item, anchor)[1]))[:limit]


def _candidates(index: EquilibriumFieldIndex, modes: list[_Mode]) -> tuple[EquilibriumCandidate, ...]:
    rows: dict[tuple[str, int], dict[str, object]] = {}
    for mode in modes:
        for unit_id in mode.focus_unit_ids:
            unit = index.units[unit_id]
            key = (unit.semantic_key, unit.polarity)
            row = rows.setdefault(key, {"unit_id": unit_id, "confidence": 0.0, "bodies": set(), "sources": set(), "provenance": set()})
            if mode.confidence > float(row["confidence"]):
                row["unit_id"] = unit_id
                row["confidence"] = mode.confidence
            row["bodies"].update(mode.supporting_body_ids)  # type: ignore[union-attr]
            row["sources"].update(mode.supporting_source_keys)  # type: ignore[union-attr]
            row["provenance"].update(mode.provenance_ids)  # type: ignore[union-attr]
    ordered = sorted(rows.items(), key=lambda item: (-float(item[1]["confidence"]), item[0]))
    result = []
    for ordinal, ((semantic_key, polarity), row) in enumerate(ordered):
        second = float(ordered[ordinal + 1][1]["confidence"]) if ordinal + 1 < len(ordered) else 0.0
        confidence = float(row["confidence"])
        result.append(
            EquilibriumCandidate(
                str(row["unit_id"]),
                semantic_key,
                polarity,
                confidence,
                confidence - second,
                tuple(sorted(row["bodies"])),  # type: ignore[arg-type]
                tuple(sorted(row["sources"])),  # type: ignore[arg-type]
                tuple(sorted(row["provenance"])),  # type: ignore[arg-type]
            )
        )
    return tuple(result)


def optimize(
    index: EquilibriumFieldIndex,
    prompt: CompiledPromptField,
    *,
    compatibility: Compatibility | None = None,
    kernel: object | None = None,
    maximum_steps: int = 64,
    maximum_bodies: int = 128,
    maximum_cumulative_bodies: int = 2048,
    maximum_modes: int = 8,
    inner_updates: int = 4,
    confidence_threshold: float = 0.70,
    margin_threshold: float = 0.05,
    coverage_threshold: float = 0.90,
    convergence_residual: float = 1e-3,
) -> FieldEquilibriumResult:
    """Relax source-backed alternatives without granting them factual authority."""
    if not 0 < maximum_steps <= 64 or not 0 < maximum_modes <= 8 or not 0 < inner_updates <= 4:
        raise ValueError("optimizer bounds outside L5 profile")
    if prompt.disposition != "accept":
        disposition = "quarantine" if prompt.disposition == "quarantine" else "unknown"
        return FieldEquilibriumResult(prompt.prompt_id, disposition, (), (), (), None, (), (), (), "uncertified", ("PROMPT_NOT_ACCEPTED",), ())
    try:
        scope_key, reality_key, valid_at = _context(prompt)
    except ValueError:
        return FieldEquilibriumResult(prompt.prompt_id, "quarantine", (), (), (), None, (), (), (), "uncertified", ("PROMPT_CONTEXT_MISMATCH",), ())
    callback = _kernel_callable(kernel, compatibility)
    anchor = _unit(np.asarray(prompt.anchor_position, dtype=np.float32))
    query_weight = float(np.mean([item.query_relevance_weight * item.compiler_confidence * item.modality_weight for item in prompt.influences]))
    clamp = max(0.05, float(np.mean([item.clamp_strength * item.compiler_confidence for item in prompt.influences])))
    modes = _initial_modes(index, prompt, maximum_modes)
    initial = tuple(_public_mode(mode) for mode in modes)
    trace: list[EquilibriumStep] = []
    frontiers: list[FrontierSnapshot] = []
    opened: set[str] = set()
    previous_frontier: set[str] = set()
    last_energy = 0.0
    stable_steps = 0
    coverage = 1.0
    exhausted = False
    for step in range(maximum_steps):
        expanded: list[_Mode] = []
        selected_cells = {}
        current_bodies = {}
        step_coverage = []
        for mode in modes:
            cells, bodies = index.frontier(
                mode.position,
                scope_key,
                reality_key,
                valid_at,
                maximum_bodies,
                frozenset(mode.active_keys),
                frozenset(mode.applied_body_ids),
            )
            selected_cells.update((cell.cell_id, cell) for cell in cells)
            current_bodies.update((body.body_id, body) for body in bodies)
            step_coverage.append(
                index.coverage_bound(
                    cells,
                    bodies,
                    frozenset(mode.applied_body_ids),
                    scope_key,
                    reality_key,
                    valid_at,
                    frozenset(mode.active_keys),
                )
            )
            authority_weights, geometry_weights = _body_scores(
                index, mode, bodies, query_weight, callback
            )
            expanded.extend(
                _expand_mode(
                    index,
                    mode,
                    bodies,
                    authority_weights,
                    geometry_weights,
                )
            )
        newly_opened = set(current_bodies) - opened
        opened.update(current_bodies)
        if len(opened) > maximum_cumulative_bodies:
            exhausted = True
            break
        modes = _deduplicate_modes(expanded, anchor, maximum_modes)
        mode_energies: list[float] = []
        max_residual = 0.0
        rate = 0.0
        for mode in modes:
            energy, residual, mode_rate = _relax(index, mode, anchor, clamp, inner_updates)
            mode_energies.append(energy)
            max_residual = max(max_residual, residual)
            rate = max(rate, mode_rate)
        # Every child inherits its parent's objective history and ``_relax``
        # accepts only non-increasing proposals.  The maximum mode energy is
        # therefore a real aggregate Lyapunov value; do not cosmetically clamp
        # telemetry to the previous persisted scalar.
        step_energy = max(mode_energies, default=last_energy)
        if step_energy > last_energy + 1e-8:
            raise RuntimeError("FIELD_OBJECTIVE_INCREASE")
        frontier_ids = set(current_bodies)
        frontier_hash = _hash(tuple(sorted(selected_cells)), tuple(sorted(frontier_ids)))
        coverage = min(step_coverage, default=1.0)
        frontiers.append(
            FrontierSnapshot(
                step,
                tuple(sorted(selected_cells)),
                tuple(sorted(frontier_ids)),
                tuple(sorted(newly_opened)),
                tuple(sorted(previous_frontier - frontier_ids)),
                float(coverage),
                frontier_hash,
            )
        )
        trace.append(
            EquilibriumStep(
                step,
                float(step_energy),
                float(max_residual),
                True,
                float(rate),
                tuple(_public_mode(mode).state_hash for mode in modes),
                frontier_hash,
            )
        )
        frontier_stable = frontier_ids == previous_frontier
        if max_residual <= convergence_residual and frontier_stable and all(mode.stable_steps > 0 for mode in modes):
            stable_steps += 1
        else:
            stable_steps = 0
        previous_frontier = frontier_ids
        last_energy = step_energy
        if stable_steps >= 3:
            break
    candidates = _candidates(index, modes)
    stable = stable_steps >= 3
    certified = stable and coverage >= coverage_threshold and not exhausted
    selected = None
    failure_codes = []
    if exhausted:
        disposition = "incomplete_frontier"
        failure_codes.append("CUMULATIVE_FRONTIER_LIMIT")
    elif not certified:
        disposition = "incomplete_frontier"
        failure_codes.append("UNCERTIFIED_CONVERGENCE_OR_COVERAGE")
    elif not candidates:
        disposition = "unknown"
    else:
        top = candidates[0]
        tied = [item for item in candidates if abs(item.confidence - top.confidence) <= margin_threshold]
        opposing = any(item.semantic_key == top.semantic_key and item.polarity != top.polarity for item in tied)
        if opposing:
            disposition = "ambiguous"
        elif len(tied) > 1:
            disposition = "alternatives"
        elif top.confidence >= confidence_threshold and top.margin >= margin_threshold:
            disposition = "candidate"
            selected = top.unit_id
        else:
            disposition = "ambiguous"
    return FieldEquilibriumResult(
        prompt.prompt_id,
        disposition,
        initial,
        tuple(_public_mode(mode) for mode in modes),
        candidates,
        selected,
        tuple(trace),
        tuple(frontiers),
        (),
        "certified" if certified else "incomplete_frontier",
        tuple(failure_codes),
        (),
    )


__all__ = ["Compatibility", "optimize"]
