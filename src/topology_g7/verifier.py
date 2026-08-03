from __future__ import annotations

import numpy as np

from topology_g6.engine import execute

from .energy import energy_and_gradient, index
from .schemas import ReconciliationProblem, ReconciliationResult


def values_from(result: ReconciliationResult, problem: ReconciliationProblem) -> np.ndarray:
    all_values = dict(result.final_state.confidence_values)
    all_values.update(dict(result.final_state.preference_values)); all_values.update(dict(result.final_state.reference_values))
    all_values["u:unknown"] = result.final_state.uncertainty
    return np.array([all_values[variable.variable_id] for variable in problem.soft_variables], dtype=np.float64)


def verify(problem: ReconciliationProblem, result: ReconciliationResult, settings: dict) -> tuple[bool, str | None]:
    if execute(problem.g6_program) != result.hard_result: return False, "HARD_STATE_CHANGED"
    values = values_from(result, problem)
    if not np.isfinite(values).all(): return False, "NUMERICAL_FAILURE"
    positions = index(problem)
    for variable in problem.soft_variables:
        value = values[positions[variable.variable_id]]
        if not variable.lower - 1e-12 <= value <= variable.upper + 1e-12: return False, "OUT_OF_RANGE"
    for group in problem.reference_groups:
        if abs(sum(values[positions[item]] for item in group) - 1.0) > 1e-9: return False, "REFERENCE_SIMPLEX"
    energy, _, _ = energy_and_gradient(values, problem, result.selected_branch)
    if abs(energy - result.final_energy) > 1e-8: return False, "ENERGY_MISMATCH"
    if result.disposition == "abstain" and result.final_state.uncertainty < settings["abstention_threshold"]: return False, "UNJUSTIFIED_ABSTENTION"
    if result.selected_branch and result.selected_branch not in {item.alternative_id for item in problem.alternatives}: return False, "INVALID_BRANCH"
    return True, None
