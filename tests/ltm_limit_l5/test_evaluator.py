from __future__ import annotations

import inspect
import math
from dataclasses import replace

from ltm_limit_l5 import evaluator
from ltm_limit_l5.dataset import FAMILIES, build_case
from ltm_limit_l5.experiment import run_runtime_case
from ltm_limit_l5.schemas import EquilibriumCandidate


def _candidate(case, row):
    return EquilibriumCandidate(
        unit_id=row.unit_ids[0],
        semantic_key=row.semantic_key,
        polarity=row.polarity,
        confidence=1.0,
        margin=0.5,
        supporting_body_ids=row.body_ids,
        supporting_source_keys=row.source_keys,
        provenance_ids=row.provenance_ids,
    )


def test_independent_oracle_matches_every_fixture_family() -> None:
    for index, family in enumerate(FAMILIES):
        generated = build_case(index, 1941, family=family)
        assert evaluator.gold_agrees(generated.public, generated.expected), family


def test_same_source_is_deduplicated_and_independent_source_accumulates() -> None:
    generated = build_case(5, 1941, family="weighted_contradiction")
    outcome = evaluator.source_normalized_outcome(generated.public)
    positive = next(item for item in outcome.candidates if item.polarity == 1)
    assert positive.support_mass == 0.9

    repeated = generated.public.bodies[1]
    independent = replace(repeated, independent_source_key="source:independent")
    changed_case = replace(generated.public, bodies=(generated.public.bodies[0], independent, *generated.public.bodies[2:]))
    changed = evaluator.source_normalized_outcome(changed_case)
    changed_positive = next(item for item in changed.candidates if item.polarity == 1)
    assert math.isclose(changed_positive.support_mass, 1.7)


def test_context_gates_and_missing_conjunction_fail_closed() -> None:
    scoped = build_case(8, 1941, family="scope_isolation")
    outcome = evaluator.source_normalized_outcome(scoped.public)
    assert outcome.selected == scoped.expected.selected
    assert all("out_of_scope" not in item.semantic_key for item in outcome.candidates)

    unknown = build_case(9, 1941, family="unknown")
    assert evaluator.source_normalized_outcome(unknown.public).disposition == "unknown"


def test_certificates_are_reconstructed_and_tampering_is_rejected() -> None:
    generated = build_case(2, 1941, family="dependency_2_4")
    oracle = evaluator.source_normalized_outcome(generated.public)
    candidate = _candidate(generated.public, oracle.candidates[0])
    certificate = evaluator.certificate_for(generated.public, candidate)
    assert evaluator.verify_candidate_certificate(generated.public, candidate, certificate)
    assert not evaluator.verify_candidate_certificate(
        generated.public,
        candidate,
        replace(certificate, certificate_hash="0" * 64),
    )


def test_evaluator_has_no_optimizer_dependency() -> None:
    source = inspect.getsource(evaluator)
    assert "from .optimizer" not in source
    assert "import optimizer" not in source


def test_score_results_reports_primary_oracle_and_certification_metrics() -> None:
    generated = (
        build_case(0, 1941, family="one_body"),
        build_case(4, 1941, family="conjunction"),
        build_case(6, 1941, family="balanced_contradiction"),
        build_case(9, 1941, family="unknown", domain="abstract"),
    )
    results = tuple(run_runtime_case(item.public).result for item in generated)
    metrics = evaluator.score_results(
        tuple(item.public for item in generated),
        tuple(item.expected for item in generated),
        results,
    )

    assert metrics["answerable_cases"] == 3
    assert metrics["unsupported_cases"] == 1
    assert metrics["answerable_case_exactness"] == 1.0
    assert metrics["answerable_exactness"] == 1.0
    assert metrics["global_optimum_oracle_agreement"] == 1.0
    assert metrics["global_optimum_agreement"] == 1.0
    assert metrics["energy_nonincrease"] == 1.0
    assert metrics["accepted_energy_increases"] == 0
    assert metrics["coverage_certification"] == 1.0
    assert metrics["convergence_certification"] == 1.0
    assert metrics["frontier_stability"] == 1.0
    assert metrics["certificate_safety"] == 1.0
    assert metrics["candidate_confidence_agreement"] == 1.0
    assert metrics["required_body_frontier_recall"] == 1.0
    assert metrics["certified_answerable_case_exactness"] == 1.0
    assert metrics["ambiguity_unknown_recall"] == 1.0
    assert set(metrics["domain_exactness"]) == {"abstract", "math"}
    assert set(metrics["depth_exactness"]) == {"1", "2"}
    assert metrics["safe_coverage"] == metrics["all_case_exactness"]
    assert "safe_coverage" in metrics["metric_semantics"]


