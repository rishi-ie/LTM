"""Public and evaluator-only contracts for the G2.10 kernel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from topology_field_ir import FieldProgram
from topology_g1.schemas import TopologyOperation


@dataclass(frozen=True, slots=True)
class PublicAtom:
    atom_id: str
    kind: str
    text: str
    start: int
    end: int
    provenance_sha256: str


@dataclass(frozen=True, slots=True)
class SourceExample:
    source_id: str
    text: str
    atoms: tuple[PublicAtom, ...]
    source_hash: str


@dataclass(frozen=True, slots=True)
class GoldExample:
    source_id: str
    cell_id: str | None
    atom_ids: tuple[str, ...]
    scope_id: str
    modality: str
    disposition: Literal["accept", "clarification_required", "quarantine"]
    surface_relation: str | None
    atom_records: tuple[tuple[str, str, int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionDecision:
    cell_id: str | None
    atom_ids: tuple[str, ...]
    disposition: Literal["accept", "clarification_required", "quarantine"]
    distance: float
    margin: float
    port_probability: float
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompilationArtifact:
    source_id: str
    decision: ProjectionDecision
    scope_id: str
    modality: str
    atoms: tuple[PublicAtom, ...]
    field_program: FieldProgram | None
    operations: tuple[TopologyOperation, ...]
    numeric_digest: str | None
    failure_codes: tuple[str, ...]
