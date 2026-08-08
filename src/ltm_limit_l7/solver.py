"""Synchronous, fixed-law L7 equilibrium solver.

This module never follows an exact input-to-consumer index.  It repeatedly
minimizes one whole factor-graph objective from a neutral state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .field import RealityField
from .schemas import (
    AtomState,
    Candidate,
    EquilibriumResult,
    EquilibriumStep,
    PublicPrompt,
    state_hash,
)


@dataclass(frozen=True, slots=True)
class SolverOptions:
    maximum_sweeps: int = 256
    residual_tolerance: float = 1e-8
    objective_tolerance: float = 1e-10
    one_sweep: bool = False
    no_optimization: bool = False
    no_relational_law: bool = False
    conjunction_max: bool = False
    count_only: bool = False
    no_tension: bool = False
    ignore_reality: bool = False
    shuffle_endpoints: bool = False


def _objective(positive: dict[str, float], negative: dict[str, float], tension: dict[str, float], factors: dict[str, float], targets: tuple[dict[str, float], dict[tuple[str, int], float], dict[str, float]], clamps: set[str]) -> float:
    factor_targets, atom_targets, tension_targets = targets
    total = sum((factors[key] - value) ** 2 for key, value in factor_targets.items())
    total += sum(((positive if polarity > 0 else negative)[atom] - value) ** 2 for (atom, polarity), value in atom_targets.items())
    total += sum((tension[key] - value) ** 2 for key, value in tension_targets.items())
    total += sum((positive[key] - 1.0) ** 2 for key in clamps)
    # Registered relational-satisfaction term.  It makes newly satisfied,
    # source-backed constraints lower the objective rather than treating the
    # next valid hop as a transient energy increase.
    # Atom support is already source-normalized in the atom targets.  Factor
    # counts are intentionally excluded so duplicating one source cannot
    # alter the objective.
    return total - 2.0 * (sum(positive.values()) + sum(negative.values()))


def _targets(field: RealityField, prompt: PublicPrompt, factors: tuple, positive: dict[str, float], negative: dict[str, float], factor_values: dict[str, float], *, options: SolverOptions) -> tuple[dict[str, float], dict[tuple[str, int], float], dict[str, float], dict[tuple[str, int], tuple[str, ...]]]:
    factor_targets: dict[str, float] = {}
    source_groups: dict[tuple[str, int, str], list[tuple[float, str]]] = {}
    for position, factor in enumerate(factors):
        input_values = [positive[item] for item in factor.input_atom_ids]
        complete = (max(input_values) if options.conjunction_max else min(input_values))
        target = 0.0 if options.no_relational_law else complete
        factor_targets[factor.body_id] = target
        outcome = factor.outcome_atom_id
        if options.shuffle_endpoints:
            outcome = field.atoms[(position + 1) % len(field.atoms)].atom_id
        weight = 1.0 if options.count_only else factor.weight
        # Atom targets read the previous factor state.  This prevents a
        # synchronous sweep from silently traversing two graph edges.
        source_groups.setdefault((outcome, factor.outcome_polarity, factor.independent_source_key), []).append((weight * factor_values[factor.body_id], factor.body_id))
    atom_targets = {(atom.atom_id, polarity): 0.0 for atom in field.atoms for polarity in (-1, 1)}
    support_rows = {(atom.atom_id, polarity): () for atom in field.atoms for polarity in (-1, 1)}
    normalized: dict[tuple[str, int], list[tuple[float, str]]] = {}
    for (outcome, sign, _source), rows in source_groups.items():
        normalized.setdefault((outcome, sign), []).append(max(rows))
    for key, rows in normalized.items():
        atom_targets[key] = 1.0 - math.prod(1.0 - max(0.0, min(1.0, amount)) for amount, _body in rows)
        support_rows[key] = tuple(sorted(body for _amount, body in rows))
    tension_targets = {atom.atom_id: 0.0 if options.no_tension else min(atom_targets[(atom.atom_id, 1)], atom_targets[(atom.atom_id, -1)]) for atom in field.atoms}
    return factor_targets, atom_targets, tension_targets, support_rows


def solve(field: RealityField, prompt: PublicPrompt, *, options: SolverOptions | None = None) -> EquilibriumResult:
    options = options or SolverOptions()
    ids = tuple(atom.atom_id for atom in field.atoms)
    positive = {item: 1.0 if item in prompt.assumption_atom_ids else 0.0 for item in ids}
    negative = dict.fromkeys(ids, 0.0)
    tension = dict.fromkeys(ids, 0.0)
    active = _canonical_factors(field.applicable(prompt.reality_key, prompt.scope_key, prompt.valid_at, ignore_reality=options.ignore_reality))
    factor_values = dict.fromkeys((item.body_id for item in active), 0.0)
    trajectories = []
    prior_objective = math.inf
    final_support: dict[tuple[str, int], tuple[str, ...]] = {}
    sweeps = 0 if options.no_optimization else (1 if options.one_sweep else options.maximum_sweeps)
    for sweep in range(sweeps):
        # All targets are derived from the pre-update snapshot.
        factor_targets, atom_targets, tension_targets, final_support = _targets(field, prompt, active, positive, negative, factor_values, options=options)
        proposed_factors = dict(factor_targets)
        # Atom targets deliberately see the new factor block but the old atom
        # block.  This is synchronous block-coordinate descent: one sweep can
        # cross one factor, never an arbitrary hidden route.
        _next_factors, proposed_atom_targets, proposed_tension, _next_support = _targets(field, prompt, active, positive, negative, proposed_factors, options=options)
        proposed_positive = {item: 1.0 if item in prompt.assumption_atom_ids else proposed_atom_targets[(item, 1)] for item in ids}
        proposed_negative = {item: proposed_atom_targets[(item, -1)] for item in ids}
        proposed_targets = _targets(field, prompt, active, proposed_positive, proposed_negative, proposed_factors, options=options)[:3]
        before_targets = (factor_targets, atom_targets, tension_targets)
        before = _objective(positive, negative, tension, factor_values, before_targets, set(prompt.assumption_atom_ids))
        after = _objective(proposed_positive, proposed_negative, proposed_tension, proposed_factors, proposed_targets, set(prompt.assumption_atom_ids))
        # The acyclic generated graphs make full Jacobi steps monotone.  A
        # rejected step is retained as an explicit incomplete equilibrium.
        state_change = max((abs(proposed_positive[item] - positive[item]) for item in ids), default=0.0)
        accepted = after <= before + options.objective_tolerance
        if accepted:
            positive, negative, tension, factor_values = proposed_positive, proposed_negative, proposed_tension, proposed_factors
            objective = after
        else:
            objective = before
        residual = state_change if accepted else 0.0
        trajectories.append(EquilibriumStep(sweep, objective, residual, accepted, state_hash(tuple(sorted(positive.items())), tuple(sorted(negative.items())), tuple(sorted(factor_values.items())))))
        if not accepted:
            break
        if accepted and residual <= options.residual_tolerance and abs(prior_objective - objective) <= options.objective_tolerance:
            break
        prior_objective = objective
    if sweeps == 0:
        factor_targets, atom_targets, tension_targets, final_support = _targets(field, prompt, active, positive, negative, factor_values, options=options)
        objective = _objective(positive, negative, tension, factor_values, (factor_targets, atom_targets, tension_targets), set(prompt.assumption_atom_ids))
        residual = math.inf
    else:
        objective = trajectories[-1].objective
        residual = trajectories[-1].residual
    states = tuple(AtomState(item, positive[item], negative[item], tension[item]) for item in ids)
    candidates = _candidates(field, prompt, positive, negative, tension, final_support)
    disposition, selected = _disposition(candidates, residual, options)
    return EquilibriumResult(prompt.prompt_id, disposition, states, tuple(sorted(factor_values.items())), candidates, selected, tuple(trajectories), objective, residual)


def _canonical_factors(rows: tuple) -> tuple:
    """One source/equivalent outcome is one field constraint, not 20 votes."""
    selected = {}
    for factor in rows:
        key = (factor.reality_key, factor.input_atom_ids, factor.outcome_atom_id, factor.outcome_polarity, factor.independent_source_key, factor.scope_key)
        selected.setdefault(key, factor)
    return tuple(selected.values())


def _candidates(field: RealityField, prompt: PublicPrompt, positive: dict[str, float], negative: dict[str, float], tension: dict[str, float], support: dict[tuple[str, int], tuple[str, ...]]) -> tuple[Candidate, ...]:
    rows = []
    atoms = {atom.atom_id: atom for atom in field.atoms}
    # Query expression is semantic content, not an ID.  Candidate discovery
    # scans active outcome atoms of the requested formal sort only.
    for atom in atoms.values():
        if atom.reality_key != prompt.reality_key or atom.sort != prompt.query_sort or atom.expression != prompt.query_expression:
            continue
        for polarity, activation, opposing in ((1, positive[atom.atom_id], negative[atom.atom_id]), (-1, negative[atom.atom_id], positive[atom.atom_id])):
            if activation >= 0.5:
                rows.append(Candidate(f"{atom.atom_id}:{polarity:+d}", atom.expression, polarity, activation, abs(activation - opposing), opposing, support.get((atom.atom_id, polarity), ()), support.get((atom.atom_id, -polarity), ())))
    return tuple(sorted(rows, key=lambda item: (-item.activation, item.atom_id)))


def _disposition(candidates: tuple[Candidate, ...], residual: float, options: SolverOptions) -> tuple[str, str | None]:
    if options.no_optimization or residual > options.residual_tolerance:
        return "incomplete_equilibrium", None
    if not candidates:
        return "unknown", None
    if options.no_tension:
        return "candidate", candidates[0].atom_id
    if len(candidates) > 1 and abs(candidates[0].activation - candidates[1].activation) <= 0.05:
        return "alternatives", None
    if candidates[0].margin <= 0.05:
        return "alternatives", None
    return "candidate", candidates[0].atom_id
