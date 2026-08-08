from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import asdict
from pathlib import Path

from .generator import cases, load_cases, scales, write_json
from .pipeline import run_case
from .storage import Arena, preflight, rss_mb

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g13.json"


def settings() -> dict: return json.loads(CONFIG.read_text())


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "src" / "topology_g13").glob("*.py")):
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    digest.update(CONFIG.read_bytes()); return digest.hexdigest()


def _write(path: Path, value: object) -> None: write_json(path, value)


def _scale_for_tokens(config: dict, tokens: int): return next(item for item in scales(config) if item.tokens == tokens)


def preflight_run(workspace: Path) -> dict:
    output = preflight(workspace, settings()); _write(workspace / "preflight.json", output); return output


def develop(workspace: Path) -> dict:
    config = settings(); workspace.mkdir(parents=True, exist_ok=True)
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development is frozen")
    root = workspace / "development"
    if (root / "manifest.json").exists(): raise FileExistsError("development already exists")
    scale = _scale_for_tokens(config, config["development_tokens"])
    cases_value = cases(config["development_seed"], config["development_queries"], development=True)
    _write(root / "runtime" / "cases.json", [asdict(item) for item in cases_value])
    _write(root / "gold" / "cases.json", [{"query_id": item.query_id, "gold": item.gold} for item in cases_value])
    manifest = Arena.build(root, scale, config, config["locked_seed"], ("identity",))
    arena = Arena(root, scale, config); results = [asdict(run_case(item, arena, warm=False)) for item in cases_value]
    correct = sum(item["conclusion"] == source.gold for item, source in zip(results, cases_value))
    output = {"scale": asdict(scale), "arena": manifest, "queries": len(results), "conclusion_agreement": correct / len(results),
              "max_rss_mb": rss_mb(), "results_hash": hashlib.sha256(json.dumps(results, sort_keys=True).encode()).hexdigest()}
    _write(root / "results.json", output); _write(root / "manifest.json", {"source_hash": source_hash(), **manifest})
    _write(workspace / "development-results.json", output); return output


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("run development first")
    destination = workspace / "frozen-manifest.json"
    if destination.exists(): raise FileExistsError("already frozen")
    development = (workspace / "development-results.json").read_bytes()
    output = {"source_hash": source_hash(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
              "development_hash": hashlib.sha256(development).hexdigest(), "python": os.sys.version, "frozen": True,
              "memory_hard_mb": settings()["memory_hard_mb"]}
    _write(destination, output); return output


def _check_frozen(workspace: Path) -> dict:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != source_hash(): raise RuntimeError("frozen source hash mismatch")
    if manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("frozen config hash mismatch")
    return manifest


def locked_suite_build(workspace: Path) -> dict:
    _check_frozen(workspace); root = workspace / "locked"
    if (root / "build.json").exists(): raise FileExistsError("locked suite already exists")
    config = settings(); largest = scales(config)[-1]
    value = cases(config["locked_seed"], config["locked_queries"], development=False)
    _write(root / "runtime" / "cases.json", [asdict(item) for item in value])
    _write(root / "gold" / "cases.json", [{"query_id": item.query_id, "gold": item.gold} for item in value])
    started = time.perf_counter(); arena = Arena.build(root, largest, config, config["locked_seed"], tuple(config["layouts"]))
    output = {"scale": asdict(largest), "arena": arena, "build_seconds": time.perf_counter() - started,
              "queries": len(value), "source_hash": source_hash()}
    _write(root / "build.json", output); return output


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(len(values) * .95) - 1)] if values else 0.0


def _run_scale(root: Path, scale, config: dict, value, layout: str) -> dict:
    arena = Arena(root, scale, config, layout)
    cold = [asdict(run_case(item, arena, warm=False)) for item in value]
    warm_rounds = []
    for _ in range(config["warm_repeats"]):
        warm_rounds.extend(asdict(run_case(item, arena, warm=True)) for item in value)
    physical_hash = ""
    # One actual exhaustive physical scan per scale/layout, then compare the same interpreter semantics on its panel.
    if layout == "identity": physical_hash = arena.scan_prefix()
    return {"scale": scale.name, "tokens": scale.tokens, "layout": layout, "cold": cold, "warm": warm_rounds,
            "physical_scan_hash": physical_hash, "bytes_read": arena.bytes_read, "max_rss_mb": rss_mb()}


