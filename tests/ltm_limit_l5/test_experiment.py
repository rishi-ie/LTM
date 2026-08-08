from __future__ import annotations

import inspect
import json
from pathlib import Path

from ltm_limit_l5.dataset import FAMILIES, build_case
from ltm_limit_l5.experiment import (
    classification,
    evaluate_observations,
    run_cases,
    run_control_panel,
    run_interventions,
    run_runtime_case,
    wilson_interval,
)


def _panel():
    return tuple(build_case(index, 1941, family=family) for index, family in enumerate(FAMILIES))


def test_runtime_path_verifies_and_decodes_without_gold() -> None:
    generated = _panel()
    observations = run_cases(tuple(item.public for item in generated))
    assert all(item.runtime_error is None for item in observations)
    assert all(item.energy_nonincreasing for item in observations)
    assert all(item.certificate_count_matches for item in observations)
    assert all(item.realization is not None for item in observations)
    source = inspect.getsource(run_runtime_case)
    assert "ExpectedOutcome" not in source
    assert "from .evaluator" not in source


def test_metrics_separate_supplied_contract_optimizer_and_end_to_end() -> None:
    generated = _panel()
    metrics = evaluate_observations(generated, run_cases(tuple(item.public for item in generated)))
    assert metrics["supplied_input_contract"]["rate"] == 1.0
    assert metrics["optimizer_conditional_on_supplied"]["rate"] == 1.0
    assert metrics["end_to_end_from_supplied"]["rate"] == 1.0
    assert metrics["certificate_safety"]["rate"] == 1.0
    assert metrics["decoder_authorization"]["rate"] == 1.0
    assert set(metrics["family"]) == set(FAMILIES)
    assert set(metrics["domain"]) == {"math"}
    assert set(metrics["depth"]) >= {"1", "2", "5", "9"}


def test_controls_and_interventions_are_causally_sensitive() -> None:
    generated = tuple(build_case(index, 1941, family=family) for index, family in enumerate(FAMILIES))
    controls = run_control_panel(generated)
    assert controls["effects"]["full_minus_no_optimization"] > 0
    assert controls["effects"]["multi_minus_single_mode_conflicts"] > 0
    assert controls["effects"]["context_gate_drop"] > 0
    assert controls["effects"]["raw_duplicate_semantic_changes"] == 0
    assert controls["effects"]["full_minus_no_learned_geometry"] == 0.0
    assert controls["effects"]["full_minus_fixed_state"] == 0.0
    assert controls["effects"]["full_minus_random_geometry"] == 0.0
    assert controls["effects"]["fixed_state_movement_rate"] == 0.0
    assert controls["mechanism_gates"]["learned_compatibility_supplied"] is False
    assert controls["mechanism_gates"]["passed"] is False
    interventions = run_interventions(generated)
    assert interventions["relevant_removal_accuracy"]["rate"] == 1.0
    assert interventions["irrelevant_region_invariance"]["rate"] == 1.0
    assert interventions["duplicate_source_invariance"]["rate"] == 1.0
    assert interventions["conjunction_input_sensitivity"]["rate"] == 1.0


def test_wilson_intervals_and_classification_are_mechanical() -> None:
    lower, upper = wilson_interval(20, 20)
    assert 0.83 < lower < 0.85
    assert upper == 1.0
    generated = tuple(
        build_case(index, 1941, family=FAMILIES[index % len(FAMILIES)])
        for index in range(80)
    )
    metrics = evaluate_observations(generated, run_cases(tuple(item.public for item in generated)))
    config = json.loads(Path("configs/ltm-limit-l5.json").read_text())
    assert classification(config, metrics).startswith("L5-B")
    compiler_metrics = {
        "accepted_semantic_precision": 1.0,
        "safe_coverage": 1.0,
        "exact_content_agreement": 1.0,
        "coordinate_recall_at_8": 1.0,
        "incorrect_accepted_compilations": 0,
    }
    assert classification(config, metrics, compiler_metrics=compiler_metrics).startswith("L5-A")
    failed_mechanism = {
        "effects": {"full_minus_no_optimization": 1.0},
        "mechanism_gates": {"passed": False},
    }
    assert classification(
        config,
        metrics,
        controls=failed_mechanism,
        compiler_metrics=compiler_metrics,
    ).startswith("L5-E")
