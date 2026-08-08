from __future__ import annotations

from dataclasses import dataclass

from topology_g1.schemas import RelationInstance, TopologyNode


@dataclass(frozen=True, slots=True)
class IntegrationCase:
    case_id: str
    split: str
    family: str
    nodes: tuple[TopologyNode, ...]
    relation: RelationInstance
    target_atom_id: str
    expected_disposition: str


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    case_id: str
    semantic_equal: bool
    artifact_equal: bool
    projection_equal: bool
    address_equal: bool
    frontier_equal: bool
    coverage_equal: bool
    hard_equal: bool
    soft_equal: bool
    g9_equal: bool
    decoder_equal: bool
    vector_rows: int
    failure_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AttackResult:
    attack_id: str
    rejected: bool
    primary_code: str | None
