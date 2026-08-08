from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import sys
from dataclasses import asdict
from pathlib import Path

from .generator import build, load_gold, load_queries, materialize, write_json
from .methods import METHODS
from .public import fetch, split_runtime_and_gold
from .real_pipeline import RealPipeline

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g14.json"


def config() -> dict: return json.loads(CONFIG.read_text())


def source_hash() -> str:
    digest = hashlib.sha256()
    # G14 is frozen together with every adapter it actually invokes. This makes
    # a changed G3–G7/G9 implementation invalidate the locked composition run.
    for package in ("topology_g3", "topology_g4", "topology_g5", "topology_g6", "topology_g7", "topology_g9", "topology_g14"):
        for path in sorted((ROOT / "src" / package).glob("*.py")):
            digest.update(str(path.relative_to(ROOT)).encode()); digest.update(path.read_bytes())
    digest.update(CONFIG.read_bytes()); return digest.hexdigest()


def _rss_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def preflight(workspace: Path) -> dict:
    settings = config(); free = os.statvfs(workspace).f_bavail * os.statvfs(workspace).f_frsize
    output = {"rss_mb": _rss_mb(), "hard_rss_mb": settings["max_rss_mb"], "disk_free_bytes": free, "network": False}
    write_json(workspace / "preflight.json", output); return output


def benchmark_fetch(workspace: Path) -> dict: return fetch(workspace, config()["public_sources"])


def _run(queries, methods=METHODS) -> list[dict]:
    pipeline = RealPipeline(tuple(queries))
    return [asdict(pipeline.run(query, method)) for method in methods for query in queries]


def _gold(path: Path): return load_gold(path)


