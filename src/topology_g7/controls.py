from __future__ import annotations

from .energy import weight
from .schemas import ReconciliationProblem


def neutral(problem: ReconciliationProblem) -> dict:
    return {"selected_branch": None, "disposition": "unknown", "state_value": .5}


def highest_weight(problem: ReconciliationProblem) -> dict:
    selected = None
    branch_factors = [item for item in problem.soft_factors if item.alternative_id]
    if branch_factors:
        strongest = max(branch_factors, key=lambda item: (weight(item), item.factor_id)); selected = strongest.alternative_id
    return {"selected_branch": selected, "disposition": "resolved", "state_value": strongest.target_values[0] if branch_factors else .5}


def weighted_average(problem: ReconciliationProblem) -> dict:
    factors = [item for item in problem.soft_factors if item.applicable and item.factor_type in {"evidence", "branch"}]
    numerator = sum(weight(item) * item.target_values[0] for item in factors); denominator = sum(weight(item) for item in factors) or 1
    return {"selected_branch": None, "disposition": "resolved", "state_value": numerator / denominator}


def no_branch(problem: ReconciliationProblem) -> dict:
    return {"selected_branch": None, "disposition": "resolved", "state_value": .5}


def untyped(problem: ReconciliationProblem) -> dict:
    # Deliberately conflates preference/reference/evidence into one average.
    return weighted_average(problem)
