from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


def canonical(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_kind: str
    text: str
    content_hash: str
    authority: float


@dataclass(frozen=True, slots=True)
class AddressRecord:
    address_id: str
    object_kind: str
    scope_id: str
    session_id: str
    valid_from: int | None
    valid_to: int | None


@dataclass(frozen=True, slots=True)
class FactRecord:
    fact_id: str
    literal: str
    address_id: str
    source_ids: tuple[str, ...]
    scope_id: str
    valid_from: int | None
    valid_to: int | None


@dataclass(frozen=True, slots=True)
class RuleRecord:
    rule_id: str
    kind: str
    premises: tuple[str, ...]
    conclusion: str | None
    scope_id: str
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SupersessionRecord:
    old_fact_id: str
    replacement_fact_id: str


@dataclass(frozen=True, slots=True)
class ProofRecord:
    conclusion: str
    rule_id: str
    premises: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class CoverageRecord:
    manifest_region_ids: tuple[str, ...]
    opened_region_ids: tuple[str, ...]
    summarized_region_ids: tuple[str, ...]
    uncertifiable_region_ids: tuple[str, ...]
    threats: tuple[str, ...]
    open_obligations: tuple[str, ...]
    checked_hard_indexes: tuple[str, ...]
    checked_exception_indexes: tuple[str, ...]
    total_error_bound: float
    state_tolerance: float
    disposition: str


@dataclass(frozen=True, slots=True)
class SoftFactorRecord:
    factor_id: str
    variable_id: str
    target: float
    weight: float
    alternative_id: str | None
    source_id: str


@dataclass(frozen=True, slots=True)
class SoftRecord:
    variable_ids: tuple[str, ...]
    factors: tuple[SoftFactorRecord, ...]
    alternatives: tuple[str, ...]
    final_values: tuple[tuple[str, float], ...]
    selected_branch: str | None
    retained_branches: tuple[str, ...]
    final_energy: float
    residuals: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class CandidateBundle:
    bundle_id: str
    topology_version: str
    field_version: str
    request_address_id: str
    target_literal: str
    scope_id: str
    session_id: str
    valid_at: int
    sources: tuple[SourceRecord, ...]
    addresses: tuple[AddressRecord, ...]
    facts: tuple[FactRecord, ...]
    rules: tuple[RuleRecord, ...]
    supersessions: tuple[SupersessionRecord, ...]
    hard_constraint_ids: tuple[str, ...]
    applied_hard_ids: tuple[str, ...]
    claimed_conclusion: str
    proof: tuple[ProofRecord, ...]
    claimed_conflicts: tuple[str, ...]
    coverage: CoverageRecord
    soft: SoftRecord
    decisive_provenance_ids: tuple[str, ...]
    confidence: float
    self_claimed_valid: bool


@dataclass(frozen=True, slots=True)
class VerificationResult:
    bundle_id: str
    status: str
    authorized_conclusion: str | None
    verified_proof: tuple[ProofRecord, ...]
    verified_provenance_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    failure_codes: tuple[str, ...]
    checked_invariants: tuple[str, ...]


def row(value: object) -> dict:
    return asdict(value)
