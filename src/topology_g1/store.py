from __future__ import annotations

import sqlite3
from pathlib import Path

from .codec import (
    canonical_json,
    decode_node,
    decode_relation,
    digest,
    encode_node,
    encode_relation,
)
from .schemas import RelationInstance, SchemaError, TopologyNode


class TopologyStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, scope_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS relations (id TEXT PRIMARY KEY, relation_type TEXT NOT NULL, scope_id TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, operation_type TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources (source_id TEXT PRIMARY KEY, source_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS quarantine (id INTEGER PRIMARY KEY, code TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY, description TEXT NOT NULL);
            """
        )
        self.db.execute("INSERT OR IGNORE INTO schema_versions VALUES (2, 'G1 topology schema')")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def insert_node(self, node: TopologyNode) -> None:
        payload = encode_node(node)
        with self.db:
            for source in node.provenance:
                self._source(source.source_id, source.source_hash)
            self._insert("nodes", node.node_id, payload, (node.kind.value, node.scope_id, node.schema_version))
            self._operation(node.node_id, "insert_node", payload)

    def insert_relation(self, relation: RelationInstance) -> None:
        payload = encode_relation(relation)
        with self.db:
            for source in relation.provenance:
                self._source(source.source_id, source.source_hash)
            self._insert("relations", relation.relation_id, payload, (relation.relation_type, relation.scope_id, relation.schema_version))
            self._operation(relation.relation_id, "insert_relation", payload)

    def _source(self, source_id: str, source_hash: str) -> None:
        existing = self.db.execute("SELECT source_hash FROM sources WHERE source_id=?", (source_id,)).fetchone()
        if existing is not None and existing[0] != source_hash:
            raise SchemaError("SOURCE_HASH_MISMATCH", source_id)
        self.db.execute("INSERT OR IGNORE INTO sources VALUES (?, ?)", (source_id, source_hash))

    def _insert(self, table: str, identity: str, payload: str, fields: tuple[object, ...]) -> None:
        existing = self.db.execute(f"SELECT payload FROM {table} WHERE id=?", (identity,)).fetchone()
        if existing is not None:
            if existing[0] != payload:
                raise SchemaError("CONFLICTING_ID", identity)
            return
        self.db.execute(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?)", (identity, *fields, payload))

    def _operation(self, identity: str, operation_type: str, payload: str) -> None:
        existing = self.db.execute("SELECT payload FROM operations WHERE id=?", (identity,)).fetchone()
        if existing is not None:
            if existing[0] != payload:
                raise SchemaError("CONFLICTING_ID", identity)
            return
        self.db.execute("INSERT INTO operations VALUES (?, ?, ?)", (identity, operation_type, payload))

    def nodes(self) -> dict[str, TopologyNode]:
        rows = self.db.execute("SELECT payload FROM nodes ORDER BY id").fetchall()
        return {node.node_id: node for (payload,) in rows for node in (decode_node(payload),)}

    def relations(self) -> dict[str, RelationInstance]:
        rows = self.db.execute("SELECT payload FROM relations ORDER BY id").fetchall()
        return {relation.relation_id: relation for (payload,) in rows for relation in (decode_relation(payload),)}

    def snapshot_hash(self) -> str:
        rows = []
        for table in ("nodes", "relations", "operations", "sources", "schema_versions"):
            rows.append((table, self.db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()))
        return digest(rows)

    def replay(self, target: Path) -> TopologyStore:
        result = TopologyStore(target)
        for node in self.nodes().values():
            result.insert_node(node)
        for relation in self.relations().values():
            result.insert_relation(relation)
        return result

    def quarantine(self, code: str, payload: object) -> None:
        with self.db:
            self.db.execute("INSERT INTO quarantine(code, payload) VALUES (?, ?)", (code, canonical_json(payload)))
