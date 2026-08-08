"""Evaluator-owned L5 reachability, source normalization, and certificates.

This module intentionally does not import the learned field kernel or runtime
optimizer. It reconstructs support directly from public bodies and contexts.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass

from .dataset import ExpectedOutcome, PublicFieldCase
from .schemas import (
    EquilibriumBody,
    EquilibriumCandidate,
    FieldEquilibriumResult,
    SupportCertificate,
)

VERIFIER_REVISION = "l5-independent-oracle/1"

SCORE_METRIC_SEMANTICS = {
    "corpus_oracle_agreement": (
        "Evaluator-authored ExpectedOutcome rows exactly match an independently "
        "reconstructed source-normalized oracle; this audits the corpus, not the model."
    ),
    "safe_coverage": (
        "Legacy compatibility metric: independently exact results divided by all "
        "cases; currently identical to all_case_exactness."
    ),
    "all_case_exactness": (
        "Cases passing strict result disposition, full candidate-set, selected-state, "
        "support-certificate, identity, and no-factual-operation verification."
    ),
    "accepted_verified_precision": (
        "Strictly exact results divided by results whose runtime disposition is "
        "candidate or alternatives; ambiguous and abstaining dispositions are excluded."
    ),
    "answerable_case_exactness": (
        "Independently exact results among cases whose evaluator outcome contains "
        "at least one source-backed candidate."
    ),
    "answerable_exactness": "Alias of answerable_case_exactness for configured-gate compatibility.",
    "unsupported_case_exactness": (
        "Independently exact results among cases whose evaluator outcome contains no "
        "source-backed candidate."
    ),
    "global_optimum_oracle_agreement": (
        "Runtime disposition and selected source-normalized optimum (or complete "
        "tied optimum set) agree with the independent oracle."
    ),
    "global_optimum_agreement": "Alias of global_optimum_oracle_agreement.",
    "oracle_disposition_agreement": (
        "Runtime disposition equals the independently reconstructed oracle disposition, "
        "without implying candidate or certificate correctness."
    ),
    "candidate_set_exactness": (
        "Runtime semantic-key/polarity candidate set equals the full independent oracle "
        "candidate set, without implying selection or certificate correctness."
    ),
    "selected_optimum_agreement": (
        "Runtime selected semantic-key/polarity equals the oracle selection, including "
        "both being absent; disposition and candidate-set checks are separate."
    ),
    "energy_nonincrease": (
        "Cases with no non-finite or increasing transition between consecutive "
        "persisted accepted energy steps; the unrecorded initial energy is excluded."
    ),
    "accepted_energy_increases": (
        "Count of non-finite or increasing transitions between consecutive persisted "
        "accepted energy steps."
    ),
    "coverage_certification": (
        "Cases marked certified whose final public frontier coverage meets the "
        "profile threshold and whose frontier bounds are finite and valid."
    ),
    "convergence_certification": (
        "Cases whose final three recorded steps are accepted, below the residual "
        "threshold, and share one stable frontier hash."
    ),
    "frontier_stability": (
        "Cases whose final configured number of public frontier snapshots share one "
        "frontier hash; residual and coverage checks are separate."
    ),
    "certificate_safety": (
        "Cases with exactly one independently reconstructed, byte-equal support "
        "certificate per runtime candidate and no extra certificate. A certificate may "
        "name one complete derivation subset; aggregate confidence is checked separately."
    ),
    "candidate_confidence_agreement": (
        "Cases where every runtime candidate confidence equals 1-exp(-2*support_mass) "
        "from the full independent source-normalized oracle candidate."
    ),
    "factual_operation_safety": (
        "Cases whose result contains no factual topology operation."
    ),
    "required_body_frontier_recall": (
        "Micro recall of independently reachable body IDs in the union of runtime "
        "frontier snapshots."
    ),
    "required_body_frontier_complete": (
        "Cases with at least one independently reachable body for which every such body "
        "appears in some runtime frontier snapshot."
    ),
    "certified_all_case_exactness": (
        "Strictly exact cases that also pass energy, coverage, convergence, certificate, "
        "and no-factual-operation checks."
    ),
    "certified_answerable_case_exactness": (
        "Certified strict exactness restricted to evaluator-answerable cases."
    ),
    "ambiguity_unknown_recall": (
        "Expected ambiguous or unknown cases receiving the matching oracle disposition; "
        "candidate and certificate checks are separate."
    ),
    "family_domain_dependency_depth_exactness": (
        "Strict all-case exactness grouped independently by evaluator family, domain, "
        "dependency band, and exact dependency count."
    ),
}


@dataclass(frozen=True, slots=True)
class OracleCandidate:
    semantic_key: str
    polarity: int
    support_mass: float
    unit_ids: tuple[str, ...]
    body_ids: tuple[str, ...]
    source_keys: tuple[str, ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OracleOutcome:
    disposition: str
    candidates: tuple[OracleCandidate, ...]
    selected: tuple[str, int] | None
    reachable_body_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Activation:
    strength: float
    terminal_source: str
    body_ids: frozenset[str]
    terminal_body_id: str | None


def _compatible(case: PublicFieldCase, body: EquilibriumBody) -> bool:
    contexts = {(item.scope_key, item.reality_key, item.valid_at) for item in case.prompt.influences}
    for scope, reality, valid_at in contexts:
        time_ok = (valid_at is None or body.valid_from is None or valid_at >= body.valid_from) and (
            valid_at is None or body.valid_to is None or valid_at <= body.valid_to
        )
        if body.scope_key in {"global", scope} and body.reality_key == reality and time_ok:
            return True
    return False


def source_normalized_outcome(case: PublicFieldCase, *, source_mass_cap: float = 8.0) -> OracleOutcome:
    """Independently resolve reachable terminal hypotheses from exact bodies."""

    if not math.isfinite(source_mass_cap) or source_mass_cap <= 0:
        raise ValueError("source mass cap must be positive and finite")
    units = {item.unit_id: item for item in case.units}
    bodies = {item.body_id: item for item in case.bodies}
    compatible = tuple(sorted((item for item in case.bodies if _compatible(case, item)), key=lambda item: item.body_id))
    semantic_activation: dict[tuple[str, int], _Activation] = {}
    unit_activation: dict[str, _Activation] = {}
    for influence in case.prompt.influences:
        strength = (
            influence.clamp_strength
            * influence.query_relevance_weight
            * influence.modality_weight
            * influence.compiler_confidence
        )
        semantic_activation[(influence.semantic_key, influence.polarity_sign)] = _Activation(
            strength, f"prompt:{case.case_id}", frozenset(), None
        )

    signatures = {
        body.body_id: tuple((units[unit_id].semantic_key, units[unit_id].polarity) for unit_id in body.input_unit_ids)
        for body in compatible
    }
    consumers: dict[tuple[str, int], list[EquilibriumBody]] = defaultdict(list)
    for body in compatible:
        for signature in signatures[body.body_id]:
            consumers[signature].append(body)
    queue = deque(
        body for body in compatible if all(signature in semantic_activation for signature in signatures[body.body_id])
    )
    scheduled = {body.body_id for body in queue}
    reachable: set[str] = set()
    while queue:
        body = queue.popleft()
        scheduled.discard(body.body_id)
        required = signatures[body.body_id]
        if not all(signature in semantic_activation for signature in required):
            continue
        body_strength = body.base_weight * body.authority * body.confidence
        input_strength = min(semantic_activation[signature].strength for signature in required)
        strength = min(body_strength, input_strength)
        closure = frozenset({body.body_id}).union(
            *(semantic_activation[signature].body_ids for signature in required)
        )
        reachable.add(body.body_id)
        for output_id in body.outcome_unit_ids:
            previous = unit_activation.get(output_id)
            proposal = _Activation(strength, body.independent_source_key, closure, body.body_id)
            changed = previous is None or proposal.strength > previous.strength + 1e-15
            if previous is not None and abs(proposal.strength - previous.strength) <= 1e-15:
                merged = previous.body_ids | proposal.body_ids
                changed = merged != previous.body_ids
                proposal = _Activation(
                    previous.strength,
                    previous.terminal_source,
                    merged,
                    previous.terminal_body_id,
                )
            if not changed:
                continue
            unit_activation[output_id] = proposal
            output = units[output_id]
            signature = (output.semantic_key, output.polarity)
            semantic_previous = semantic_activation.get(signature)
            semantic_changed = semantic_previous is None or proposal.strength > semantic_previous.strength + 1e-15
            if semantic_previous is not None and abs(proposal.strength - semantic_previous.strength) <= 1e-15:
                merged = semantic_previous.body_ids | proposal.body_ids
                semantic_changed = merged != semantic_previous.body_ids
                proposal = _Activation(
                    semantic_previous.strength,
                    semantic_previous.terminal_source,
                    merged,
                    semantic_previous.terminal_body_id,
                )
            if not semantic_changed:
                continue
            semantic_activation[signature] = proposal
            for consumer in consumers[signature]:
                if consumer.body_id not in scheduled and all(
                    item in semantic_activation for item in signatures[consumer.body_id]
                ):
                    queue.append(consumer)
                    scheduled.add(consumer.body_id)

    input_signatures = {
        (units[unit_id].semantic_key, units[unit_id].polarity)
        for body in compatible
        for unit_id in body.input_unit_ids
    }
    terminal_ids = {
        unit_id
        for body in compatible
        for unit_id in body.outcome_unit_ids
        if (units[unit_id].semantic_key, units[unit_id].polarity) not in input_signatures
        and unit_id in unit_activation
    }
    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for unit_id in terminal_ids:
        unit = units[unit_id]
        groups[(unit.semantic_key, unit.polarity)].append(unit_id)

    candidates: list[OracleCandidate] = []
    for (semantic_key, polarity), unit_ids in groups.items():
        per_source_signature: dict[tuple[object, ...], float] = {}
        body_ids: set[str] = set()
        for unit_id in unit_ids:
            item = unit_activation[unit_id]
            if item.terminal_body_id is None:
                raise AssertionError("terminal field outcome has no source body")
            terminal_body = bodies[item.terminal_body_id]
            signature = (
                tuple(sorted((units[value].semantic_key, units[value].polarity) for value in terminal_body.input_unit_ids)),
                tuple(sorted((units[value].semantic_key, units[value].polarity) for value in terminal_body.outcome_unit_ids)),
                terminal_body.scope_key,
                terminal_body.reality_key,
                terminal_body.valid_from,
                terminal_body.valid_to,
            )
            source_signature = (item.terminal_source, signature)
            per_source_signature[source_signature] = max(
                per_source_signature.get(source_signature, 0.0), item.strength
            )
            body_ids.update(item.body_ids)
        source_keys = {bodies[body_id].independent_source_key for body_id in body_ids}
        provenance = {value for body_id in body_ids for value in bodies[body_id].provenance_ids}
        candidates.append(
            OracleCandidate(
                semantic_key=semantic_key,
                polarity=polarity,
                support_mass=min(source_mass_cap, sum(per_source_signature.values())),
                unit_ids=tuple(sorted(unit_ids)),
                body_ids=tuple(sorted(body_ids)),
                source_keys=tuple(sorted(source_keys)),
                provenance_ids=tuple(sorted(provenance)),
            )
        )
    candidates.sort(key=lambda item: (-item.support_mass, item.semantic_key, -item.polarity))
    if not candidates:
        return OracleOutcome("unknown", (), None, tuple(sorted(reachable)))

    maximum = candidates[0].support_mass
    tied = tuple(item for item in candidates if abs(item.support_mass - maximum) <= 1e-12)
    if len(tied) == 1:
        selected = (tied[0].semantic_key, tied[0].polarity)
        disposition = "candidate"
    elif len({item.semantic_key for item in tied}) == 1 and len({item.polarity for item in tied}) > 1:
        selected = None
        disposition = "ambiguous"
    else:
        selected = None
        disposition = "alternatives"
    return OracleOutcome(disposition, tuple(candidates), selected, tuple(sorted(reachable)))


def gold_agrees(case: PublicFieldCase, expected: ExpectedOutcome, *, tolerance: float = 1e-12) -> bool:
    oracle = source_normalized_outcome(case)
    if expected.case_id != case.case_id or expected.disposition != oracle.disposition or expected.selected != oracle.selected:
        return False
    expected_rows = {(item.semantic_key, item.polarity): item.support_mass for item in expected.candidates}
    oracle_rows = {(item.semantic_key, item.polarity): item.support_mass for item in oracle.candidates}
    return expected_rows.keys() == oracle_rows.keys() and all(
        abs(value - oracle_rows[key]) <= tolerance for key, value in expected_rows.items()
    )


def _certificate_hash(
    candidate_unit_id: str,
    body_ids: tuple[str, ...],
    source_keys: tuple[str, ...],
    provenance_ids: tuple[str, ...],
) -> str:
    payload = json.dumps(
        {
            "candidate_unit_id": candidate_unit_id,
            "body_ids": body_ids,
            "source_keys": source_keys,
            "provenance_ids": provenance_ids,
            "verifier_revision": VERIFIER_REVISION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def certificate_for(case: PublicFieldCase, candidate: EquilibriumCandidate) -> SupportCertificate:
    oracle = source_normalized_outcome(case)
    match = next(
        (
            item
            for item in oracle.candidates
            if candidate.unit_id in item.unit_ids
            and candidate.semantic_key == item.semantic_key
            and candidate.polarity == item.polarity
        ),
        None,
    )
    if match is None:
        raise ValueError("candidate is not source-backed")
    body_ids = tuple(sorted(candidate.supporting_body_ids))
    source_keys = tuple(sorted(candidate.supporting_source_keys))
    provenance_ids = tuple(sorted(candidate.provenance_ids))
    if not body_ids or not set(body_ids) <= set(match.body_ids):
        raise ValueError("candidate support does not match independent reconstruction")
    bodies = {item.body_id: item for item in case.bodies}
    units = {item.unit_id: item for item in case.units}
    if any(item not in bodies for item in body_ids):
        raise ValueError("candidate support contains an unknown body")
    active = {(item.semantic_key, item.polarity_sign) for item in case.prompt.influences}
    remaining = set(body_ids)
    while remaining:
        ready = [
            item
            for item in sorted(remaining)
            if {(units[value].semantic_key, units[value].polarity) for value in bodies[item].input_unit_ids}
            <= active
        ]
        if not ready:
            raise ValueError("candidate support is not a complete source-backed path")
        for body_id in ready:
            active.update(
                (units[value].semantic_key, units[value].polarity)
                for value in bodies[body_id].outcome_unit_ids
            )
            remaining.remove(body_id)
    if (candidate.semantic_key, candidate.polarity) not in active:
        raise ValueError("candidate support does not derive the candidate")
    expected_sources = tuple(sorted({bodies[item].independent_source_key for item in body_ids}))
    expected_provenance = tuple(
        sorted({value for item in body_ids for value in bodies[item].provenance_ids})
    )
    if source_keys != expected_sources or provenance_ids != expected_provenance:
        raise ValueError("candidate support metadata differs from exact bodies")
    return SupportCertificate(
        candidate_unit_id=candidate.unit_id,
        body_ids=body_ids,
        source_keys=source_keys,
        provenance_ids=provenance_ids,
        verifier_revision=VERIFIER_REVISION,
        verified=True,
        certificate_hash=_certificate_hash(candidate.unit_id, body_ids, source_keys, provenance_ids),
    )


def verify_candidate_certificate(
    case: PublicFieldCase,
    candidate: EquilibriumCandidate,
    certificate: SupportCertificate,
) -> bool:
    try:
        expected = certificate_for(case, candidate)
    except ValueError:
        return False
    return certificate == expected


def verify_result(case: PublicFieldCase, result: FieldEquilibriumResult) -> bool:
    if result.prompt_id != case.case_id or result.factual_operations:
        return False
    oracle = source_normalized_outcome(case)
    if result.disposition != oracle.disposition:
        return False
    by_unit = {item.unit_id: item for item in result.candidates}
    certificates = {item.candidate_unit_id: item for item in result.certificates}
    if by_unit.keys() != certificates.keys():
        return False
    if any(not verify_candidate_certificate(case, item, certificates[item.unit_id]) for item in result.candidates):
        return False
    observed = {(item.semantic_key, item.polarity) for item in result.candidates}
    expected = {(item.semantic_key, item.polarity) for item in oracle.candidates}
    if observed != expected:
        return False
    if not _candidate_confidence_agrees(oracle, result):
        return False
    if oracle.selected is None:
        return result.selected_candidate_id is None
    selected = by_unit.get(result.selected_candidate_id or "")
    return selected is not None and (selected.semantic_key, selected.polarity) == oracle.selected


def _candidate_signatures(result: FieldEquilibriumResult) -> set[tuple[str, int]]:
    return {(item.semantic_key, item.polarity) for item in result.candidates}


def _selected_signature(result: FieldEquilibriumResult) -> tuple[str, int] | None:
    if result.selected_candidate_id is None:
        return None
    selected = next(
        (item for item in result.candidates if item.unit_id == result.selected_candidate_id),
        None,
    )
    return None if selected is None else (selected.semantic_key, selected.polarity)


def _global_optimum_agrees(oracle: OracleOutcome, result: FieldEquilibriumResult) -> bool:
    """Compare only the oracle optimum, separately from certificate correctness."""

    if result.disposition != oracle.disposition:
        return False
    if oracle.selected is not None:
        return _selected_signature(result) == oracle.selected
    if result.selected_candidate_id is not None:
        return False
    if not oracle.candidates:
        return not result.candidates
    maximum = max(item.support_mass for item in oracle.candidates)
    expected = {
        (item.semantic_key, item.polarity)
        for item in oracle.candidates
        if abs(item.support_mass - maximum) <= 1e-12
    }
    return _candidate_signatures(result) == expected


def _candidate_confidence_agrees(
    oracle: OracleOutcome,
    result: FieldEquilibriumResult,
    *,
    tolerance: float = 1e-9,
) -> bool:
    observed = {
        (item.semantic_key, item.polarity): item.confidence
        for item in result.candidates
    }
    expected = {
        (item.semantic_key, item.polarity): 1.0 - math.exp(-2.0 * item.support_mass)
        for item in oracle.candidates
    }
    return observed.keys() == expected.keys() and all(
        math.isfinite(value)
        and math.isclose(value, expected[key], rel_tol=tolerance, abs_tol=tolerance)
        for key, value in observed.items()
    )


def _certificate_safe(case: PublicFieldCase, result: FieldEquilibriumResult) -> bool:
    candidates = {item.unit_id: item for item in result.candidates}
    certificates = {item.candidate_unit_id: item for item in result.certificates}
    if (
        len(candidates) != len(result.candidates)
        or len(certificates) != len(result.certificates)
        or candidates.keys() != certificates.keys()
    ):
        return False
    return all(
        verify_candidate_certificate(case, candidate, certificates[unit_id])
        for unit_id, candidate in candidates.items()
    )


def _accepted_energy_increases(
    result: FieldEquilibriumResult,
    *,
    tolerance: float,
) -> int:
    increases = 0
    previous: float | None = None
    for step in result.trajectory:
        if not step.accepted:
            continue
        if not math.isfinite(step.energy):
            increases += 1
            previous = None
            continue
        if previous is not None and step.energy > previous + tolerance:
            increases += 1
        previous = step.energy
    return increases


def _coverage_certified(
    result: FieldEquilibriumResult,
    *,
    coverage_threshold: float,
) -> bool:
    if result.coverage_disposition != "certified" or not result.frontiers:
        return False
    bounds = tuple(item.coverage_bound for item in result.frontiers)
    return (
        result.disposition != "incomplete_frontier"
        and all(math.isfinite(item) and 0 <= item <= 1 for item in bounds)
        and bounds[-1] >= coverage_threshold
    )


def _frontier_stable(result: FieldEquilibriumResult, *, stability_steps: int) -> bool:
    if stability_steps <= 0 or len(result.frontiers) < stability_steps:
        return False
    tail = result.frontiers[-stability_steps:]
    return len({item.frontier_hash for item in tail}) == 1


def _convergence_certified(
    result: FieldEquilibriumResult,
    *,
    convergence_residual: float,
    stability_steps: int,
) -> bool:
    if stability_steps <= 0 or len(result.trajectory) < stability_steps:
        return False
    tail = result.trajectory[-stability_steps:]
    return (
        _frontier_stable(result, stability_steps=stability_steps)
        and all(
            item.accepted
            and math.isfinite(item.residual)
            and 0 <= item.residual <= convergence_residual
            for item in tail
        )
        and len({item.frontier_hash for item in tail}) == 1
    )


def _rate(successes: int, cases: int, *, empty: float = 1.0) -> float:
    return successes / cases if cases else empty


def score_results(
    cases: tuple[PublicFieldCase, ...],
    gold: tuple[ExpectedOutcome, ...],
    results: tuple[FieldEquilibriumResult, ...],
    *,
    coverage_threshold: float = 0.90,
    convergence_residual: float = 1e-3,
    stability_steps: int = 3,
    energy_tolerance: float = 1e-8,
) -> dict[str, object]:
    """Score persisted results without importing optimizer or decoder state.

    Existing keys retain their historical meanings. In particular,
    ``safe_coverage`` remains an alias of strict all-case exactness for backward
    compatibility. New keys expose answerability, oracle optimum, dynamics,
    frontier, and certificate boundaries independently.
    """

    if not 0 <= coverage_threshold <= 1:
        raise ValueError("coverage threshold outside [0,1]")
    if convergence_residual < 0 or stability_steps <= 0 or energy_tolerance < 0:
        raise ValueError("invalid evaluator certification threshold")
    if len(cases) != len(gold) or len(cases) != len(results):
        raise ValueError("public/gold/result count mismatch")
    gold_by_id = {item.case_id: item for item in gold}
    result_by_id = {item.prompt_id: item for item in results}
    if len(gold_by_id) != len(gold) or len(result_by_id) != len(results):
        raise ValueError("duplicate case identity")
    correct = 0
    accepted = 0
    accepted_correct = 0
    corpus_agreement = 0
    answerable = 0
    answerable_correct = 0
    unsupported = 0
    unsupported_correct = 0
    optimum_correct = 0
    disposition_correct = 0
    candidate_set_correct = 0
    selected_optimum_correct = 0
    energy_correct = 0
    accepted_energy_increases = 0
    coverage_correct = 0
    convergence_correct = 0
    frontier_stable = 0
    certificate_correct = 0
    confidence_correct = 0
    factual_operation_safe = 0
    certified_exact = 0
    certified_answerable_exact = 0
    ambiguity_unknown_cases = 0
    ambiguity_unknown_correct = 0
    required_bodies = 0
    opened_required_bodies = 0
    required_frontier_cases = 0
    required_frontier_complete = 0
    by_family: dict[str, list[bool]] = defaultdict(list)
    by_domain: dict[str, list[bool]] = defaultdict(list)
    by_dependency: dict[str, list[bool]] = defaultdict(list)
    by_depth: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        expected = gold_by_id.get(case.case_id)
        result = result_by_id.get(case.case_id)
        if expected is None or result is None:
            raise ValueError("public/gold/result identity mismatch")
        oracle = source_normalized_outcome(case)
        corpus_agreement += int(gold_agrees(case, expected))
        valid = verify_result(case, result)
        correct += int(valid)
        is_answerable = bool(expected.candidates)
        answerable += int(is_answerable)
        answerable_correct += int(is_answerable and valid)
        unsupported += int(not is_answerable)
        unsupported_correct += int(not is_answerable and valid)
        disposition_ok = result.disposition == oracle.disposition
        disposition_correct += int(disposition_ok)
        candidate_set_ok = _candidate_signatures(result) == {
            (item.semantic_key, item.polarity) for item in oracle.candidates
        }
        candidate_set_correct += int(candidate_set_ok)
        selected_ok = _selected_signature(result) == oracle.selected
        selected_optimum_correct += int(selected_ok)
        optimum_ok = _global_optimum_agrees(oracle, result)
        optimum_correct += int(optimum_ok)
        increases = _accepted_energy_increases(result, tolerance=energy_tolerance)
        accepted_energy_increases += increases
        energy_ok = increases == 0
        energy_correct += int(energy_ok)
        coverage_ok = _coverage_certified(result, coverage_threshold=coverage_threshold)
        coverage_correct += int(coverage_ok)
        stable_ok = _frontier_stable(result, stability_steps=stability_steps)
        frontier_stable += int(stable_ok)
        convergence_ok = _convergence_certified(
            result,
            convergence_residual=convergence_residual,
            stability_steps=stability_steps,
        )
        convergence_correct += int(convergence_ok)
        certificate_ok = _certificate_safe(case, result)
        certificate_correct += int(certificate_ok)
        confidence_ok = _candidate_confidence_agrees(oracle, result)
        confidence_correct += int(confidence_ok)
        factual_ok = not result.factual_operations
        factual_operation_safe += int(factual_ok)
        certified_ok = (
            valid
            and energy_ok
            and coverage_ok
            and convergence_ok
            and certificate_ok
            and confidence_ok
            and factual_ok
        )
        certified_exact += int(certified_ok)
        certified_answerable_exact += int(is_answerable and certified_ok)
        is_ambiguity_unknown = expected.disposition in {"ambiguous", "unknown"}
        ambiguity_unknown_cases += int(is_ambiguity_unknown)
        ambiguity_unknown_correct += int(is_ambiguity_unknown and disposition_ok)
        opened = {body_id for item in result.frontiers for body_id in item.body_ids}
        required = set(oracle.reachable_body_ids)
        required_bodies += len(required)
        opened_required_bodies += len(required & opened)
        if required:
            required_frontier_cases += 1
            required_frontier_complete += int(required <= opened)
        if result.disposition in {"candidate", "alternatives"}:
            accepted += 1
            accepted_correct += int(valid)
        by_family[expected.family].append(valid)
        by_domain[expected.domain].append(valid)
        band = "1" if expected.dependency_count == 1 else "2_4" if expected.dependency_count <= 4 else "5_8" if expected.dependency_count <= 8 else "9_16"
        by_dependency[band].append(valid)
        by_depth[str(expected.dependency_count)].append(valid)
    total = len(cases)
    return {
        "cases": total,
        "answerable_cases": answerable,
        "unsupported_cases": unsupported,
        "accepted_cases": accepted,
        "corpus_oracle_agreement": corpus_agreement / total if total else 1.0,
        "accepted_verified_precision": accepted_correct / accepted if accepted else 1.0,
        "incorrect_accepted_candidates": accepted - accepted_correct,
        "safe_coverage": correct / total if total else 0.0,
        "all_case_exactness": correct / total if total else 0.0,
        "answerable_case_exactness": _rate(answerable_correct, answerable),
        "answerable_exactness": _rate(answerable_correct, answerable),
        "unsupported_case_exactness": _rate(unsupported_correct, unsupported),
        "global_optimum_oracle_agreement": _rate(optimum_correct, total),
        "global_optimum_agreement": _rate(optimum_correct, total),
        "oracle_disposition_agreement": _rate(disposition_correct, total),
        "candidate_set_exactness": _rate(candidate_set_correct, total),
        "selected_optimum_agreement": _rate(selected_optimum_correct, total),
        "energy_nonincrease": _rate(energy_correct, total),
        "accepted_energy_increases": accepted_energy_increases,
        "coverage_certification": _rate(coverage_correct, total),
        "convergence_certification": _rate(convergence_correct, total),
        "frontier_stability": _rate(frontier_stable, total),
        "certificate_safety": _rate(certificate_correct, total),
        "candidate_confidence_agreement": _rate(confidence_correct, total),
        "factual_operation_safety": _rate(factual_operation_safe, total),
        "required_body_frontier_recall": _rate(
            opened_required_bodies,
            required_bodies,
        ),
        "required_body_frontier_complete": _rate(
            required_frontier_complete,
            required_frontier_cases,
        ),
        "certified_all_case_exactness": _rate(certified_exact, total, empty=0.0),
        "certified_answerable_case_exactness": _rate(
            certified_answerable_exact,
            answerable,
        ),
        "ambiguity_unknown_recall": _rate(
            ambiguity_unknown_correct,
            ambiguity_unknown_cases,
        ),
        "family_exactness": {key: sum(rows) / len(rows) for key, rows in sorted(by_family.items())},
        "domain_exactness": {key: sum(rows) / len(rows) for key, rows in sorted(by_domain.items())},
        "dependency_exactness": {key: sum(rows) / len(rows) for key, rows in sorted(by_dependency.items())},
        "depth_exactness": {
            key: sum(rows) / len(rows)
            for key, rows in sorted(by_depth.items(), key=lambda item: int(item[0]))
        },
        "metric_counts": {
            "corpus_oracle_agreement": (corpus_agreement, total),
            "accepted_verified_precision": (accepted_correct, accepted),
            "all_case_exactness": (correct, total),
            "answerable_case_exactness": (answerable_correct, answerable),
            "unsupported_case_exactness": (unsupported_correct, unsupported),
            "global_optimum_oracle_agreement": (optimum_correct, total),
            "oracle_disposition_agreement": (disposition_correct, total),
            "candidate_set_exactness": (candidate_set_correct, total),
            "selected_optimum_agreement": (selected_optimum_correct, total),
            "energy_nonincrease": (energy_correct, total),
            "coverage_certification": (coverage_correct, total),
            "convergence_certification": (convergence_correct, total),
            "frontier_stability": (frontier_stable, total),
            "certificate_safety": (certificate_correct, total),
            "candidate_confidence_agreement": (confidence_correct, total),
            "factual_operation_safety": (factual_operation_safe, total),
            "required_body_frontier_recall": (
                opened_required_bodies,
                required_bodies,
            ),
            "required_body_frontier_complete": (
                required_frontier_complete,
                required_frontier_cases,
            ),
            "certified_all_case_exactness": (certified_exact, total),
            "certified_answerable_case_exactness": (
                certified_answerable_exact,
                answerable,
            ),
            "ambiguity_unknown_recall": (
                ambiguity_unknown_correct,
                ambiguity_unknown_cases,
            ),
        },
        "metric_semantics": SCORE_METRIC_SEMANTICS,
    }