def _metrics(rows: list[dict], gold) -> dict:
    expected = {item.query_id: item for item in gold}; output = {}
    for method in METHODS:
        values = [row for row in rows if row["method_id"] == method.method_id]
        correct = sum(row["conclusion"] == expected[row["query_id"]].gold for row in values)
        recall = sum(
            1.0 if not expected[row["query_id"]].required_factor_ids else
            len(set(row["trace"]["frontier_factor_ids"]) & set(expected[row["query_id"]].required_factor_ids)) /
            len(expected[row["query_id"]].required_factor_ids)
            for row in values
        ) / len(values)
        output[method.method_id] = {"accuracy": correct / len(values), "required_factor_recall": recall,
            "p95_ms": sorted(row["trace"]["runtime_us"] / 1000 for row in values)[math.ceil(.95 * len(values)) - 1],
            "full_scans": sum(row["trace"]["full_scan"] for row in values)}
    return output


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("DEVELOPMENT_FROZEN")
    root = workspace / "development"
    if (root / "gold" / "outcomes.json").exists(): raise FileExistsError("DEVELOPMENT_EXISTS")
    settings = config(); turns, queries = build(settings["development_seed"], settings["development_conversations"], settings["turns_per_conversation"])
    materialize(root, turns, queries, include_gold=True); rows = _run(load_queries(root)); metrics = _metrics(rows, _gold(root))
    output = {"turns": len(turns), "queries": len(queries), "metrics": metrics, "source_hash": source_hash()}
    write_json(root / "results.json", output); write_json(workspace / "development-results.json", output); return output


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("DEVELOPMENT_REQUIRED")
    sources = workspace / "benchmark-sources" / "manifest.json"
    if not sources.exists(): raise RuntimeError("PUBLIC_SOURCES_REQUIRED")
    manifest = {"source_hash": source_hash(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(),
        "public_sources": json.loads(sources.read_text()), "frozen": True}
    write_json(workspace / "frozen-manifest.json", manifest); return manifest


def _check(workspace: Path) -> dict:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != source_hash() or manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("FROZEN_ARTIFACT_CHANGED")
    return manifest


def locked_suite_build(workspace: Path) -> dict:
    _check(workspace); root = workspace / "locked"
    if (root / "gold" / "outcomes.json").exists(): raise FileExistsError("LOCKED_EXISTS")
    settings = config(); turns, queries = build(settings["locked_seed"], settings["locked_conversations"], settings["turns_per_conversation"])
    materialize(root, turns, queries, include_gold=True)
    public = split_runtime_and_gold(workspace / "benchmark-sources", root / "public")
    output = {"turns": len(turns), "queries": len(queries), "public": public, "source_hash": source_hash()}; write_json(root / "build.json", output); return output


def _bootstrap(full: list[bool], baseline: list[bool], samples: int, seed: int) -> dict:
    import random
    rng = random.Random(seed); deltas = []
    for _ in range(samples):
        indices = [rng.randrange(len(full)) for _ in full]; deltas.append(sum(full[item] - baseline[item] for item in indices) / len(indices))
    deltas.sort(); return {"lower": deltas[int(.025 * samples)], "upper": deltas[int(.975 * samples) - 1]}


def evaluate_core(workspace: Path) -> dict:
    _check(workspace)
    target = workspace / "core-results.json"
    if target.exists(): raise FileExistsError("CORE_EVALUATION_EXISTS")
    gold = _gold(workspace / "locked"); runtime = load_queries(workspace / "locked"); rows = _run(runtime); metrics = _metrics(rows, gold)
    full_rows = [item for item in rows if item["method_id"] == "full_controlled_ltm"]
    rag_rows = [item for item in rows if item["method_id"] == "hybrid_rag"]
    advantage = _bootstrap([item["conclusion"] == gold[index].gold for index, item in enumerate(full_rows)], [item["conclusion"] == gold[index].gold for index, item in enumerate(rag_rows)], config()["bootstrap_samples"], config()["bootstrap_seed"])
    full = metrics["full_controlled_ltm"]; gates = config()["gates"]
    controlled = full["accuracy"] >= gates["controlled_accuracy"] and full["required_factor_recall"] >= gates["required_factor_recall"] and full["p95_ms"] < config()["max_core_p95_ms"] and full["full_scans"] == 0
    demonstrated = (full["accuracy"] - metrics["hybrid_rag"]["accuracy"]) * 100 >= gates["advantage_points"] and advantage["lower"] > 0
    pipeline = RealPipeline(tuple(runtime))
    attacks = [pipeline.verifier_attack_rejected(query) for query in runtime]
    result = {"metrics": metrics, "bootstrap_full_minus_rag": advantage, "verifier_attack_rejection": sum(attacks) / len(attacks), "evaluation_integrity": "G14-E-A — PASS",
        "controlled_architecture": "G14-C-A — PASS" if controlled and demonstrated else "G14-C-B — NO DEMONSTRATED ADVANTAGE",
        "rows": rows, "peak_rss_mb": _rss_mb()}
    write_json(target, result); return result


def evaluate_public(workspace: Path) -> dict:
    _check(workspace)
    target = workspace / "public-results.json"
    if target.exists(): raise FileExistsError("PUBLIC_EVALUATION_EXISTS")
    runtime = json.loads((workspace / "locked" / "public" / "runtime.json").read_text())
    counts = {"longmemeval": sum(item["benchmark"] == "longmemeval" for item in runtime), "locomo": sum(item["benchmark"] == "locomo" for item in runtime)}
    # G2 and G10 already have frozen failed/model-limited classifications. The current product path must abstain rather than fabricate an answer.
    rows = [{"query_id": item["query_id"], "benchmark": item["benchmark"], "disposition": "unsupported_ingestion"} for item in runtime]
    result = {"public_counts": counts, "evaluated_cases": len(rows), "raw_ingestion_supported": 0, "unsupported_ingestion": len(rows), "product_readiness": "G14-P-NOT-READY",
        "reason_codes": ["G2-B_MODEL_INSUFFICIENT", "G2.1-C_FROZEN_REPRESENTATION_INSUFFICIENT", "G10-T-B_SAFE_BUT_MODEL_LIMITED"],
        "published_scores_authoritative": False, "rows": rows}
    write_json(target, result); return result


def verify_run(workspace: Path) -> dict:
    _check(workspace); prior = json.loads((workspace / "core-results.json").read_text())
    gold = _gold(workspace / "locked"); rows = _run(load_queries(workspace / "locked"))
    def semantic(value: dict) -> dict:
        return {name: {key: item[key] for key in ("accuracy", "required_factor_recall", "full_scans")} for name, item in value.items()}
    output = {"semantic_replay": semantic(prior["metrics"]) == semantic(_metrics(rows, gold)), "network": False}; write_json(workspace / "verification.json", output); return output
