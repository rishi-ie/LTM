from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from topology_g6.schemas import ProgramResult, Rule
from topology_g7.schemas import DiscreteAlternative, SoftFactor, SoftVariable, StructuredState


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, default=str, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class StoredFactor:
    factor_id: str
    factor_kind: str
    block_id: str
    query_keys: tuple[str, ...]
    hard_literal: str | None
    hard_rule: Rule | None
    soft_factor: SoftFactor | None
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BatchRequest:
    request_id: str
    family: str
    target: str
    scope: str
    selected_block_ids: tuple[str, ...]
    soft_variables: tuple[SoftVariable, ...]
    alternatives: tuple[DiscreteAlternative, ...]
    reference_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class BlockContribution:
    block_ids: tuple[str, ...]
    hard_facts: tuple[str, ...]
    hard_rules: tuple[Rule, ...]
    energy: float
    gradient: tuple[float, ...]
    factor_residuals: tuple[tuple[str, float], ...]
    provenance_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MemoryTrace:
    blocks_opened: int
    block_reads: int
    peak_resident_blocks: int
    peak_resident_factors: int
    peak_resident_bytes: int
    complete_field_materialization: bool


@dataclass(frozen=True, slots=True)
class BatchedExecutionResult:
    request_id: str
    hard_result: ProgramResult
    final_state: StructuredState
    selected_branch: str | None
    retained_branches: tuple[str, ...]
    disposition: str
    final_energy: float
    residuals: tuple[tuple[str, float], ...]
    decisive_provenance_ids: tuple[str, ...]
    memory_trace: MemoryTrace


def row(value: object) -> dict:
    return asdict(value)
