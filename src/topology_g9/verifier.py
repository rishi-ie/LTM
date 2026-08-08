from __future__ import annotations

import math

from .schemas import CandidateBundle, SoftRecord, VerificationResult, text_hash


def _reject(bundle: CandidateBundle, code: str, checked: list[str]) -> VerificationResult:
    return VerificationResult(bundle.bundle_id, "rejected", None, (), (), (), (code,), tuple(checked))


def _within(value: float, start: int | None, end: int | None) -> bool:
    return math.isfinite(value) and (start is None or value >= start) and (end is None or value <= end)


def _coverage_ok(bundle: CandidateBundle) -> bool:
    record = bundle.coverage
    partition = set(record.opened_region_ids) | set(record.summarized_region_ids) | set(record.uncertifiable_region_ids)
    disjoint = sum(len(part) for part in (set(record.opened_region_ids), set(record.summarized_region_ids), set(record.uncertifiable_region_ids))) == len(partition)
    return (
        partition == set(record.manifest_region_ids)
        and disjoint
        and not record.uncertifiable_region_ids
        and not record.threats
        and not record.open_obligations
        and bool(record.checked_hard_indexes)
        and bool(record.checked_exception_indexes)
        and record.total_error_bound <= record.state_tolerance
        and record.disposition == "certified"
    )


def solve_soft(record: SoftRecord) -> tuple[dict[str, float], str | None, tuple[str, ...], float, tuple[tuple[str, float], ...]]:
    """Independent exact solver for the registered separable quadratic soft law."""
    alternatives = record.alternatives or (None,)
    candidates = []
    for alternative in alternatives:
        factors = tuple(item for item in record.factors if item.alternative_id in (None, alternative))
        values: dict[str, float] = {}
        for variable in record.variable_ids:
            matching = [item for item in factors if item.variable_id == variable]
            if not matching: values[variable] = .5
            else: values[variable] = min(1.0, max(0.0, sum(item.weight * item.target for item in matching) / sum(item.weight for item in matching)))
        residuals = tuple(sorted((item.factor_id, item.weight * (values[item.variable_id] - item.target) ** 2) for item in factors))
        candidates.append((sum(value for _, value in residuals), "" if alternative is None else alternative, alternative, values, residuals))
    candidates.sort(key=lambda item: (item[0], item[1])); energy, _key, selected, values, residuals = candidates[0]
    retained = tuple(item[2] for item in candidates if item[0] - energy <= .05 and item[2] is not None)
    return values, selected, retained, energy, residuals


