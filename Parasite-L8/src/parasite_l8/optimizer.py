from __future__ import annotations

import hashlib
import math
from collections import defaultdict, deque
from typing import Any

from .contracts import CompiledPolicy, L8Candidate, L8Result, L8Trace
from .policy import policy_values


def _applicable(factor: Any, scope: str, valid_at: int | None) -> bool:
    if factor.scope_key not in {"global", scope}:
        return False
    return not (valid_at is not None and ((factor.valid_from is not None and factor.valid_from > valid_at) or (factor.valid_to is not None and factor.valid_to < valid_at)))


def _acyclic_depths(atom_ids: set[str], factors: tuple[Any, ...], assumptions: set[str]) -> dict[str, int]:
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = dict.fromkeys(atom_ids, 0)
    for factor in factors:
        for source in factor.input_atom_ids:
            outgoing[source].append(factor.outcome_atom_id)
            indegree[factor.outcome_atom_id] += 1
    queue = deque(sorted(item for item, count in indegree.items() if count == 0))
    order: list[str] = []
    while queue:
        item = queue.popleft(); order.append(item)
        for outcome in outgoing[item]:
            indegree[outcome] -= 1
            if indegree[outcome] == 0:
                queue.append(outcome)
    if len(order) != len(atom_ids):
        raise ValueError("CYCLE_UNSUPPORTED")
    depths = {item: 0 for item in atom_ids}
    for atom_id in order:
        if atom_id in assumptions:
            depths[atom_id] = max(depths[atom_id], 0)
        for outcome in outgoing[atom_id]:
            depths[outcome] = max(depths[outcome], depths[atom_id] + 1)
    return depths


def _state_hash(pos: dict[str, float], neg: dict[str, float], factors: dict[str, float]) -> str:
    payload = (tuple(sorted(pos.items())), tuple(sorted(neg.items())), tuple(sorted(factors.items())))
    return hashlib.sha256(repr(payload).encode()).hexdigest()


def _conjunction(values: list[float], mode: Any) -> float:
    if not values:
        return 0.0
    if mode == "all":
        return min(values)
    k = min(len(values), int(mode["k"]))
    return sorted(values, reverse=True)[k - 1]


def _objective(pos: dict[str, float], neg: dict[str, float], tension: dict[str, float], fv: dict[str, float], ft: dict[str, float], at: dict[tuple[str, int], float], tt: dict[str, float], assumptions: set[str]) -> float:
    value = sum((fv[key] - ft[key]) ** 2 for key in fv)
    value += sum(((pos if polarity > 0 else neg)[atom] - target) ** 2 for (atom, polarity), target in at.items())
    value += sum((tension[atom] - target) ** 2 for atom, target in tt.items())
    value += sum((pos[atom] - 1.0) ** 2 for atom in assumptions)
    return value


