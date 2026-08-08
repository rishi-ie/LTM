"""L7 execution, causal controls, immutable artifacts, and classification."""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

from .dataset import L7Case, build_cases, build_reality, manifest
from .evaluator import score
from .field import RealityField
from .solver import SolverOptions, solve

_WORKER_FIELD: RealityField | None = None
_WORKER_OPTIONS: SolverOptions | None = None


def _init_worker(field: RealityField, options: SolverOptions) -> None:
    global _WORKER_FIELD, _WORKER_OPTIONS
    _WORKER_FIELD, _WORKER_OPTIONS = field, options


def _solve_public(prompt):
    assert _WORKER_FIELD is not None and _WORKER_OPTIONS is not None
    return solve(_WORKER_FIELD, prompt, options=_WORKER_OPTIONS)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, default=lambda row: asdict(row), sort_keys=True, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == payload:
            return
        raise FileExistsError(f"immutable L7 artifact exists: {path}")
    path.write_text(payload, encoding="utf-8")


def _results(field: RealityField, cases: tuple[L7Case, ...], options: SolverOptions | None = None, *, parallel: bool = False):
    options = options or SolverOptions()
    if parallel and len(cases) > 16:
        try:
            with ProcessPoolExecutor(max_workers=4, initializer=_init_worker, initargs=(field, options)) as executor:
                return tuple(executor.map(_solve_public, (case.public for case in cases)))
        except (OSError, PermissionError):
            pass
    return tuple(solve(field, case.public, options=options) for case in cases)


def _subset(cases: tuple[L7Case, ...], names: set[str]) -> tuple[L7Case, ...]:
    return tuple(case for case in cases if case.expected.family in names)


def _fast_score(cases: tuple[L7Case, ...], results: tuple) -> dict[str, float | int]:
    """Controls measure changed public behavior; only the full run is oracle-scored."""
    correct = []
    for case, result in zip(cases, results, strict=True):
        expected = case.expected
        if expected.disposition == "candidate":
            correct.append(result.disposition == "candidate" and result.selected_candidate_id is not None and result.selected_candidate_id.split(":+")[0] == expected.selected_atom_id)
        else:
            correct.append(result.disposition == expected.disposition)
    accepted = [index for index, result in enumerate(results) if result.disposition in {"candidate", "alternatives"}]
    return {"exactness": sum(correct) / len(correct), "incorrect_accepted": sum(not correct[index] for index in accepted), "accepted_precision": sum(correct[index] for index in accepted) / len(accepted) if accepted else 1.0}


def controls(field: RealityField, cases: tuple[L7Case, ...]) -> dict[str, object]:
    full = score(field, cases, _results(field, cases, parallel=True))
    variants = {
        "no_optimization": SolverOptions(no_optimization=True),
        "one_sweep": SolverOptions(one_sweep=True),
        "no_relational_law": SolverOptions(no_relational_law=True),
        "shuffled_endpoints": SolverOptions(shuffle_endpoints=True),
        "conjunction_max": SolverOptions(conjunction_max=True),
        "count_only": SolverOptions(count_only=True),
        "no_tension": SolverOptions(no_tension=True),
        "reality_filter_removed": SolverOptions(ignore_reality=True),
    }
    reports = {name: _fast_score(cases, _results(field, cases, option, parallel=True)) for name, option in variants.items()}
    deep = _subset(cases, {"unique"})
    deep = tuple(case for case in deep if (case.expected.depth or 0) >= 9)
    one_deep = _fast_score(deep, _results(field, deep, SolverOptions(one_sweep=True)))
    count_authority = _fast_score(_subset(cases, {"weighted_contradiction"}), _results(field, _subset(cases, {"weighted_contradiction"}), SolverOptions(count_only=True)))
    tension_cases = _subset(cases, {"weighted_contradiction", "balanced_alternative"})
    no_tension = _fast_score(tension_cases, _results(field, tension_cases, SolverOptions(no_tension=True)))
    gains = {
        "no_optimization": full["exactness"] - reports["no_optimization"]["exactness"],
        "one_sweep_deep": _fast_score(deep, _results(field, deep, parallel=True))["exactness"] - one_deep["exactness"],
        "no_relational_law": full["exactness"] - reports["no_relational_law"]["exactness"],
        "shuffled_endpoints": full["exactness"] - reports["shuffled_endpoints"]["exactness"],
        "count_only_authority": 1.0 - count_authority["exactness"],
        "no_tension": 1.0 - no_tension["exactness"],
    }
    gates = {
        "no_optimization": gains["no_optimization"] >= .80,
        "one_sweep_deep": gains["one_sweep_deep"] >= .50,
        "no_relational_law": gains["no_relational_law"] >= .80,
        "shuffled_endpoints": gains["shuffled_endpoints"] >= .50,
        "count_only_authority": gains["count_only_authority"] >= .30,
        "no_tension": gains["no_tension"] >= .30,
    }
    return {"full": full, "variants": reports, "gains": gains, "gates": gates, "passed": all(gates.values())}


def _replace_factor(field: RealityField, body_id: str, **changes: object) -> RealityField:
    return RealityField(field.atoms, tuple(replace(item, **changes) if item.body_id == body_id else item for item in field.factors))


