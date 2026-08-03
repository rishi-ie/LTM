from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RegionRecord:
    region_id: str
    factor_ids: tuple[str, ...]
    block_ids: tuple[str, ...]
    scope_ids: tuple[str, ...]
    time_min: int | None
    time_max: int | None
    region_hash: str


@dataclass(frozen=True, slots=True)
class FactorInfluence:
    factor_id: str
    influence_keys: tuple[str, ...]
    force_vector: tuple[float, ...]
    force_weight: float


@dataclass(frozen=True, slots=True)
class RegionSummary:
    region_id: str
    influence_keys: tuple[str, ...]
    possible_positive_literals: tuple[str, ...]
    possible_negative_literals: tuple[str, ...]
    boundary_premises: tuple[str, ...]
    factor_type_mask: tuple[str, ...]
    scope_ids: tuple[str, ...]
    valid_from: int | None
    valid_to: int | None
    episode_ids: tuple[str, ...]
    contains_hard_constraint: bool
    contains_exact_exception: bool
    contains_correction: bool
    contains_conflict: bool
    contains_bridge: bool
    approximate_force: tuple[float, ...]
    force_error_bound: float
    certifiable: bool
    summary_hash: str


@dataclass(frozen=True, slots=True)
class CoverageThreat:
    region_id: str
    threat_type: str
    affected_literal: str | None
    affected_obligation: str | None
    maximum_symbolic_effect: float
    latent_error_bound: float
    priority: int
    reason: str


@dataclass(frozen=True, slots=True)
class CoverageCertificate:
    request_id: str
    opened_region_ids: tuple[str, ...]
    summarized_region_ids: tuple[str, ...]
    irrelevant_region_ids_hash: str
    uncertifiable_region_ids: tuple[str, ...]
    checked_hard_indexes: tuple[str, ...]
    checked_exception_indexes: tuple[str, ...]
    checked_correction_indexes: tuple[str, ...]
    checked_conflict_indexes: tuple[str, ...]
    open_obligations: tuple[str, ...]
    symbolic_threats: tuple[CoverageThreat, ...]
    current_conclusion: str
    approximate_state: tuple[float, ...]
    total_latent_error_bound: float
    state_tolerance: float
    disposition: str
    next_region_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    summary_postings_visited: int
    exact_factors_opened: int
    complete_region_scan: bool


@dataclass(frozen=True, slots=True)
class CertifiedExecutionResult:
    request_id: str
    conclusion: str
    latent_state: tuple[float, ...]
    disposition: str
    widening_rounds: int
    opened_region_ids: tuple[str, ...]
    certificates: tuple[CoverageCertificate, ...]
    proof_factor_ids: tuple[str, ...]
    decisive_provenance_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    abstention_reason: str | None
    runtime_us: int


def jsonable(value: object) -> object:
    return asdict(value) if hasattr(value, "__dataclass_fields__") else value
