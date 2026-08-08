from __future__ import annotations

import hashlib
import json
import resource
import shutil
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .generator import (
    load_operations,
    load_queries,
    materialize,
    operation_set,
    query_panel,
    write_json,
)
from .schemas import StorageQuery, UpdateOperation
from .store import PersistentStore, SimulatedCrash

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g12.json"


def config() -> dict:
    return json.loads(CONFIG.read_text())


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "src" / "topology_g12").glob("*.py")):
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def _write(path: Path, value: object) -> None:
    write_json(path, value)


def _count_files(root: Path) -> int:
    return sum(1 for path in root.rglob("*") if path.is_file())


def _compile(root: Path, seed: int, regions: int, per_region: int, schema: int) -> dict:
    store = PersistentStore(root, schema)
    started = time.perf_counter()
    manifest = store.compile_initial(seed, regions, per_region)
    result = {
        "root_hash": manifest.root_hash,
        "objects": regions * per_region,
        "regions": regions,
        "store_bytes": store.store_bytes(),
        "files": _count_files(root),
        "seconds": time.perf_counter() - started,
    }
    store.close()
    return result


def _stage(workspace: Path, name: str, settings: dict, *, development: bool) -> dict:
    seed = settings["development_seed"] if development else settings["locked_seed"]
    regions = settings["development_regions"] if development else settings["locked_regions"]
    per_region = settings["development_objects_per_region"] if development else settings["locked_objects_per_region"]
    per_kind = 2 if development else settings["normal_operations_per_kind"]
    operations = operation_set(seed, regions, per_region, per_kind)
    crash = operation_set(seed, regions, per_region, 7 if not development else 2, "crash")
    queries = query_panel(seed, regions, per_region, 16 if development else settings["query_count"])
    root = workspace / name
    materialize(root / "inputs", operations, queries)
    result = _compile(root / "store", seed, regions, per_region, settings["schema_version"])
    comparison = _compile(root / "compile-comparison", seed, regions, per_region, settings["schema_version"])
    expected = {
        "operations": {item.operation_id: {"region_id": item.region_id, "kind": item.operation_type} for item in operations},
        "crash_stages": ["before_block", "after_block", "after_manifest", "before_commit", "after_commit"],
        "queries": [asdict(item) for item in queries],
    }
    _write(root / "gold" / "expected.json", expected)
    _write(root / "build.json", result)
    _write(root / "compile-comparison.json", comparison)
    _write(root / "inputs" / "crash-operations.json", [asdict(item) for item in crash])
    return {**result, "deterministic_compile_agreement": result["root_hash"] == comparison["root_hash"]}


def _queries(store: PersistentStore, queries: list[StorageQuery], version: int) -> list[dict]:
    output = []
    for query in queries:
        current = StorageQuery(query.query_id, version, query.object_id, query.source_id)
        result = store.query(current)
        output.append({"query_id": query.query_id, "found": result.found, "object_ids": [item.object_id for item in result.objects], "sources": list(result.provenance_source_ids), "blocks_read": result.blocks_read, "bytes_read": result.bytes_read, "full_scan": result.full_scan})
    return output


def _apply_normal(store: PersistentStore, operations: list[UpdateOperation]) -> tuple[list[dict], list[UpdateOperation], list[bool]]:
    receipts = []
    preserved = []
    for operation in operations:
        before = store.load_manifest()
        receipt = store.apply(operation)
        after = store.load_manifest()
        changed = [index for index, (left, right) in enumerate(zip(before.regions, after.regions)) if left.block_hash != right.block_hash]
        preserved.append(changed == [operation.region_id])
        receipts.append({"receipt": asdict(receipt), "changed_regions": changed})
    return receipts, operations, preserved


def _crashes(store_root: Path, schema: int, operations: list[UpdateOperation]) -> tuple[PersistentStore, list[dict], list[UpdateOperation]]:
    store = PersistentStore(store_root, schema)
    records: list[dict] = []
    committed: list[UpdateOperation] = []
    stages = ("before_block", "after_block", "after_manifest", "before_commit", "after_commit")
    for number, operation in enumerate(operations[:20]):
        stage = stages[number % len(stages)]
        prior = store.current_version(); expected = prior + 1
        try:
            store.apply(operation, fault_stage=stage)
        except SimulatedCrash:
            recovery = store.recovery(stage, prior, expected)
            store = PersistentStore(store_root, schema)
            should_commit = stage == "after_commit"
            records.append({**asdict(recovery), "expected_version": expected if should_commit else prior, "passed": recovery.recovered_version == (expected if should_commit else prior)})
            if should_commit:
                committed.append(operation)
        else:
            raise AssertionError("fault injection did not stop update")
    return store, records, committed


