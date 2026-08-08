"""Stable public contracts shared by all four Parasite components."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any


def _identity(value: str, name: str) -> None:
    if not value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise ValueError(f"invalid {name}")


def _digest(value: str, name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be a lower-case sha256")


@dataclass(frozen=True, slots=True)
class IngestRequest:
    tenant_id: str
    reality_id: str
    source_id: str
    source_hash: str
    input_kind: str
    payload: dict[str, Any]
    session_id: str | None = None
    scope_key: str = "global"
    valid_from: int | None = None
    valid_to: int | None = None

    def __post_init__(self) -> None:
        for value, name in ((self.tenant_id, "tenant_id"), (self.reality_id, "reality_id"), (self.source_id, "source_id"), (self.scope_key, "scope_key")):
            _identity(value, name)
        _digest(self.source_hash, "source_hash")
        if self.input_kind not in {"topology_document", "mathematical_reality", "conversation_turn"}:
            raise ValueError("unsupported input_kind")
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise ValueError("invalid validity interval")


@dataclass(frozen=True, slots=True)
class CompileResult:
    disposition: str
    transaction_id: str
    semantic_hash: str | None
    artifact_hash: str | None
    failure_codes: tuple[str, ...]
    evidence: tuple[tuple[str, Any], ...]


@dataclass(frozen=True, slots=True)
class QueryRequest:
    tenant_id: str
    reality_id: str
    query_id: str
    profile_id: str
    query_kind: str
    payload: dict[str, Any]
    session_id: str | None = None
    scope_key: str = "global"
    valid_at: int | None = None
    requested_style: str = "brief"

    def __post_init__(self) -> None:
        for value, name in ((self.tenant_id, "tenant_id"), (self.reality_id, "reality_id"), (self.query_id, "query_id"), (self.scope_key, "scope_key")):
            _identity(value, name)
        if self.profile_id not in {"exact", "fixed_equilibrium", "conversation_memory"}:
            raise ValueError("unsupported profile_id")
        if self.requested_style not in {"brief", "detailed"}:
            raise ValueError("unsupported requested_style")


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    generation_id: str
    substrate_hash: str
    fieldir_hash: str
    archive_hash: str
    previous_generation_id: str | None
    committed: bool


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    disposition: str
    authorized_claims: tuple[str, ...]
    alternatives: tuple[str, ...]
    supporting_sources: tuple[str, ...]
    opposing_sources: tuple[str, ...]
    tension: float
    proof_or_equilibrium_certificate: tuple[str, ...]
    response_text: str
    trace: tuple[tuple[str, Any], ...]
    failure_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.tension) or not 0 <= self.tension <= 1:
            raise ValueError("tension must be finite in [0, 1]")


@dataclass(frozen=True, slots=True)
class EquilibriumAtom:
    atom_id: str
    expression: str
    sort: str
    reality_id: str


@dataclass(frozen=True, slots=True)
class EquilibriumFactor:
    body_id: str
    input_atom_ids: tuple[str, ...]
    outcome_atom_id: str
    outcome_polarity: int
    authority: float
    confidence: float
    base_weight: float
    independent_source_key: str
    scope_key: str
    valid_from: int | None
    valid_to: int | None

    def __post_init__(self) -> None:
        if not self.input_atom_ids or self.outcome_polarity not in {-1, 1}:
            raise ValueError("invalid equilibrium factor")
        for value in (self.authority, self.confidence, self.base_weight):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("factor weights must be finite in [0, 1]")

    @property
    def weight(self) -> float:
        return self.authority * self.confidence * self.base_weight


@dataclass(frozen=True, slots=True)
class CandidateTransaction:
    transaction_id: str
    tenant_id: str
    reality_id: str
    source_id: str
    source_text: str
    nodes: tuple[Any, ...]
    relations: tuple[Any, ...]
    equilibrium_atoms: tuple[EquilibriumAtom, ...] = ()
    equilibrium_factors: tuple[EquilibriumFactor, ...] = ()
    conversation_event: tuple[tuple[str, Any], ...] = ()


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()
