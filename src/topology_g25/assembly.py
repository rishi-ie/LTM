"""Atomic G1 assembly from already-selected typed factors."""

from __future__ import annotations

from topology_g1.codec import canonical_json, digest, semantic_id
from topology_g1.registry import validate_relation
from topology_g1.schemas import (
    Provenance,
    RelationInstance,
    RoleBinding,
    TopologyNode,
    TopologyOperation,
    ValidityInterval,
)

from .field import channel_hashes
from .schemas import ContentAtomOccurrence, SentenceSource, StructuredFieldHandoff, TopologyFactor


def _provenance(source: SentenceSource, atom: ContentAtomOccurrence | None = None) -> Provenance:
    if atom is None:
        return Provenance(source.source_id, 0, len(source.text), source.source_hash)
    return Provenance(source.source_id, atom.source_start, atom.source_end, source.source_hash)


def assemble_handoff(
    source: SentenceSource,
    atoms: tuple[ContentAtomOccurrence, ...],
    factors: tuple[TopologyFactor, ...],
) -> StructuredFieldHandoff | None:
    try:
        nodes: list[TopologyNode] = []
        local_to_node: dict[str, str] = {}
        for atom in atoms:
            node_id = semantic_id(
                "g25-node",
                {
                    "source": source.source_hash,
                    "kind": atom.node_kind,
                    "span": (atom.source_start, atom.source_end),
                    "text": atom.text.casefold(),
                    "scope": atom.scope_id,
                    "polarity": atom.polarity,
                    "modality": atom.modality,
                },
            )
            node = TopologyNode(
                node_id,
                2,
                __import__("topology_g1.schemas", fromlist=["NodeKind"]).NodeKind(atom.node_kind),
                tuple(
                    sorted(
                        (
                            ("end", atom.source_end),
                            ("modality", atom.modality),
                            ("polarity", atom.polarity),
                            ("start", atom.source_start),
                            ("text", atom.text),
                        )
                    )
                ),
                atom.scope_id,
                ValidityInterval(atom.valid_from, atom.valid_to),
                (_provenance(source, atom),),
            )
            nodes.append(node)
            local_to_node[atom.atom_id] = node_id
        relations: list[RelationInstance] = []
        for factor in factors:
            arguments = tuple(
                RoleBinding(role, local_to_node[atom_id])
                for role, atom_id in factor.sparse_incidence
            )
            relation = RelationInstance(
                semantic_id(
                    "g25-relation",
                    {
                        "type": factor.relation_type,
                        "arguments": tuple((item.role, item.node_id) for item in arguments),
                        "scope": factor.context.scope_id,
                        "source": source.source_hash,
                    },
                ),
                2,
                factor.relation_type,
                arguments,
                factor.context.scope_id,
                ValidityInterval(factor.context.valid_from, factor.context.valid_to),
                factor.confidence,
                factor.context.authority,
                (_provenance(source),),
            )
            relations.append(relation)
        node_map = {node.node_id: node for node in nodes}
        for relation in relations:
            validate_relation(relation, node_map)
        provenance = (_provenance(source),)
        operations = tuple(
            [
                TopologyOperation(
                    semantic_id("g25-op", {"type": "insert_node", "payload": canonical_json(node)}),
                    "insert_node",
                    node,
                    provenance,
                )
                for node in nodes
            ]
            + [
                TopologyOperation(
                    semantic_id(
                        "g25-op", {"type": "insert_relation", "payload": canonical_json(relation)}
                    ),
                    "insert_relation",
                    relation,
                    provenance,
                )
                for relation in relations
            ]
        )
        channels = channel_hashes(factors)
        # G1 canonical codec deliberately accepts immutable tuple structures;
        # mutable lists are not valid semantic payloads.
        exact_hash = digest(
            {"nodes": tuple(nodes), "relations": tuple(relations), "operations": operations}
        )
        return StructuredFieldHandoff(
            atoms, factors, operations, *channels[:5], exact_hash, channels[5]
        )
    except (KeyError, TypeError, ValueError):
        return None
