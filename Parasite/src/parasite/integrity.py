"""Small non-replaceable integrity kernel for Parasite."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from ltm.adapters import to_g1
from ltm.codec import semantic_hash as fieldir_semantic_hash
from ltm_r2.codebook import CLASS_CODES, NODE_CODES, OPERATOR_CODES, ROLE_CODES, feature_mask
from ltm_r2.codec import make_program
from ltm_r2.schemas import MUMBRANE_SCHEMA, MumbranePort, MumbraneUnit
from topology_g1.registry import validate_relation


def plain(value: Any) -> Any:
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [plain(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if isinstance(value, bytes) else (value if isinstance(value, str) else canonical_json(value)).encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def validate_g1(nodes: tuple, relations: tuple) -> None:
    node_map = {node.node_id: node for node in nodes}
    if len(node_map) != len(nodes):
        raise ValueError("DUPLICATE_NODE_ID")
    if len({item.relation_id for item in relations}) != len(relations):
        raise ValueError("DUPLICATE_RELATION_ID")
    for relation in relations:
        validate_relation(relation, node_map)


def _unit_hash(kind: str, identity: str, semantic: str, bindings: object = ()) -> str:
    return digest({"kind": kind, "identity": identity, "semantic": semantic, "bindings": bindings})


def mumbrane_from_g1(nodes: tuple, relations: tuple, source_archive: tuple[tuple[str, str], ...]):
    """Create the canonical Mumbrane occurrence view without adding semantics."""
    validate_g1(nodes, relations)
    ordered_nodes = tuple(sorted(nodes, key=lambda item: item.node_id))
    ordered_relations = tuple(sorted(relations, key=lambda item: item.relation_id))
    unit_ids = [item.node_id for item in ordered_nodes] + [item.relation_id for item in ordered_relations]
    index = {identity: position for position, identity in enumerate(unit_ids)}
    ports: list[MumbranePort] = []
    units: list[MumbraneUnit] = []
    common_mask = feature_mask("content", "operator", "role", "context", "provenance", "identity", "integrity")
    for node in ordered_nodes:
        units.append(MumbraneUnit(
            node.node_id, MUMBRANE_SCHEMA, CLASS_CODES["content"], NODE_CODES[node.kind.value], common_mask,
            len(ports), 0, 0, 0, None, 1.0, 0,
            _unit_hash("node", node.node_id, node.kind.value, (node.attributes, node.scope_id, node.validity)),
        ))
    for relation in ordered_relations:
        start = len(ports)
        source_index = index[relation.relation_id]
        for ordinal, binding in enumerate(relation.arguments):
            ports.append(MumbranePort(source_index, ROLE_CODES[binding.role], ordinal, index[binding.node_id]))
        units.append(MumbraneUnit(
            relation.relation_id, MUMBRANE_SCHEMA, CLASS_CODES["operator"], OPERATOR_CODES[relation.relation_type], common_mask,
            start, len(relation.arguments), 0, 0, None, 1.0, 0,
            _unit_hash("relation", relation.relation_id, relation.relation_type, tuple((item.role, item.node_id) for item in relation.arguments)),
        ))
    return make_program(tuple(units), tuple(ports), (), (), (), tuple(unit_ids), source_archive)


def _g1_signature(nodes: tuple, relations: tuple) -> tuple:
    return (
        tuple(sorted((node.node_id, node.kind.value) for node in nodes)),
        tuple(sorted((relation.relation_id, relation.relation_type, tuple((arg.role, arg.node_id) for arg in relation.arguments)) for relation in relations)),
    )


def _mumbrane_signature(program) -> tuple:
    node_codes = {value: key for key, value in NODE_CODES.items()}
    operator_codes = {value: key for key, value in OPERATOR_CODES.items()}
    role_codes = {value: key for key, value in ROLE_CODES.items()}
    nodes = []
    relations = []
    for position, unit in enumerate(program.units):
        if unit.unit_class_code == CLASS_CODES["content"]:
            nodes.append((unit.unit_id, node_codes[unit.semantic_code]))
        elif unit.unit_class_code == CLASS_CODES["operator"]:
            selected = program.ports[unit.port_start : unit.port_start + unit.port_count]
            relations.append((unit.unit_id, operator_codes[unit.semantic_code], tuple((role_codes[port.role_code], program.units[port.target_unit_index].unit_id) for port in selected)))
        else:
            raise ValueError(f"UNEXPECTED_MUMBRANE_UNIT:{position}")
    return tuple(sorted(nodes)), tuple(sorted(relations))


def verify_representation_agreement(nodes: tuple, relations: tuple, mumbrane, fieldir, archive) -> str:
    expected = _g1_signature(nodes, relations)
    if _mumbrane_signature(mumbrane) != expected:
        raise ValueError("G1_MUMBRANE_DISAGREEMENT")
    restored_nodes, restored_relations = to_g1(fieldir, archive)
    if _g1_signature(restored_nodes, restored_relations) != expected:
        raise ValueError("G1_FIELDIR_DISAGREEMENT")
    return fieldir_semantic_hash(fieldir)

