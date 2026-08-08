from __future__ import annotations

import ast
import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .controls import energy_threshold, hash_only, no_coverage, self_critique
from .generator import build, load, materialize, write_json
from .verifier import verify

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g9.json"


def config() -> dict:
    return json.loads(CONFIG.read_text())


def source_hash() -> str:
    paths = sorted((ROOT / "src" / "topology_g9").glob("*.py"))
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def _independent() -> bool:
    forbidden = {"topology_g5", "topology_g6", "topology_g7", "topology_g8"}
    for path in (ROOT / "src" / "topology_g9").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(item.name.split(".")[0] in forbidden for item in node.names): return False
            if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in forbidden: return False
    return True


def _stage(workspace: Path, stage: str, seed: int, pairs: int, settings: dict) -> None:
    bundles, gold = build(seed, pairs, settings)
    materialize(workspace / stage, bundles, gold)


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("DEVELOPMENT_FROZEN")
    settings = config(); _stage(workspace, "development", settings["development_seed"], settings["development_pairs"], settings)
    bundles = load(workspace / "development")
    result = {"bundles": len(bundles), "independent": _independent(), "source_hash": source_hash()}
    write_json(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("DEVELOP_FIRST")
    manifest = {"source_hash": source_hash(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(), "offline": True}
    write_json(workspace / "frozen-manifest.json", manifest); return manifest


def check_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != source_hash() or manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("FROZEN_ARTIFACT_CHANGED")


def locked_suite_build(workspace: Path) -> dict:
    check_freeze(workspace)
    if (workspace / "locked" / "bundles.json").exists(): raise RuntimeError("LOCKED_SUITE_EXISTS")
    settings = config(); _stage(workspace, "locked", settings["locked_seed"], settings["locked_pairs"], settings)
    return {"bundles": settings["locked_pairs"] * 2}


def _runtime_rows(bundles) -> list[dict]:
    """Runtime phase intentionally receives candidate bundles only, never evaluator gold."""
    return [{"bundle_id": bundle.bundle_id, "result": asdict(verify(bundle)), "controls": {"hash_only": asdict(hash_only(bundle)), "energy_threshold": asdict(energy_threshold(bundle)), "no_coverage": asdict(no_coverage(bundle)), "self_critique": asdict(self_critique(bundle))}} for bundle in bundles]


def _metrics(rows: list[dict], gold: dict) -> dict:
    valid = [row for row in rows if gold[row["bundle_id"]]["failure"] is None]
    invalid = [row for row in rows if gold[row["bundle_id"]]["failure"] is not None]
    status = lambda row: row["result"]["status"]
    codes = lambda row: tuple(row["result"]["failure_codes"])
    rate = lambda values: sum(values) / len(values) if values else 1.0
    control_false = {name: rate([row["controls"][name]["status"] != "rejected" for row in invalid]) for name in ("hash_only", "energy_threshold", "no_coverage", "self_critique")}
    coverage = [row for row in invalid if gold[row["bundle_id"]]["failure"] == "INSUFFICIENT_COVERAGE"]
    return {
        "valid_structural_handling": rate([status(row) != "rejected" for row in valid]),
        "valid_status_agreement": rate([status(row) == gold[row["bundle_id"]]["status"] for row in valid]),
        "corrupted_rejection": rate([status(row) == "rejected" for row in invalid]),
        "registered_false_accepts": float(sum(status(row) != "rejected" for row in invalid)),
        "primary_failure_code_agreement": rate([codes(row) == (gold[row["bundle_id"]]["failure"],) for row in invalid]),
        "proof_replay_accuracy": rate(["proof" in row["result"]["checked_invariants"] for row in valid]),
        "source_provenance_integrity": rate(["sources" in row["result"]["checked_invariants"] and "provenance" in row["result"]["checked_invariants"] for row in valid]),
        "scope_time_supersession_accuracy": rate([gold[row["bundle_id"]]["failure"] != "SCOPE_VIOLATION" or codes(row) == ("SCOPE_VIOLATION",) for row in invalid]),
        "hard_factor_recall": rate([gold[row["bundle_id"]]["failure"] != "MISSING_HARD_FACTOR" or codes(row) == ("MISSING_HARD_FACTOR",) for row in invalid]),
        "conflict_disclosure_accuracy": rate([gold[row["bundle_id"]]["failure"] != "UNDISCLOSED_CONFLICT" or codes(row) == ("UNDISCLOSED_CONFLICT",) for row in invalid]),
        "coverage_validation_accuracy": rate([gold[row["bundle_id"]]["failure"] != "INSUFFICIENT_COVERAGE" or codes(row) == ("INSUFFICIENT_COVERAGE",) for row in invalid]),
        "assistant_self_evidence_rejection": rate([gold[row["bundle_id"]]["failure"] != "ASSISTANT_SELF_EVIDENCE" or codes(row) == ("ASSISTANT_SELF_EVIDENCE",) for row in invalid]),
        "soft_state_branch_accuracy": rate([gold[row["bundle_id"]]["failure"] != "SOFT_STATE_MISMATCH" or codes(row) == ("SOFT_STATE_MISMATCH",) for row in invalid]),
        "energy_residual_accuracy": rate(["soft" in row["result"]["checked_invariants"] for row in valid]),
        "control_false_accept_rates": control_false,
        "no_coverage_attack_false_accept": rate([row["controls"]["no_coverage"]["status"] != "rejected" for row in coverage]),
    }


def _classification(metrics: dict, elapsed: float, rss: float, independent: bool, settings: dict) -> str:
    if not independent: return "G9-E — INDEPENDENCE FAILURE"
    if metrics["registered_false_accepts"]: return "G9-B — FALSE ACCEPT"
    if metrics["valid_status_agreement"] != 1.0: return "G9-C — FALSE REJECT"
    required = ("primary_failure_code_agreement", "proof_replay_accuracy", "source_provenance_integrity", "scope_time_supersession_accuracy", "hard_factor_recall", "conflict_disclosure_accuracy", "coverage_validation_accuracy", "assistant_self_evidence_rejection", "soft_state_branch_accuracy", "energy_residual_accuracy")
    if any(metrics[name] != 1.0 for name in required): return "G9-D — DIAGNOSTIC FAILURE"
    if elapsed >= settings["runtime_limit_seconds"] or rss >= settings["peak_rss_limit_mb"]: return "G9-COMPUTE"
    return "G9-A — PASS"


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("LOCKED_EVALUATION_EXISTS")
    check_freeze(workspace); settings = config(); started = time.perf_counter(); bundles = load(workspace / "locked")
    rows = _runtime_rows(bundles)
    gold = json.loads((workspace / "locked" / "gold" / "expected.json").read_text())
    metrics = _metrics(rows, gold); elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    result = {"classification": _classification(metrics, elapsed, rss, _independent(), settings), "metrics": metrics, "runtime_seconds": elapsed, "peak_rss_mb": rss, "rows": rows}
    write_json(workspace / "locked-results.json", result)
    return {key: value for key, value in result.items() if key != "rows"}


def verify_run(workspace: Path) -> dict:
    check_freeze(workspace); stored = json.loads((workspace / "locked-results.json").read_text()); replay = _runtime_rows(load(workspace / "locked"))
    return {"classification": stored["classification"], "identical_results": json.dumps(stored["rows"], sort_keys=True) == json.dumps(replay, sort_keys=True), "independent": _independent()}