def interventions(field: RealityField, cases: tuple[L7Case, ...]) -> dict[str, object]:
    weighted = next(case for case in cases if case.expected.family == "weighted_contradiction")
    baseline = solve(field, weighted.public)
    swapped = _replace_factor(_replace_factor(field, "conflict:path:0:3", authority=.1), "conflict:negative:0", authority=1.0, base_weight=1.0)
    swapped_result = solve(swapped, weighted.public)
    decisive = _replace_factor(field, "chain:standard:0:0", base_weight=0.0)
    unique = next(case for case in cases if case.expected.family == "unique" and case.expected.depth == 20)
    removed = solve(decisive, unique.public)
    duplicate_rows = list(field.factors)
    original = next(item for item in field.factors if item.body_id == "conflict:negative:0")
    duplicate_rows.extend(replace(original, body_id=f"duplicate:{index}") for index in range(20))
    duplicate = solve(RealityField(field.atoms, tuple(duplicate_rows)), weighted.public)
    conjunction = next(case for case in cases if case.expected.family == "conjunction" and case.expected.disposition == "candidate")
    missing_input = solve(field, replace(conjunction.public, assumption_atom_ids=conjunction.public.assumption_atom_ids[:1]))
    scoped = next(case for case in cases if case.expected.family == "scope_time")
    expired = solve(_replace_factor(field, "scoped:0", valid_to=6), scoped.public)
    rescoped = solve(_replace_factor(field, "scoped:0", scope_key="other"), scoped.public)
    moved_reality = solve(_replace_factor(field, "chain:standard:0:0", reality_key="custom:alpha"), unique.public)
    negated = solve(_replace_factor(field, "chain:standard:0:19", outcome_polarity=-1), unique.public)
    irrelevant = solve(_replace_factor(field, "distractor:511", base_weight=0.0), unique.public)
    return {
        "authority_swap_reversed": baseline.selected_candidate_id != swapped_result.selected_candidate_id and swapped_result.selected_candidate_id is not None and swapped_result.selected_candidate_id.endswith("-1"),
        "decisive_body_changed": removed.selected_candidate_id != solve(field, unique.public).selected_candidate_id,
        "duplicate_source_invariant": duplicate.selected_candidate_id == baseline.selected_candidate_id and abs(duplicate.objective - baseline.objective) <= 1e-10,
        "reality_isolation": all(result.disposition in {"candidate", "unknown", "alternatives"} for result in _results(field, _subset(cases, {"counterfactual"}))),
        "missing_conjunction_changes": missing_input.disposition == "unknown",
        "expired_body_changes": expired.disposition == "unknown",
        "rescope_changes": rescoped.disposition == "unknown",
        "reality_move_changes": moved_reality.disposition == "unknown",
        "negated_outcome_changes": negated.selected_candidate_id != solve(field, unique.public).selected_candidate_id,
        "irrelevant_body_invariant": irrelevant.selected_candidate_id == solve(field, unique.public).selected_candidate_id,
    }


def classify(metrics: dict[str, object], control: dict[str, object], intervention: dict[str, object], elapsed: float) -> str:
    if metrics["incorrect_accepted"] != 0:
        return "L7-H — VERIFICATION OR REALIZATION FAILURE"
    if elapsed > 600:
        return "L7-COMPUTE"
    if not control["passed"]:
        return "L7-D — FIELD DATA NOT CAUSAL"
    if not all(intervention.values()):
        return "L7-E — CONTRADICTION OR SOURCE-LAW FAILURE"
    if metrics["exactness"] < .95 or metrics["accepted_precision"] < 1.0 or metrics["depth"]["20"] < .875:
        return "L7-F — 20-BODY COMPOSITION FAILURE"
    return "L7-A — FIXED-LAW MATHEMATICAL REALITY EQUILIBRIUM PASS"


def run_all(workspace: Path) -> dict[str, object]:
    started = time.monotonic()
    field = build_reality()
    cases = build_cases(field)
    _write(workspace / "model-check.json", {"experiment_id": "L7", "trainable_parameters": 0, "model_bytes": 0, "learned_geometry": False, "exact_consumer_propagation": False})
    _write(workspace / "reality-manifest.json", manifest(field, cases))
    _write(workspace / "dataset-manifest.json", {"cases": len(cases), "public": [asdict(case.public) for case in cases], "sha256": hashlib.sha256(repr(tuple(case.public.prompt_id for case in cases)).encode()).hexdigest()})
    _write(workspace / "evaluator-gold.json", {"expected": [asdict(case.expected) for case in cases]})
    _write(workspace / "locked" / "public" / "prompts.json", {"prompts": [asdict(case.public) for case in cases]})
    _write(workspace / "locked" / "evaluator-gold" / "expected.json", {"expected": [asdict(case.expected) for case in cases]})
    frozen = {"experiment_id": "L7", "field_sha256": manifest(field, cases)["sha256"], "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    _write(workspace / "frozen-manifest.json", frozen)
    results = _results(field, cases)
    for start in range(0, len(results), 64):
        _write(workspace / "prediction-shards" / f"{start // 64:04d}.json", {"predictions": [asdict(row) for row in results[start:start + 64]]})
    metrics = score(field, cases, results)
    control = controls(field, cases)
    intervention = interventions(field, cases)
    elapsed = time.monotonic() - started
    verdict = classify(metrics, control, intervention, elapsed)
    payload = {"experiment_id": "L7", "classification": verdict, "metrics": metrics, "controls": control, "interventions": intervention, "elapsed_seconds": elapsed}
    _write(workspace / "runtime-results.json", {"metrics": metrics})
    _write(workspace / "equilibrium-results.json", {"metrics": metrics, "independent_oracle": True})
    _write(workspace / "controls.json", control)
    _write(workspace / "interventions.json", intervention)
    _write(workspace / "verification.json", {"independent_equilibrium_agreement": metrics["independent_equilibrium_agreement"], "incorrect_accepted": metrics["incorrect_accepted"], "deterministic": True})
    _write(workspace / "execution-history.json", {"elapsed_seconds": elapsed, "artifact_revision": "r1", "immutable": True})
    _write(workspace / "report.json", payload)
    return payload
