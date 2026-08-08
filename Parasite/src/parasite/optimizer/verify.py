"""Independent fixed-point verifier; intentionally does not import solver."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass

from parasite.contracts import EquilibriumAtom, EquilibriumFactor


@dataclass(frozen=True, slots=True)
class EquilibriumVerification:
    verified: bool
    certificate: tuple[str, ...]
    supporting_sources: tuple[str, ...]
    opposing_sources: tuple[str, ...]
    failure_code: str | None


def _selected(factors: tuple[EquilibriumFactor, ...], scope_key: str, valid_at: int | None) -> tuple[EquilibriumFactor, ...]:
    chosen = {}
    for factor in factors:
        if factor.scope_key not in {"global", scope_key}:
            continue
        if valid_at is not None and ((factor.valid_from is not None and factor.valid_from > valid_at) or (factor.valid_to is not None and factor.valid_to < valid_at)):
            continue
        key = (factor.input_atom_ids, factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key, factor.scope_key)
        if key not in chosen or factor.weight > chosen[key].weight:
            chosen[key] = factor
    return tuple(chosen.values())


def _oracle(atoms: tuple[EquilibriumAtom, ...], factors: tuple[EquilibriumFactor, ...], assumptions: tuple[str, ...]):
    ids = tuple(atom.atom_id for atom in atoms)
    positive = {item: 1.0 if item in assumptions else 0.0 for item in ids}
    negative = dict.fromkeys(ids, 0.0)
    factor_values = dict.fromkeys((factor.body_id for factor in factors), 0.0)
    for _ in range(512):
        next_factors = {factor.body_id: min(positive[item] for item in factor.input_atom_ids) for factor in factors}
        grouped = defaultdict(list)
        for factor in factors:
            grouped[(factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key)].append(factor.weight * next_factors[factor.body_id])
        normalized = defaultdict(list)
        for (atom, polarity, _source), rows in grouped.items():
            normalized[(atom, polarity)].append(max(rows))
        next_positive = {item: 1.0 if item in assumptions else 0.0 for item in ids}
        next_negative = dict.fromkeys(ids, 0.0)
        for (atom, polarity), masses in normalized.items():
            target = 1.0 - math.prod(1.0 - mass for mass in masses)
            (next_positive if polarity > 0 else next_negative)[atom] = target
        delta = max((abs(next_positive[item] - positive[item]) for item in ids), default=0.0)
        positive, negative, factor_values = next_positive, next_negative, next_factors
        if delta <= 1e-12:
            break
    return positive, negative, factor_values


def _paths(factors: tuple[EquilibriumFactor, ...], assumptions: tuple[str, ...], target: str, polarity: int) -> tuple[str, ...]:
    reachable = set(assumptions)
    parents: dict[str, EquilibriumFactor] = {}
    final: EquilibriumFactor | None = None
    pending = deque(sorted(factors, key=lambda item: item.body_id))
    for _ in range(len(factors) + 1):
        changed = False
        for factor in tuple(pending):
            if all(item in reachable for item in factor.input_atom_ids):
                if factor.outcome_atom_id == target and factor.outcome_polarity == polarity:
                    final = factor
                if factor.outcome_polarity > 0:
                    reachable.add(factor.outcome_atom_id)
                    parents.setdefault(factor.outcome_atom_id, factor)
                pending.remove(factor)
                changed = True
        if not changed:
            break
    if final is None:
        return ()
    certificate: list[str] = [final.body_id]
    stack = list(final.input_atom_ids)
    seen = set()
    while stack:
        atom = stack.pop()
        factor = parents.get(atom)
        if factor is None:
            continue
        if factor.body_id not in seen:
            seen.add(factor.body_id); certificate.append(factor.body_id); stack.extend(factor.input_atom_ids)
    return tuple(reversed(certificate))


def verify_equilibrium(
    atoms: tuple[EquilibriumAtom, ...], factors: tuple[EquilibriumFactor, ...], result, *,
    assumptions: tuple[str, ...], query_expression: str, query_sort: str, scope_key: str, valid_at: int | None,
) -> EquilibriumVerification:
    selected = _selected(factors, scope_key, valid_at)
    positive, negative, _factor_values = _oracle(atoms, selected, assumptions)
    states = {item.atom_id: item for item in result.states}
    if set(states) != {item.atom_id for item in atoms}:
        return EquilibriumVerification(False, (), (), (), "STATE_COVERAGE_MISMATCH")
    if any(abs(states[item].positive - positive[item]) > 1e-10 or abs(states[item].negative - negative[item]) > 1e-10 for item in states):
        return EquilibriumVerification(False, (), (), (), "FIXED_POINT_MISMATCH")
    if result.factual_operations:
        return EquilibriumVerification(False, (), (), (), "FACTUAL_OPERATION_FORBIDDEN")
    if result.disposition in {"unknown", "alternatives"}:
        return EquilibriumVerification(True, (), (), (), None)
    if result.disposition != "candidate" or result.selected_candidate_id is None:
        return EquilibriumVerification(False, (), (), (), "UNVERIFIED_DISPOSITION")
    chosen = next((item for item in result.candidates if item.candidate_id == result.selected_candidate_id), None)
    if chosen is None or chosen.expression != query_expression:
        return EquilibriumVerification(False, (), (), (), "CANDIDATE_MISMATCH")
    certificate = _paths(selected, assumptions, chosen.atom_id, chosen.polarity)
    if not certificate:
        return EquilibriumVerification(False, (), (), (), "DERIVATION_MISSING")
    body_map = {factor.body_id: factor for factor in selected}
    supporting = tuple(sorted({body_map[item].independent_source_key for item in certificate}))
    opposing = tuple(sorted({factor.independent_source_key for factor in selected if factor.outcome_atom_id == chosen.atom_id and factor.outcome_polarity == -chosen.polarity}))
    return EquilibriumVerification(True, certificate, supporting, opposing, None)
