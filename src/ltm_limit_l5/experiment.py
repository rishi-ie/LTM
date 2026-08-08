"""Measured L5 execution harness with runtime/evaluator separation."""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np

from .dataset import PublicFieldCase
from .decoder import EquilibriumRealization, authorize, realize
from .field import EquilibriumFieldIndex, build_minimap
from .optimizer import Compatibility, optimize
from .schemas import FieldEquilibriumResult
from .verifier import certify_result

if TYPE_CHECKING:
    from .dataset import GeneratedCase


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    case_id: str
    control: str
    result: FieldEquilibriumResult
    realization: EquilibriumRealization | None
    runtime_ms: float
    energy_nonincreasing: bool
    convergence_certified: bool
    frontier_stable: bool
    certificate_count_matches: bool
    runtime_error: str | None


def wilson_interval(successes: int, cases: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if cases < 0 or successes < 0 or successes > cases:
        raise ValueError("invalid Wilson counts")
    if cases == 0:
        return (0.0, 1.0)
    rate = successes / cases
    denominator = 1.0 + z * z / cases
    center = (rate + z * z / (2.0 * cases)) / denominator
    radius = z * math.sqrt(rate * (1.0 - rate) / cases + z * z / (4.0 * cases * cases)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def _rate(rows: list[bool]) -> dict[str, object]:
    successes = sum(rows)
    return {
        "successes": successes,
        "cases": len(rows),
        "rate": successes / len(rows) if rows else 1.0,
        "wilson_95": wilson_interval(successes, len(rows)),
    }


def _index(case: PublicFieldCase) -> EquilibriumFieldIndex:
    vectors = np.asarray(case.vector_table, dtype=np.float32)
    cells, summaries = build_minimap(case.bodies, case.units, vectors)
    return EquilibriumFieldIndex(case.bodies, case.units, vectors, cells, summaries)


def _immediate_field(case: PublicFieldCase) -> PublicFieldCase:
    active = {item.semantic_key for item in case.prompt.influences}
    units = {item.unit_id: item for item in case.units}
    bodies = tuple(
        body
        for body in case.bodies
        if {units[item].semantic_key for item in body.input_unit_ids} <= active
    )
    return replace(case, bodies=bodies)


def _without_context_gates(case: PublicFieldCase) -> PublicFieldCase:
    influence = case.prompt.influences[0]
    bodies = tuple(
        replace(body, scope_key=influence.scope_key, reality_key=influence.reality_key)
        for body in case.bodies
    )
    body_ids = {item.body_id for item in bodies}
    units = tuple(
        replace(item, scope_key=influence.scope_key, reality_key=influence.reality_key)
        if item.body_id in body_ids
        else item
        for item in case.units
    )
    return replace(case, units=units, bodies=bodies)


def _body_signature(case: PublicFieldCase, body_id: str) -> tuple[object, ...]:
    units = {item.unit_id: item for item in case.units}
    body = next(item for item in case.bodies if item.body_id == body_id)
    return (
        tuple(sorted((units[item].semantic_key, units[item].polarity) for item in body.input_unit_ids)),
        tuple(sorted((units[item].semantic_key, units[item].polarity) for item in body.outcome_unit_ids)),
        body.scope_key,
        body.reality_key,
        body.valid_from,
        body.valid_to,
    )


def _raw_duplicate_field(case: PublicFieldCase) -> PublicFieldCase:
    groups: dict[tuple[object, ...], list[str]] = defaultdict(list)
    for body in case.bodies:
        groups[(body.independent_source_key, _body_signature(case, body.body_id))].append(body.body_id)
    changed_sources = {
        body_id: f"raw-duplicate:{body_id}"
        for rows in groups.values()
        for body_id in sorted(rows)[1:]
    }
    bodies = tuple(
        replace(body, independent_source_key=changed_sources[body.body_id])
        if body.body_id in changed_sources
        else body
        for body in case.bodies
    )
    units = tuple(
        replace(item, independent_source_key=changed_sources[item.body_id])
        if item.body_id in changed_sources
        else item
        for item in case.units
    )
    return replace(case, units=units, bodies=bodies)


def _empty_result(case: PublicFieldCase) -> FieldEquilibriumResult:
    return FieldEquilibriumResult(
        case.case_id,
        "unknown",
        (),
        (),
        (),
        None,
        (),
        (),
        (),
        "certified",
        ("CONTROL_NO_OPTIMIZATION",),
        (),
    )


def _fixed_state_compatibility(
    state: np.ndarray,
    body_input: np.ndarray,
    body_output: np.ndarray,
    body: object,
) -> float:
    del state, body_input, body_output, body
    return 0.0


def _random_geometry_compatibility(
    state: np.ndarray,
    body_input: np.ndarray,
    body_output: np.ndarray,
    body: object,
) -> float:
    del state, body_input, body_output
    body_id = str(getattr(body, "body_id", body))
    value = int.from_bytes(hashlib.sha256(body_id.encode()).digest()[:8], "big")
    return 0.05 + 0.95 * value / (2**64 - 1)


def run_runtime_case(
    case: PublicFieldCase,
    *,
    control: str = "full",
    maximum_steps: int = 64,
    compatibility: Compatibility | None = None,
) -> RuntimeObservation:
    """Run only public data through optimization, verification, and decoding.

    This capability boundary accepts no hidden scoring record or expected outcome.
    """

    if control not in {"full", "no_optimization", "single_mode", "fixed_frontier", "no_context", "raw_duplicates"}:
        raise ValueError(f"unknown L5 control: {control}")
    runtime_case = (
        _immediate_field(case)
        if control == "fixed_frontier"
        else _without_context_gates(case)
        if control == "no_context"
        else _raw_duplicate_field(case)
        if control == "raw_duplicates"
        else case
    )
    started = time.perf_counter()
    realization = None
    error = None
    try:
        result = (
            _empty_result(runtime_case)
            if control == "no_optimization"
            else optimize(
                _index(runtime_case),
                runtime_case.prompt,
                compatibility=compatibility,
                maximum_steps=maximum_steps,
                maximum_modes=1 if control == "single_mode" else 8,
            )
        )
        result = certify_result(runtime_case, result)
        view = authorize(result)
        archive = {item.semantic_key: item.semantic_key for item in runtime_case.units}
        realization = realize(view, archive)
    except (RuntimeError, ValueError) as caught:
        error = f"{type(caught).__name__}:{caught}"
        if "result" not in locals():
            result = _empty_result(runtime_case)
    elapsed = (time.perf_counter() - started) * 1_000.0
    nonincreasing = all(
        later.energy <= earlier.energy + 1e-8
        for earlier, later in zip(result.trajectory, result.trajectory[1:])
    )
    stable = len(result.frontiers) >= 3 and len({item.frontier_hash for item in result.frontiers[-3:]}) == 1
    return RuntimeObservation(
        case_id=case.case_id,
        control=control,
        result=result,
        realization=realization,
        runtime_ms=elapsed,
        energy_nonincreasing=nonincreasing,
        convergence_certified=result.coverage_disposition == "certified",
        frontier_stable=stable or result.disposition == "unknown" and not result.frontiers,
        certificate_count_matches=len(result.certificates) == len(result.candidates),
        runtime_error=error,
    )


def run_cases(
    cases: tuple[PublicFieldCase, ...],
    *,
    control: str = "full",
    compatibility: Compatibility | None = None,
) -> tuple[RuntimeObservation, ...]:
    return tuple(
        run_runtime_case(
            case,
            control=control,
            compatibility=compatibility,
        )
        for case in cases
    )


def _supplied_input_valid(case: PublicFieldCase) -> bool:
    if case.prompt.disposition != "accept" or case.prompt.encoder_calls != 1 or not case.prompt.influences:
        return False
    contexts = {(item.scope_key, item.reality_key, item.valid_at) for item in case.prompt.influences}
    vectors = {item.semantic_key: case.vector_table[item.semantic_vector_ref] for item in case.units}
    return len(contexts) == 1 and all(
        item.semantic_key in vectors
        and np.allclose(item.semantic_position, vectors[item.semantic_key], atol=1e-7, rtol=0.0)
        for item in case.prompt.influences
    )


def _decoder_correct(observation: RuntimeObservation) -> bool:
    output = observation.realization
    result = observation.result
    if output is None or output.disposition != result.disposition or output.failure_codes:
        return False
    if result.disposition == "candidate":
        return output.authorized_unit_ids == (result.selected_candidate_id,)
    if result.disposition in {"alternatives", "ambiguous"}:
        return set(output.authorized_unit_ids) == {item.unit_id for item in result.candidates}
    return not output.authorized_unit_ids


def evaluate_observations(
    generated: tuple[GeneratedCase, ...],
    observations: tuple[RuntimeObservation, ...],
) -> dict[str, object]:
    """Score completed runtime outputs using evaluator-only expectations."""

    from .evaluator import (
        gold_agrees,
        source_normalized_outcome,
        verify_candidate_certificate,
        verify_result,
    )

    by_id = {item.case_id: item for item in observations}
    if len(by_id) != len(observations) or {item.public.case_id for item in generated} != set(by_id):
        raise ValueError("generated/runtime identity mismatch")
    supplied_rows: list[bool] = []
    optimizer_rows: list[bool] = []
    end_to_end_rows: list[bool] = []
    accepted_rows: list[bool] = []
    energy_rows: list[bool] = []
    convergence_rows: list[bool] = []
    frontier_rows: list[bool] = []
    frontier_stability_rows: list[bool] = []
    certificate_rows: list[bool] = []
    decoder_rows: list[bool] = []
    corpus_rows: list[bool] = []
    family: dict[str, list[bool]] = defaultdict(list)
    domain: dict[str, list[bool]] = defaultdict(list)
    dependency: dict[str, list[bool]] = defaultdict(list)
    depth: dict[str, list[bool]] = defaultdict(list)
    runtimes: list[float] = []
    observations_payload = []
    for item in generated:
        public, expected = item.public, item.expected
        observation = by_id[public.case_id]
        supplied_ok = _supplied_input_valid(public)
        optimizer_ok = observation.runtime_error is None and verify_result(public, observation.result)
        decoder_ok = _decoder_correct(observation)
        end_to_end = supplied_ok and optimizer_ok and decoder_ok
        supplied_rows.append(supplied_ok)
        if supplied_ok:
            optimizer_rows.append(optimizer_ok)
        end_to_end_rows.append(end_to_end)
        decoder_rows.append(decoder_ok)
        if observation.result.disposition in {"candidate", "alternatives"}:
            accepted_rows.append(end_to_end)
        energy_rows.append(observation.energy_nonincreasing)
        convergence_rows.append(observation.convergence_certified)
        oracle = source_normalized_outcome(public)
        required = set(oracle.reachable_body_ids)
        opened = {body_id for snapshot in observation.result.frontiers for body_id in snapshot.body_ids}
        frontier_rows.append(not required or required <= opened)
        frontier_stability_rows.append(observation.frontier_stable)
        certificates = {row.candidate_unit_id: row for row in observation.result.certificates}
        certificate_ok = observation.certificate_count_matches and all(
            candidate.unit_id in certificates
            and verify_candidate_certificate(public, candidate, certificates[candidate.unit_id])
            for candidate in observation.result.candidates
        )
        certificate_rows.append(certificate_ok)
        corpus_rows.append(gold_agrees(public, expected))
        family[expected.family].append(end_to_end)
        domain[expected.domain].append(end_to_end)
        band = (
            "1"
            if expected.dependency_count == 1
            else "2_4"
            if expected.dependency_count <= 4
            else "5_8"
            if expected.dependency_count <= 8
            else "9_16"
        )
        dependency[band].append(end_to_end)
        depth[str(expected.dependency_count)].append(end_to_end)
        runtimes.append(observation.runtime_ms)
        observations_payload.append(
            {
                "case_id": public.case_id,
                "family": expected.family,
                "domain": expected.domain,
                "dependency_count": expected.dependency_count,
                "supplied_input_valid": supplied_ok,
                "optimizer_correct_from_supplied": optimizer_ok,
                "decoder_correct": decoder_ok,
                "end_to_end_correct_from_supplied": end_to_end,
                "disposition": observation.result.disposition,
                "runtime_error": observation.runtime_error,
            }
        )
    ordered_runtime = sorted(runtimes)
    p95_index = max(0, math.ceil(0.95 * len(ordered_runtime)) - 1) if ordered_runtime else 0
    return {
        "cases": len(generated),
        "supplied_input_contract": _rate(supplied_rows),
        "optimizer_conditional_on_supplied": _rate(optimizer_rows),
        "end_to_end_from_supplied": _rate(end_to_end_rows),
        "accepted_verified_precision": _rate(accepted_rows),
        "incorrect_accepted_candidates": len(accepted_rows) - sum(accepted_rows),
        "energy_nonincrease": _rate(energy_rows),
        "convergence_certified": _rate(convergence_rows),
        "required_body_frontier_recall": _rate(frontier_rows),
        "frontier_stability": _rate(frontier_stability_rows),
        "certificate_safety": _rate(certificate_rows),
        "decoder_authorization": _rate(decoder_rows),
        "corpus_oracle_agreement": _rate(corpus_rows),
        "family": {key: _rate(rows) for key, rows in sorted(family.items())},
        "domain": {key: _rate(rows) for key, rows in sorted(domain.items())},
        "dependency": {key: _rate(rows) for key, rows in sorted(dependency.items())},
        "depth": {key: _rate(rows) for key, rows in sorted(depth.items(), key=lambda item: int(item[0]))},
        "p50_runtime_ms": ordered_runtime[len(ordered_runtime) // 2] if ordered_runtime else 0.0,
        "p95_runtime_ms": ordered_runtime[p95_index] if ordered_runtime else 0.0,
        "observations": observations_payload,
    }


def _metric_rate(metrics: dict[str, object], *path: str) -> float:
    value: object = metrics
    for key in path:
        value = value[key]  # type: ignore[index]
    return float(value)


def run_control_panel(
    generated: tuple[GeneratedCase, ...],
    *,
    compatibility: Compatibility | None = None,
    minimum_geometry_gain: float = 0.05,
) -> dict[str, object]:
    if minimum_geometry_gain < 0:
        raise ValueError("minimum geometry gain cannot be negative")
    variants = ("full", "no_optimization", "single_mode", "fixed_frontier", "no_context", "raw_duplicates")
    reports = {
        name: evaluate_observations(
            generated,
            run_cases(
                tuple(item.public for item in generated),
                control=name,
                compatibility=compatibility,
            ),
        )
        for name in variants
    }
    public_cases = tuple(item.public for item in generated)
    reports.update(
        {
            "no_learned_geometry": evaluate_observations(
                generated,
                run_cases(public_cases, compatibility=None),
            ),
            "fixed_state": evaluate_observations(
                generated,
                run_cases(public_cases, compatibility=_fixed_state_compatibility),
            ),
            "random_geometry": evaluate_observations(
                generated,
                run_cases(public_cases, compatibility=_random_geometry_compatibility),
            ),
        }
    )
    deep = tuple(item for item in generated if item.expected.dependency_count >= 9)
    conflicting = tuple(
        item
        for item in generated
        if item.expected.family in {"balanced_contradiction", "alternatives"}
    )
    scoped = tuple(item for item in generated if item.expected.family == "scope_isolation")
    duplicated = tuple(item for item in generated if item.expected.family == "weighted_contradiction")
    full = reports["full"]
    full_exactness = _metric_rate(full, "end_to_end_from_supplied", "rate")
    full_observations = run_cases(public_cases, compatibility=compatibility)
    fixed_observations = run_cases(
        public_cases,
        compatibility=_fixed_state_compatibility,
    )
    effects = {
        "full_minus_no_optimization": _metric_rate(full, "end_to_end_from_supplied", "rate")
        - _metric_rate(reports["no_optimization"], "end_to_end_from_supplied", "rate"),
        "full_minus_no_learned_geometry": full_exactness
        - _metric_rate(reports["no_learned_geometry"], "end_to_end_from_supplied", "rate"),
        "full_minus_fixed_state": full_exactness
        - _metric_rate(reports["fixed_state"], "end_to_end_from_supplied", "rate"),
        "full_minus_random_geometry": full_exactness
        - _metric_rate(reports["random_geometry"], "end_to_end_from_supplied", "rate"),
        "full_state_movement_rate": _state_movement_rate(full_observations),
        "fixed_state_movement_rate": _state_movement_rate(fixed_observations),
        "full_minus_fixed_frontier_deep": (
            _metric_rate(
                evaluate_observations(
                    deep,
                    run_cases(
                        tuple(item.public for item in deep),
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            - _metric_rate(
                evaluate_observations(
                    deep,
                    run_cases(
                        tuple(item.public for item in deep),
                        control="fixed_frontier",
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            if deep
            else 0.0
        ),
        "multi_minus_single_mode_conflicts": (
            _metric_rate(
                evaluate_observations(
                    conflicting,
                    run_cases(
                        tuple(item.public for item in conflicting),
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            - _metric_rate(
                evaluate_observations(
                    conflicting,
                    run_cases(
                        tuple(item.public for item in conflicting),
                        control="single_mode",
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            if conflicting
            else 0.0
        ),
        "context_gate_drop": (
            _metric_rate(
                evaluate_observations(
                    scoped,
                    run_cases(
                        tuple(item.public for item in scoped),
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            - _metric_rate(
                evaluate_observations(
                    scoped,
                    run_cases(
                        tuple(item.public for item in scoped),
                        control="no_context",
                        compatibility=compatibility,
                    ),
                ),
                "end_to_end_from_supplied",
                "rate",
            )
            if scoped
            else 0.0
        ),
        "raw_duplicate_semantic_changes": (
            sum(
                _semantic_result(full_row) != _semantic_result(raw_row)
                for full_row, raw_row in zip(
                    run_cases(
                        tuple(item.public for item in duplicated),
                        compatibility=compatibility,
                    ),
                    run_cases(
                        tuple(item.public for item in duplicated),
                        control="raw_duplicates",
                        compatibility=compatibility,
                    ),
                    strict=True,
                )
            )
            if duplicated
            else 0
        ),
    }
    mechanism_gates = {
        "learned_compatibility_supplied": compatibility is not None,
        "full_outperforms_no_learned_geometry": effects["full_minus_no_learned_geometry"]
        >= minimum_geometry_gain,
        "full_outperforms_fixed_state": effects["full_minus_fixed_state"]
        >= minimum_geometry_gain,
        "full_outperforms_random_geometry": effects["full_minus_random_geometry"]
        >= minimum_geometry_gain,
        "full_state_moves": effects["full_state_movement_rate"] > 0.0,
        "fixed_state_stays_fixed": effects["fixed_state_movement_rate"] == 0.0,
    }
    mechanism_gates["passed"] = all(mechanism_gates.values())
    return {
        "variants": reports,
        "effects": effects,
        "mechanism_gates": mechanism_gates,
        "minimum_geometry_gain": minimum_geometry_gain,
    }


def _state_movement_rate(observations: tuple[RuntimeObservation, ...]) -> float:
    moved = []
    for observation in observations:
        initial = observation.result.initial_modes
        final = observation.result.final_modes
        anchor = np.asarray(initial[0].semantic_position, dtype=np.float32) if initial else None
        moved.append(
            anchor is not None
            and any(
                float(
                    np.linalg.norm(
                        np.asarray(item.semantic_position, dtype=np.float32) - anchor
                    )
                )
                > 1e-6
                for item in final
            )
        )
    return sum(moved) / len(moved) if moved else 0.0


def _semantic_result(observation: RuntimeObservation) -> tuple[object, ...]:
    result = observation.result
    selected = next(
        (
            (item.semantic_key, item.polarity)
            for item in result.candidates
            if item.unit_id == result.selected_candidate_id
        ),
        None,
    )
    candidates = tuple(sorted((item.semantic_key, item.polarity) for item in result.candidates))
    return result.disposition, selected, candidates


def run_interventions(
    generated: tuple[GeneratedCase, ...],
    *,
    compatibility: Compatibility | None = None,
) -> dict[str, object]:
    from .evaluator import source_normalized_outcome

    relevant: list[bool] = []
    irrelevant: list[bool] = []
    duplicate: list[bool] = []
    conjunction: list[bool] = []
    direction: list[bool] = []
    for item in generated:
        case = item.public
        baseline = run_runtime_case(case, compatibility=compatibility)
        oracle = source_normalized_outcome(case)
        if oracle.candidates:
            target = next(
                (row for row in oracle.candidates if (row.semantic_key, row.polarity) == oracle.selected),
                oracle.candidates[0],
            )
            units = {unit.unit_id: unit for unit in case.units}
            terminal = {
                body.body_id
                for body in case.bodies
                if any(
                    (units[unit_id].semantic_key, units[unit_id].polarity)
                    == (target.semantic_key, target.polarity)
                    for unit_id in body.outcome_unit_ids
                )
            }
            changed = replace(case, bodies=tuple(body for body in case.bodies if body.body_id not in terminal))
            relevant.append(
                _semantic_result(
                    run_runtime_case(changed, compatibility=compatibility)
                )
                != _semantic_result(baseline)
            )
        if item.expected.family == "scope_isolation":
            influence = case.prompt.influences[0]
            kept = tuple(
                body
                for body in case.bodies
                if body.reality_key == influence.reality_key
                and body.scope_key in {"global", influence.scope_key}
            )
            irrelevant.append(
                _semantic_result(
                    run_runtime_case(
                        replace(case, bodies=kept),
                        compatibility=compatibility,
                    )
                )
                == _semantic_result(baseline)
            )
        if item.expected.family == "weighted_contradiction":
            groups: dict[tuple[object, ...], list[str]] = defaultdict(list)
            for body in case.bodies:
                groups[(body.independent_source_key, _body_signature(case, body.body_id))].append(body.body_id)
            removable = {body_id for rows in groups.values() for body_id in sorted(rows)[1:]}
            reduced = replace(case, bodies=tuple(body for body in case.bodies if body.body_id not in removable))
            duplicate.append(
                _semantic_result(
                    run_runtime_case(reduced, compatibility=compatibility)
                )
                == _semantic_result(baseline)
            )
        if item.expected.family == "conjunction" and len(case.prompt.influences) > 1:
            prompt = replace(
                case.prompt,
                influences=case.prompt.influences[:1],
                anchor_position=case.prompt.influences[0].semantic_position,
            )
            conjunction.append(
                _semantic_result(
                    run_runtime_case(
                        replace(case, prompt=prompt),
                        compatibility=compatibility,
                    )
                )
                != _semantic_result(baseline)
            )
        if item.expected.family == "one_body" and oracle.selected is not None:
            semantic_key, polarity = oracle.selected
            outcome = next(
                unit
                for unit in case.units
                if (unit.semantic_key, unit.polarity) == (semantic_key, polarity)
            )
            vector = case.vector_table[outcome.semantic_vector_ref]
            reverse_influence = replace(
                case.prompt.influences[0],
                unit_id=f"direction-control:{case.case_id}",
                semantic_key=semantic_key,
                semantic_position=vector,
            )
            reverse_prompt = replace(
                case.prompt,
                influences=(reverse_influence,),
                anchor_position=vector,
            )
            reversed_result = run_runtime_case(
                replace(case, prompt=reverse_prompt),
                compatibility=compatibility,
            ).result
            direction.append(
                baseline.result.disposition == "candidate"
                and reversed_result.disposition == "unknown"
                and not reversed_result.candidates
            )
    return {
        "relevant_removal_accuracy": _rate(relevant),
        "irrelevant_region_invariance": _rate(irrelevant),
        "duplicate_source_invariance": _rate(duplicate),
        "conjunction_input_sensitivity": _rate(conjunction),
        "direction_reversal_accuracy": _rate(direction),
    }


def classification(
    config: dict[str, object],
    metrics: dict[str, object],
    controls: dict[str, object] | None = None,
    interventions: dict[str, object] | None = None,
    compiler_metrics: dict[str, object] | None = None,
) -> str:
    gates = config["gates"]
    if (
        metrics["incorrect_accepted_candidates"] != 0
        or _metric_rate(metrics, "energy_nonincrease", "rate") < 1.0
        or _metric_rate(metrics, "certificate_safety", "rate") < 1.0
        or _metric_rate(metrics, "corpus_oracle_agreement", "rate") < 1.0
        or _metric_rate(metrics, "supplied_input_contract", "rate") < 1.0
        or compiler_metrics is not None
        and int(compiler_metrics.get("incorrect_accepted_compilations", 0)) != 0
    ):
        return "L5-G — INTEGRITY OR LEAKAGE FAILURE"
    if compiler_metrics is None or (
        float(compiler_metrics.get("accepted_semantic_precision", 0.0))
        < float(gates["compiler_precision"])
        or float(compiler_metrics.get("safe_coverage", 0.0))
        < float(gates["compiler_safe_coverage"])
        or float(compiler_metrics.get("exact_content_agreement", 0.0))
        < float(gates["compiler_exact_content"])
        or float(compiler_metrics.get("coordinate_recall_at_8", 0.0))
        < float(gates["coordinate_recall_at_8"])
    ):
        return "L5-B — PROMPT OR SOURCE COMPILATION FAILURE"
    family = metrics["family"]
    if (
        _metric_rate(family, "one_body", "rate") < float(gates["one_body_completion"])
        or _metric_rate(family, "conjunction", "rate") < float(gates["multi_input_completeness"])
    ):
        return "L5-C — SHARED COORDINATE OR LOCAL FIELD-LAW FAILURE"
    if _metric_rate(metrics, "required_body_frontier_recall", "rate") < 0.99:
        return "L5-D — MINIMAP OR DYNAMIC FRONTIER FAILURE"
    dependency = metrics["dependency"]
    if (
        _metric_rate(dependency, "2_4", "rate") < float(gates["dependency_2_4"])
        or _metric_rate(dependency, "5_8", "rate") < float(gates["dependency_5_8"])
        or _metric_rate(dependency, "9_16", "rate") < float(gates["dependency_9_16"])
        or controls is not None
        and _metric_rate(controls, "effects", "full_minus_no_optimization")
        < float(gates["full_minus_no_optimization"])
        or _metric_rate(metrics, "convergence_certified", "rate") < 0.99
        or _metric_rate(metrics, "frontier_stability", "rate") < 0.99
    ):
        return "L5-E — LATENT EQUILIBRIUM FAILURE"
    if controls is not None and not bool(
        controls.get("mechanism_gates", {}).get("passed", False)  # type: ignore[union-attr]
    ):
        return "L5-E — LATENT EQUILIBRIUM FAILURE"
    if (
        _metric_rate(family, "weighted_contradiction", "rate") < float(gates["weighted_contradiction"])
        or _metric_rate(family, "balanced_contradiction", "rate") < float(gates["ambiguity_unknown_recall"])
        or _metric_rate(family, "alternatives", "rate") < float(gates["ambiguity_unknown_recall"])
    ):
        return "L5-F — CONTRADICTION OR MULTI-HYPOTHESIS FAILURE"
    if (
        _metric_rate(metrics, "decoder_authorization", "rate") < 1.0
        or _metric_rate(metrics, "end_to_end_from_supplied", "rate")
        < _metric_rate(metrics, "optimizer_conditional_on_supplied", "rate")
    ):
        return "L5-H — VERIFICATION OR DECODER HANDOFF FAILURE"
    if interventions is not None and any(
        _metric_rate(interventions, key, "rate")
        < (
            float(gates["force_direction"])
            if key == "direction_reversal_accuracy"
            else 0.95
        )
        for key in (
            "relevant_removal_accuracy",
            "irrelevant_region_invariance",
            "duplicate_source_invariance",
            "conjunction_input_sensitivity",
            "direction_reversal_accuracy",
        )
        if interventions[key]["cases"]
    ):
        return "L5-E — LATENT EQUILIBRIUM FAILURE"
    if (
        _metric_rate(metrics, "accepted_verified_precision", "rate") < 1.0
        or _metric_rate(metrics, "end_to_end_from_supplied", "rate")
        < float(gates["all_case_exactness"])
    ):
        return "L5-S — SAFE BUT LOW COVERAGE"
    return "L5-A — COMPILED LATENT FIELD EQUILIBRIUM PASS"


__all__ = [
    "RuntimeObservation",
    "classification",
    "evaluate_observations",
    "run_cases",
    "run_control_panel",
    "run_interventions",
    "run_runtime_case",
    "wilson_interval",
]