def solve_policy_equilibrium(
    atoms: tuple[Any, ...], factors: tuple[Any, ...], *, assumptions: tuple[str, ...], query_expression: str,
    query_sort: str, policy: CompiledPolicy, source_classes: dict[str, str] | None = None,
    scope: str = "global", valid_at: int | None = None, maximum_sweeps: int = 256,
    residual_tolerance: float = 1e-8, objective_tolerance: float = 1e-10,
) -> L8Result:
    source_classes = dict(source_classes or {})
    atom_ids = {atom.atom_id for atom in atoms}
    assumption_set = set(assumptions)
    if not assumption_set <= atom_ids:
        raise ValueError("ASSUMPTION_ATOM_MISSING")
    selected: dict[tuple[Any, ...], Any] = {}
    for factor in factors:
        if not _applicable(factor, scope, valid_at):
            continue
        key = (factor.input_atom_ids, factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key, factor.scope_key)
        if key not in selected or factor.weight > selected[key].weight:
            selected[key] = factor
    active = tuple(sorted(selected.values(), key=lambda item: item.body_id))
    depths = _acyclic_depths(atom_ids, active, assumption_set)
    values = policy_values(policy, scope, source_classes)
    required_class = values.get("require_source_class")
    if required_class:
        active = tuple(item for item in active if source_classes.get(item.independent_source_key, item.independent_source_key) == required_class)
    multipliers = values["source_multiplier"]
    decay = float(values["path_decay"])
    source_mass: dict[str, float] = {}
    for item in active:
        source = item.independent_source_key
        source_class = source_classes.get(source, source)
        source_mass[source] = max(source_mass.get(source, 0.0), min(1.0, item.weight * float(multipliers.get(source_class, multipliers.get(source, 1.0))) * decay ** depths[item.outcome_atom_id]))
    positive = {atom: 1.0 if atom in assumption_set else 0.0 for atom in atom_ids}
    negative = dict.fromkeys(atom_ids, 0.0)
    tension = dict.fromkeys(atom_ids, 0.0)
    fv = dict.fromkeys((item.body_id for item in active), 0.0)
    traces: list[L8Trace] = []
    prior = math.inf
    support: dict[tuple[str, int], tuple[str, ...]] = {}
    residual = math.inf
    for sweep in range(maximum_sweeps):
        targets: dict[str, float] = {}
        for item in active:
            targets[item.body_id] = _conjunction([positive[key] for key in item.input_atom_ids], values["conjunction_mode"])
        grouped: dict[tuple[str, int, str], list[tuple[float, str]]] = defaultdict(list)
        for item in active:
            cls = source_classes.get(item.independent_source_key, item.independent_source_key)
            mass = min(1.0, item.weight * float(multipliers.get(cls, multipliers.get(item.independent_source_key, 1.0))) * decay ** depths[item.outcome_atom_id])
            grouped[(item.outcome_atom_id, item.outcome_polarity, item.independent_source_key)].append((mass * targets[item.body_id], item.body_id))
        by_channel: dict[tuple[str, int], list[tuple[float, str]]] = defaultdict(list)
        for (atom, polarity, _source), rows in grouped.items():
            by_channel[(atom, polarity)].append(max(rows))
        at = {(atom.atom_id, polarity): 0.0 for atom in atoms for polarity in (-1, 1)}
        support = {key: tuple(sorted(body for _mass, body in rows)) for key, rows in by_channel.items()}
        for key, rows in by_channel.items():
            at[key] = 1.0 - math.prod(1.0 - max(0.0, min(1.0, mass)) for mass, _body in rows)
        tt = {atom: min(at[(atom, 1)], at[(atom, -1)]) for atom in atom_ids}
        proposed_pos = {atom: 1.0 if atom in assumption_set else at[(atom, 1)] for atom in atom_ids}
        proposed_neg = {atom: at[(atom, -1)] for atom in atom_ids}
        proposed_tension = tt
        obj = _objective(proposed_pos, proposed_neg, proposed_tension, targets, targets, at, tt, assumption_set)
        if obj > prior + objective_tolerance:
            # Fail closed: retain the last certified state rather than accepting an increase.
            break
        residual = max(
            max((abs(proposed_pos[item] - positive[item]) for item in atom_ids), default=0.0),
            max((abs(proposed_neg[item] - negative[item]) for item in atom_ids), default=0.0),
            max((abs(targets[item] - fv[item]) for item in targets), default=0.0),
        )
        positive, negative, tension, fv = proposed_pos, proposed_neg, proposed_tension, targets
        traces.append(L8Trace(sweep, obj, residual, _state_hash(positive, negative, fv)))
        if residual <= residual_tolerance and abs(prior - obj) <= objective_tolerance:
            break
        prior = obj
    candidates: list[L8Candidate] = []
    threshold = float(values["candidate_threshold"])
    min_sources = int(values["minimum_independent_sources"])
    for atom in atoms:
        if atom.expression != query_expression or atom.sort != query_sort:
            continue
        for polarity, activation, opposing in ((1, positive[atom.atom_id], negative[atom.atom_id]), (-1, negative[atom.atom_id], positive[atom.atom_id])):
            sources = tuple(sorted({item.independent_source_key for item in active if item.outcome_atom_id == atom.atom_id and item.outcome_polarity == polarity and item.body_id in support.get((atom.atom_id, polarity), ())}))
            if activation >= threshold and len(sources) >= min_sources:
                candidates.append(L8Candidate(atom.atom_id, atom.expression, polarity, activation, opposing, abs(activation - opposing), support.get((atom.atom_id, polarity), ()), support.get((atom.atom_id, -polarity), ()), sources))
    candidates.sort(key=lambda item: (-item.activation, item.atom_id, item.polarity))
    converged = bool(traces) and residual <= residual_tolerance
    if not converged:
        disposition, selected_id = "incomplete_equilibrium", None
    elif not candidates:
        disposition, selected_id = "unknown", None
    elif len(candidates) > 1 and abs(candidates[0].activation - candidates[1].activation) <= float(values["conflict_margin"]):
        disposition, selected_id = "alternatives", None
    else:
        disposition, selected_id = "candidate", candidates[0].atom_id + f":{candidates[0].polarity:+d}"
    return L8Result(disposition, tuple(candidates), selected_id, tuple(sorted(positive.items())), tuple(sorted(negative.items())), tuple(sorted(tension.items())), tuple(sorted(fv.items())), tuple(traces), traces[-1].objective if traces else math.inf, residual, policy.hash)
