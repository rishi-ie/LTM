from __future__ import annotations

from topology_g4.schemas import TraversalRequest

from .latent import equilibrium
from .schemas import CoverageCertificate, CoverageThreat, canonical_hash

PRIORITY = {"hard_constraint": 0, "exact_exception": 1, "correction": 2, "answer_polarity": 3, "conflict": 4, "open_premise": 5, "bridge": 6, "latent_uncertainty": 7, "uncertifiable": -1}


def applicable(summary, request: TraversalRequest) -> bool:
    if request.scope_id not in summary.scope_ids and "global" not in summary.scope_ids: return False
    if request.valid_at is not None and summary.valid_from is not None and request.valid_at < summary.valid_from: return False
    if request.valid_at is not None and summary.valid_to is not None and request.valid_at > summary.valid_to: return False
    return not summary.episode_ids or request.episode_id in summary.episode_ids


def issue_certificate(request, store, catalog, indexes, opened_regions: set[str], exact_state_forces, current_conclusion: str, state_tolerance: float = 0.02, force_certificate: bool = False) -> CoverageCertificate:
    candidates, postings = indexes.candidates(request.target_literal, request.target_literal, ())
    summaries = []
    threats: list[CoverageThreat] = []; total_error = 0.0; approximate = list(exact_state_forces); uncertifiable = []
    for region_id in candidates:
        if region_id in opened_regions: continue
        summary = catalog.summaries[region_id]
        if not applicable(summary, request): continue
        summaries.append(region_id)
        vector, error = catalog.term(region_id, request.target_literal)
        approximate.append(vector); total_error += error
        if not summary.certifiable:
            uncertifiable.append(region_id); threats.append(CoverageThreat(region_id, "uncertifiable", None, None, 1.0, error, PRIORITY["uncertifiable"], "applicable region has no valid force bound")); continue
        special = None
        if summary.contains_hard_constraint: special = "hard_constraint"
        elif summary.contains_exact_exception: special = "exact_exception"
        elif summary.contains_correction: special = "correction"
        elif summary.contains_conflict: special = "conflict"
        elif summary.contains_bridge: special = "bridge"
        if request.target_literal in summary.possible_positive_literals or f"not:{request.target_literal}" in summary.possible_negative_literals:
            special = special or "answer_polarity"
        if special:
            threats.append(CoverageThreat(region_id, special, request.target_literal, None, 1.0, error, PRIORITY[special], "summary may change the symbolic result"))
        elif error > state_tolerance:
            threats.append(CoverageThreat(region_id, "latent_uncertainty", None, None, 0.0, error, PRIORITY["latent_uncertainty"], "summary force error exceeds state tolerance"))
    threats.sort(key=lambda item: (item.priority, -item.latent_error_bound, item.region_id))
    state = equilibrium(request.request_id, approximate)
    if uncertifiable:
        disposition, next_ids, reasons = "abstain", (), ("UNCERTIFIABLE_REGION",)
    elif threats and not force_certificate:
        disposition, next_ids, reasons = "widen_required", tuple(dict.fromkeys(item.region_id for item in threats)), ("UNRESOLVED_THREAT",)
    elif total_error > state_tolerance and not force_certificate:
        disposition, next_ids, reasons = "widen_required", tuple(sorted(summaries)), ("LATENT_BOUND_EXCEEDED",)
    else:
        disposition, next_ids, reasons = "certified", (), ()
    all_regions = set(store.regions); irrelevant = tuple(sorted(all_regions - opened_regions - set(summaries)))
    return CoverageCertificate(request.request_id, tuple(sorted(opened_regions)), tuple(summaries), canonical_hash(irrelevant), tuple(sorted(uncertifiable)), tuple(sorted(indexes.hard.get(request.target_literal, ()))), tuple(sorted(indexes.exception.get(request.target_literal, ()))), tuple(sorted(indexes.correction.get(request.target_literal, ()))), tuple(sorted(indexes.conflict.get(request.target_literal, ()))), (), tuple(threats), current_conclusion, tuple(state), total_error, state_tolerance, disposition, next_ids, reasons, postings, sum(len(store.regions[region].factor_ids) for region in opened_regions), False)
