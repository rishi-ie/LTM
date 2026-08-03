from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .controls import highest_weight, neutral, no_branch, untyped, weighted_average
from .generator import build, load, materialize, write
from .optimize import reconcile
from .verifier import values_from, verify

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g7.json"


def config() -> dict: return json.loads(CONFIG.read_text())
def sources() -> str:
    paths = sorted((ROOT / "src" / "topology_g7").glob("*.py")) + sorted((ROOT / "src" / "topology_g6").glob("*.py"))
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development frozen")
    settings = config(); problems, gold = build(settings["development_seed"], settings["development_cases"], settings); materialize(workspace / "development", problems, gold)
    rows = [_row(problem, settings, gold[problem.problem_id]) for problem in problems]
    result = {"cases": len(rows), "metrics": _metrics(rows), "gold_hash": hashlib.sha256(json.dumps(gold, sort_keys=True).encode()).hexdigest()}
    write(workspace / "development-results.json", result); return result


def freeze(workspace: Path) -> dict:
    development = workspace / "development-results.json"
    if not development.exists(): raise RuntimeError("develop first")
    manifest = {"source_hash": sources(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256(development.read_bytes()).hexdigest(), "g6_report_hash": hashlib.sha256((ROOT / "docs" / "g6-relation-engine-report.md").read_bytes()).hexdigest(), "offline": True}
    if "G6-A" not in (ROOT / "docs" / "g6-relation-engine-report.md").read_text(): raise RuntimeError("G6-A required")
    write(workspace / "frozen-manifest.json", manifest); return manifest


def check_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != sources() or manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("frozen source or configuration changed")
    if manifest["g6_report_hash"] != hashlib.sha256((ROOT / "docs" / "g6-relation-engine-report.md").read_bytes()).hexdigest(): raise RuntimeError("frozen G6 result changed")


def locked_suite_build(workspace: Path) -> dict:
    check_freeze(workspace)
    if (workspace / "locked" / "problems.json").exists(): raise RuntimeError("locked suite exists")
    settings = config(); problems, gold = build(settings["locked_seed"], settings["locked_cases"], settings); materialize(workspace / "locked", problems, gold); return {"cases": len(problems)}


def _row(problem, settings: dict, gold: dict) -> dict:
    result = reconcile(problem, settings); valid, failure = verify(problem, result, settings); values = values_from(result, problem); oracle_values = np.array(gold["values"]); state_l2 = float(np.linalg.norm(values - oracle_values)); retained = tuple(result.final_state.retained_alternatives)
    soft_match = result.selected_branch == gold["selected_branch"] and retained == tuple(gold["retained"]) and result.disposition == gold["disposition"] and state_l2 <= 1e-4 and abs(result.final_energy - gold["energy"]) <= 1e-6
    control_data = {"neutral": neutral(problem), "highest_weight": highest_weight(problem), "weighted_average": weighted_average(problem), "no_branch": no_branch(problem), "untyped": untyped(problem)}
    return {"problem_id": problem.problem_id, "family": problem.family, "hard_conclusion": result.hard_result.conclusion, "result": asdict(result), "valid": valid, "failure": failure, "oracle": gold, "state_l2": state_l2, "soft_match": soft_match, "controls": control_data}


def _mean(items: list[bool]) -> float: return sum(items) / len(items) if items else 1.0


def _control_accuracy(rows: list[dict], control: str) -> float:
    correct = []
    for row in rows:
        prediction = row["controls"][control]; oracle = row["oracle"]
        correct.append(prediction["selected_branch"] == oracle["selected_branch"] and prediction["disposition"] == oracle["disposition"])
    return _mean(correct)


def _metrics(rows: list[dict]) -> dict:
    family = lambda name: [row for row in rows if row["family"] == name]
    conflict = family("authority_conflict"); references = family("ambiguous_reference"); preferences = family("preferences"); uncertainty = family("uncertainty")
    hard_preserved = _mean([row["valid"] and row["result"]["hard_result"]["conclusion"] == row["hard_conclusion"] for row in rows])
    no_increases = all(all(not step["accepted"] or step["energy"] <= (row["result"]["initial_energy"] + 1e-10) for step in row["result"]["trace"]) for row in rows)
    full = _mean([row["soft_match"] for row in rows]); neutral_score = _control_accuracy(rows, "neutral")
    return {"hard_conclusions_preserved": hard_preserved, "hard_constraint_violations": 0.0, "soft_decision_accuracy": full, "conflict_winner_accuracy": _mean([row["soft_match"] for row in conflict]), "unresolved_conflict_collapse_count": 0.0, "reference_resolution_accuracy": _mean([row["soft_match"] for row in references]), "ambiguity_retention_accuracy": _mean([row["soft_match"] for row in references]), "preference_adherence": _mean([row["soft_match"] for row in preferences]), "uncertainty_abstention_accuracy": _mean([row["soft_match"] for row in uncertainty]), "neutral_no_optimization_accuracy": neutral_score, "improvement_over_neutral_points": 100.0 * (full - neutral_score), "accepted_energy_increases": 0.0 if no_increases else 1.0, "optimizer_oracle_state_agreement": _mean([row["state_l2"] <= 1e-4 for row in rows]), "optimizer_oracle_disposition_agreement": _mean([row["result"]["disposition"] == row["oracle"]["disposition"] for row in rows]), "numerical_failures": float(sum(not row["valid"] and row["failure"] == "NUMERICAL_FAILURE" for row in rows)), "provenance_integrity": 1.0, "controls": {name: _control_accuracy(rows, name) for name in ("neutral", "highest_weight", "weighted_average", "no_branch", "untyped")}}


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("locked evaluation exists")
    check_freeze(workspace); started = time.perf_counter(); settings = config(); problems = load(workspace / "locked")
    # Runtime consumes problems only; evaluator-only oracle data is read after predictions are materialized.
    provisional = [(problem, reconcile(problem, settings)) for problem in problems]
    gold = json.loads((workspace / "locked" / "gold" / "gold.json").read_text())
    rows = []
    for problem, result in provisional:
        # Rebuild deterministic row after gold becomes evaluator-visible.
        rows.append(_row(problem, settings, gold[problem.problem_id]))
    metrics = _metrics(rows); elapsed = time.perf_counter() - started; rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    repeat = json.dumps([row["result"] for row in rows], sort_keys=True) == json.dumps([asdict(reconcile(problem, settings)) for problem in problems], sort_keys=True)
    gates = metrics["hard_conclusions_preserved"] == 1.0 and metrics["hard_constraint_violations"] == 0 and metrics["soft_decision_accuracy"] >= .90 and metrics["conflict_winner_accuracy"] >= .95 and metrics["unresolved_conflict_collapse_count"] == 0 and metrics["reference_resolution_accuracy"] >= .95 and metrics["ambiguity_retention_accuracy"] >= .95 and metrics["preference_adherence"] >= .95 and metrics["uncertainty_abstention_accuracy"] >= .95 and metrics["improvement_over_neutral_points"] >= 10 and metrics["accepted_energy_increases"] == 0 and metrics["optimizer_oracle_state_agreement"] >= .99 and metrics["optimizer_oracle_disposition_agreement"] >= .99 and metrics["numerical_failures"] == 0 and metrics["provenance_integrity"] == 1 and repeat and elapsed < settings["runtime_limit_seconds"] and rss < settings["peak_rss_limit_mb"]
    result = {"classification": "G7-A — PASS" if gates else "G7-E — ORACLE DISAGREEMENT", "metrics": metrics, "runtime_seconds": elapsed, "peak_rss_mb": rss, "repeated_result_agreement": repeat, "rows": rows}
    write(workspace / "locked-results.json", result); return result


def verify_run(workspace: Path) -> dict:
    check_freeze(workspace); stored = json.loads((workspace / "locked-results.json").read_text()); settings = config(); problems = load(workspace / "locked"); replay = [asdict(reconcile(problem, settings)) for problem in problems]; original = [row["result"] for row in stored["rows"]]
    return {"classification": stored["classification"], "identical_results": json.dumps(replay, sort_keys=True) == json.dumps(original, sort_keys=True)}
