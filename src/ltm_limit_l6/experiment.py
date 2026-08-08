"""Small, deterministic L6 harness with causal controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .dataset import GeneratedCase, iter_cases, reality_profile
from .evaluator import score_results
from .optimizer import optimize


def run_cases(cases: tuple[GeneratedCase, ...], *, control: str = "full"):
    rows = []
    for case in cases:
        rows.append(optimize(case.field, case.prompt, reality_profile(case.prompt.reality_key), learned_geometry=control not in {"no_geometry", "random_geometry"}, fixed_state=control == "fixed_state", random_geometry=control == "random_geometry", single_mode=control == "single_mode", source_weights=control != "count_only", contradiction_terms=control != "no_contradictions", maximum_steps=64))
    return tuple(rows)


def control_panel(cases: tuple[GeneratedCase, ...]) -> dict[str, object]:
    full = score_results(cases, run_cases(cases))
    variants = {name: score_results(cases, run_cases(cases, control=name)) for name in ("no_geometry", "fixed_state", "random_geometry", "count_only", "no_contradictions", "single_mode")}
    gains = {name: full["exactness"] - report["exactness"] for name, report in variants.items()}
    return {"full": full, "variants": variants, "gains": gains, "mechanism_gates": {"no_geometry": gains["no_geometry"] >= 0.20, "fixed_state": gains["fixed_state"] >= 0.20, "random_geometry": gains["random_geometry"] >= 0.30, "count_only": gains["count_only"] >= 0.20, "single_mode": gains["single_mode"] >= 0.20, "passed": all(value >= 0.20 for value in gains.values())}}


def classification(metrics: dict[str, object], controls: dict[str, object]) -> str:
    if metrics.get("incorrect_accepted", 1) != 0:
        return "L6-H — VERIFICATION OR DECODER FAILURE"
    if not bool(controls.get("mechanism_gates", {}).get("passed")):
        return "L6-D — LATENT MECHANISM NOT CAUSAL"
    if float(metrics.get("accepted_precision", 0.0)) < 1.0 or float(metrics.get("exactness", 0.0)) < 0.90:
        return "L6-F — MULTIHOP COMPOSITION FAILURE"
    return "L6-A — CAUSAL MATHEMATICAL REALITY EQUILIBRIUM PASS"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path.name}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def run(workspace: Path, *, limit: int = 40) -> dict[str, object]:
    workspace.mkdir(parents=True, exist_ok=True)
    cases = iter_cases(limit, seed=1960)
    results = run_cases(cases)
    metrics = score_results(cases, results)
    controls = control_panel(cases)
    output = {"experiment_id": "L6", "classification": classification(metrics, controls), "metrics": metrics, "controls": controls, "cases": len(cases), "field_bodies_per_case": len(cases[0].field.bodies) if cases else 0, "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_json(workspace / "results.json", output)
    return output


def model_check(workspace: Path) -> dict[str, object]:
    value = {"experiment_id": "L6", "state_dimension": 128, "maximum_hops": 20, "exact_consumer_propagation": False, "runtime_evaluator_gold_access": False}
    write_json(workspace / "model-check.json", value)
    return value


def dataset_build(workspace: Path, limit: int = 40) -> dict[str, object]:
    cases = iter_cases(limit, seed=1960)
    value = {"experiment_id": "L6", "cases": limit, "depths": sorted({case.depth for case in cases}), "families": sorted({case.family for case in cases}), "manifest_sha256": hashlib.sha256(repr([(case.prompt.prompt_id, case.depth, case.family) for case in cases]).encode()).hexdigest()}
    write_json(workspace / "dataset-manifest.json", value)
    return value
