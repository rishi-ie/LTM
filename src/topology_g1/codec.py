from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .schemas import (
    NodeKind,
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    ValidityInterval,
)


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_plain(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_plain(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def source_hash(source_id: str) -> str:
    return hashlib.sha256(source_id.encode("utf-8")).hexdigest()


def semantic_id(kind: str, payload: dict[str, Any]) -> str:
    return digest({"kind": kind, "payload": payload})


def encode_node(node: TopologyNode) -> str:
    return canonical_json(node)


def decode_node(text: str) -> TopologyNode:
    raw = json.loads(text)
    expected = {"node_id", "schema_version", "kind", "attributes", "scope_id", "validity", "provenance"}
    if set(raw) != expected:
        raise ValueError("unknown or missing node JSON fields")
    provenance = tuple(Provenance(**item) for item in raw["provenance"])
    validity = ValidityInterval(**raw["validity"])
    return TopologyNode(
        node_id=raw["node_id"],
        schema_version=raw["schema_version"],
        kind=NodeKind(raw["kind"]),
        attributes=tuple((str(key), value) for key, value in raw["attributes"]),
        scope_id=raw["scope_id"],
        validity=validity,
        provenance=provenance,
    )


def encode_relation(relation: RelationInstance) -> str:
    return canonical_json(relation)


def decode_relation(text: str) -> RelationInstance:
    raw = json.loads(text)
    expected = {
        "relation_id", "schema_version", "relation_type", "arguments", "scope_id", "validity",
        "confidence", "authority", "provenance",
    }
    if set(raw) != expected:
        raise ValueError("unknown or missing relation JSON fields")
    return RelationInstance(
        relation_id=raw["relation_id"],
        schema_version=raw["schema_version"],
        relation_type=raw["relation_type"],
        arguments=tuple(RoleBinding(**item) for item in raw["arguments"]),
        scope_id=raw["scope_id"],
        validity=ValidityInterval(**raw["validity"]),
        confidence=raw["confidence"],
        authority=raw["authority"],
        provenance=tuple(Provenance(**item) for item in raw["provenance"]),
    )