def verify(bundle: CandidateBundle, *, verify_coverage: bool = True) -> VerificationResult:
    """Standalone verifier: it intentionally imports neither G5–G8 engines nor optimizers."""
    checked: list[str] = []
    if bundle.topology_version != "topology-v1" or bundle.field_version != "field-v1" or not math.isfinite(bundle.confidence):
        return _reject(bundle, "VERSION_MISMATCH", checked)
    checked.append("versions")
    sources = {item.source_id: item for item in bundle.sources}
    if len(sources) != len(bundle.sources) or any(text_hash(item.text) != item.content_hash for item in bundle.sources):
        return _reject(bundle, "SOURCE_HASH_MISMATCH", checked)
    checked.append("sources")
    addresses = {item.address_id: item for item in bundle.addresses}
    address = addresses.get(bundle.request_address_id)
    if address is None or address.scope_id != bundle.scope_id or address.session_id != bundle.session_id or not _within(bundle.valid_at, address.valid_from, address.valid_to):
        return _reject(bundle, "INVALID_ADDRESS", checked)
    checked.append("address")
    facts_by_id = {item.fact_id: item for item in bundle.facts}
    if any(source not in sources for fact in bundle.facts for source in fact.source_ids):
        return _reject(bundle, "PROVENANCE_MISMATCH", checked)
    if any(fact.address_id not in addresses or fact.scope_id != bundle.scope_id or not _within(bundle.valid_at, fact.valid_from, fact.valid_to) for fact in bundle.facts):
        return _reject(bundle, "TEMPORAL_VIOLATION", checked)
    inactive_ids = {item.old_fact_id for item in bundle.supersessions if item.old_fact_id in facts_by_id and item.replacement_fact_id in facts_by_id}
    active_facts = [item for item in bundle.facts if item.fact_id not in inactive_ids]
    active = {item.literal for item in active_facts}
    checked.append("facts")
    if not set(bundle.hard_constraint_ids).issubset(bundle.applied_hard_ids):
        return _reject(bundle, "MISSING_HARD_FACTOR", checked)
    checked.append("hard_factors")
    if verify_coverage and not _coverage_ok(bundle):
        return _reject(bundle, "INSUFFICIENT_COVERAGE", checked)
    checked.append("coverage")
    rules = {item.rule_id: item for item in bundle.rules}
    proof = tuple(sorted(bundle.proof, key=lambda item: (item.depth, item.rule_id)))
    for step in proof:
        rule = rules.get(step.rule_id)
        if rule is None: return _reject(bundle, "FABRICATED_CONCLUSION", checked)
        if rule.scope_id != bundle.scope_id: return _reject(bundle, "SCOPE_VIOLATION", checked)
        if rule.conclusion != step.conclusion:
            return _reject(bundle, "REVERSED_RELATION", checked)
        if rule.premises != step.premises:
            return _reject(bundle, "MISSING_PREMISE", checked)
        for premise in step.premises:
            old = [item for item in bundle.facts if item.literal == premise and item.fact_id in inactive_ids]
            current = [item for item in active_facts if item.literal == premise]
            if old and not current: return _reject(bundle, "SUPERSEDED_EVIDENCE", checked)
            if premise not in active: return _reject(bundle, "MISSING_PREMISE", checked)
            source_kinds = {sources[source].source_kind for fact in active_facts if fact.literal == premise for source in fact.source_ids}
            if source_kinds == {"assistant"}: return _reject(bundle, "ASSISTANT_SELF_EVIDENCE", checked)
        active.add(step.conclusion)
    checked.append("proof")
    conflicts = tuple(sorted(rule.rule_id for rule in bundle.rules if rule.kind == "excludes" and all(item in active for item in rule.premises)))
    positive, negative = bundle.target_literal in active, f"not:{bundle.target_literal}" in active
    conclusion = "conflict" if conflicts or positive and negative else "entailed" if positive else "contradicted" if negative else "unknown"
    if tuple(sorted(bundle.claimed_conflicts)) != conflicts:
        return _reject(bundle, "UNDISCLOSED_CONFLICT", checked)
    if bundle.claimed_conclusion != conclusion:
        return _reject(bundle, "HARD_STATE_MISMATCH", checked)
    checked.append("hard_replay")
    values, selected, retained, energy, residuals = solve_soft(bundle.soft)
    supplied = dict(bundle.soft.final_values)
    if set(supplied) != set(values) or any(not math.isfinite(value) or abs(supplied[name] - value) > 1e-10 for name, value in values.items()):
        return _reject(bundle, "SOFT_STATE_MISMATCH", checked)
    if bundle.soft.selected_branch != selected or tuple(sorted(bundle.soft.retained_branches)) != tuple(sorted(retained)):
        return _reject(bundle, "SOFT_STATE_MISMATCH", checked)
    reported_residuals = dict(bundle.soft.residuals); expected_residuals = dict(residuals)
    if (
        abs(bundle.soft.final_energy - energy) > 1e-10
        or set(reported_residuals) != set(expected_residuals)
        or any(abs(reported_residuals[name] - value) > 1e-10 for name, value in expected_residuals.items())
    ):
        return _reject(bundle, "ENERGY_MISMATCH", checked)
    checked.append("soft")
    expected_provenance = ("src:rule", "src:user")
    if tuple(sorted(bundle.decisive_provenance_ids)) != expected_provenance:
        return _reject(bundle, "PROVENANCE_MISMATCH", checked)
    checked.append("provenance")
    status = "unknown" if conclusion == "unknown" else "verified_with_tension" if conclusion == "conflict" else "verified"
    return VerificationResult(bundle.bundle_id, status, bundle.target_literal if status.startswith("verified") else None, proof, expected_provenance, conflicts, (), tuple(checked))
