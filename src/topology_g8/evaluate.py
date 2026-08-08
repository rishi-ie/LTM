from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .controls import scores
from .engine import evaluate_batched, evaluate_reference
from .generator import build_dataset, load_requests, materialize, write_json

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "topology-g8.json"


def config() -> dict:
    return json.loads(CONFIG.read_text())


def sources() -> str:
    paths = []
    for name in ("topology_g6", "topology_g7", "topology_g8"):
        paths.extend(sorted((ROOT / "src" / name).glob("*.py")))
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def _write_stage(workspace: Path, stage: str, seed: int, cases: int, settings: dict) -> None:
    requests, blocks = build_dataset(seed, cases, settings)
    root = workspace / stage
    materialize(root, requests, blocks)
    reference = {
        request.request_id: asdict(evaluate_reference(request, root / "field", settings))
        for request in requests
    }
    write_json(root / "gold" / "reference.json", reference)


def develop(workspace: Path) -> dict:
    if (workspace / "frozen-manifest.json").exists():
        raise RuntimeError("development frozen")
    settings = config()
    _write_stage(workspace, "development", settings["development_seed"], settings["development_cases"], settings)
    result = {"cases": settings["development_cases"], "source_hash": sources()}
    write_json(workspace / "development-results.json", result)
    return result


def freeze(workspace: Path) -> dict:
    if not (workspace / "development-results.json").exists():
        raise RuntimeError("develop first")
    manifest = {
        "source_hash": sources(),
        "config_hash": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "development_hash": hashlib.sha256((workspace / "development-results.json").read_bytes()).hexdigest(),
        "offline": True,
    }
    write_json(workspace / "frozen-manifest.json", manifest)
    return manifest


