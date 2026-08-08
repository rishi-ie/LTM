"""Profile execution, independent oracle comparison, migrations, and adapters."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import replace

from topology_g1.registry import REGISTRY

from .codebook import AXIS_CODES, CLASS_BY_CODE, NODE_BY_CODE, OPERATOR_BY_CODE, ROLE_BY_CODE
from .codec import digest
from .generator import SemanticBody
from .schemas import (
    CompiledTopologyProfile,
    MigrationResult,
    MumbraneProgram,
    ProfileExecution,
    TopologyProfile,
)


def _relation_rows(program: MumbraneProgram):
    for index, unit in enumerate(program.units):
        if CLASS_BY_CODE[unit.unit_class_code] != "operator":
            continue
        relation = OPERATOR_BY_CODE.get(unit.semantic_code)
        if relation is None:
            raise ValueError("UNKNOWN_SEMANTIC_CODE")
        bindings: dict[str, list[str]] = {}
        for port in program.ports[unit.port_start : unit.port_start + unit.port_count]:
            if port.source_unit_index != index:
                raise ValueError("INVALID_PORT")
            role = ROLE_BY_CODE.get(port.role_code)
            if role is None:
                raise ValueError("ROLE_BINDING_MISMATCH")
            bindings.setdefault(role, []).append(program.units[port.target_unit_index].unit_id)
        specification = REGISTRY[relation]
        for role in specification.roles:
            ids = bindings.get(role.name, [])
            if not role.minimum <= len(ids) <= role.maximum:
                raise ValueError("ROLE_BINDING_MISMATCH")
            for atom_id in ids:
                target = next(item for item in program.units if item.unit_id == atom_id)
                if NODE_BY_CODE[target.semantic_code] not in {item.value for item in role.allowed_kinds}:
                    raise ValueError("ROLE_BINDING_MISMATCH")
        yield unit, relation, tuple(sorted((role, tuple(ids)) for role, ids in bindings.items()))


def _geometry(program: MumbraneProgram, vector_bundle_index: int | None) -> tuple[float, int]:
    if vector_bundle_index is None:
        return 1.0, 0
    bundle = program.vector_bundles[vector_bundle_index]
    if bundle.binding_vector is None:
        return 1.0, 0
    return program.vectors[bundle.binding_vector][0], 1


def execute_program(program: MumbraneProgram, compiled: CompiledTopologyProfile) -> ProfileExecution:
    for coordinate in program.coordinates:
        if coordinate.axis_code not in AXIS_CODES.values():
            raise ValueError("CONTEXT_MISMATCH")
        if (
            coordinate.axis_code == AXIS_CODES["scope"]
            and CLASS_BY_CODE[program.units[coordinate.unit_index].unit_class_code] == "operator"
            and coordinate.value_code not in (1, 2, 3, 4)
        ):
            raise ValueError("SCOPE_OR_SESSION_VIOLATION")
    required = compiled.profile.required_feature_mask
    active_codes = set(compiled.operator_codes)
    hard: list[tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]]] = []
    soft: dict[str, float] = {}
    active_ids: list[str] = []
    reads = 0
    for unit, relation, bindings in _relation_rows(program):
        if unit.semantic_code not in active_codes:
            continue
        if unit.feature_mask & required != required:
            raise ValueError("PROFILE_SCHEMA_MISMATCH")
        active_ids.append(unit.unit_id)
        specification = REGISTRY[relation]
        geometry, consumed = _geometry(program, unit.vector_bundle_index)
        reads += consumed
        weight = unit.base_weight * compiled.profile.dynamics_weight * (1.0 + .25 * geometry)
        if specification.hard_or_soft == "hard":
            hard.append((unit.unit_id, relation, bindings))
        elif relation == "supports":
            soft["confidence"] = soft.get("confidence", .5) + weight
        elif relation == "opposes":
            soft["confidence"] = soft.get("confidence", .5) - weight
        elif relation == "uncertainty":
            soft["uncertainty"] = soft.get("uncertainty", .0) + abs(weight)
        elif relation == "prefers":
            soft["preference"] = soft.get("preference", .0) + weight
        elif relation == "refers_to":
            soft["reference"] = soft.get("reference", .0) + weight
        elif relation == "causes_hypothetically":
            soft["hypothesis"] = soft.get("hypothesis", .0) + weight
    hard_signature = digest(tuple(sorted(hard)))
    normalized_soft = tuple(sorted((key, round(min(1.0, max(0.0, value)), 6)) for key, value in soft.items()))
    disposition = "verified_with_tension" if any(name == "excludes" for _id, name, _bindings in hard) else "unknown" if not hard and not normalized_soft else "verified"
    return ProfileExecution(compiled.profile.profile_id, program.substrate_sha256, compiled.execution_sha256, hard_signature, normalized_soft, disposition, tuple(sorted(active_ids)), reads)


def execute_oracle(body: SemanticBody, compiled: CompiledTopologyProfile) -> ProfileExecution:
    """Evaluator-owned route: reads semantic-program records, not Mumbrane rows."""
    active = set(compiled.profile.active_operator_ids)
    hard = []
    soft: dict[str, float] = {}
    ids = []
    for relation in body.relations:
        if relation.relation_type not in active:
            continue
        ids.append(relation.relation_id)
        specification = REGISTRY[relation.relation_type]
        geometry = struct.unpack("<f", struct.pack("<f", relation.geometry))[0]
        base_weight = struct.unpack("<f", struct.pack("<f", relation.base_weight))[0]
        weight = base_weight * compiled.profile.dynamics_weight * (1.0 + .25 * geometry)
        if specification.hard_or_soft == "hard":
            hard.append((relation.relation_id, relation.relation_type, tuple(sorted(relation.role_bindings))))
        elif relation.relation_type == "supports":
            soft["confidence"] = soft.get("confidence", .5) + weight
        elif relation.relation_type == "opposes":
            soft["confidence"] = soft.get("confidence", .5) - weight
        elif relation.relation_type == "uncertainty":
            soft["uncertainty"] = soft.get("uncertainty", .0) + abs(weight)
        elif relation.relation_type == "prefers":
            soft["preference"] = soft.get("preference", .0) + weight
        elif relation.relation_type == "refers_to":
            soft["reference"] = soft.get("reference", .0) + weight
        elif relation.relation_type == "causes_hypothetically":
            soft["hypothesis"] = soft.get("hypothesis", .0) + weight
    hard_signature = digest(tuple(sorted(hard)))
    normalized_soft = tuple(sorted((key, round(min(1.0, max(0.0, value)), 6)) for key, value in soft.items()))
    disposition = "verified_with_tension" if any(name == "excludes" for _id, name, _bindings in hard) else "unknown" if not hard and not normalized_soft else "verified"
    substrate = digest({"body": body.body_id, "semantic": "oracle"})
    return ProfileExecution(compiled.profile.profile_id, substrate, compiled.execution_sha256, hard_signature, normalized_soft, disposition, tuple(sorted(ids)), 0)


def equivalent(universal: ProfileExecution, oracle: ProfileExecution) -> bool:
    return (
        universal.profile_id == oracle.profile_id
        and universal.hard_signature == oracle.hard_signature
        and universal.soft_state == oracle.soft_state
        and universal.disposition == oracle.disposition
        and universal.active_unit_ids == oracle.active_unit_ids
    )


def migrate(program: MumbraneProgram, old: CompiledTopologyProfile, new: CompiledTopologyProfile, tier: int) -> MigrationResult:
    if tier == 1:
        return MigrationResult(1, "switched", (), tuple(item.unit_id for item in program.units), old.execution_sha256, new.execution_sha256, program.substrate_sha256)
    if tier == 3:
        return MigrationResult(3, "SOURCE_RECOMPILATION_REQUIRED", (), tuple(item.unit_id for item in program.units), old.execution_sha256, new.execution_sha256)
    old_active = set(old.operator_codes)
    new_active = set(new.operator_codes)
    affected = tuple(sorted(item.unit_id for item in program.units if item.semantic_code in old_active - new_active))
    unchanged = tuple(sorted(item.unit_id for item in program.units if item.unit_id not in affected))
    return MigrationResult(2, "migrated", affected, unchanged, old.execution_sha256, new.execution_sha256, program.substrate_sha256)


def structural_variant(profile: TopologyProfile) -> TopologyProfile:
    active = tuple(name for name in profile.active_operator_ids if name != "supports")
    payload = {"profile": profile.profile_sha256, "active": active, "structural": "remove-supports"}
    return replace(profile, revision=f"{profile.revision}-structural", active_operator_ids=active, profile_sha256=hashlib.sha256(str(payload).encode()).hexdigest())


def profile_execution_hash(program: MumbraneProgram, compiled: CompiledTopologyProfile) -> str:
    return digest({"substrate": program.substrate_sha256, "profile": compiled.execution_sha256})
