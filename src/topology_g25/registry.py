"""G1-derived, closed vocabularies for G2.5."""

from __future__ import annotations

from topology_g1.registry import REGISTRY
from topology_g1.schemas import NodeKind

NODE_KINDS = tuple(kind.value for kind in NodeKind)
RELATIONS = tuple(REGISTRY)
ROLES = tuple(
    dict.fromkeys(role.name for specification in REGISTRY.values() for role in specification.roles)
)
POLARITIES = ("positive", "negative")
MODALITIES = ("asserted", "conditional", "hypothetical", "uncertain", "observed")
SCOPES = ("global", "conversation_local", "fictional", "hypothetical", "temporally_bounded")
DISPOSITIONS = ("accept", "clarification_required", "quarantine")


def relation_index(relation: str) -> int:
    return RELATIONS.index(relation)


def role_index(role: str) -> int:
    return ROLES.index(role)