def check_freeze(workspace: Path) -> None:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    if manifest["source_hash"] != sources() or manifest["config_hash"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest():
        raise RuntimeError("FROZEN_ARTIFACT_CHANGED")


def locked_suite_build(workspace: Path) -> dict:
    check_freeze(workspace)
    if (workspace / "locked" / "requests.json").exists():
        raise RuntimeError("locked suite exists")
    settings = config()
    _write_stage(workspace, "locked", settings["locked_seed"], settings["locked_cases"], settings)
    return {"cases": settings["locked_cases"]}


def _state_vector(row: dict, request) -> np.ndarray:
    state = row["final_state"]
    values = dict(state["confidence_values"])
    values.update(dict(state["preference_values"]))
    values.update(dict(state["reference_values"]))
    values["u:unknown"] = state["uncertainty"]
    return np.array([values[item.variable_id] for item in request.soft_variables], dtype=np.float64)


def _signature(result: dict) -> tuple:
    hard = result["hard_result"]
    proofs = tuple(
        (item["conclusion"], item["rule_id"], tuple(item["premises"]))
        for item in hard["proofs"]
    )
    return (
        hard["conclusion"],
        tuple(hard["active"]),
        tuple(hard["inactive"]),
        proofs,
        tuple(hard["conflicts"]),
        tuple(hard["obligations"]),
        result["selected_branch"],
        tuple(result["retained_branches"]),
        result["disposition"],
        tuple(result["decisive_provenance_ids"]),
    )


def _canonical(value: object) -> str:
    """Compare serialized experimental objects, not Python list/tuple containers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _candidate_row(request, field_root: Path, settings: dict) -> dict:
    configurations = []
    for width in settings["batch_widths"]:
        for order in settings["orders"]:
            rendered = asdict(
                evaluate_batched(
                    request, field_root, settings, batch_width=width, order=order,
                    seed=settings["locked_seed"],
                )
            )
            configurations.append(
                {
                    "width": width,
                    "order": order,
                    "result": rendered,
                }
            )
    return {"request_id": request.request_id, "family": request.family, "configurations": configurations}


def _score_row(request, candidate: dict, field_root: Path, settings: dict, reference: dict) -> dict:
    """Evaluator-only phase: attach gold comparisons after candidate execution."""
    expected = _state_vector(reference, request)
    residuals = dict(reference["residuals"])
    configurations = []
    for entry in candidate["configurations"]:
        rendered = entry["result"]
        actual = _state_vector(rendered, request)
        configurations.append(
            {
                **entry,
                "state_l2": float(np.linalg.norm(actual - expected)),
                "state_cosine": float(actual @ expected / (np.linalg.norm(actual) * np.linalg.norm(expected))),
                "energy_error": abs(rendered["final_energy"] - reference["final_energy"]),
                "residual_error": max(
                    [abs(value - residuals.get(name, 0.0)) for name, value in rendered["residuals"]]
                    or [0.0]
                ),
                "semantic_match": _signature(rendered) == _signature(reference),
            }
        )
    oracle = evaluate_reference(request, field_root, settings)
    control = scores(request, field_root, settings, oracle, settings["locked_seed"])
    return {
        "request_id": request.request_id,
        "family": request.family,
        "reference": reference,
        "configurations": configurations,
        "controls": control,
    }


def _mean(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 1.0


def _metrics(rows: list[dict]) -> dict:
    entries = [entry for row in rows for entry in row["configurations"]]
    hard = [
        _canonical(entry["result"]["hard_result"]) == _canonical(row["reference"]["hard_result"])
        for row in rows
        for entry in row["configurations"]
    ]
    provenance = [
        _canonical(entry["result"]["decisive_provenance_ids"])
        == _canonical(row["reference"]["decisive_provenance_ids"])
        for row in rows
        for entry in row["configurations"]
    ]
    cap = [entry["result"]["memory_trace"]["peak_resident_blocks"] <= entry["width"] and not entry["result"]["memory_trace"]["complete_field_materialization"] for entry in entries]
    controls = {
        name: 1.0 - _mean([row["controls"][name] for row in rows])
        for name in ("last_block_wins", "average_local_states", "sequential_update")
    }
    return {
        "hard_conclusion_agreement": _mean(hard),
        "full_hard_state_agreement": _mean(hard),
        "branch_disposition_provenance_agreement": _mean([entry["semantic_match"] for entry in entries]),
        "decisive_provenance_agreement": _mean(provenance),
        "state_l2_max": max(entry["state_l2"] for entry in entries),
        "state_cosine_min": min(entry["state_cosine"] for entry in entries),
        "energy_error_max": max(entry["energy_error"] for entry in entries),
        "residual_error_max": max(entry["residual_error"] for entry in entries),
        "cross_order_semantic_agreement": _mean([entry["semantic_match"] for entry in entries]),
        "memory_cap_agreement": _mean(cap),
        "memory_cap_violations": float(sum(not item for item in cap)),
        "complete_field_materializations": float(sum(entry["result"]["memory_trace"]["complete_field_materialization"] for entry in entries)),
        "control_failure_rates": controls,
    }


def evaluate_locked(workspace: Path) -> dict:
    if (workspace / "locked-results.json").exists():
        raise RuntimeError("locked evaluation exists")
    check_freeze(workspace)
    settings = config()
    started = time.perf_counter()
    requests = load_requests(workspace / "locked")
    field_root = workspace / "locked" / "field"
    # Candidate calls below receive only requests, field blocks, and frozen settings.
    candidates = [_candidate_row(request, field_root, settings) for request in requests]
    # Only this evaluator phase reads the reference file.
    reference = json.loads((workspace / "locked" / "gold" / "reference.json").read_text())
    rows = [
        _score_row(request, candidate, field_root, settings, reference[request.request_id])
        for request, candidate in zip(requests, candidates, strict=True)
    ]
    metrics = _metrics(rows)
    elapsed = time.perf_counter() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    controls_ok = all(value >= .20 for value in metrics["control_failure_rates"].values())
    gates = (
        metrics["hard_conclusion_agreement"] == 1.0
        and metrics["full_hard_state_agreement"] == 1.0
        and metrics["branch_disposition_provenance_agreement"] == 1.0
        and metrics["decisive_provenance_agreement"] == 1.0
        and metrics["state_l2_max"] <= 1e-8
        and metrics["state_cosine_min"] >= .999999
        and metrics["energy_error_max"] <= 1e-10
        and metrics["residual_error_max"] <= 1e-10
        and metrics["cross_order_semantic_agreement"] == 1.0
        and metrics["memory_cap_violations"] == 0
        and metrics["complete_field_materializations"] == 0
        and controls_ok
        and elapsed < settings["runtime_limit_seconds"]
        and rss < settings["peak_rss_limit_mb"]
    )
    result = {
        "classification": "G8-A — PASS" if gates else "G8-B — ORDER DEPENDENT",
        "metrics": metrics,
        "runtime_seconds": elapsed,
        "peak_rss_mb": rss,
        "rows": rows,
    }
    write_json(workspace / "locked-results.json", result)
    return {key: value for key, value in result.items() if key != "rows"}


def verify_run(workspace: Path) -> dict:
    check_freeze(workspace)
    stored = json.loads((workspace / "locked-results.json").read_text())
    settings = config()
    requests = load_requests(workspace / "locked")
    reference = json.loads((workspace / "locked" / "gold" / "reference.json").read_text())
    candidates = [_candidate_row(request, workspace / "locked" / "field", settings) for request in requests]
    replay = [
        _score_row(request, candidate, workspace / "locked" / "field", settings, reference[request.request_id])
        for request, candidate in zip(requests, candidates, strict=True)
    ]
    return {
        "classification": stored["classification"],
        "identical_results": json.dumps(replay, sort_keys=True) == json.dumps(stored["rows"], sort_keys=True),
    }