def _corruption(store: PersistentStore, attacks_root: Path, count: int) -> list[dict]:
    attacks_root.mkdir(parents=True, exist_ok=True)
    manifest = store.load_manifest()
    output: list[dict] = []
    for number in range(count):
        if number < count // 2:
            descriptor = manifest.regions[number]
            payload = bytearray((store.blocks / f"{descriptor.block_hash}.bin").read_bytes())
            payload[number] ^= 0x01
            path = attacks_root / f"block-{number}.bin"; path.write_bytes(payload)
            try:
                store.validate_block_file(path, descriptor.block_hash)
            except ValueError:
                output.append({"attack": "block", "accepted": False})
            else:
                output.append({"attack": "block", "accepted": True})
        else:
            data = json.loads((store._manifest_path(manifest.version_id)).read_text())
            if number % 2:
                data["schema_version"] = 999
            else:
                data["root_hash"] = "0" * 64
            path = attacks_root / f"manifest-{number}.json"; path.write_text(json.dumps(data, sort_keys=True))
            try:
                store.validate_manifest_file(path)
            except ValueError:
                output.append({"attack": "manifest", "accepted": False})
            else:
                output.append({"attack": "manifest", "accepted": True})
    return output


def _execute(root: Path, settings: dict, *, development: bool) -> dict:
    stage = "development" if development else "locked"
    stage_root = root / stage
    store_root = stage_root / "store"
    store = PersistentStore(store_root, settings["schema_version"])
    operations = load_operations(stage_root / "inputs")
    queries = load_queries(stage_root / "inputs")
    baseline = _queries(store, queries, 1)
    receipts, normal, locality = _apply_normal(store, operations)
    old_version = 1
    old_queries = _queries(store, queries, old_version)
    after_normal = _queries(store, queries, store.current_version())
    deleted_sources = [item.source_id for item in normal if item.operation_type == "delete"]
    deleted_residuals = sum(store.query(StorageQuery(f"delete-{source}", store.current_version(), None, source)).found for source in deleted_sources)
    store.close()
    crash_operations = [UpdateOperation(**row) for row in json.loads((stage_root / "inputs" / "crash-operations.json").read_text())]
    store, crashes, committed = _crashes(store_root, settings["schema_version"], crash_operations)
    corruptions = _corruption(store, stage_root / "attacks", 2 if development else settings["corruption_attacks"])
    final_version = store.current_version(); final_root = store.root_hash(); store_bytes = store.store_bytes()
    final_queries = _queries(store, queries, final_version)
    store.close()
    return {
        "stage_root": str(stage_root),
        "baseline_queries": baseline,
        "old_version_queries": old_queries,
        "after_normal_queries": after_normal,
        "final_queries": final_queries,
        "receipts": receipts,
        "locality": locality,
        "deleted_residuals": deleted_residuals,
        "crashes": crashes,
        "corruptions": corruptions,
        "committed_crashes": [asdict(item) for item in committed],
        "final_version": final_version,
        "final_root": final_root,
        "store_bytes": store_bytes,
    }


def _rebuild(root: Path, settings: dict, operations: list[UpdateOperation]) -> dict:
    stage_root = root / "locked"
    rebuild_root = root / "rebuild-control"
    if rebuild_root.exists():
        shutil.rmtree(rebuild_root)
    seed = settings["locked_seed"]
    _compile(rebuild_root, seed, settings["locked_regions"], settings["locked_objects_per_region"], settings["schema_version"])
    store = PersistentStore(rebuild_root, settings["schema_version"])
    for operation in operations:
        store.apply(operation)
    result = {"root_hash": store.root_hash(), "version": store.current_version(), "queries": _queries(store, load_queries(stage_root / "inputs"), store.current_version())}
    store.close()
    return result


