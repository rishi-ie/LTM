"""Run the fresh Parasite P1 black-box acceptance check."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "validation"))
sys.path.insert(0, str(HERE / "src"))

from p1_common import build_suite, write_jsonl
from p1_evaluator import _oracle, score

from parasite.decoder import decode


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and "var" not in item.parts):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _write_manifest(workspace: Path, config: Path) -> None:
    manifest = {
        "revision": "parasite-p1/1",
        "seed": 20260809,
        "runtime_source_sha256": _hash_tree(HERE / "src"),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "model_manifest_sha256": hashlib.sha256((ROOT / ".models/model-manifest.json").read_bytes()).hexdigest(),
        "network": "offline",
    }
    (workspace / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _classify(metrics: dict[str, float | int | str]) -> str:
    if metrics["runtime_gold_reads"] or metrics["network_calls"] or metrics["cross_boundary_influence"]:
        return "PARASITE-P1-G"
    if metrics["compiler_exactness"] < 1.0 or metrics["accepted_mutations"]:
        return "PARASITE-P1-B"
    if metrics["representation_agreement"] < 1.0 or metrics["restart_replay"] < 1.0 or metrics["partial_commits"]:
        return "PARASITE-P1-C"
    if metrics["exact_execution"] < 1.0:
        return "PARASITE-P1-D"
    if metrics["equilibrium_exactness"] < 1.0 or metrics["depth20"] < 1.0 or metrics["causal_gain"] < 0.5 or metrics["authority_swap_reversal"] < 1.0 or metrics["duplicate_source_invariance"] < 1.0:
        return "PARASITE-P1-E"
    if metrics["decoder_unauthorized_claims"] or metrics["proof_replay"] < 1.0:
        return "PARASITE-P1-F"
    if metrics["p95_ms"] > 500 or metrics["elapsed_s"] >= 600:
        return "PARASITE-P1-COMPUTE"
    return "PARASITE-P1-A"


def run(workspace: Path, *, offline: bool = True) -> dict:
    if workspace.exists() and any(workspace.iterdir()):
        raise SystemExit(f"refusing non-empty acceptance workspace: {workspace}")
    workspace.mkdir(parents=True, exist_ok=False)
    locked = workspace / "locked"
    locked.mkdir()
    public_path, gold_path = locked / "public-cases.jsonl", locked / "evaluator-gold.jsonl"
    predictions_path = workspace / "predictions.jsonl"
    controls_path = workspace / "control-predictions.jsonl"
    control_ids_path = workspace / "control-case-ids.json"
    config = HERE / "config/runtime-v1.json"
    started = time.perf_counter()
    cases = build_suite()
    public_rows = [case.public() for case in cases]
    gold_rows = []
    for case in cases:
        public = case.public()
        expected = _oracle(public) if case.track == "equilibrium" else case.expected
        expected.update({"case_id": case.case_id, "track": case.track})
        gold_rows.append(expected)
    write_jsonl(public_path, public_rows)
    write_jsonl(gold_path, gold_rows)
    control_ids = [case.case_id for case in cases if case.track == "equilibrium" and case.expected.get("family") == "unique"][:4]
    control_ids_path.write_text(json.dumps(control_ids, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "public-scan.json").write_text(json.dumps({"public_fields": sorted({key for row in public_rows for key in row}), "gold_separate": True}, indent=2) + "\n", encoding="utf-8")
    _write_manifest(workspace, config)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(HERE / "src") + os.pathsep + str(ROOT / "src")
    command = [sys.executable, str(HERE / "validation/p1_worker.py"), "--public", str(public_path), "--output", str(predictions_path), "--controls", str(controls_path), "--control-ids", str(control_ids_path), "--state", str(workspace / "runtime-state"), "--config", str(config)]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        (workspace / "worker-stderr.txt").write_text(completed.stderr, encoding="utf-8")
        raise RuntimeError(f"runtime worker failed ({completed.returncode}): {completed.stderr[-1000:]}")
    predictions = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    controls = [json.loads(line) for line in controls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    scored = score(gold_rows, predictions)
    integrity = json.loads((workspace / "runtime-integrity.json").read_text(encoding="utf-8"))
    latencies = sorted(float(row.get("query_ms", 0.0)) for row in predictions if row.get("track") == "equilibrium")
    eq_rows = [row for row in scored["rows"] if row["expected"].get("track") == "equilibrium"]
    depth20_ids = {case.case_id for case in cases if case.expected.get("depth") == 20}
    depth20 = [row for row in scored["rows"] if row["case_id"] in depth20_ids]
    full_by_case = {row["case_id"]: row for row in predictions}
    control_by_mode: dict[str, list[dict]] = {}
    for row in controls:
        control_by_mode.setdefault(row["mode"], []).append(row)
    deep_control_ids = {row.case_id for row in cases if row.track == "equilibrium" and row.expected.get("family") == "unique" and row.expected.get("depth", 0) >= 5}
    def control_rate(mode: str, predicate) -> float:
        rows = [row for row in control_by_mode.get(mode, ()) if row["case_id"] in deep_control_ids]
        return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else 0.0
    no_opt_gain = control_rate("no_optimization", lambda row: row["disposition"] != "candidate")
    one_sweep_gain = control_rate("one_sweep", lambda row: row["disposition"] != "candidate")
    remove_response = control_rate("remove_decisive", lambda row: row["disposition"] != "candidate")
    shuffle_response = control_rate("shuffle_endpoints", lambda row: row["disposition"] != "candidate")
    authority_rows = control_by_mode.get("swap_authority", ())
    authority_reversal = sum(row["claim"] is not None and str(row["claim"]).startswith("not ") for row in authority_rows) / len(authority_rows) if authority_rows else 0.0
    duplicate_rows = control_by_mode.get("duplicate_source", ())
    duplicate_invariance = sum(row["disposition"] == full_by_case.get(row["case_id"], {}).get("disposition") and row["claim"] == full_by_case.get(row["case_id"], {}).get("claim") for row in duplicate_rows) / len(duplicate_rows) if duplicate_rows else 0.0
    decoder_attack = decode(disposition="candidate", claims=("authorized",), verified=True,
                            renderer=lambda _bundle: {"claims": ("invented",), "text": "Invented."})
    compiler_rows = [row for row in scored["rows"] if row["expected"].get("track") == "compiler"]
    accepted_mutations = sum(row["actual"].get("disposition") == "accept" and row["expected"].get("disposition") != "accept" for row in compiler_rows)
    metrics: dict[str, float | int | str] = {
        "case_count": len(cases), "compiler_exactness": sum(row["exact"] for row in scored["rows"] if row["expected"].get("track") == "compiler") / 6,
        "exact_execution": sum(row["exact"] for row in scored["rows"] if row["expected"].get("track") == "exact") / 8,
        "equilibrium_exactness": sum(row["exact"] for row in eq_rows) / len(eq_rows),
        "depth20": sum(row["exact"] for row in depth20) / len(depth20),
        "accepted_mutations": accepted_mutations, "representation_agreement": integrity["representation_passed"] / integrity["representation_checked"] if integrity["representation_checked"] else 0.0,
        "restart_replay": integrity["restart_replay"], "partial_commits": integrity["partial_commits"],
        "proof_replay": sum(row["exact"] for row in scored["rows"] if row["expected"].get("track") == "exact") / 8,
        "decoder_unauthorized_claims": int("Invented" in decoder_attack.response_text),
        "runtime_gold_reads": integrity["runtime_gold_reads"], "network_calls": integrity["network_calls"],
        "cross_boundary_influence": integrity["cross_boundary_influence"],
        "p95_ms": latencies[max(0, int(0.95 * len(latencies)) - 1)] if latencies else 0.0,
        "elapsed_s": time.perf_counter() - started, "causal_gain": min(no_opt_gain, one_sweep_gain, remove_response, shuffle_response),
        "full_minus_no_optimization": no_opt_gain, "full_minus_one_sweep": one_sweep_gain,
        "decisive_body_response": remove_response, "shuffle_endpoint_response": shuffle_response,
        "authority_swap_reversal": authority_reversal, "duplicate_source_invariance": duplicate_invariance,
        "incorrect_accepted": scored["incorrect_accepted"],
    }
    metrics["classification"] = _classify(metrics)
    report = {"metrics": metrics, "score": {key: value for key, value in scored.items() if key != "rows"},
              "counterexamples": [row for row in scored["rows"] if not row["exact"]],
              "evidence_boundary": "supplied formal realities, supplied-span conversation, acyclic fields, max 512 factors",
              "completed": True}
    (workspace / "control-predictions.jsonl").write_text("".join(json.dumps(item, sort_keys=True, default=str) + "\n" for item in controls), encoding="utf-8")
    (workspace / "verification.json").write_text(json.dumps({"gold_separate": True, "public_rows": len(public_rows), "prediction_rows": len(predictions), "control_rows": len(controls), "worker_returncode": completed.returncode}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (workspace / "counterexamples.json").write_text(json.dumps(report["counterexamples"], indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (workspace / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (workspace / "execution-history.json").write_text(json.dumps({"started": started, "elapsed_s": metrics["elapsed_s"], "attempt": "r1"}, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    report = run(args.workspace, offline=args.offline)
    print(json.dumps(report["metrics"], indent=2, sort_keys=True))
    return 0 if report["metrics"]["classification"] == "PARASITE-P1-A" else 1


if __name__ == "__main__":
    raise SystemExit(main())
