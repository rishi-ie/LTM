from __future__ import annotations

from dataclasses import replace

from topology_g4.execute import execute

from .frontier import _exact_forces, _request, run_candidate
from .latent import equilibrium
from .schemas import CertifiedExecutionResult


def fixed_frontier(dataset: dict, row: dict) -> CertifiedExecutionResult:
    request = _request(row); opened = set(row["seed_regions"]); factors = tuple(factor for region in opened for factor in dataset["store"].open_region(region)); symbolic = execute(request, factors); state = equilibrium(request.request_id, _exact_forces(dataset, request, opened))
    return CertifiedExecutionResult(request.request_id, symbolic.conclusion, tuple(state), "fixed", 0, tuple(sorted(opened)), (), symbolic.proof_factor_ids, symbolic.decisive_provenance_ids, symbolic.conflicts, None, 0)


def run_controls(dataset: dict, catalog, indexes, row: dict) -> dict[str, CertifiedExecutionResult]:
    fixed = fixed_frontier(dataset, row)
    semantic = replace(fixed, disposition="semantic_fixed")
    return {
        "full": run_candidate(dataset, catalog, indexes, row),
        "fixed_g4": fixed,
        "summary_only": run_candidate(dataset, catalog, indexes, row, force_certificate=True, no_widen=True),
        "semantic_distance": semantic,
        "no_safety": run_candidate(dataset, catalog, indexes, row, no_safety=True),
        "no_continuous_bound": run_candidate(dataset, catalog, indexes, row, force_certificate=True),
        "no_widen": run_candidate(dataset, catalog, indexes, row, no_widen=True),
        "forced_certification": run_candidate(dataset, catalog, indexes, row, force_certificate=True),
    }
