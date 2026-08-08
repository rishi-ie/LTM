"""G1-derived inventories used by the factorized compiler."""

from topology_g1.registry import REGISTRY
from topology_g1.schemas import NodeKind

NODE_KINDS = tuple(kind.value for kind in NodeKind)
RELATIONS = tuple(sorted(REGISTRY))
ROLES = tuple(dict.fromkeys(role.name for spec in REGISTRY.values() for role in spec.roles))
POLARITIES = ("positive", "negative")
MODALITIES = ("asserted", "conditional", "hypothetical", "uncertain", "observed")
SCOPES = ("global", "conversation_local", "fictional", "hypothetical", "temporally_bounded")
DISPOSITIONS = ("accept", "clarification_required", "quarantine")

ROLE_INDEX = {name: index for index, name in enumerate(ROLES)}
RELATION_INDEX = {name: index for index, name in enumerate(RELATIONS)}

