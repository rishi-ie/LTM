from __future__ import annotations

from dataclasses import replace

from ltm_limit_l7.dataset import build_cases, build_reality, manifest
from ltm_limit_l7.evaluator import verify
from ltm_limit_l7.field import RealityField
from ltm_limit_l7.solver import SolverOptions, solve


def test_fixed_field_has_no_model_or_consumer_api() -> None:
    field = build_reality()
    assert manifest(field, build_cases(field))["trainable_parameters"] == 0
    assert not hasattr(field, "consumer")


def test_neutral_state_needs_multiple_sweeps_for_deep_path() -> None:
    field, case = build_reality(), build_cases(build_reality())[152]
    full = solve(field, case.public)
    one = solve(field, case.public, options=SolverOptions(one_sweep=True))
    assert full.selected_candidate_id is not None
    assert one.selected_candidate_id != full.selected_candidate_id


def test_prompt_clamps_are_immutable_and_runtime_matches_independent_oracle() -> None:
    field = build_reality()
    case = build_cases(field)[0]
    original = case.public.assumption_atom_ids
    result = solve(field, case.public)
    assert case.public.assumption_atom_ids == original
    assert verify(field, case, result)


def test_source_duplicates_do_not_change_equilibrium() -> None:
    field = build_reality()
    case = next(case for case in build_cases(field) if case.expected.family == "weighted_contradiction")
    original = next(item for item in field.factors if item.body_id == "conflict:negative:0")
    duplicate = RealityField(field.atoms, field.factors + tuple(replace(original, body_id=f"dup:{index}") for index in range(20)))
    assert solve(field, case.public).selected_candidate_id == solve(duplicate, case.public).selected_candidate_id


def test_balanced_contradiction_and_unknown_are_explicit() -> None:
    field = build_reality()
    cases = build_cases(field)
    balanced = next(case for case in cases if case.expected.family == "balanced_alternative")
    unknown = next(case for case in cases if case.expected.family == "unknown")
    assert solve(field, balanced.public).disposition == "alternatives"
    assert solve(field, unknown.public).disposition == "unknown"


def test_partial_conjunction_and_expired_scope_factor_abstain() -> None:
    field = build_reality()
    cases = build_cases(field)
    partial = next(case for case in cases if case.expected.family == "conjunction" and case.expected.disposition == "unknown")
    scoped = next(case for case in cases if case.expected.family == "scope_time")
    assert solve(field, partial.public).disposition == "unknown"
    expired = RealityField(field.atoms, tuple(replace(row, valid_to=6) if row.body_id == "scoped:0" else row for row in field.factors))
    assert solve(expired, scoped.public).disposition == "unknown"


def test_scope_and_reality_are_isolated() -> None:
    field = build_reality()
    case = next(case for case in build_cases(field) if case.expected.family == "counterfactual")
    good = solve(field, case.public)
    wrong = solve(field, replace(case.public, reality_key="standard"))
    assert good.selected_candidate_id is not None
    assert wrong.selected_candidate_id != good.selected_candidate_id
