from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .controls import semantic_topk
from .execute import execute
from .generator import build_dataset, manifest, read_jsonl, validate_required_factors, write_jsonl
from .indexes import FactorIndexes
from .metrics import calculate, classify
from .schemas import TopologyFactor, TraversalRequest, canonical_hash
from .traverse import build_frontier

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g4.json"


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"); temp.replace(path)


def _materialize(workspace: Path, split: str, seed: int, factors_n: int, cases_n: int) -> dict:
    factors, requests, gold = build_dataset(seed, factors_n, cases_n); validate_required_factors(factors, requests, gold); base = workspace / split; base.mkdir(parents=True, exist_ok=True)
    factor_rows = [asdict(x) for x in factors]; _write(base / "factors.json", factor_rows)
    block_hashes = {}
    for start in range(0, len(factor_rows), 256):
        block_id = f"block-{start // 256:05d}"; rows = factor_rows[start:start+256]
        _write(base / "blocks" / f"{block_id}.json", rows); block_hashes[block_id] = canonical_hash(rows)
    write_jsonl(requests, base / "cases.jsonl"); write_jsonl(gold, base / "gold" / "gold.jsonl"); indexes = FactorIndexes(factors); index_manifest = {**indexes.manifest(), "block_hashes": block_hashes}; _write(base / "index-manifest.json", index_manifest); return {**manifest(factors), "cases": len(requests), "index": index_manifest}


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development frozen")
    result = _materialize(workspace, "development", 1732, 25_000, 120); _write(workspace / "development-results.json", result); return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("run development first")
    result = {"config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(), "source_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "locked_seed": 20260805}
    _write(workspace / "frozen-manifest.json", result); return result


def locked_suite_build(workspace: Path) -> dict:
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("freeze first")
    if (workspace / "locked" / "cases.jsonl").exists(): raise RuntimeError("locked suite exists")
    return _materialize(workspace, "locked", 20260805, 100_000, 300)


def _load(workspace: Path):
    factors = tuple(TopologyFactor(**{**row, "source_ids": tuple(row["source_ids"]), "target_ids": tuple(row["target_ids"]), "provenance_ids": tuple(row["provenance_ids"])}) for row in json.loads((workspace / "locked" / "factors.json").read_text()))
    requests = [TraversalRequest(**{**row, "starting_entity_ids": tuple(row["starting_entity_ids"]), "starting_predicate_ids": tuple(row["starting_predicate_ids"])}) for row in read_jsonl(workspace / "locked" / "cases.jsonl")]
    gold = {row["request_id"]: row for row in read_jsonl(workspace / "locked" / "gold" / "gold.jsonl")}; return factors, requests, gold


def _g3_diagnostic(requests: list[TraversalRequest]) -> dict:
    from topology_g3.indexes import Indexes as G3Indexes
    from topology_g3.resolver import resolve as g3_resolve
    from topology_g3.schemas import PromptMention, PromptSignature, TopologyAddress

    addresses = []
    for request in requests:
        entity = request.starting_entity_ids[0]; predicate = request.starting_predicate_ids[0]
        addresses.append(TopologyAddress(entity, entity, "entity", entity, (), None, None, request.scope_id, None, None, request.episode_id, "agent", (f"prov:{entity}",)))
        addresses.append(TopologyAddress(predicate, predicate, "predicate", predicate, (), predicate, "query", "global", None, None, None, None, (f"prov:{predicate}",)))
    indexes = G3Indexes(tuple(addresses)); correct = 0; unsafe = 0
    for request in requests:
        entity = request.starting_entity_ids[0]; mention = PromptMention(entity, entity.lower(), "entity", 0, len(entity))
        signature = PromptSignature(request.request_id, "question", (mention,), (request.starting_predicate_ids[0],), ("query",), (), (), request.valid_at, None, request.polarity, "asserted", (request.episode_id,) if request.episode_id else (), "clarify")
        result = g3_resolve(signature, indexes)
        correct += entity in result.resolved_addresses
        unsafe += result.disposition == "resolved" and entity not in result.resolved_addresses
    return {"status": "actual-g3-controlled-signature", "starting_address_agreement": correct / len(requests), "unsafe_resolutions": unsafe}


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("locked evaluation exists")
    began = time.perf_counter(); factors, requests, gold = _load(workspace); indexes = FactorIndexes(factors); methods = {}
    oracle = [execute(request, factors) for request in requests]
    oracle_agreement = sum(item.conclusion == gold[item.request_id]["gold_conclusion"] for item in oracle) / len(oracle)
    for mode in ("full", "forward_only", "untyped_bfs", "no_safety", "no_session", "no_correction", "no_conflict"):
        frontiers = [build_frontier(request, indexes, mode) for request in requests]
        executions = [execute(request, tuple(indexes.factors[fid] for fid in frontier.exact_factor_ids)) for request, frontier in zip(requests, frontiers)]
        methods[mode] = {"frontiers": [asdict(x) for x in frontiers], "executions": [asdict(x) for x in executions], "metrics": calculate(frontiers, executions, gold, len(factors))}
    semantic_frontiers = semantic_topk(requests, indexes)
    semantic_executions = [execute(request, tuple(indexes.factors[fid] for fid in frontier.exact_factor_ids)) for request, frontier in zip(requests, semantic_frontiers)]
    methods["semantic_topk"] = {"frontiers": [asdict(x) for x in semantic_frontiers], "executions": [asdict(x) for x in semantic_executions], "metrics": calculate(semantic_frontiers, semantic_executions, gold, len(factors))}
    runtime = time.perf_counter() - began; raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; peak = raw/(1024*1024) if sys.platform == "darwin" else raw/1024
    classification = classify(methods["full"]["metrics"], runtime, peak)
    if oracle_agreement != 1.0: classification = "G4-F — INTEGRITY FAILURE"
    result = {"classification": classification, "runtime_seconds": runtime, "peak_rss_mb": peak, "methods": methods, "oracle_agreement": oracle_agreement, "topology_hash": manifest(factors)["topology_hash"], "g3_integration": _g3_diagnostic(requests)}
    _write(workspace / "locked-results.json", result); return result


def verify(workspace: Path) -> dict:
    stored = json.loads((workspace / "locked-results.json").read_text()); factors, requests, _ = _load(workspace); indexes = FactorIndexes(factors); reproduced = [asdict(build_frontier(request, indexes, "full")) for request in requests]; original = stored["methods"]["full"]["frontiers"]
    for left, right in zip(reproduced, original): left.pop("runtime_us", None); right.pop("runtime_us", None)
    return {"classification": stored["classification"], "identical_frontiers": canonical_hash(reproduced) == canonical_hash(original)}
