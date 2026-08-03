from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class TopologyFactor:
    factor_id: str
    factor_type: str
    source_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    scope_id: str = "global"
    valid_from: int | None = None
    valid_to: int | None = None
    episode_id: str | None = None
    hard: bool = False
    exact_exception: bool = False
    session_factor: bool = False
    bridge_region_id: str | None = None
    confidence: float = 1.0
    authority: float = 1.0
    provenance_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TraversalRequest:
    request_id: str
    starting_entity_ids: tuple[str, ...]
    starting_predicate_ids: tuple[str, ...]
    target_literal: str
    scope_id: str
    valid_at: int | None
    episode_id: str | None
    polarity: str
    max_depth: int = 8
    max_exact_factors: int = 512
    max_branches: int = 16
    max_blocks: int = 64


@dataclass(frozen=True, slots=True)
class ProofObligation:
    obligation_id: str
    required_literal: str
    originating_factor_id: str
    direction: str
    depth: int
    status: str
    candidate_factor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OmittedFactorRecord:
    factor_id: str
    originating_obligation: str
    reason: str


@dataclass(frozen=True, slots=True)
class ActiveFrontier:
    request_id: str
    starting_addresses: tuple[str, ...]
    exact_factor_ids: tuple[str, ...]
    active_literal_ids: tuple[str, ...]
    proof_obligations: tuple[ProofObligation, ...]
    hard_constraint_ids: tuple[str, ...]
    exact_exception_ids: tuple[str, ...]
    conflict_branch_ids: tuple[str, ...]
    session_factor_ids: tuple[str, ...]
    bridge_factor_ids: tuple[str, ...]
    represented_region_ids: tuple[str, ...]
    omitted_factor_records: tuple[OmittedFactorRecord, ...]
    blocks_read: tuple[str, ...]
    bytes_read: int
    traversal_steps: int
    maximum_depth_reached: int
    budget_exhausted: bool
    runtime_us: int


@dataclass(frozen=True, slots=True)
class FrontierExecutionResult:
    request_id: str
    conclusion: str
    proof_factor_ids: tuple[str, ...]
    decisive_provenance_ids: tuple[str, ...]
    conflicts: tuple[str, ...]
    unresolved_obligations: tuple[str, ...]


def to_dict(value: object) -> dict:
    return asdict(value)
