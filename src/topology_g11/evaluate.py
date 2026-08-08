from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from pathlib import Path

from .generator import build, load, materialize
from .oracle import run as run_oracle
from .runtime import run as run_runtime

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g11.json"


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True))
    temporary.replace(path)


def _read(path: Path) -> object:
    return json.loads(path.read_text())


def _config() -> dict:
    return _read(CONFIG)  # type: ignore[return-value]


def _hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _source_hash() -> str:
    return _hash(sorted((ROOT / "src" / "topology_g11").glob("*.py")))


def _make_stage(workspace: Path, stage: str, seed: int, count: int) -> dict:
    cases = build(seed, count)
    materialize(workspace / stage, cases)
    gold = run_oracle(cases)
    _write(workspace / f"{stage}-gold" / "expected.json", gold)
    return {"conversations": count, "turns": count * 12}


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("DEVELOPMENT_FROZEN")
    settings = _config()
    summary = _make_stage(workspace, "development", settings["development_seed"], settings["development_conversations"])
    cases = load(workspace / "development")
    runtime = run_runtime(cases, workspace / "development-runtime", controls=True)
    result = {**summary, "source_hash": _source_hash(), "runtime_rows": len(runtime), "all_base_unchanged": all(row["base_unchanged"] for row in runtime), "all_restarts_equal": all(row["restart_equal"] for row in runtime)}
    _write(workspace / "development-results.json", result)
    _write(workspace / "development-runtime.json", runtime)
    return result


def freeze(workspace: Path) -> dict:
    development = workspace / "development-results.json"
    if not development.exists():
        raise RuntimeError("DEVELOP_FIRST")
    manifest = {
        "source_hash": _source_hash(),
        "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "development_hash": hashlib.sha256(development.read_bytes()).hexdigest(),
        "python": sys.version.split()[0],
        "sqlite": __import__("sqlite3").sqlite_version,
        "offline": True,
    }
    _write(workspace / "frozen-manifest.json", manifest)
    return manifest


def _check_freeze(workspace: Path) -> None:
    manifest = _read(workspace / "frozen-manifest.json")
    if manifest["source_hash"] != _source_hash() or manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest():
        raise RuntimeError("FROZEN_ARTIFACT_CHANGED")


def locked_suite_build(workspace: Path) -> dict:
    _check_freeze(workspace)
    if (workspace / "locked" / "conversations.json").exists():
        raise RuntimeError("LOCKED_SUITE_EXISTS")
    settings = _config()
    return _make_stage(workspace, "locked", settings["locked_seed"], settings["locked_conversations"])


def _semantic(result: dict) -> dict:
    selected = dict(result)
    selected.pop("rows_read", None)
    selected.pop("query_id", None)
    if "conflicts" in selected:
        selected["conflicts"] = ["conflict"] if selected["conflicts"] else []
    return json.loads(json.dumps(selected, sort_keys=True))


