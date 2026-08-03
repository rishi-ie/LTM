from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .generator import build_prompts, build_topology, read_jsonl, topology_manifest, write_jsonl
from .indexes import Indexes
from .metrics import calculate, classify
from .resolver import resolve, signature_from_dict
from .schemas import canonical_hash
from .signatures import parse_controlled

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g3.json"

def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"); temp.replace(path)

def _materialize(workspace: Path, split: str, seed: int, prompts: int) -> dict:
    base = workspace / split; topology = build_topology(seed); runtime, gold = build_prompts(topology, seed + 1, prompts)
    base.mkdir(parents=True, exist_ok=True); _write(base / "topology.json", [asdict(x) for x in topology]); write_jsonl(runtime, base / "inputs.jsonl"); write_jsonl(gold, base / "gold" / "gold.jsonl")
    index = Indexes(topology); _write(base / "index-manifest.json", index.manifest()); return {**topology_manifest(topology), "prompts": len(runtime), "index": index.manifest()}

def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists(): raise RuntimeError("development is frozen")
    result = _materialize(workspace, "development", 1731, 200); _write(workspace / "development-results.json", result); return result

def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists(): raise RuntimeError("run development first")
    manifest = {"config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(), "source_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "seed": 20260804}
    _write(workspace / "frozen-manifest.json", manifest); return manifest

def locked_suite_build(workspace: Path) -> dict:
    if not (workspace / "frozen-manifest.json").exists(): raise RuntimeError("freeze first")
    if (workspace / "locked" / "inputs.jsonl").exists(): raise RuntimeError("locked suite already exists")
    return _materialize(workspace, "locked", 20260804, 400)

def _load_topology(path: Path):
    from .schemas import TopologyAddress
    return tuple(TopologyAddress(**x) for x in json.loads(path.read_text()))

def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists(): raise RuntimeError("locked evaluation already exists")
    if not (workspace / "locked" / "inputs.jsonl").exists(): raise RuntimeError("build locked suite first")
    began = time.perf_counter(); topology = _load_topology(workspace / "locked" / "topology.json"); indexes = Indexes(topology); inputs = read_jsonl(workspace / "locked" / "inputs.jsonl"); gold = {x["prompt_id"]: x for x in read_jsonl(workspace / "locked" / "gold" / "gold.jsonl")}
    methods = {}
    for mode in ("full", "lexical", "semantic"):
        rows = [resolve(signature_from_dict(x["signature"]), indexes, mode) for x in inputs]
        metrics = calculate(rows, gold, len(topology)); methods[mode] = {"metrics": metrics, "predictions": [asdict(x) for x in rows]}
    text_rows = [resolve(parse_controlled(x), indexes, "full") for x in inputs]
    methods["text"] = {"metrics": calculate(text_rows, gold, len(topology)), "predictions": [asdict(x) for x in text_rows]}
    runtime = time.perf_counter() - began
    raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports KiB.
    peak = raw_rss / (1024 * 1024) if sys.platform == "darwin" else raw_rss / 1024
    outcome = {"classification": classify(methods["full"]["metrics"], runtime, peak), "runtime_seconds": runtime, "peak_rss_mb": peak, "methods": methods, "topology_hash": topology_manifest(topology)["topology_hash"]}
    _write(workspace / "locked-results.json", outcome); return outcome

def verify(workspace: Path) -> dict:
    stored = json.loads((workspace / "locked-results.json").read_text()); topology = _load_topology(workspace / "locked" / "topology.json"); indexes = Indexes(topology); inputs = read_jsonl(workspace / "locked" / "inputs.jsonl"); reproduced = [asdict(resolve(signature_from_dict(x["signature"]), indexes, "full")) for x in inputs]
    original = stored["methods"]["full"]["predictions"]
    for left, right in zip(reproduced, original):
        left.pop("runtime_us", None); right.pop("runtime_us", None)
    return {"identical_predictions": canonical_hash(reproduced) == canonical_hash(original), "classification": stored["classification"]}
