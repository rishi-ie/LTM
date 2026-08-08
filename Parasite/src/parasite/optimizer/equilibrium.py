"""Zero-parameter synchronous fixed-law equilibrium solver."""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict, deque
from dataclasses import dataclass

from parasite.contracts import EquilibriumAtom, EquilibriumFactor


@dataclass(frozen=True, slots=True)
class AtomActivation:
    atom_id: str
    positive: float
    negative: float
    tension: float


@dataclass(frozen=True, slots=True)
class EquilibriumCandidate:
    candidate_id: str
    atom_id: str
    expression: str
    polarity: int
    activation: float
    opposing_activation: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    opposing_body_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EquilibriumTraceStep:
    sweep: int
    objective: float
    residual: float
    state_hash: str


@dataclass(frozen=True, slots=True)
class FixedEquilibriumResult:
    disposition: str
    states: tuple[AtomActivation, ...]
    factor_activations: tuple[tuple[str, float], ...]
    candidates: tuple[EquilibriumCandidate, ...]
    selected_candidate_id: str | None
    trajectory: tuple[EquilibriumTraceStep, ...]
    objective: float
    residual: float
    factual_operations: tuple[()] = ()


def _applicable(factor: EquilibriumFactor, scope_key: str, valid_at: int | None) -> bool:
    if factor.scope_key not in {"global", scope_key}:
        return False
    return not (valid_at is not None and ((factor.valid_from is not None and factor.valid_from > valid_at) or (factor.valid_to is not None and factor.valid_to < valid_at)))


def _canonical_factors(factors: tuple[EquilibriumFactor, ...], scope_key: str, valid_at: int | None) -> tuple[EquilibriumFactor, ...]:
    selected: dict[tuple, EquilibriumFactor] = {}
    for factor in factors:
        if not _applicable(factor, scope_key, valid_at):
            continue
        key = (factor.input_atom_ids, factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key, factor.scope_key)
        old = selected.get(key)
        if old is None or factor.weight > old.weight:
            selected[key] = factor
    return tuple(sorted(selected.values(), key=lambda item: item.body_id))


def _targets(
    atoms: tuple[EquilibriumAtom, ...],
    factors: tuple[EquilibriumFactor, ...],
    positive: dict[str, float],
    factor_values: dict[str, float],
) -> tuple[dict[str, float], dict[tuple[str, int], float], dict[str, float], dict[tuple[str, int], tuple[str, ...]]]:
    factor_targets = {factor.body_id: min(positive[item] for item in factor.input_atom_ids) for factor in factors}
    grouped: dict[tuple[str, int, str], list[tuple[float, str]]] = {}
    for factor in factors:
        key = (factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key)
        grouped.setdefault(key, []).append((factor.weight * factor_values[factor.body_id], factor.body_id))
    normalized: dict[tuple[str, int], list[tuple[float, str]]] = {}
    for (atom_id, polarity, _source), rows in grouped.items():
        normalized.setdefault((atom_id, polarity), []).append(max(rows))
    atom_targets = {(atom.atom_id, polarity): 0.0 for atom in atoms for polarity in (-1, 1)}
    supports = {(atom.atom_id, polarity): () for atom in atoms for polarity in (-1, 1)}
    for key, rows in normalized.items():
        atom_targets[key] = 1.0 - math.prod(1.0 - max(0.0, min(1.0, mass)) for mass, _body in rows)
        supports[key] = tuple(sorted(body for _mass, body in rows))
    tensions = {atom.atom_id: min(atom_targets[(atom.atom_id, 1)], atom_targets[(atom.atom_id, -1)]) for atom in atoms}
    return factor_targets, atom_targets, tensions, supports


def _objective(
    positive: dict[str, float], negative: dict[str, float], tension: dict[str, float], factor_values: dict[str, float],
    targets: tuple[dict[str, float], dict[tuple[str, int], float], dict[str, float]], clamps: set[str],
) -> float:
    factor_targets, atom_targets, tension_targets = targets
    value = sum((factor_values[key] - target) ** 2 for key, target in factor_targets.items())
    value += sum(((positive if polarity > 0 else negative)[atom_id] - target) ** 2 for (atom_id, polarity), target in atom_targets.items())
    value += sum((tension[atom_id] - target) ** 2 for atom_id, target in tension_targets.items())
    value += sum((positive[atom_id] - 1.0) ** 2 for atom_id in clamps)
    return value - 2.0 * (sum(positive.values()) + sum(negative.values()))


def _state_hash(positive: dict[str, float], negative: dict[str, float], factors: dict[str, float]) -> str:
    return hashlib.sha256(repr((tuple(sorted(positive.items())), tuple(sorted(negative.items())), tuple(sorted(factors.items())))).encode()).hexdigest()


