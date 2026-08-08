from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import torch

from topology_g213.inference import load_checkpoint

from .calibration import choose_thresholds
from .dataset import build_split, load_gold, load_split
from .evaluate import _exact, passes, score
from .gate import gate_cases

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g2-14.json"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _settings() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _gold_cases(workspace: Path, split: str):
    cases = load_split(workspace / "datasets" / split / "public.jsonl")
    gold = load_gold(workspace / "datasets" / split / "gold.jsonl")
    values = []
    for item in cases:
        value = gold[item.case.source.source_id]
        case = replace(item.case, act=value["act"], action=value["action"], reference_state=value["reference_state"], polarity=value["polarity"], modality=value["modality"], scope_id=value["scope_id"], disposition=value["disposition"], target_id=value.get("target_id"))
        values.append(replace(item, case=case))
    return tuple(values)


def model_check(workspace: Path) -> None:
    from topology_g213.encoder import assert_model_hashes

    checkpoint = ROOT / _settings()["frozen_checkpoint"]
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    _write(workspace / "model-check.json", {"checkpoint_sha256": _hash(checkpoint), "checkpoint_keys": sorted(state), "model_hashes": assert_model_hashes(), "frozen_g213": True})


def dataset_build(workspace: Path) -> None:
    _write(workspace / "dataset-manifest.json", {split: build_split(workspace, split) for split in ("calibration", "locked")})


def calibrate(workspace: Path) -> None:
    model = load_checkpoint(ROOT / _settings()["frozen_checkpoint"])
    cases = _gold_cases(workspace, "calibration")
    thresholds, metrics = choose_thresholds(model, cases, _settings()["gates"])
    _write(workspace / "calibration.json", {"thresholds": thresholds, "metrics": metrics})


def freeze(workspace: Path) -> None:
    destination = workspace / "frozen-manifest.json"
    if destination.exists():
        raise RuntimeError("G2.14_ALREADY_FROZEN")
    calibration = workspace / "calibration.json"
    if not calibration.exists():
        raise RuntimeError("G2.14_CALIBRATION_MISSING")
    checkpoint = ROOT / _settings()["frozen_checkpoint"]
    _write(destination, {"config_sha256": _hash(CONFIG), "checkpoint_sha256": _hash(checkpoint), "calibration_sha256": _hash(calibration), "offline": True})


def locked_suite_build(workspace: Path) -> None:
    if (workspace / "locked-manifest.json").exists():
        raise RuntimeError("G2.14_LOCKED_ALREADY_BUILT")
    root = workspace / "datasets" / "locked"
    _write(workspace / "locked-manifest.json", {"public_sha256": _hash(root / "public.jsonl"), "gold_sha256": _hash(root / "gold.jsonl"), "shard_size": 256, "evaluator_only": True})


def evaluate(workspace: Path) -> dict[str, object]:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("G2.14_LOCKED_EVALUATION_EXISTS")
    model = load_checkpoint(ROOT / _settings()["frozen_checkpoint"])
    cases = _gold_cases(workspace, "locked")
    thresholds = json.loads((workspace / "calibration.json").read_text())["thresholds"]
    results = gate_cases(model, cases, thresholds)
    metrics = score(cases, results)
    ungated_predictions = tuple(result.original_prediction for result in results)
    ungated_cases = tuple(item.case for item in cases)
    # The comparison is computed from the same frozen model, before the gate.
    ungated = {
        "accepted": sum(prediction.disposition == "accept" for prediction in ungated_predictions),
        "incorrect_accepted": sum(prediction.disposition == "accept" and not (prediction.disposition == case.disposition and prediction.act == case.act and prediction.action == case.action and prediction.reference_state == case.reference_state) for case, prediction in zip(ungated_cases, ungated_predictions)),
    }
    confidence_only: list[bool] = []
    margin_only: list[bool] = []
    for gated in results:
        evidence = gated.acceptance_evidence
        prediction = gated.original_prediction
        confidence_only.append(prediction.disposition == "accept" and evidence.minimum_probability >= thresholds["confidence"])
        resolved = all(resolution.disposition == "existing" and resolution.confidence >= thresholds["identity_confidence"] and resolution.margin >= thresholds["identity_margin"] for resolution in evidence.resolutions)
        margin_only.append(prediction.disposition == "accept" and evidence.minimum_margin >= thresholds["margin"] and resolved)
    def control_summary(flags: list[bool]) -> dict[str, object]:
        accepted_indexes = [index for index, flag in enumerate(flags) if flag]
        incorrect = sum(not _exact(item, results[index]) for index, item in enumerate(cases) if index in accepted_indexes)
        return {"accepted": len(accepted_indexes), "incorrect_accepted": incorrect}
    controls = {
        "ungated_frozen_g213": ungated,
        "confidence_threshold_only": control_summary(confidence_only),
        "candidate_margin_and_typed_filter_only": control_summary(margin_only),
        "full_joint_gate": {"accepted": metrics["accepted"], "incorrect_accepted": metrics["incorrect_accepted_predictions"]},
        "attack_expectations": {
            "ambiguous_candidates_clarify": metrics["ambiguity_recall"] == 1.0,
            "cross_session_targets_blocked": metrics["cross_session_targets"] == 0,
            "bounded_candidates": max(len(item.candidates) for item in cases) <= _settings()["max_candidates"],
        },
    }
    result = {"metrics": metrics, "thresholds": thresholds, "ungated": ungated, "controls": controls, "classification": "G2.14-A — SUPPLIED-SPAN CONVERSATIONAL COMPILER PASS" if passes(metrics, _settings()["gates"]) else ("G2.14-B — ACCEPTANCE GATE FAILURE" if metrics["incorrect_accepted_predictions"] else "G2.14-D — SAFE BUT LOW COVERAGE")}
    _write(workspace / "locked-results.json", result)
    _write(workspace / "locked-predictions.json", [asdict(result_item) for result_item in results])
    return result


