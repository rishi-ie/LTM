from __future__ import annotations

import json

import pytest

import ltm_limit_l5.lifecycle as lifecycle_module
from ltm_limit_l5.lifecycle import (
    COMMANDS,
    L5Lifecycle,
    LifecycleError,
    main,
)

SMALL = {
    "development_field_bodies": 12,
    "locked_field_bodies": 12,
    "scale_field_bodies": 32,
    "training_compiler_items": 16,
    "development_compiler_items": 12,
    "locked_compiler_items": 12,
    "primary_locked_queries": 20,
    "stress_queries": 4,
    "decoder_cases": 48,
    "development_queries": 20,
    "compiler_alignment_steps": 2,
    "deterministic_encoder": True,
}


def _through_locked(workspace):
    lifecycle = L5Lifecycle(workspace, limits=SMALL)
    assert lifecycle.model_check()["passed"]
    assert lifecycle.dataset_build()["passed"]
    assert lifecycle.compiler_develop()["passed"]
    assert lifecycle.field_build()["passed"]
    assert lifecycle.equilibrium_develop()["passed"]
    assert lifecycle.calibrate()["passed"]
    assert lifecycle.freeze()["passed"]
    assert lifecycle.locked_suite_build()["passed"]
    return lifecycle


def test_primary_lifecycle_is_offline_separated_and_immutable(tmp_path) -> None:
    lifecycle = _through_locked(tmp_path)
    result = lifecycle.evaluate()

    assert result["passed"]
    assert result["runtime_gold_reads"] == 0
    assert result["runtime_evaluator_process_separation"]
    assert result["runtime_process_id"] != result["evaluator_process_id"]
    access_audit = json.loads(
        (tmp_path / "locked-runtime-access-audit.json").read_text(encoding="utf-8")
    )
    assert access_audit["passed"]
    assert access_audit["lifecycle_import_guarded"]
    assert access_audit["probe_denials"] == 3
    assert access_audit["unexpected_gold_access_denials"] == 0
    assert access_audit["network_probe_denials"] >= 1
    assert access_audit["network_calls"] == 0
    assert (tmp_path / "locked/public/cases.jsonl").exists()
    assert (tmp_path / "locked/evaluator-gold/gold.jsonl").exists()
    public = (tmp_path / "locked/public/cases.jsonl").read_text(encoding="utf-8")
    compiler_public = (tmp_path / "locked/compiler-public/cases.jsonl").read_text(
        encoding="utf-8"
    )
    end_to_end_public = (
        tmp_path / "locked/end-to-end-public/cases.jsonl"
    ).read_text(encoding="utf-8")
    assert "expected_depth" not in public and "required_body_ids" not in public
    assert "should_accept" not in compiler_public
    assert "expected_semantic_key" not in end_to_end_public
    assert '"depth"' not in end_to_end_public
    assert result["compiler_metrics"]["accepted_semantic_precision"] == 1.0
    assert result["end_to_end_metrics"]["accepted_precision"] == 1.0
    assert result["end_to_end_metrics"]["safe_coverage"] >= 0.90
    assert result["end_to_end_metrics"]["unknown_or_alternative_agreement"] == 1.0
    assert result["end_to_end_metrics"]["incorrect_accepted_predictions"] == 0
    assert (tmp_path / "locked-end-to-end-predictions.jsonl").exists()
    with pytest.raises(LifecycleError, match="second locked"):
        lifecycle.evaluate()


def test_execution_history_and_freeze_detect_source_independent_artifact_corruption(tmp_path) -> None:
    lifecycle = _through_locked(tmp_path)
    history = json.loads((tmp_path / "execution-history.json").read_text(encoding="utf-8"))
    assert [item["stage"] for item in history["events"]][-1] == "locked-suite-build"

    (tmp_path / "selected-kernel.pt").write_bytes(b"corrupt")
    with pytest.raises(LifecycleError, match="frozen artifact"):
        lifecycle.evaluate()