def test_confidence_must_match_full_source_normalized_support() -> None:
    generated = build_case(0, 1941, family="one_body")
    result = run_runtime_case(generated.public).result
    changed_candidate = replace(result.candidates[0], confidence=0.01)
    changed = replace(result, candidates=(changed_candidate,))

    # A proof certificate may remain a valid derivation subset; aggregate source
    # confidence is a separate, independently reconstructed requirement.
    assert evaluator.verify_candidate_certificate(
        generated.public,
        changed_candidate,
        changed.certificates[0],
    )
    assert not evaluator.verify_result(generated.public, changed)
    metrics = evaluator.score_results(
        (generated.public,),
        (generated.expected,),
        (changed,),
    )
    assert metrics["certificate_safety"] == 1.0
    assert metrics["candidate_confidence_agreement"] == 0.0
    assert metrics["all_case_exactness"] == 0.0
    assert metrics["certified_all_case_exactness"] == 0.0


def test_dynamics_and_coverage_metrics_do_not_hide_invalid_trajectories() -> None:
    generated = build_case(0, 1941, family="one_body")
    result = run_runtime_case(generated.public).result
    trajectory = list(result.trajectory)
    trajectory[-1] = replace(
        trajectory[-1],
        energy=trajectory[-2].energy + 1.0,
    )
    frontiers = list(result.frontiers)
    frontiers[-1] = replace(frontiers[-1], coverage_bound=0.50)
    corrupted = replace(result, trajectory=tuple(trajectory), frontiers=tuple(frontiers))
    metrics = evaluator.score_results(
        (generated.public,),
        (generated.expected,),
        (corrupted,),
    )

    # Semantic verification alone remains true, while explicit dynamics gates fail.
    assert metrics["all_case_exactness"] == 1.0
    assert metrics["energy_nonincrease"] == 0.0
    assert metrics["accepted_energy_increases"] == 1
    assert metrics["coverage_certification"] == 0.0
    assert metrics["certified_all_case_exactness"] == 0.0


def test_global_optimum_and_certificate_metrics_are_independent() -> None:
    generated = build_case(5, 1941, family="weighted_contradiction")
    result = run_runtime_case(generated.public).result
    wrong = next(item.unit_id for item in result.candidates if item.polarity == -1)
    wrong_selection = replace(result, selected_candidate_id=wrong)
    wrong_metrics = evaluator.score_results(
        (generated.public,),
        (generated.expected,),
        (wrong_selection,),
    )
    assert wrong_metrics["candidate_set_exactness"] == 1.0
    assert wrong_metrics["certificate_safety"] == 1.0
    assert wrong_metrics["global_optimum_oracle_agreement"] == 0.0
    assert wrong_metrics["all_case_exactness"] == 0.0

    certificate = result.certificates[0]
    corrupted_certificate = replace(certificate, certificate_hash="0" * 64)
    corrupted = replace(
        result,
        certificates=(corrupted_certificate, *result.certificates[1:]),
    )
    certificate_metrics = evaluator.score_results(
        (generated.public,),
        (generated.expected,),
        (corrupted,),
    )
    assert certificate_metrics["global_optimum_oracle_agreement"] == 1.0
    assert certificate_metrics["certificate_safety"] == 0.0
    assert certificate_metrics["all_case_exactness"] == 0.0


def test_score_results_validates_certification_thresholds() -> None:
    generated = build_case(0, 1941, family="one_body")
    result = run_runtime_case(generated.public).result
    for kwargs in (
        {"coverage_threshold": 1.1},
        {"convergence_residual": -1.0},
        {"stability_steps": 0},
        {"energy_tolerance": -1.0},
    ):
        try:
            evaluator.score_results(
                (generated.public,),
                (generated.expected,),
                (result,),
                **kwargs,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid score threshold accepted: {kwargs}")