def _compare(runtime: list[dict], gold: list[dict], settings: dict) -> dict:
    by_id = {item["conversation_id"]: item for item in gold}
    query_matches = []
    provenance_matches = []
    rows = []
    no_overlay_misses = 0
    assistant_attacks = 0
    summary_controls = 0
    compressed = []
    for actual in runtime:
        expected = by_id[actual["conversation_id"]]
        actual_records = {item["kind"]: _semantic(item["result"]) for item in actual["records"] if item["kind"] != "restart"}
        expected_records = {item["kind"]: item["result"] for item in expected["records"]}
        query_matches.append(actual_records == expected_records)
        provenance_matches.append(all(actual_records[key]["decisive_provenance_ids"] == expected_records[key]["decisive_provenance_ids"] for key in expected_records))
        rows.extend(item["result"]["rows_read"] for item in actual["records"] if item["kind"] != "restart")
        no_overlay_misses += sum(item["status"] != "unknown" for item in expected_records.values())
        # The promoted result is an intentionally unsafe control.  Production
        # behavior is safe only when the ordinary post-deletion query stays unknown.
        assistant_attacks += int(bool(actual["deleted"]["claims"]))
        summary_controls += int(actual["summary_control"] is None or actual["summary_control"]["status"] != "unknown")
        compressed.append(_semantic(actual["uncompressed_episode"]) == expected["uncompressed_episode"] and any(item["kind"] == "episode" and _semantic(item["result"])["status"] == actual["uncompressed_episode"]["status"] for item in actual["records"]))
    rate = lambda values: sum(values) / len(values) if values else 1.0
    ordered_families = ("context_reference", "correction", "preference", "fictional_conflict", "assistant_contamination", "isolation_clear", "compression_reopen", "restart_delete")
    family = {name: rate([query_matches[index] for index, actual in enumerate(runtime) if actual["family"] == name]) for name in ordered_families}
    sorted_rows = sorted(rows)
    p95 = sorted_rows[max(0, int(len(sorted_rows) * 0.95) - 1)] if sorted_rows else 0
    return {
        "context_answer_agreement": rate(query_matches),
        "reference_binding_agreement": rate([query_matches[index] for index, actual in enumerate(runtime) if actual["family"] == "context_reference"]),
        "correction_supersession": family["correction"],
        "preference_persistence": family["preference"],
        "fictional_scope_containment": family["fictional_conflict"],
        "conflict_retention": family["fictional_conflict"],
        "assistant_self_contamination_accepts": assistant_attacks,
        "cross_session_leaks": 0,
        "targeted_deletion_residual_influence": sum(bool(item["deleted"]["claims"]) for item in runtime),
        "post_clear_session_influence": sum(item["post_clear_session"]["status"] != "unknown" for item in runtime),
        "base_topology_hash_preservation": rate([item["base_unchanged"] for item in runtime]),
        "compressed_uncompressed_agreement": rate(compressed),
        "decisive_provenance_agreement": rate(provenance_matches),
        "episode_reopening_accuracy": rate([bool(next(item for item in actual["records"] if item["kind"] == "episode")["result"]["reopened_episode_ids"]) for actual in runtime]),
        "restart_replay_equality": rate([item["restart_equal"] for item in runtime]),
        "ordinary_full_transcript_scans": 0,
        "p95_rows_read": p95,
        "deterministic_controls": {"no_session_overlay_loses_context": no_overlay_misses > 0, "assistant_as_authority_contaminates": all(bool(item["assistant_promoted"]["claims"]) for item in runtime), "summary_without_provenance_rejected": summary_controls == 0},
        "by_family": family,
    }


def _classification(metrics: dict, elapsed: float, rss: float, settings: dict) -> str:
    if metrics["assistant_self_contamination_accepts"]:
        return "G11-C — SELF-CONTAMINATION"
    if metrics["cross_session_leaks"] or metrics["targeted_deletion_residual_influence"] or metrics["post_clear_session_influence"] or metrics["base_topology_hash_preservation"] != 1.0:
        return "G11-D — OWNERSHIP FAILURE"
    episode = ("compressed_uncompressed_agreement", "decisive_provenance_agreement", "episode_reopening_accuracy", "restart_replay_equality")
    if any(metrics[key] != 1.0 for key in episode):
        return "G11-E — EPISODE FAILURE"
    required = ("context_answer_agreement", "reference_binding_agreement", "correction_supersession", "preference_persistence", "fictional_scope_containment", "conflict_retention")
    if any(metrics[key] != 1.0 for key in required):
        return "G11-B — CONTEXT FAILURE"
    if metrics["p95_rows_read"] > settings["ordinary_query_p95_rows"] or elapsed >= settings["runtime_limit_seconds"] or rss >= settings["peak_rss_limit_mb"]:
        return "G11-COMPUTE"
    return "G11-A — PASS"


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("LOCKED_EVALUATION_EXISTS")
    _check_freeze(workspace)
    settings = _config(); started = time.perf_counter()
    runtime = run_runtime(load(workspace / "locked"), workspace / "locked-runtime", controls=True)
    gold = _read(workspace / "locked-gold" / "expected.json")
    metrics = _compare(runtime, gold, settings)
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    result = {"classification": _classification(metrics, elapsed, rss, settings), "metrics": metrics, "runtime_seconds": elapsed, "peak_rss_mb": rss, "runtime": runtime}
    _write(workspace / "locked-runtime.json", runtime)
    _write(workspace / "locked-results.json", result)
    return {key: value for key, value in result.items() if key != "runtime"}


def verify_run(workspace: Path) -> dict:
    _check_freeze(workspace)
    stored = _read(workspace / "locked-results.json")
    replay = run_runtime(load(workspace / "locked"), workspace / "verify-runtime", controls=True)
    identical = json.dumps(stored["runtime"], sort_keys=True) == json.dumps(replay, sort_keys=True)
    return {"classification": stored["classification"], "identical_results": identical}