def test_run_all_executes_every_measured_panel(tmp_path) -> None:
    lifecycle = L5Lifecycle(tmp_path, limits=SMALL)
    result = lifecycle.run_all()

    assert result["passed"]
    assert result["classification"].startswith("L5-A")
    assert (tmp_path / "stress-results.json").exists()
    assert (tmp_path / "scale-results.json").exists()
    assert (tmp_path / "intervention-results.json").exists()
    assert (tmp_path / "controls.json").exists()
    assert (tmp_path / "verification.json").exists()
    assert result["locked_raw_end_to_end_metrics"]["accepted_precision"] == 1.0
    verification = json.loads(
        (tmp_path / "verification.json").read_text(encoding="utf-8")
    )
    assert verification["end_to_end_replayed_safety_cases"] == 6
    assert verification["evaluator_metric_replay"]


def test_failed_mechanism_gate_still_gets_read_only_verification(
    tmp_path, monkeypatch
) -> None:
    lifecycle = L5Lifecycle(tmp_path, limits=SMALL)
    original = lifecycle_module.run_control_panel

    def failed_panel(*args, **kwargs):
        row = original(*args, **kwargs)
        row["effects"]["full_minus_no_optimization"] = 0.0
        row["mechanism_gates"]["passed"] = False
        return row

    monkeypatch.setattr(lifecycle_module, "run_control_panel", failed_panel)
    result = lifecycle.run_all()

    assert not result["passed"]
    assert result["classification"].startswith("L5-E")
    assert json.loads(
        (tmp_path / "verification.json").read_text(encoding="utf-8")
    )["passed"]


def test_resume_reuses_complete_immutable_runtime_outputs(tmp_path) -> None:
    lifecycle = _through_locked(tmp_path)
    lifecycle._run_compiler_locked()
    compiler_before = (tmp_path / "locked-compiler-predictions.jsonl").read_bytes()

    result = lifecycle.resume()

    assert result["passed"]
    audit = json.loads(
        (tmp_path / "locked-runtime-access-audit.json").read_text(encoding="utf-8")
    )
    assert audit["probe_denials"] == 3
    assert audit["network_probe_denials"] >= 1
    assert audit["network_calls"] == 0
    assert (tmp_path / "locked-compiler-predictions.jsonl").read_bytes() == compiler_before
    with pytest.raises(LifecycleError, match="second locked"):
        lifecycle.evaluate()


def test_freeze_binds_effective_limit_overrides(tmp_path) -> None:
    _through_locked(tmp_path)
    changed = {**SMALL, "maximum_macro_steps": 63}

    with pytest.raises(LifecycleError, match="effective limits"):
        L5Lifecycle(tmp_path, limits=changed).evaluate()


def test_freeze_rechecks_model_and_semantic_dependency_hashes(
    tmp_path, monkeypatch
) -> None:
    dependency = {"semantic.py": "a"}
    model = {"model.safetensors": "a"}
    monkeypatch.setattr(lifecycle_module, "_dependency_hashes", lambda: dict(dependency))
    monkeypatch.setattr(lifecycle_module, "_model_hashes", lambda _root: dict(model))
    lifecycle = _through_locked(tmp_path)

    dependency["semantic.py"] = "b"
    with pytest.raises(LifecycleError, match="semantic dependency"):
        lifecycle._verify_freeze()
    dependency["semantic.py"] = "a"
    model["model.safetensors"] = "b"
    with pytest.raises(LifecycleError, match="MiniLM"):
        lifecycle._verify_freeze()


def test_all_required_commands_are_exposed() -> None:
    assert set(COMMANDS) == {
        "model-check", "dataset-build", "compiler-develop", "field-build",
        "equilibrium-develop", "calibrate", "freeze", "locked-suite-build",
        "evaluate", "stress-evaluate", "scale-evaluate", "intervene", "controls",
        "verify", "report", "resume", "run-all",
    }


def test_cli_reports_stage_order_failure(tmp_path, capsys) -> None:
    assert main(["dataset-build", "--workspace", str(tmp_path), "--offline"]) == 2
    assert "required stage artifact missing" in capsys.readouterr().out
