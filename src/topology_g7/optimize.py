from __future__ import annotations

import numpy as np

from topology_g6.engine import execute

from .energy import energy_and_gradient, index
from .schemas import OptimizationStep, ReconciliationProblem, ReconciliationResult, StructuredState


def project(values: np.ndarray, problem: ReconciliationProblem) -> np.ndarray:
    out = values.copy()
    positions = index(problem)
    for variable in problem.soft_variables:
        pos = positions[variable.variable_id]
        out[pos] = min(variable.upper, max(variable.lower, out[pos]))
    for group in problem.reference_groups:
        ps = [positions[item] for item in group]
        vector = np.maximum(out[ps], 0.0)
        if vector.sum() == 0:
            out[ps] = 1.0 / len(ps)
        else:
            # Euclidean projection onto the unit simplex.
            ordered = np.sort(vector)[::-1]; cssv = np.cumsum(ordered) - 1
            rho = np.nonzero(ordered - cssv / np.arange(1, len(vector) + 1) > 0)[0][-1]
            theta = cssv[rho] / (rho + 1.0); out[ps] = np.maximum(vector - theta, 0.0)
    return out


def _state(problem: ReconciliationProblem, values: np.ndarray, selected: str | None, retained: tuple[str, ...]) -> StructuredState:
    positions = index(problem)
    by_type: dict[str, list[tuple[str, float]]] = {"confidence": [], "preference": [], "reference": []}
    uncertainty = 0.0
    for variable in problem.soft_variables:
        value = float(values[positions[variable.variable_id]])
        if variable.variable_type == "uncertainty": uncertainty = value
        elif variable.variable_type in by_type: by_type[variable.variable_type].append((variable.variable_id, value))
    return StructuredState(tuple(by_type["confidence"]), tuple(by_type["preference"]), tuple(by_type["reference"]), uncertainty, (selected,) if selected else (), retained)


def admissible(problem: ReconciliationProblem) -> tuple[str | None, ...]:
    hard = execute(problem.g6_program)
    active = set(hard.active)
    output: list[str | None] = []
    alternatives = problem.alternatives or (None,)
    for alternative in alternatives:
        if alternative is None or not set(alternative.incompatible_hard_ids) & active: output.append(None if alternative is None else alternative.alternative_id)
    return tuple(output)


def optimize_branch(problem: ReconciliationProblem, alternative_id: str | None, settings: dict) -> tuple[np.ndarray, float, tuple[OptimizationStep, ...], str, int, tuple[tuple[str, float], ...]]:
    values = project(np.array([item.initial for item in problem.soft_variables], dtype=np.float64), problem)
    _, _, _ = energy_and_gradient(values, problem, alternative_id)
    trace: list[OptimizationStep] = []; evaluations = 1; reason = "step_limit"
    for step in range(1, settings["maximum_steps"] + 1):
        current, gradient, _ = energy_and_gradient(values, problem, alternative_id); evaluations += 1
        norm = float(np.linalg.norm(gradient))
        if norm <= settings["convergence_tolerance"]:
            trace.append(OptimizationStep(step, current, norm, True, 0.0)); reason = "gradient_tolerance"; break
        learning_rate = settings["learning_rate"]; accepted = False
        for _ in range(settings["backtracking_retries"]):
            proposed = project(values - learning_rate * gradient, problem)
            proposal_energy, _, _ = energy_and_gradient(proposed, problem, alternative_id); evaluations += 1
            if proposal_energy <= current + settings["accepted_energy_tolerance"]:
                values = proposed; trace.append(OptimizationStep(step, proposal_energy, norm, True, learning_rate)); accepted = True; break
            trace.append(OptimizationStep(step, proposal_energy, norm, False, learning_rate)); learning_rate *= 0.5
        if not accepted:
            reason = "backtracking_exhausted"; break
        if evaluations >= settings["maximum_evaluations"]:
            reason = "evaluation_limit"; break
    final, _, residuals = energy_and_gradient(values, problem, alternative_id)
    return values, final, tuple(trace), reason, evaluations, residuals


def reconcile(problem: ReconciliationProblem, settings: dict) -> ReconciliationResult:
    hard = execute(problem.g6_program); possible = admissible(problem)
    initial_values = project(np.array([item.initial for item in problem.soft_variables], dtype=np.float64), problem)
    initial_energy, _, _ = energy_and_gradient(initial_values, problem, possible[0] if possible else None)
    if not possible:
        empty = _state(problem, initial_values, None, ()); return ReconciliationResult(problem.problem_id, hard, empty, empty, None, "infeasible", initial_energy, initial_energy, (), (), "infeasible", 0)
    candidates = [(alternative, *optimize_branch(problem, alternative, settings)) for alternative in possible]
    candidates.sort(key=lambda item: (item[2], "" if item[0] is None else item[0]))
    selected, values, energy, trace, reason, evaluations, residuals = candidates[0]
    retained = tuple(item[0] for item in candidates if item[2] - energy <= settings["decision_margin"] and item[0] is not None)
    state = _state(problem, values, selected, retained)
    if state.uncertainty >= settings["abstention_threshold"]: disposition = "abstain"
    elif len(retained) > 1: disposition = "clarification_required" if problem.family == "ambiguous_reference" else "resolved_with_tension"
    elif hard.conclusion == "conflict": disposition = "resolved_with_tension"
    else: disposition = "resolved"
    return ReconciliationResult(problem.problem_id, hard, _state(problem, initial_values, None, ()), state, selected, disposition, initial_energy, energy, trace, residuals, reason, evaluations)