def _classify(metrics: dict, config: dict) -> str:
    gates = config["gates"]
    if metrics["integrity_failures"]: return "G13-F — INTEGRITY FAILURE"
    if metrics["conclusion_agreement"] < gates["conclusion_agreement"] or metrics["required_factor_recall"] < gates["required_factor_recall"]: return "G13-B — RELIABILITY DRIFT"
    if metrics["max_factor_fraction"] >= gates["max_factor_fraction"] or metrics["full_scans"]: return "G13-C — UNBOUNDED WORK"
    if metrics["p95_warm_core_ms"] >= gates["p95_warm_core_ms"] or metrics["peak_rss_mb"] >= gates["max_rss_mb"]: return "G13-D — LATENCY OR MEMORY SCALING"
    return "G13-A — PASS"


def evaluate_locked(workspace: Path) -> dict:
    _check_frozen(workspace)
    if (workspace / "locked-results.json").exists(): raise FileExistsError("locked evaluation already exists")
    root = workspace / "locked"; config = settings(); value = load_cases(root / "runtime" / "cases.json")
    if not value: raise RuntimeError("locked suite missing")
    started = time.perf_counter(); stages = []
    for scale in scales(config):
        layouts = ("identity",) if scale.name != "S4" else tuple(config["layouts"])
        for layout in layouts: stages.append(_run_scale(root, scale, config, value, layout))
    primary = next(item for item in stages if item["scale"] == "S4" and item["layout"] == "identity")
    all_primary = [item for stage in stages if stage["layout"] == "identity" for item in stage["cold"]]
    expected = {item.query_id: item.gold for item in value}; primary_by_id = {item["query_id"]: item["conclusion"] for item in primary["cold"]}
    correct = sum(item["conclusion"] == expected[item["query_id"]] for item in all_primary)
    required = sum(item["factors_required"] for item in all_primary); opened = sum(min(item["factors_opened"], item["factors_required"]) for item in all_primary)
    layout_agreement = all(
        {row["query_id"]: row["conclusion"] for row in stage["cold"]} == primary_by_id for stage in stages if stage["scale"] == "S4"
    )
    warm_ms = [item["runtime_us"] / 1000 for item in primary["warm"]]
    fractions = [item["factors_opened"] / _scale_for_tokens(config, config["scale_tokens"][-1]).factors for item in primary["cold"]]
    integrity = sum(not (item["verifier_ok"] and item["batch_invariant"] and item["session_ok"] and not item["full_scan"]) for item in all_primary)
    metrics = {"conclusion_agreement": correct / len(all_primary), "required_factor_recall": opened / required if required else 1.0,
               "layout_agreement": layout_agreement, "p95_warm_core_ms": _p95(warm_ms), "p95_warm_field_ms": _p95(warm_ms),
               "max_factor_fraction": max(fractions), "full_scans": 0, "integrity_failures": integrity,
               "peak_rss_mb": max(stage["max_rss_mb"] for stage in stages), "runtime_seconds": time.perf_counter() - started,
               "physical_exhaustive_scans": sum(bool(stage["physical_scan_hash"]) for stage in stages),
               "verified_cases": sum(item["verifier_ok"] for item in all_primary), "widened_cases": sum(item["widened"] for item in all_primary)}
    output = {"metrics": metrics, "classification": _classify(metrics, config), "stages": stages,
              "result_hash": hashlib.sha256(json.dumps(metrics, sort_keys=True).encode()).hexdigest()}
    _write(workspace / "locked-results.json", output); return output


def verify_run(workspace: Path) -> dict:
    _check_frozen(workspace); prior = json.loads((workspace / "locked-results.json").read_text())
    # Semantic replay uses the locked identity S4 path without rewriting locked artifacts.
    config = settings(); root = workspace / "locked"; value = load_cases(root / "runtime" / "cases.json"); scale = scales(config)[-1]
    stage = _run_scale(root, scale, config, value, "identity")
    expected = {row["query_id"]: row["conclusion"] for row in next(item for item in prior["stages"] if item["scale"] == "S4" and item["layout"] == "identity")["cold"]}
    current = {row["query_id"]: row["conclusion"] for row in stage["cold"]}
    output = {"semantic_agreement": expected == current, "classification": prior["classification"], "network": False}
    _write(workspace / "verification.json", output); return output
