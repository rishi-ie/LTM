"""Evaluator-owned L7 semantic and numerical oracle; never imports solver."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass

from .dataset import L7Case
from .field import RealityField
from .schemas import EquilibriumResult


@dataclass(frozen=True, slots=True)
class OracleState:
    positive: dict[str, float]
    negative: dict[str, float]
    tension: dict[str, float]
    factors: dict[str, float]


def _applicable(field: RealityField, case: L7Case):
    selected = {}
    for factor in field.applicable(case.public.reality_key, case.public.scope_key, case.public.valid_at):
        key = (factor.reality_key, factor.input_atom_ids, factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key, factor.scope_key)
        selected.setdefault(key, factor)
    return tuple(selected.values())


def solve_oracle(field: RealityField, case: L7Case) -> OracleState:
    """Independent fixed-point calculation using lower/upper-equivalent DAG updates."""
    prompt = case.public
    ids = tuple(atom.atom_id for atom in field.atoms)
    positive = {item: 1.0 if item in prompt.assumption_atom_ids else 0.0 for item in ids}
    negative = dict.fromkeys(ids, 0.0)
    tension = dict.fromkeys(ids, 0.0)
    factors = dict.fromkeys((factor.body_id for factor in _applicable(field, case)), 0.0)
    rows = _applicable(field, case)
    for _ in range(256):
        next_factors = {factor.body_id: min(positive[item] for item in factor.input_atom_ids) for factor in rows}
        grouped: dict[tuple[str, int, str], list[tuple[float, str]]] = defaultdict(list)
        for factor in rows:
            grouped[(factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key)].append((factor.weight * next_factors[factor.body_id], factor.body_id))
        next_positive = {item: 1.0 if item in prompt.assumption_atom_ids else 0.0 for item in ids}
        next_negative = dict.fromkeys(ids, 0.0)
        normalized: dict[tuple[str, int], list[float]] = defaultdict(list)
        for (atom, polarity, _source), values in grouped.items():
            normalized[(atom, polarity)].append(max(value[0] for value in values))
        for (atom, polarity), masses in normalized.items():
            target = 1.0 - math.prod(1.0 - mass for mass in masses)
            (next_positive if polarity > 0 else next_negative)[atom] = target
        next_tension = {item: min(next_positive[item], next_negative[item]) for item in ids}
        delta = max((abs(next_positive[item] - positive[item]) for item in ids), default=0.0)
        positive, negative, tension, factors = next_positive, next_negative, next_tension, next_factors
        if delta <= 1e-12:
            break
    return OracleState(positive, negative, tension, factors)


def certificate(field: RealityField, case: L7Case) -> tuple[str, ...]:
    expected = case.expected.selected_atom_id
    if expected is None:
        return ()
    rows = _applicable(field, case)
    by_input: dict[str, list] = defaultdict(list)
    for factor in rows:
        for item in factor.input_atom_ids:
            by_input[item].append(factor)
    queue = deque((item, ()) for item in case.public.assumption_atom_ids)
    seen = set(case.public.assumption_atom_ids)
    while queue:
        current, path = queue.popleft()
        if current == expected:
            return path
        for factor in by_input[current]:
            if factor.outcome_atom_id not in seen:
                seen.add(factor.outcome_atom_id)
                queue.append((factor.outcome_atom_id, path + (factor.body_id,)))
    return ()


def verify(field: RealityField, case: L7Case, result: EquilibriumResult) -> bool:
    if result.factual_operations:
        return False
    oracle = solve_oracle(field, case)
    states = {state.atom_id: state for state in result.atom_states}
    if any(abs(states[item].positive_activation - oracle.positive[item]) > 1e-10 or abs(states[item].negative_activation - oracle.negative[item]) > 1e-10 for item in states):
        return False
    expected = case.expected
    if expected.disposition == "unknown":
        return result.disposition == "unknown"
    if expected.disposition == "alternatives":
        return result.disposition == "alternatives"
    if result.disposition != "candidate" or result.selected_candidate_id is None:
        return False
    return result.selected_candidate_id.split(":+")[0] == expected.selected_atom_id and bool(certificate(field, case))


def score(field: RealityField, cases: tuple[L7Case, ...], results: tuple[EquilibriumResult, ...]) -> dict[str, object]:
    if len(cases) != len(results):
        raise ValueError("case/result count mismatch")
    checked = tuple(verify(field, case, result) for case, result in zip(cases, results, strict=True))
    accepted = tuple(index for index, result in enumerate(results) if result.disposition in {"candidate", "alternatives"})
    by_family = {family: sum(ok for case, ok in zip(cases, checked, strict=True) if case.expected.family == family) / max(1, sum(case.expected.family == family for case in cases)) for family in sorted({case.expected.family for case in cases})}
    by_depth = {str(depth): sum(ok for case, ok in zip(cases, checked, strict=True) if case.expected.depth == depth) / max(1, sum(case.expected.depth == depth for case in cases)) for depth in range(1, 21)}
    return {
        "cases": len(cases),
        "exactness": sum(checked) / len(cases),
        "accepted_precision": sum(checked[index] for index in accepted) / len(accepted) if accepted else 1.0,
        "incorrect_accepted": sum(not checked[index] for index in accepted),
        "families": by_family,
        "depth": by_depth,
        "independent_equilibrium_agreement": sum(checked) / len(cases),
        "accepted_energy_increases": sum(any(not step.accepted for step in result.trajectory) for result in results),
    }