def lifecycle_evaluate(workspace: Path) -> None:
    if (workspace / "lifecycle-results.json").exists():
        raise RuntimeError("G2.14_LIFECYCLE_EVALUATION_EXISTS")
    result = json.loads((workspace / "locked-results.json").read_text())
    if not result["classification"].startswith("G2.14-A"):
        _write(workspace / "lifecycle-results.json", {"authorized": False, "reason": "compiler gates failed"})
        return
    # G11 remains the independent lifecycle authority; execute a fresh 400-case
    # structured panel only after the acceptance gate passes.
    from topology_g11.evaluate import _compare, _config
    from topology_g11.generator import build
    from topology_g11.oracle import run as run_oracle
    from topology_g11.runtime import run as run_runtime

    cases = build(20261221, 400)
    runtime = run_runtime(cases, workspace / "lifecycle-runtime-r1", controls=True)
    # The independent G11 oracle contains tuples while its JSON runtime
    # contract contains lists. Normalize only the evaluator copy so this
    # adapter does not alter G11 source or semantics.
    oracle = json.loads(json.dumps(run_oracle(cases)))
    metrics = _compare(runtime, oracle, _config())
    _write(workspace / "lifecycle-results.json", {"authorized": True, "cases": 400, "metrics": metrics, "g11_independent_oracle": True})


def report(workspace: Path) -> None:
    result = {}
    for name in ("model-check.json", "dataset-manifest.json", "calibration.json", "locked-results.json", "lifecycle-results.json", "verification.json"):
        path = workspace / name
        if path.exists():
            result[name.removesuffix(".json")] = json.loads(path.read_text())
    _write(workspace / "report.json", result)
    classification = result.get("locked-results", {}).get("classification", "PENDING")
    metrics = result.get("locked-results", {}).get("metrics", {})
    lines = ["# G2.14 — Margin-Gated Conversational Compiler", "", f"**Classification:** **{classification}**", "", "| Metric | Result |", "| --- | ---: |", f"| Accepted precision | `{metrics.get('accepted_precision', 0):.4f}` |", f"| Safe coverage | `{metrics.get('safe_coverage', 0):.4f}` |", f"| All-case exactness | `{metrics.get('all_case_exactness', 0):.4f}` |", f"| Incorrect accepted predictions | `{metrics.get('incorrect_accepted_predictions', 0)}` |", f"| Ambiguity recall | `{metrics.get('ambiguity_recall', 0):.4f}` |", f"| Unique-reference precision | `{metrics.get('unique_reference_precision', 0):.4f}` |"]
    (workspace / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(workspace: Path) -> None:
    required = ("model-check.json", "dataset-manifest.json", "calibration.json", "frozen-manifest.json", "locked-manifest.json", "locked-results.json")
    _write(workspace / "verification.json", {"required_artifacts": {name: (workspace / name).exists() for name in required}, "checkpoint_unchanged": _hash(ROOT / _settings()["frozen_checkpoint"]) == json.loads((workspace / "frozen-manifest.json").read_text())["checkpoint_sha256"]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m topology_g214")
    parser.add_argument("command", choices=("model-check", "dataset-build", "calibrate", "freeze", "locked-suite-build", "evaluate", "lifecycle-evaluate", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = args.workspace
    if args.command == "model-check":
        model_check(workspace)
    elif args.command == "dataset-build":
        dataset_build(workspace)
    elif args.command == "calibrate":
        calibrate(workspace)
    elif args.command == "freeze":
        freeze(workspace)
    elif args.command == "locked-suite-build":
        locked_suite_build(workspace)
    elif args.command == "evaluate":
        evaluate(workspace)
    elif args.command == "lifecycle-evaluate":
        lifecycle_evaluate(workspace)
    elif args.command == "verify":
        verify(workspace)
    elif args.command == "report":
        report(workspace)
    elif args.command in {"resume", "run-all"}:
        stages = (
            (model_check, workspace / "model-check.json"),
            (dataset_build, workspace / "dataset-manifest.json"),
            (calibrate, workspace / "calibration.json"),
            (freeze, workspace / "frozen-manifest.json"),
            (locked_suite_build, workspace / "locked-manifest.json"),
        )
        for function, marker in stages:
            if marker.exists():
                continue
            try:
                function(workspace)
            except RuntimeError as error:
                if "already" not in str(error).lower():
                    raise
        if not (workspace / "locked-results.json").exists():
            evaluate(workspace)
        if not (workspace / "lifecycle-results.json").exists():
            lifecycle_evaluate(workspace)
        verify(workspace)
        report(workspace)
    return 0
