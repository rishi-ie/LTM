from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

from .generator import build, load, materialize, write_json
from .model import EXPECTED, RuntimeUnavailable, verify_files
from .validator import adversarial, fallback, validate

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g10.json"


def config() -> dict:
    return json.loads(CONFIG.read_text())


def _path(settings: dict) -> Path:
    return ROOT / settings["model_path"]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash() -> str:
    paths = sorted((ROOT / "src" / "topology_g10").glob("*.py")) + [ROOT / "src" / "topology_g9" / "schemas.py"]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def _command(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
    return subprocess.run(arguments, capture_output=True, check=False, env=environment, text=True)


def model_check(workspace: Path) -> dict:
    settings, started = config(), time.perf_counter()
    completed = _command([sys.executable, "-m", "topology_g10.probe", str(_path(settings))])
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {"status": "blocked", "reason": "METAL_UNAVAILABLE:probe_process_failed", "stderr": completed.stderr[-1000:]}
    if completed.returncode != 0:
        result = {"status": "blocked", "reason": "METAL_UNAVAILABLE:probe_process_failed", "stderr": completed.stderr[-1000:]}
    if result.get("status") == "ready" and (not result.get("identical") or result.get("mlx_version") != "0.32.0" or result.get("mlx_lm_version") != "0.31.3"):
        result = {"status": "blocked", "reason": "PREFLIGHT_CONTRACT_FAILED"}
    result["wall_seconds"] = time.perf_counter() - started
    write_json(workspace / "model-check.json", result)
    return result


def _stage(workspace: Path, stage: str, seed: int, cases: int) -> None:
    bundles, gold = build(seed, cases)
    materialize(workspace / stage, bundles, gold)


def _runtime_path(workspace: Path, stage: str) -> Path:
    return workspace / f"{stage}-generations.json"


def _run_runtime(workspace: Path, stage: str, output: Path | None = None) -> dict:
    settings, output = config(), output or _runtime_path(workspace, stage)
    completed = _command([sys.executable, "-m", "topology_g10.worker", "--bundles", str(workspace / stage / "bundles.json"), "--output", str(output), "--model-path", str(_path(settings)), "--max-tokens", str(settings["max_tokens"])])
    if completed.returncode != 0 or not output.exists():
        raise RuntimeUnavailable(f"RUNTIME_WORKER_FAILED:{completed.stderr[-1000:]}")
    return json.loads(output.read_text())


def _rate(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 1.0


def _result_validation(result: dict) -> dict:
    return result["validation"]


def _metric_panel(results: list[dict], bundles: dict[str, object], category: str) -> list[dict]:
    return [result for result in results if bundles[result["bundle_id"]].category == category]


def _metrics(runtime: dict, bundles, gold: dict) -> tuple[dict, dict, list[dict]]:
    by_id = {bundle.bundle_id: bundle for bundle in bundles}
    final = runtime["full"]
    validations = [_result_validation(result) for result in final]
    original_validations = [validate(result["generation"]["original_text"], by_id[result["bundle_id"]]) for result in final]
    expected_claims = [len(gold[result["bundle_id"]]["claims"]) for result in final]
    found_claims = [len(item["extracted_claims"]) - len(item["unauthorized_claims"]) for item in validations]
    categories = {category: _metric_panel(final, by_id, category) for category in {bundle.category for bundle in bundles}}
    panel_full = {result["bundle_id"]: result for result in final if result["bundle_id"] in runtime["control_panel_ids"]}
    controls = runtime["controls"]
    attack_panel = [next(bundle for bundle in bundles if bundle.category == category) for category in sorted(categories)]
    attacks = [{"bundle_id": bundle.bundle_id, "text": text, "accepted": validate(text, bundle).accepted} for bundle in attack_panel for text in adversarial(bundle)]
    no_state = controls["no_state"]
    state_only = controls["state_only"]
    no_state_original = [validate(result["generation"]["original_text"], by_id[result["bundle_id"]]).accepted for result in no_state]
    full_panel_original = [validate(panel_full[result["bundle_id"]]["generation"]["original_text"], by_id[result["bundle_id"]]).accepted for result in no_state]
    state_only_original = [validate(result["generation"]["original_text"], by_id[result["bundle_id"]]).accepted for result in state_only]
    grouped = lambda rows, category: [row for row in rows if by_id[row["bundle_id"]].category == category]
    def acceptance(rows: list[dict]) -> float:
        return _rate([_result_validation(row)["accepted"] for row in rows])
    def direct_acceptance(rows: list[dict]) -> float:
        return _rate([validate(row["generation"]["original_text"], by_id[row["bundle_id"]]).accepted for row in rows])
    state_metrics = {
        "full_panel_direct_acceptance": _rate(full_panel_original),
        "no_state_direct_acceptance": _rate(no_state_original),
        "state_only_direct_acceptance": _rate(state_only_original),
        "full_preference_adherence": acceptance(grouped([panel_full[item] for item in runtime["control_panel_ids"]], "preference")),
        "no_state_preference_adherence": acceptance(grouped(no_state, "preference")),
        "full_conflict_disclosure": acceptance(grouped([panel_full[item] for item in runtime["control_panel_ids"]], "conflict")),
        "no_state_conflict_disclosure": acceptance(grouped(no_state, "conflict")),
        "full_unknown_abstention": acceptance(grouped([panel_full[item] for item in runtime["control_panel_ids"]], "unknown")),
        "no_state_unknown_abstention": acceptance(grouped(no_state, "unknown")),
    }
    direct_accepted = [validation.accepted for validation in original_validations]
    repair_recovered = [not first.accepted and not result["fallback_used"] for first, result in zip(original_validations, final, strict=True)]
    metrics = {
        "authorized_claim_precision": _rate([not item["unauthorized_claims"] for item in validations]),
        "authorized_claim_recall": sum(min(found, expected) for found, expected in zip(found_claims, expected_claims, strict=True)) / max(1, sum(expected_claims)),
        "unsupported_final_claims": float(sum(bool(item["unauthorized_claims"]) for item in validations)),
        "opposite_polarity_final_claims": float(sum(any(claim["polarity"] == "negative" for claim in item["unauthorized_claims"]) for item in validations)),
        "correct_final_disposition": _rate([result["disposition"] == gold[result["bundle_id"]]["disposition"] for result in final]),
        "conflict_disclosure": acceptance(categories["conflict"]),
        "ood_abstention": acceptance(categories["unknown"]),
        "preference_adherence": acceptance(categories["preference"]),
        "ordinary_fallback_rate": _rate([result["fallback_used"] for result in final if by_id[result["bundle_id"]].category != "unknown"]),
        "direct_generation_acceptance": _rate(direct_accepted),
        "repair_recovery_rate": _rate(repair_recovered),
        "raw_unsupported_claims": float(sum(bool(validation.unauthorized_claims) for validation in original_validations)),
        "validator_adversarial_rejection": _rate([not attack["accepted"] for attack in attacks]),
        "rejected_text_exposed": float(sum(not item["accepted"] for item in validations)),
        "fallback_control_acceptance": _rate([validate(fallback(bundle), bundle).accepted for bundle in bundles]),
        "adversarial_cases": float(len(attacks)),
    }
    counterexamples = [result for result, original in zip(final, original_validations, strict=True) if not original.accepted or result["fallback_used"]]
    return metrics, state_metrics, [{"attacks": attacks}, {"counterexamples": counterexamples}]


def _state_benefit(state: dict) -> bool:
    improvements = (
        state["full_panel_direct_acceptance"] - state["no_state_direct_acceptance"],
        state["full_preference_adherence"] - state["no_state_preference_adherence"],
        state["full_conflict_disclosure"] - state["no_state_conflict_disclosure"],
        state["full_unknown_abstention"] - state["no_state_unknown_abstention"],
    )
    return any(delta > 0 for delta in improvements) and min(improvements) >= 0


def _classification(metrics: dict, state: dict, elapsed: float, rss: float, settings: dict) -> str:
    safe = metrics["authorized_claim_precision"] == 1.0 and metrics["unsupported_final_claims"] == 0 and metrics["opposite_polarity_final_claims"] == 0 and metrics["rejected_text_exposed"] == 0 and metrics["validator_adversarial_rejection"] == 1.0
    faithful = metrics["authorized_claim_recall"] >= .95 and metrics["correct_final_disposition"] >= .98 and metrics["conflict_disclosure"] >= .95 and metrics["ood_abstention"] >= .98 and metrics["preference_adherence"] >= .95
    if not safe:
        return "G10-T-C — VALIDATOR FAILURE"
    if not faithful:
        return "G10-T-D — FAITHFULNESS FAILURE"
    if metrics["ordinary_fallback_rate"] >= .10:
        return "G10-T-B — SAFE BUT MODEL-LIMITED"
    if elapsed >= settings["runtime_limit_seconds"] or rss >= settings["peak_rss_limit_mb"]:
        return "G10-COMPUTE"
    if not _state_benefit(state):
        return "G10-T-E — STATE CHANNEL NOT USEFUL"
    return "G10-T-A — TECHNICAL PASS"


def _evaluate_stage(workspace: Path, stage: str, runtime: dict) -> tuple[dict, dict, list[dict]]:
    bundles = load(workspace / stage)
    gold = json.loads((workspace / stage / "gold" / "expected.json").read_text())
    return _metrics(runtime, bundles, gold)


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists() or (workspace / "development-results.json").exists():
        raise RuntimeError("DEVELOPMENT_EXISTS_OR_FROZEN")
    settings = config()
    _stage(workspace, "development", settings["development_seed"], settings["development_cases"])
    preflight = model_check(workspace)
    if preflight["status"] != "ready":
        raise RuntimeUnavailable(preflight.get("reason", "METAL_UNAVAILABLE"))
    runtime = _run_runtime(workspace, "development")
    metrics, state, artifacts = _evaluate_stage(workspace, "development", runtime)
    result = {"bundles": settings["development_cases"], "metrics": metrics, "state_channel": state, "source_hash": source_hash()}
    write_json(workspace / "development-results.json", result)
    write_json(workspace / "development-validator-attacks.json", artifacts[0])
    write_json(workspace / "development-counterexamples.json", artifacts[1])
    return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists() or not _runtime_path(workspace, "development").exists():
        raise RuntimeError("DEVELOPMENT_INFERENCE_REQUIRED")
    settings = config()
    verify_files(_path(settings))
    required = [workspace / "development" / "bundles.json", workspace / "development" / "gold" / "expected.json", _runtime_path(workspace, "development"), workspace / "development-results.json", workspace / "development-validator-attacks.json", workspace / "development-counterexamples.json"]
    manifest = {"source_hash": source_hash(), "config_hash": _hash(CONFIG), "model_hashes": EXPECTED, "offline": True, "control_panel_ids": json.loads(_runtime_path(workspace, "development").read_text())["control_panel_ids"], "development_hashes": {str(path.relative_to(workspace)): _hash(path) for path in required}, "seeds": {"development": settings["development_seed"], "locked": settings["locked_seed"]}}
    write_json(workspace / "frozen-manifest.json", manifest)
    return manifest


def check_freeze(workspace: Path) -> None:
    settings = config()
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != source_hash() or manifest["config_hash"] != _hash(CONFIG):
        raise RuntimeError("FROZEN_ARTIFACT_CHANGED")
    verify_files(_path(settings))
    for name, expected in manifest["development_hashes"].items():
        if _hash(workspace / name) != expected:
            raise RuntimeError(f"DEVELOPMENT_ARTIFACT_CHANGED:{name}")


def locked_suite_build(workspace: Path) -> dict:
    check_freeze(workspace)
    if (workspace / "locked" / "bundles.json").exists():
        raise RuntimeError("LOCKED_SUITE_EXISTS")
    settings = config()
    _stage(workspace, "locked", settings["locked_seed"], settings["locked_cases"])
    return {"bundles": settings["locked_cases"]}


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("LOCKED_EVALUATION_EXISTS")
    check_freeze(workspace)
    settings, started = config(), time.perf_counter()
    preflight = model_check(workspace)
    if preflight["status"] != "ready":
        result = {"classification": "BLOCKED-RUNTIME", "reason": preflight.get("reason", "METAL_UNAVAILABLE"), "metrics": {}, "state_channel": {}, "runtime_seconds": time.perf_counter() - started, "peak_rss_mb": 0.0}
        write_json(workspace / "locked-results.json", result)
        return result
    try:
        runtime = _run_runtime(workspace, "locked")
    except RuntimeUnavailable as error:
        result = {"classification": "BLOCKED-RUNTIME", "reason": str(error), "metrics": {}, "state_channel": {}, "runtime_seconds": time.perf_counter() - started, "peak_rss_mb": 0.0}
        write_json(workspace / "locked-results.json", result)
        return result
    metrics, state, artifacts = _evaluate_stage(workspace, "locked", runtime)
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    result = {"classification": _classification(metrics, state, elapsed, rss, settings), "metrics": metrics, "state_channel": state, "runtime_seconds": elapsed, "peak_rss_mb": rss}
    write_json(workspace / "locked-results.json", result)
    write_json(workspace / "validator-attacks.json", artifacts[0])
    write_json(workspace / "counterexamples.json", artifacts[1])
    return result


def _semantic(runtime: dict) -> dict:
    def record(result: dict) -> dict:
        generation = result["generation"]
        return {"bundle_id": result["bundle_id"], "final_text": result["final_text"], "validation": result["validation"], "fallback_used": result["fallback_used"], "disposition": result["disposition"], "generation": {"method": generation["method"], "original_text": generation["original_text"], "repair_text": generation["repair_text"], "generated_tokens": generation["generated_tokens"]}}
    return {"full": [record(result) for result in runtime["full"]], "controls": {name: [record(result) for result in rows] for name, rows in runtime["controls"].items()}, "control_panel_ids": runtime["control_panel_ids"]}


def verify_run(workspace: Path) -> dict:
    check_freeze(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text())
    if stored["classification"] == "BLOCKED-RUNTIME":
        result = {"classification": "BLOCKED-RUNTIME", "identical_results": True}
        write_json(workspace / "verification.json", result)
        return result
    replay_path = workspace / "verification-generations.json"
    if replay_path.exists():
        raise RuntimeError("VERIFICATION_EXISTS")
    replay = _run_runtime(workspace, "locked", replay_path)
    source = json.loads(_runtime_path(workspace, "locked").read_text())
    metrics, state, _ = _evaluate_stage(workspace, "locked", replay)
    result = {"classification": stored["classification"], "identical_results": _semantic(source) == _semantic(replay), "identical_metrics": stored["metrics"] == metrics and stored["state_channel"] == state}
    write_json(replay_path, replay)
    write_json(workspace / "verification.json", result)
    return result