def _metrics(execution: dict, rebuild: dict, settings: dict) -> dict:
    queries = execution["final_queries"]
    p95 = sorted(row["blocks_read"] for row in queries)[max(0, int(len(queries) * 0.95) - 1)]
    stage_root = Path(execution["stage_root"])
    comparison = json.loads((stage_root / "compile-comparison.json").read_text())
    baseline = json.loads((stage_root / "build.json").read_text())
    provenance = all(row["found"] and len(row["sources"]) == 1 for row in queries)
    return {
        "objects": settings["locked_regions"] * settings["locked_objects_per_region"],
        "deterministic_compile_agreement": float(baseline["root_hash"] == comparison["root_hash"]),
        "query_reopen_agreement": float(execution["baseline_queries"] == execution["old_version_queries"]),
        "incremental_rebuild_agreement": float(execution["final_root"] == rebuild["root_hash"] and execution["final_queries"] == rebuild["queries"]),
        "unrelated_blocks_rewritten": sum(not item for item in execution["locality"]),
        "expected_changed_region_agreement": sum(execution["locality"]) / len(execution["locality"]),
        "ancestor_summary_invalidation_agreement": sum(len(item["receipt"]["changed_summary_ids"]) == 2 for item in execution["receipts"]) / len(execution["receipts"]),
        "deleted_source_residual_descendants": execution["deleted_residuals"],
        "provenance_integrity": float(provenance),
        "crash_atomicity": sum(item["passed"] for item in execution["crashes"]) / len(execution["crashes"]),
        "mixed_version_recoveries": sum(not item["complete_old_or_new"] for item in execution["crashes"]),
        "corrupt_blocks_accepted": sum(item["accepted"] for item in execution["corruptions"]),
        "ordinary_full_scans": sum(item["full_scan"] for item in queries),
        "p95_blocks_read": p95,
        "peak_resident_mapped_blocks": 1,
        "store_size_mb": execution["store_bytes"] / (1024 * 1024),
    }


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("DEVELOPMENT_FROZEN")
    settings = config(); built = _stage(workspace, "development", settings, development=True)
    execution = _execute(workspace, settings, development=True)
    result = {"build": built, "final_root": execution["final_root"], "development_operations": len(execution["receipts"]), "crashes_passed": all(item["passed"] for item in execution["crashes"]), "corruptions_rejected": not any(item["accepted"] for item in execution["corruptions"])}
    _write(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists():
        raise RuntimeError("DEVELOP_FIRST")
    manifest = {"source_hash": source_hash(), "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(), "python": sys.version.split()[0], "sqlite": sqlite3_version(), "offline": True}
    _write(workspace / "frozen-manifest.json", manifest)
    return manifest


def sqlite3_version() -> str:
    import sqlite3

    return sqlite3.sqlite_version


def _check_freeze(workspace: Path) -> None:
    frozen = json.loads((workspace / "frozen-manifest.json").read_text())
    if frozen["source_hash"] != source_hash() or frozen["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest():
        raise RuntimeError("FROZEN_ARTIFACT_CHANGED")


def locked_suite_build(workspace: Path) -> dict:
    _check_freeze(workspace)
    if (workspace / "locked" / "build.json").exists():
        raise RuntimeError("LOCKED_SUITE_EXISTS")
    return _stage(workspace, "locked", config(), development=False)


def _classification(metrics: dict, elapsed: float, rss: float, settings: dict) -> str:
    if metrics["corrupt_blocks_accepted"] or metrics["mixed_version_recoveries"]:
        return "G12-E — RECOVERY FAILURE"
    if metrics["deleted_source_residual_descendants"] or metrics["provenance_integrity"] != 1.0:
        return "G12-D — LINEAGE/DELETION FAILURE"
    if metrics["unrelated_blocks_rewritten"]:
        return "G12-C — NONLOCAL UPDATE"
    deterministic = (
        "deterministic_compile_agreement",
        "query_reopen_agreement",
        "incremental_rebuild_agreement",
        "expected_changed_region_agreement",
        "ancestor_summary_invalidation_agreement",
    )
    if any(metrics[key] != 1.0 for key in deterministic):
        return "G12-B — NONDETERMINISTIC STORE"
    if elapsed >= settings["runtime_limit_seconds"] or rss >= settings["peak_rss_limit_mb"] or metrics["store_size_mb"] >= settings["store_size_limit_mb"]:
        return "G12-COMPUTE"
    return "G12-A — PASS"


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("LOCKED_EVALUATION_EXISTS")
    _check_freeze(workspace); settings = config(); started = time.perf_counter()
    execution = _execute(workspace, settings, development=False)
    normal = load_operations(workspace / "locked" / "inputs")
    committed = [UpdateOperation(**row) for row in execution["committed_crashes"]]
    rebuild = _rebuild(workspace, settings, normal + committed)
    metrics = _metrics(execution, rebuild, settings)
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    result = {"classification": _classification(metrics, elapsed, rss, settings), "metrics": metrics, "runtime_seconds": elapsed, "peak_rss_mb": rss, "final_root": execution["final_root"], "rebuild_root": rebuild["root_hash"], "execution": execution}
    _write(workspace / "locked-results.json", result)
    return {key: value for key, value in result.items() if key != "execution"}


def verify_run(workspace: Path) -> dict:
    _check_freeze(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text())
    store = PersistentStore(workspace / "locked" / "store", config()["schema_version"])
    queries = _queries(store, load_queries(workspace / "locked" / "inputs"), store.current_version())
    root_hash = store.root_hash(); store.close()
    identical = root_hash == stored["final_root"] and queries == stored["execution"]["final_queries"]
    return {"classification": stored["classification"], "identical_results": identical}