def _require_acyclic(atom_ids: set[str], factors: tuple[EquilibriumFactor, ...]) -> None:
    outgoing: dict[str, set[str]] = defaultdict(set)
    indegree = dict.fromkeys(atom_ids, 0)
    for factor in factors:
        for source in factor.input_atom_ids:
            if factor.outcome_atom_id not in outgoing[source]:
                outgoing[source].add(factor.outcome_atom_id)
                indegree[factor.outcome_atom_id] += 1
    queue = deque(sorted(atom for atom, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        source = queue.popleft(); visited += 1
        for outcome in sorted(outgoing[source]):
            indegree[outcome] -= 1
            if indegree[outcome] == 0:
                queue.append(outcome)
    if visited != len(atom_ids):
        raise ValueError("CYCLE_UNSUPPORTED")


def solve_equilibrium(
    atoms: tuple[EquilibriumAtom, ...], factors: tuple[EquilibriumFactor, ...], *,
    assumption_atom_ids: tuple[str, ...], query_expression: str, query_sort: str,
    scope_key: str = "global", valid_at: int | None = None, maximum_sweeps: int = 256,
    confidence_threshold: float = 0.5, alternative_margin: float = 0.05,
) -> FixedEquilibriumResult:
    ids = {atom.atom_id for atom in atoms}
    if not set(assumption_atom_ids) <= ids:
        raise ValueError("ASSUMPTION_ATOM_MISSING")
    if any(set(factor.input_atom_ids + (factor.outcome_atom_id,)) - ids for factor in factors):
        raise ValueError("FACTOR_ATOM_MISSING")
    selected = _canonical_factors(factors, scope_key, valid_at)
    _require_acyclic(ids, selected)
    positive = {atom_id: 1.0 if atom_id in assumption_atom_ids else 0.0 for atom_id in ids}
    negative = dict.fromkeys(ids, 0.0)
    tension = dict.fromkeys(ids, 0.0)
    factor_values = dict.fromkeys((factor.body_id for factor in selected), 0.0)
    clamps = set(assumption_atom_ids)
    trajectory: list[EquilibriumTraceStep] = []
    support: dict[tuple[str, int], tuple[str, ...]] = {}
    prior_objective = math.inf
    residual = math.inf
    for sweep in range(maximum_sweeps):
        before = _targets(atoms, selected, positive, factor_values)
        proposed_factors = before[0]
        # Outcome targets read the newly optimized factor block but the old
        # atom snapshot. This crosses one graph edge per synchronous sweep.
        _unused, atom_targets, proposed_tension, support = _targets(atoms, selected, positive, proposed_factors)
        proposed_positive = {atom_id: 1.0 if atom_id in clamps else atom_targets[(atom_id, 1)] for atom_id in ids}
        proposed_negative = {atom_id: atom_targets[(atom_id, -1)] for atom_id in ids}
        after_targets = _targets(atoms, selected, proposed_positive, proposed_factors)[:3]
        before_objective = _objective(positive, negative, tension, factor_values, before[:3], clamps)
        after_objective = _objective(proposed_positive, proposed_negative, proposed_tension, proposed_factors, after_targets, clamps)
        if after_objective > before_objective + 1e-10:
            residual = math.inf
            break
        residual = max(
            max((abs(proposed_positive[key] - positive[key]) for key in ids), default=0.0),
            max((abs(proposed_negative[key] - negative[key]) for key in ids), default=0.0),
        )
        positive, negative, tension, factor_values = proposed_positive, proposed_negative, proposed_tension, proposed_factors
        trajectory.append(EquilibriumTraceStep(sweep, after_objective, residual, _state_hash(positive, negative, factor_values)))
        if residual <= 1e-8 and abs(prior_objective - after_objective) <= 1e-10:
            break
        prior_objective = after_objective
    states = tuple(AtomActivation(atom.atom_id, positive[atom.atom_id], negative[atom.atom_id], tension[atom.atom_id]) for atom in sorted(atoms, key=lambda item: item.atom_id))
    candidates = []
    for atom in atoms:
        if atom.expression != query_expression or atom.sort != query_sort:
            continue
        for polarity, activation, opposing in ((1, positive[atom.atom_id], negative[atom.atom_id]), (-1, negative[atom.atom_id], positive[atom.atom_id])):
            if activation >= confidence_threshold:
                candidates.append(EquilibriumCandidate(
                    f"{atom.atom_id}:{polarity:+d}", atom.atom_id, atom.expression, polarity, activation, opposing,
                    abs(activation - opposing), support.get((atom.atom_id, polarity), ()), support.get((atom.atom_id, -polarity), ()),
                ))
    candidates.sort(key=lambda item: (-item.activation, item.candidate_id))
    converged = bool(trajectory) and residual <= 1e-8
    if not converged:
        disposition, selected_id = "incomplete_equilibrium", None
    elif not candidates:
        disposition, selected_id = "unknown", None
    elif len(candidates) > 1 and abs(candidates[0].activation - candidates[1].activation) <= alternative_margin or candidates[0].margin <= alternative_margin:
        disposition, selected_id = "alternatives", None
    else:
        disposition, selected_id = "candidate", candidates[0].candidate_id
    objective = trajectory[-1].objective if trajectory else math.inf
    return FixedEquilibriumResult(disposition, states, tuple(sorted(factor_values.items())), tuple(candidates), selected_id, tuple(trajectory), objective, residual)
