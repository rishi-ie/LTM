from __future__ import annotations

from .schemas import NodeKind, Provenance, SchemaError, TopologyNode, ValidityInterval


def node_v1_to_v2(raw: dict[str, object]) -> TopologyNode:
    required = {
        "node_id", "schema_version", "kind", "attributes", "scope", "source_id", "source_span_start",
        "source_span_end", "source_hash", "valid_from", "valid_to",
    }
    if set(raw) != required or raw.get("schema_version") != 1:
        raise SchemaError("SCHEMA_VERSION_MISMATCH", "invalid version 1 node")
    try:
        provenance = Provenance(
            str(raw["source_id"]), int(raw["source_span_start"]), int(raw["source_span_end"]), str(raw["source_hash"])
        )
        return TopologyNode(
            str(raw["node_id"]), 2, NodeKind(str(raw["kind"])),
            tuple((str(key), value) for key, value in raw["attributes"]), str(raw["scope"]),
            ValidityInterval(raw["valid_from"], raw["valid_to"]), (provenance,),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, SchemaError):
            raise
        raise SchemaError("SCHEMA_VERSION_MISMATCH", "invalid version 1 node") from exc
