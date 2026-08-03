from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from topology_g7.energy import energy_and_gradient, finite_difference
from topology_g7.generator import build
from topology_g7.optimize import project, reconcile
from topology_g7.oracle import solve
from topology_g7.verifier import verify

SETTINGS = json.loads(Path("configs/topology-g7.json").read_text())


def test_analytic_gradient_matches_finite_difference():
    problem = build(1735, 6, SETTINGS)[0][0]
    values = np.array([variable.initial for variable in problem.soft_variables], dtype=float)
    _, analytic, _ = energy_and_gradient(values, problem, problem.alternatives[0].alternative_id)
    numeric = finite_difference(values, problem, problem.alternatives[0].alternative_id)
    relative = np.max(np.abs(analytic - numeric) / np.maximum(1.0, np.abs(numeric)))
    assert relative < 1e-5


def test_reference_projection_is_a_simplex():
    problem = build(1735, 2, SETTINGS)[0][1]
    values = np.array([3.0, -.2, .5, .5, .5], dtype=float)
    projected = project(values, problem)
    positions = {variable.variable_id: index for index, variable in enumerate(problem.soft_variables)}
    assert projected[positions["r:alpha"]] >= 0
    assert projected[positions["r:beta"]] >= 0
    assert abs(projected[positions["r:alpha"]] + projected[positions["r:beta"]] - 1) < 1e-12


def test_optimizer_preserves_g6_and_matches_oracle():
    problem, _gold = build(20260808, 6, SETTINGS)
    item = problem[5]; result = reconcile(item, SETTINGS); oracle = solve(item, SETTINGS)
    assert verify(item, result, SETTINGS) == (True, None)
    assert result.selected_branch == oracle["selected_branch"]
    assert result.disposition == oracle["disposition"]
    assert result.hard_result.conclusion == "entailed"


def test_genuine_uncertainty_abstains():
    problems, _ = build(20260808, 12, SETTINGS)
    abstaining = next(item for item in problems if item.family == "uncertainty" and item.problem_id.endswith("004"))
    assert reconcile(abstaining, SETTINGS).disposition == "abstain"
