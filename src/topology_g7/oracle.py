from __future__ import annotations

import numpy as np

from .energy import factors_for, index, weight
from .optimize import admissible
from .schemas import ReconciliationProblem


def _quadratic(problem: ReconciliationProblem, alternative_id: str | None) -> tuple[np.ndarray, np.ndarray, float]:
    """Construct the independent exact quadratic used by locked G7 cases.

    Coupling/certainty are implemented by the runtime but intentionally absent
    from generated locked cases because their hinge/product forms are not
    quadratic. This keeps the oracle mathematically independent and exact.
    """
    n = len(problem.soft_variables); hessian = np.zeros((n, n)); linear = np.zeros(n); constant = 0.0; positions = index(problem)
    for factor in factors_for(problem, alternative_id):
        if factor.factor_type not in {"evidence", "preference", "reference", "branch", "uncertainty"}:
            raise ValueError("nonquadratic factor in quadratic oracle")
        pos = positions[factor.variable_ids[0]]; w = weight(factor); target = factor.target_values[0]
        hessian[pos, pos] += 2 * w; linear[pos] += 2 * w * target; constant += w * target * target
    return hessian, linear, constant


def _solve_simplex(diagonal: np.ndarray, linear: np.ndarray) -> np.ndarray:
    # Enumerate nonempty faces; this is exact for diagonal positive quadratic.
    best: tuple[float, np.ndarray] | None = None; size = len(diagonal)
    for mask in range(1, 1 << size):
        active = [i for i in range(size) if mask & (1 << i)]; inv = 1.0 / diagonal[active]
        lam = (sum(linear[i] / diagonal[i] for i in active) - 1.0) / sum(inv)
        candidate = np.zeros(size)
        candidate[active] = (linear[active] - lam) / diagonal[active]
        if (candidate[active] < -1e-12).any(): continue
        energy = .5 * float(candidate @ np.diag(diagonal) @ candidate) - float(linear @ candidate)
        if best is None or energy < best[0]: best = (energy, candidate)
    assert best is not None
    return best[1]


def solve_branch(problem: ReconciliationProblem, alternative_id: str | None) -> tuple[np.ndarray, float]:
    hessian, linear, constant = _quadratic(problem, alternative_id); diagonal = np.diag(hessian)
    values = np.divide(linear, diagonal, out=np.zeros_like(linear), where=diagonal > 0)
    positions = index(problem)
    grouped = {variable_id for group in problem.reference_groups for variable_id in group}
    for group in problem.reference_groups:
        ps = [positions[item] for item in group]; values[ps] = _solve_simplex(diagonal[ps], linear[ps])
    for variable in problem.soft_variables:
        if variable.variable_id not in grouped:
            pos = positions[variable.variable_id]; values[pos] = min(variable.upper, max(variable.lower, values[pos]))
    energy = .5 * float(values @ hessian @ values) - float(linear @ values) + constant
    return values, energy


def solve(problem: ReconciliationProblem, settings: dict) -> dict:
    choices = []
    for alternative in admissible(problem):
        values, energy = solve_branch(problem, alternative); choices.append((energy, "" if alternative is None else alternative, alternative, values))
    choices.sort(key=lambda item: (item[0], item[1])); energy, _, selected, values = choices[0]
    retained = tuple(item[2] for item in choices if item[0] - energy <= settings["decision_margin"] and item[2] is not None)
    uncertainty = next(values[index(problem)[variable.variable_id]] for variable in problem.soft_variables if variable.variable_type == "uncertainty")
    if uncertainty >= settings["abstention_threshold"]: disposition = "abstain"
    elif len(retained) > 1: disposition = "clarification_required" if problem.family == "ambiguous_reference" else "resolved_with_tension"
    elif problem.g6_program.family == "exclusion": disposition = "resolved_with_tension"
    else: disposition = "resolved"
    return {"selected_branch": selected, "retained": retained, "values": tuple(float(x) for x in values), "energy": float(energy), "disposition": disposition}
