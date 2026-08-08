"""Runtime-safe support reconstruction after L5 convergence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from ltm_limit_l2.parser import ParseError, parse_proposition
from ltm_limit_l4.exact import enumerate_proposals

from .dataset import PublicFieldCase
from .schemas import EquilibriumCandidate, FieldEquilibriumResult, SupportCertificate

VERIFIER_REVISION = "l5-independent-oracle/1"


def _hash(
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


def _context_ok(case: PublicFieldCase, body) -> bool:
    return any(
        body.reality_key == item.reality_key
        and body.scope_key in {"global", item.scope_key}
        and (item.valid_at is None or body.valid_from is None or body.valid_from <= item.valid_at)
        and (item.valid_at is None or body.valid_to is None or item.valid_at <= body.valid_to)
        for item in case.prompt.influences
    )


def _math_step(left_key: str, right_key: str) -> bool:
    if not left_key.startswith("math|") or not right_key.startswith("math|"):
        return True
    left_parts = left_key.split("|", 2)
    right_parts = right_key.split("|", 2)
    if len(left_parts) != 3 or len(right_parts) != 3 or left_parts[1] != right_parts[1]:
        return False
    try:
        left, right = parse_proposition(f"{left_parts[2]} = {right_parts[2]}")
    except ParseError:
        return False
    return any(item.after == right for item in enumerate_proposals(left))


def verify_candidate(case: PublicFieldCase, candidate: EquilibriumCandidate) -> SupportCertificate:
    units = {item.unit_id: item for item in case.units}
    bodies = {item.body_id: item for item in case.bodies}
    requested = tuple(sorted(candidate.supporting_body_ids))
    if not requested or any(item not in bodies for item in requested):
        raise ValueError("SUPPORT_BODY_MISSING")
    active = {(item.semantic_key, item.polarity_sign) for item in case.prompt.influences}
    remaining = set(requested)
    used: list[str] = []
    while remaining:
        progressed = False
        for body_id in sorted(remaining):
            body = bodies[body_id]
            if not _context_ok(case, body):
                raise ValueError("SUPPORT_CONTEXT_MISMATCH")
            required = {(units[item].semantic_key, units[item].polarity) for item in body.input_unit_ids}
            if not required <= active:
                continue
            outputs = tuple(units[item] for item in body.outcome_unit_ids)
            mathematical_inputs = tuple(key for key, _polarity in required if key.startswith("math|"))
            if (
                outputs
                and outputs[0].semantic_key.startswith("math|")
                and not any(_math_step(left, outputs[0].semantic_key) for left in mathematical_inputs)
            ):
                raise ValueError("INVALID_MATHEMATICAL_BODY")
            active.update((item.semantic_key, item.polarity) for item in outputs)
            used.append(body_id)
            remaining.remove(body_id)
            progressed = True
        if not progressed:
            raise ValueError("SUPPORT_GRAPH_INCOMPLETE")
    selected = units.get(candidate.unit_id)
    if selected is None or (candidate.semantic_key, candidate.polarity) not in active:
        raise ValueError("CANDIDATE_NOT_DERIVED")
    if selected.unit_id not in {item for body_id in used for item in bodies[body_id].outcome_unit_ids}:
        raise ValueError("CANDIDATE_UNIT_NOT_SUPPORTED")
    source_keys = tuple(sorted({bodies[item].independent_source_key for item in used}))
    provenance = tuple(sorted({value for item in used for value in bodies[item].provenance_ids}))
    if source_keys != tuple(sorted(candidate.supporting_source_keys)):
        raise ValueError("SUPPORT_SOURCE_MISMATCH")
    if provenance != tuple(sorted(candidate.provenance_ids)):
        raise ValueError("SUPPORT_PROVENANCE_MISMATCH")
    body_ids = tuple(sorted(used))
    return SupportCertificate(
        candidate.unit_id,
        body_ids,
        source_keys,
        provenance,
        VERIFIER_REVISION,
        True,
        _hash(candidate.unit_id, body_ids, source_keys, provenance),
    )


def certify_result(case: PublicFieldCase, result: FieldEquilibriumResult) -> FieldEquilibriumResult:
    if result.prompt_id != case.case_id or result.factual_operations:
        raise ValueError("RESULT_IDENTITY_MISMATCH")
    certificates = tuple(verify_candidate(case, item) for item in result.candidates)
    return replace(result, certificates=certificates)
