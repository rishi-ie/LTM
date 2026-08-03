from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .controls import run_controls
from .generator import build_dataset, load, materialize, validate_dataset, write_json
from .metrics import calculate, classify
from .oracle import exhaustive
from .summaries import SummaryCatalog
from .summary_index import SummaryIndexes

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g5.json"


def _config() -> dict:
    return json.loads(CONFIG.read_text())


def _source_tree_hash() -> str:
    paths = sorted((ROOT / "src" / "topology_g5").glob("*.py"))
    payload = b"".join(path.name.encode() + b"\0" + path.read_bytes() for path in paths)
    return hashlib.sha256(payload).hexdigest()


def _build_gold(dataset: dict) -> dict[str, dict]:
    exhaustive_rows = {row["request_id"]: exhaustive(dataset, row) for row in dataset["cases"]}; gold = {}
    pairs: dict[str, list[dict]] = {}
    for row in dataset["cases"]: pairs.setdefault(row["pair_id"], []).append(row)
    for pair_id, rows in pairs.items():
        base = next(row for row in rows if row["variant"] == "base"); twin = next(row for row in rows if row["variant"] == "twin"); base_oracle = exhaustive_rows[base["request_id"]]; twin_oracle = exhaustive_rows[twin["request_id"]]
        remote = twin["remote_region"]; summary = dataset["catalog"].summaries[remote]; force_distance = float(sum((left-right)**2 for left, right in zip(base_oracle["state"], twin_oracle["state"]))) ** 0.5
        family = pair_id and ("premise", "correction", "hard_constraint", "exception", "conflict", "bridge")[int(pair_id[-4:]) % 6]
        for row, oracle in ((base, base_oracle), (twin, twin_oracle)):
            is_twin = row["variant"] == "twin"; answer_changes = is_twin and oracle["conclusion"] != base_oracle["conclusion"]; material = is_twin and not answer_changes and force_distance >= 0.10
            gold[row["request_id"]] = {"request_id": row["request_id"], "pair_id": pair_id, "family": family, "hidden_region_ids": [remote] if is_twin else [], "exhaustive_conclusion": oracle["conclusion"], "exhaustive_state": list(oracle["state"]), "answer_changes": answer_changes, "state_change_norm": force_distance if is_twin else 0.0, "materially_changes_state": material, "certifiable": summary.certifiable or not is_twin}
    return gold


def _materialize(workspace: Path, name: str, seed: int, factor_count: int, pairs: int) -> dict:
    dataset = build_dataset(seed, factor_count, pairs); validate_dataset(dataset); base = workspace / name; base.mkdir(parents=True, exist_ok=True); info = materialize(base, dataset); catalog = SummaryCatalog(dataset["store"], dataset["influences"], dataset["summary_modes"]); dataset["catalog"] = catalog; indexes = SummaryIndexes(catalog); write_json(base / "summaries.json", catalog.serializable()); write_json(base / "summary-index.json", {"by_key": indexes.by_key, "by_literal": indexes.by_literal, "hard": indexes.hard, "exception": indexes.exception, "correction": indexes.correction, "conflict": indexes.conflict, "bridge": indexes.bridge}); gold = _build_gold(dataset); write_json(base / "gold" / "gold.json", gold); return {**info, "summary_count": len(catalog.summaries), "gold_hash": hashlib.sha256((base / "gold" / "gold.json").read_bytes()).hexdigest()}


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development is frozen")
    config = _config(); result = _materialize(workspace, "development", config["development_seed"], config["development_factors"], config["development_pairs"]); write_json(workspace / "development-results.json", result); return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("run development first")
    result = {"config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(), "source_tree_hash": _source_tree_hash(), "locked_seed": _config()["locked_seed"], "g4_schema_hash": hashlib.sha256((ROOT / "src" / "topology_g4" / "schemas.py").read_bytes()).hexdigest()}; write_json(workspace / "frozen-manifest.json", result); return result


def _verify_freeze(workspace: Path) -> None:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text())
    if frozen["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest(): raise RuntimeError("frozen configuration changed")
    if frozen["source_tree_hash"] != _source_tree_hash(): raise RuntimeError("frozen source changed")
    if frozen["g4_schema_hash"] != hashlib.sha256((ROOT / "src" / "topology_g4" / "schemas.py").read_bytes()).hexdigest(): raise RuntimeError("frozen G4 schema changed")


def locked_suite_build(workspace: Path) -> dict:
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("freeze first")
    _verify_freeze(workspace)
    if (workspace / "locked" / "cases.json").exists(): raise RuntimeError("locked suite exists")
    config = _config(); return _materialize(workspace, "locked", config["locked_seed"], config["locked_factors"], config["locked_pairs"])


def _loaded(workspace: Path) -> tuple[dict, SummaryCatalog, SummaryIndexes]:
    dataset = load(workspace / "locked")
    catalog = SummaryCatalog(dataset["store"], dataset["influences"], dataset["summary_modes"])
    indexes = SummaryIndexes(catalog)
    return dataset, catalog, indexes


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("locked evaluation exists")
    _verify_freeze(workspace)
    began = time.perf_counter(); dataset, catalog, indexes = _loaded(workspace); methods: dict[str, list[dict]] = {}
    for row in dataset["cases"]:
        for method, result in run_controls(dataset, catalog, indexes, row).items():
            methods.setdefault(method, []).append({"result": asdict(result), "opened_factor_ids": [dataset["store"].regions[region].factor_ids for region in result.opened_region_ids]})
    # Runtime above receives only public topology, summaries, and requests. Gold is read only for this evaluator step.
    gold = json.loads((workspace / "locked" / "gold" / "gold.json").read_text())
    metric_rows = {name: calculate(rows, gold, len(dataset["factors"])) for name, rows in methods.items()}
    runtime = time.perf_counter() - began; raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; peak = raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024
    classification = classify(metric_rows["full"], runtime, peak)
    result = {"classification": classification, "runtime_seconds": runtime, "peak_rss_mb": peak, "methods": {name: {"metrics": metric_rows[name], "results": rows} for name, rows in methods.items()}, "topology_partition_hash": dataset["store"].partition_hash, "summary_count": len(catalog.summaries)}; write_json(workspace / "locked-results.json", result); return result


def verify(workspace: Path) -> dict:
    _verify_freeze(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text()); dataset, catalog, indexes = _loaded(workspace); reproduced = []
    for row in dataset["cases"]:
        value = asdict(run_controls(dataset, catalog, indexes, row)["full"]); value.pop("runtime_us", None); reproduced.append(value)
    original = []
    for row in stored["methods"]["full"]["results"]:
        value = dict(row["result"]); value.pop("runtime_us", None); original.append(value)
    def normalize(value):
        if isinstance(value, float): return round(value, 12)
        if isinstance(value, list): return [normalize(item) for item in value]
        if isinstance(value, tuple): return [normalize(item) for item in value]
        if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
        return value
    return {"classification": stored["classification"], "identical_results": json.dumps(normalize(reproduced), sort_keys=True) == json.dumps(normalize(original), sort_keys=True)}
