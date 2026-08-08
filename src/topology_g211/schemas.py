"""Immutable G2.11 public contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AtomicBasisSpec:
    basis_id: str
    category: str
    description: str
    source: str


@dataclass(frozen=True, slots=True)
class AttentionState:
    source_id: str
    token_offsets: tuple[tuple[int, int], ...]
    token_states: tuple[tuple[float, ...], ...]
    sentence_state: tuple[float, ...]
    clause_states: tuple[tuple[float, ...], ...]
    forward_count: int

    def __post_init__(self) -> None:
        if self.forward_count != 1:
            raise ValueError("G2.11 requires exactly one encoder forward")
        if not self.token_states or any(len(row) != 384 for row in self.token_states):
            raise ValueError("invalid MiniLM token state")
        if len(self.sentence_state) != 384:
            raise ValueError("invalid MiniLM sentence state")


@dataclass(frozen=True, slots=True)
class AtomicCoordinate:
    basis_id: str
    value: float
    source_span_ids: tuple[str, ...] = ()
    role: str | None = None

    def __post_init__(self) -> None:
        if not self.basis_id or not math.isfinite(self.value):
            raise ValueError("invalid atomic coordinate")
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("atomic coordinate must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class AtomicRelationSignature:
    relation_type: str
    coordinates: tuple[str, ...]
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BasisManifest:
    revision: str
    features: tuple[AtomicBasisSpec, ...]
    relation_signatures: tuple[AtomicRelationSignature, ...]
    basis_sha256: str


@dataclass(frozen=True, slots=True)
class AtomicFieldPatch:
    source_id: str
    coordinates: tuple[AtomicCoordinate, ...]
    relation_types: tuple[str, ...]
    residual: tuple[float, ...]
    disposition: str
    failure_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.disposition not in {"accept", "clarification_required", "quarantine"}:
            raise ValueError("invalid atomic patch disposition")
        if not all(math.isfinite(value) for value in self.residual):
            raise ValueError("residual must be finite")
