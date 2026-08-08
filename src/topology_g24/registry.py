"""G1-derived operator vocabulary for G2.4."""

from __future__ import annotations

from topology_g1.registry import REGISTRY
from topology_g1.schemas import NodeKind

NODE_KINDS = tuple(kind.value for kind in NodeKind)
RELATION_LABELS = tuple(REGISTRY)
ROLE_LABELS = tuple(dict.fromkeys(role.name for spec in REGISTRY.values() for role in spec.roles))


def relation_index(relation_type: str) -> int:
    return RELATION_LABELS.index(relation_type)


def node_kind_index(node_kind: str) -> int:
    return NODE_KINDS.index(node_kind)


def legal_role_bindings(
    relation_type: str,
    atoms: tuple[object, ...],
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...]:
    """Enumerate bounded G1-legal bindings; caller applies score pruning."""
    from itertools import permutations, product

    spec = REGISTRY[relation_type]
    per_role = []
    for role in spec.roles:
        legal = tuple(atom.local_id for atom in atoms if atom.node_kind in {kind.value for kind in role.allowed_kinds})
        if len(legal) < role.minimum:
            return ()
        if role.minimum > 1:
            choices = tuple(tuple(value) for value in permutations(legal, role.minimum))
        else:
            choices = tuple((value,) for value in legal)
        per_role.append(choices)
    output = []
    for choice in product(*per_role):
        flat = tuple(item for values in choice for item in values)
        if relation_type != "conjoins" and len(flat) != len(set(flat)):
            continue
        output.append(tuple((role.name, tuple(values)) for role, values in zip(spec.roles, choice)))
    return tuple(output)
