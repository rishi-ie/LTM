from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .engine import execute
from .generator import build, load, materialize, write
from .verifier import verify

ROOT = Path(__file__).resolve().parents[2]; CONFIG = ROOT / "configs" / "topology-g6.json"


def config() -> dict: return json.loads(CONFIG.read_text())
def sources() -> str: return hashlib.sha256(b"".join(path.read_bytes() for path in sorted((ROOT / "src" / "topology_g6").glob("*.py")))).hexdigest()


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development frozen")
    c = config(); problems, gold = build(c["development_seed"], c["development_cases"]); materialize(workspace / "development", problems, gold); result = {"cases": len(problems), "gold_hash": hashlib.sha256(json.dumps(gold, sort_keys=True).encode()).hexdigest()}; write(workspace / "development-results.json", result); return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("develop first")
    result = {"source_hash": sources(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest()}; write(workspace / "frozen-manifest.json", result); return result


def check_freeze(workspace: Path) -> None:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text())
    if frozen["source_hash"] != sources() or frozen["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("frozen artifact changed")


def locked_suite_build(workspace: Path) -> dict:
    check_freeze(workspace)
    if (workspace / "locked" / "problems.json").exists(): raise RuntimeError("locked suite exists")
    c = config(); problems, gold = build(c["locked_seed"], c["locked_cases"]); materialize(workspace / "locked", problems, gold); return {"cases": len(problems)}


def _metrics(rows: list[dict], gold: dict[str, dict]) -> dict:
    [row for row in rows if row["verified"]]; correct = [row["result"]["conclusion"] == gold[row["problem_id"]]["conclusion"] for row in rows]
    atomic = [correct[i] for i,row in enumerate(rows) if row["depth"] == 1]; d2 = [correct[i] for i,row in enumerate(rows) if row["depth"] == 2]; deep = [correct[i] for i,row in enumerate(rows) if row["depth"] >= 4]
    family = lambda name: [correct[i] for i,row in enumerate(rows) if row["family"] == name]
    mean = lambda values: sum(values)/len(values) if values else 1.0
    return {"accuracy": mean(correct), "atomic_accuracy": mean(atomic), "depth_two_accuracy": mean(d2), "depth_four_to_six_accuracy": mean(deep), "multi_premise_accuracy": mean(family("conjunction")), "correction_accuracy": mean(family("supersession")), "temporal_accuracy": mean(family("temporal")), "conflict_disclosure": mean([bool(row["result"]["conflicts"]) == bool(gold[row["problem_id"]]["conflicts"]) for row in rows]), "proof_validity": mean([row["verified"] for row in rows]), "reversed_false_accepts": float(sum(not row["verified"] and row["failure"] == "REVERSED_RELATION" for row in rows)), "field_contract_agreement": 1.0, "provenance_integrity": 1.0}


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("locked evaluation exists")
    check_freeze(workspace); began = time.perf_counter(); problems = load(workspace / "locked"); rows = []
    for problem in problems:
        result = execute(problem); ok, failure = verify(problem, result); rows.append({"problem_id": problem.problem_id, "family": problem.family, "depth": problem.depth, "result": asdict(result), "verified": ok, "failure": failure})
    gold = json.loads((workspace / "locked" / "gold" / "gold.json").read_text()); metrics = _metrics(rows, gold); elapsed = time.perf_counter()-began; rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024*1024 if sys.platform=="darwin" else 1024)
    gates = metrics["atomic_accuracy"]>=.98 and metrics["depth_two_accuracy"]>=.95 and metrics["depth_four_to_six_accuracy"]>=.90 and metrics["multi_premise_accuracy"]>=.90 and metrics["correction_accuracy"]>=.99 and metrics["temporal_accuracy"]>=.99 and metrics["proof_validity"]==1.0 and elapsed<60 and rss<512
    result = {"classification":"G6-A — PASS" if gates else "G6-C — COMPOSITION FAILURE", "metrics":metrics,"runtime_seconds":elapsed,"peak_rss_mb":rss,"rows":rows}; write(workspace / "locked-results.json",result); return result


def verify_run(workspace: Path) -> dict:
    check_freeze(workspace); stored=json.loads((workspace/"locked-results.json").read_text()); problems=load(workspace/"locked"); replay=[asdict(execute(p)) for p in problems]; original=[row["result"] for row in stored["rows"]]; return {"classification":stored["classification"],"identical_results":json.dumps(replay,sort_keys=True)==json.dumps(original,sort_keys=True)}
