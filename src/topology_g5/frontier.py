from __future__ import annotations

from topology_g4.execute import execute
from topology_g4.schemas import TraversalRequest

from .certificate import issue_certificate
from .schemas import CertifiedExecutionResult


def _request(row: dict) -> TraversalRequest:
    value = row["request"]
    return TraversalRequest(**{**value, "starting_entity_ids": tuple(value["starting_entity_ids"]), "starting_predicate_ids": tuple(value["starting_predicate_ids"])})


def _applicable(factor, request: TraversalRequest) -> bool:
    return factor.scope_id in ("global", request.scope_id) and (not factor.episode_id or factor.episode_id == request.episode_id) and (factor.valid_from is None or request.valid_at is None or request.valid_at >= factor.valid_from) and (factor.valid_to is None or request.valid_at is None or request.valid_at <= factor.valid_to)


def _exact_forces(dataset: dict, request: TraversalRequest, opened_regions: set[str]):
    influence = {item.factor_id: item for item in dataset["influences"]}; forces = []
    for region_id in opened_regions:
        for factor in dataset["store"].open_region(region_id):
            item = influence.get(factor.factor_id)
            if item and request.target_literal in item.influence_keys and _applicable(factor, request):
                import numpy as np
                forces.append(np.array(item.force_vector, dtype=np.float64))
    return forces


def run_candidate(dataset: dict, catalog, indexes, row: dict, *, force_certificate: bool = False, no_widen: bool = False, no_summary: bool = False, no_safety: bool = False) -> CertifiedExecutionResult:
    import time
    from dataclasses import replace

    began = time.perf_counter_ns(); request = _request(row); opened = set(row["seed_regions"]); certificates = []; rounds = 0
    while True:
        factors = tuple(factor for region_id in opened for factor in dataset["store"].open_region(region_id))
        symbolic = execute(request, factors)
        certificate = issue_certificate(request, dataset["store"], catalog, indexes, opened, _exact_forces(dataset, request, opened), symbolic.conclusion, force_certificate=force_certificate)
        if no_summary:
            certificate = replace(certificate, total_latent_error_bound=1.0, disposition="widen_required", next_region_ids=certificate.summarized_region_ids, reason_codes=("NO_SUMMARY",))
        if no_safety:
            filtered = tuple(threat for threat in certificate.symbolic_threats if threat.threat_type not in ("hard_constraint", "exact_exception"))
            certificate = replace(certificate, symbolic_threats=filtered, disposition="widen_required" if filtered else "certified", next_region_ids=tuple(item.region_id for item in filtered))
        certificates.append(certificate)
        if certificate.disposition == "certified":
            return CertifiedExecutionResult(request.request_id, symbolic.conclusion, certificate.approximate_state, "certified", rounds, tuple(sorted(opened)), tuple(certificates), symbolic.proof_factor_ids, symbolic.decisive_provenance_ids, symbolic.conflicts, None, (time.perf_counter_ns() - began) // 1000)
        if certificate.disposition == "abstain":
            return CertifiedExecutionResult(request.request_id, symbolic.conclusion, certificate.approximate_state, "abstain", rounds, tuple(sorted(opened)), tuple(certificates), symbolic.proof_factor_ids, symbolic.decisive_provenance_ids, symbolic.conflicts, certificate.reason_codes[0], (time.perf_counter_ns() - began) // 1000)
        candidates = [region for region in certificate.next_region_ids if region not in opened]
        if no_widen or rounds >= 4 or not candidates:
            return CertifiedExecutionResult(request.request_id, symbolic.conclusion, certificate.approximate_state, "abstain", rounds, tuple(sorted(opened)), tuple(certificates), symbolic.proof_factor_ids, symbolic.decisive_provenance_ids, symbolic.conflicts, "WIDENING_BUDGET", (time.perf_counter_ns() - began) // 1000)
        opened.add(candidates[0]); rounds += 1
