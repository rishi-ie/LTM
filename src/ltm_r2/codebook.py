"""Frozen numeric vocabulary for the candidate universal representation."""

from __future__ import annotations

from topology_g1.registry import REGISTRY
from topology_g1.schemas import NodeKind

UNIT_CLASSES = (
    "content",
    "operator",
    "context",
    "provenance",
    "identity",
    "region",
    "constraint",
    "summary",
)
CLASS_CODES = {name: index + 1 for index, name in enumerate(UNIT_CLASSES)}
CLASS_BY_CODE = {value: key for key, value in CLASS_CODES.items()}

NODE_CODES = {kind.value: index + 1 for index, kind in enumerate(sorted(NodeKind, key=lambda item: item.value))}
NODE_BY_CODE = {value: key for key, value in NODE_CODES.items()}
OPERATOR_CODES = {name: index + 100 for index, name in enumerate(sorted(REGISTRY))}
OPERATOR_BY_CODE = {value: key for key, value in OPERATOR_CODES.items()}
ROLE_CODES = {
    name: index + 1
    for index, name in enumerate(sorted({role.name for spec in REGISTRY.values() for role in spec.roles}))
}
ROLE_BY_CODE = {value: key for key, value in ROLE_CODES.items()}

AXIS_CODES = {
    "scope": 1,
    "session": 2,
    "polarity": 3,
    "modality": 4,
    "valid_from": 5,
    "valid_to": 6,
    "authority": 7,
    "confidence": 8,
    "source": 9,
    "region": 10,
    "identity": 11,
}

FEATURES = (
    "content",
    "operator",
    "role",
    "context",
    "provenance",
    "geometry",
    "identity",
    "region",
    "integrity",
)
FEATURE_BITS = {name: 1 << index for index, name in enumerate(FEATURES)}
ALL_FEATURES_MASK = sum(FEATURE_BITS.values())


def feature_mask(*names: str) -> int:
    return sum(FEATURE_BITS[name] for name in names)
