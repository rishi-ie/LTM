"""SQLite catalog and content-addressed atomic field generations."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from ltm.adapters import config_from_g1, from_g1, to_g1
from ltm.codec import pack_program as pack_fieldir
from ltm.codec import read_archive, read_manifest, unpack_program, verify_packed
from ltm.schema import SourceArchive, SourceArchiveRecord
from ltm_r2.codec import pack_program as pack_mumbrane
from ltm_r2.codec import unpack_program as unpack_mumbrane

from parasite.contracts import (
    CandidateTransaction,
    CommitReceipt,
    EquilibriumAtom,
    EquilibriumFactor,
    stable_id,
)
from parasite.integrity import (
    canonical_json,
    digest,
    mumbrane_from_g1,
    verify_representation_agreement,
    write_atomic,
)


@dataclass(frozen=True, slots=True)
class LoadedGeneration:
    generation_id: str
    root: Path
    nodes: tuple
    relations: tuple
    fieldir: object
    archive: SourceArchive
    atoms: tuple[EquilibriumAtom, ...]
    factors: tuple[EquilibriumFactor, ...]
    manifest: dict


class FieldStore:
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.archive_root = state_path / "archive"
        self.fields_root = state_path / "fields"
        self.staging_root = state_path / "staging"
        for path in (state_path, self.archive_root, self.fields_root, self.staging_root):
            path.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(state_path / "catalog.sqlite")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def close(self) -> None:
        self.connection.close()

    def _schema(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS active_generations(
          tenant_id TEXT NOT NULL, reality_id TEXT NOT NULL, generation_id TEXT NOT NULL,
          PRIMARY KEY(tenant_id, reality_id)
        );
        CREATE TABLE IF NOT EXISTS commits(
          transaction_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, reality_id TEXT NOT NULL,
          generation_id TEXT NOT NULL, receipt_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS session_objects(
          tenant_id TEXT NOT NULL, session_id TEXT NOT NULL, reality_id TEXT NOT NULL,
          object_id TEXT NOT NULL, object_kind TEXT NOT NULL, payload_json TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1, authority REAL NOT NULL,
          PRIMARY KEY(tenant_id, session_id, object_id)
        );
        CREATE INDEX IF NOT EXISTS session_lookup ON session_objects(tenant_id, session_id, reality_id, active);
        """)
        self.connection.commit()

    @staticmethod
    def _partition(tenant_id: str, reality_id: str) -> tuple[str, str]:
        return stable_id("tenant", tenant_id)[:24], stable_id("reality", reality_id)[:24]

    def generation_root(self, tenant_id: str, reality_id: str, generation_id: str) -> Path:
        tenant, reality = self._partition(tenant_id, reality_id)
        return self.fields_root / tenant / reality / generation_id

    def active_generation_id(self, tenant_id: str, reality_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT generation_id FROM active_generations WHERE tenant_id=? AND reality_id=?",
            (tenant_id, reality_id),
        ).fetchone()
        return None if row is None else str(row[0])

    def load(self, tenant_id: str, reality_id: str) -> LoadedGeneration | None:
        generation_id = self.active_generation_id(tenant_id, reality_id)
        if generation_id is None:
            return None
        root = self.generation_root(tenant_id, reality_id, generation_id)
        manifest = json.loads((root / "generation.json").read_text(encoding="utf-8"))
        if manifest["tenant_id"] != tenant_id or manifest["reality_id"] != reality_id:
            raise ValueError("GENERATION_PARTITION_MISMATCH")
        fieldir_root = root / "fieldir"
        fieldir_manifest = read_manifest(fieldir_root)
        verify_packed(fieldir_root, fieldir_manifest)
        archive = read_archive(fieldir_root) or SourceArchive(())
        fieldir = unpack_program(fieldir_root, config_from_g1(), archive)
        nodes, relations = to_g1(fieldir, archive)
        mumbrane = unpack_mumbrane(root / "mumbrane")
        verify_representation_agreement(nodes, relations, mumbrane, fieldir, archive)
        equilibrium = json.loads((root / "equilibrium.json").read_text(encoding="utf-8"))
        atoms = tuple(EquilibriumAtom(**item) for item in equilibrium["atoms"])
        factors = tuple(EquilibriumFactor(
            item["body_id"], tuple(item["input_atom_ids"]), item["outcome_atom_id"], item["outcome_polarity"],
            item["authority"], item["confidence"], item["base_weight"], item["independent_source_key"],
            item["scope_key"], item["valid_from"], item["valid_to"],
        ) for item in equilibrium["factors"])
        return LoadedGeneration(generation_id, root, nodes, relations, fieldir, archive, atoms, factors, manifest)

    @staticmethod
    def _merge(existing: tuple, incoming: tuple, identity: str) -> tuple:
        values = {getattr(item, identity): item for item in existing}
        for item in incoming:
            key = getattr(item, identity)
            if key in values and values[key] != item:
                raise ValueError("IDENTITY_CONFLICT")
            values[key] = item
        return tuple(sorted(values.values(), key=lambda item: getattr(item, identity)))

    def _archive_source(self, source_id: str, text: str) -> str:
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        destination = self.archive_root / content_hash
        if destination.exists():
            if (destination / "source.txt").read_text(encoding="utf-8") != text:
                raise ValueError("SOURCE_ARCHIVE_COLLISION")
            return content_hash
        stage = self.staging_root / f"archive-{content_hash}"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        write_atomic(stage / "source.txt", text)
        write_atomic(stage / "source.json", {"source_id": source_id, "source_hash": content_hash})
        os.replace(stage, destination)
        return content_hash

    @staticmethod
    def _flush_tree(root: Path) -> None:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def commit(self, candidate: CandidateTransaction) -> CommitReceipt:
        self._archive_source(candidate.source_id, candidate.source_text)
        previous = self.load(candidate.tenant_id, candidate.reality_id)
        nodes = self._merge(() if previous is None else previous.nodes, candidate.nodes, "node_id")
        relations = self._merge(() if previous is None else previous.relations, candidate.relations, "relation_id")
        atoms = self._merge(() if previous is None else previous.atoms, candidate.equilibrium_atoms, "atom_id")
        factors = self._merge(() if previous is None else previous.factors, candidate.equilibrium_factors, "body_id")
        return self._materialize(candidate, previous, nodes, relations, atoms, factors)

    def _materialize(self, candidate, previous, nodes, relations, atoms, factors) -> CommitReceipt:
        previous_id = None if previous is None else previous.generation_id
        fieldir, generated_archive = from_g1(nodes, relations)
        old_records = () if previous is None else previous.archive.records
        records = {item.source_id: item for item in old_records}
        records[candidate.source_id] = SourceArchiveRecord(candidate.source_id, candidate.source_text, hashlib.sha256(candidate.source_text.encode("utf-8")).hexdigest())
        archive = SourceArchive(tuple(sorted(records.values(), key=lambda item: item.source_id)), generated_archive.node_attributes, generated_archive.surface_claims)
        mumbrane = mumbrane_from_g1(nodes, relations, tuple((item.source_id, item.text) for item in archive.records))
        semantic_hash = verify_representation_agreement(nodes, relations, mumbrane, fieldir, archive)
        generation_id = digest({
            "tenant": candidate.tenant_id, "reality": candidate.reality_id, "semantic": semantic_hash,
            "mumbrane": mumbrane.substrate_sha256, "atoms": atoms, "factors": factors,
        })
        destination = self.generation_root(candidate.tenant_id, candidate.reality_id, generation_id)
        row = self.connection.execute("SELECT receipt_json FROM commits WHERE transaction_id=?", (candidate.transaction_id,)).fetchone()
        if row is not None:
            return CommitReceipt(**json.loads(row[0]))
        if destination.exists():
            raise ValueError("UNREFERENCED_GENERATION_COLLISION")
        stage = self.staging_root / candidate.transaction_id
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        mumbrane_manifest = pack_mumbrane(stage / "mumbrane", mumbrane)
        fieldir_manifest = pack_fieldir(stage / "fieldir", fieldir, archive)
        write_atomic(stage / "equilibrium.json", {"atoms": [asdict(item) for item in atoms], "factors": [asdict(item) for item in factors]})
        generation = {
            "generation_id": generation_id, "tenant_id": candidate.tenant_id, "reality_id": candidate.reality_id,
            "previous_generation_id": previous_id, "transaction_id": candidate.transaction_id,
            "substrate_hash": mumbrane.substrate_sha256, "fieldir_hash": fieldir_manifest.semantic_sha256,
            "archive_hash": fieldir_manifest.archive_sha256, "mumbrane_manifest_hash": digest(mumbrane_manifest),
        }
        write_atomic(stage / "generation.json", generation)
        # Reload both packed views before they can become authoritative.
        unpack_mumbrane(stage / "mumbrane")
        verify_packed(stage / "fieldir", fieldir_manifest)
        self._flush_tree(stage)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, destination)
        receipt = CommitReceipt(generation_id, mumbrane.substrate_sha256, fieldir_manifest.semantic_sha256, fieldir_manifest.archive_sha256 or "0" * 64, previous_id, True)
        with self.connection:
            self.connection.execute(
                "INSERT INTO commits(transaction_id,tenant_id,reality_id,generation_id,receipt_json) VALUES(?,?,?,?,?)",
                (candidate.transaction_id, candidate.tenant_id, candidate.reality_id, generation_id, canonical_json(receipt)),
            )
            self.connection.execute(
                "INSERT INTO active_generations VALUES(?,?,?) ON CONFLICT(tenant_id,reality_id) DO UPDATE SET generation_id=excluded.generation_id",
                (candidate.tenant_id, candidate.reality_id, generation_id),
            )
        return receipt

    def delete_base(self, tenant_id: str, reality_id: str, object_id: str) -> bool:
        previous = self.load(tenant_id, reality_id)
        if previous is None:
            return False
        known = {node.node_id for node in previous.nodes} | {relation.relation_id for relation in previous.relations}
        if object_id not in known:
            return False
        nodes = tuple(node for node in previous.nodes if node.node_id != object_id)
        node_ids = {node.node_id for node in nodes}
        relations = tuple(
            relation for relation in previous.relations
            if relation.relation_id != object_id and all(argument.node_id in node_ids for argument in relation.arguments)
        )
        atoms = tuple(atom for atom in previous.atoms if atom.atom_id in node_ids)
        factors = tuple(
            factor for factor in previous.factors
            if factor.body_id != object_id and factor.outcome_atom_id in node_ids and set(factor.input_atom_ids) <= node_ids
        )
        source_text = f"delete:{object_id}"
        source_id = stable_id("delete-source", tenant_id, reality_id, object_id, previous.generation_id)
        candidate = CandidateTransaction(
            stable_id("delete-transaction", tenant_id, reality_id, object_id, previous.generation_id),
            tenant_id, reality_id, source_id, source_text, (), (),
        )
        self._archive_source(source_id, source_text)
        self._materialize(candidate, previous, nodes, relations, atoms, factors)
        return True

    def commit_session_event(self, candidate: CandidateTransaction, session_id: str) -> CommitReceipt:
        prior = self.connection.execute("SELECT receipt_json FROM commits WHERE transaction_id=?", (candidate.transaction_id,)).fetchone()
        if prior is not None:
            return CommitReceipt(**json.loads(prior[0]))
        self._archive_source(candidate.source_id, candidate.source_text)
        event = dict(candidate.conversation_event)
        object_id = str(event["node_id"])
        action = str(event["action"])
        if action in {"correct", "retract"}:
            target_ids = tuple(event["target_ids"])
            row = self.connection.execute(
                "SELECT object_id FROM session_objects WHERE tenant_id=? AND session_id=? AND reality_id=? AND object_id=? AND active=1",
                (candidate.tenant_id, session_id, candidate.reality_id, target_ids[0]),
            ).fetchone()
            if row is None:
                raise ValueError("TARGET_NOT_ACTIVE_IN_SESSION")
        payload = canonical_json(event)
        generation_id = digest({"session": session_id, "event": event, "transaction": candidate.transaction_id})
        # Independently prove this accepted event is representable in all three views.
        fieldir, archive = from_g1(candidate.nodes, candidate.relations)
        mumbrane = mumbrane_from_g1(candidate.nodes, candidate.relations, ((candidate.source_id, candidate.source_text),))
        verify_representation_agreement(candidate.nodes, candidate.relations, mumbrane, fieldir, archive)
        receipt = CommitReceipt(generation_id, mumbrane.substrate_sha256, digest(fieldir), hashlib.sha256(candidate.source_text.encode()).hexdigest(), None, True)
        with self.connection:
            if action in {"correct", "retract"}:
                self.connection.execute(
                    "UPDATE session_objects SET active=0 WHERE tenant_id=? AND session_id=? AND reality_id=? AND object_id=?",
                    (candidate.tenant_id, session_id, candidate.reality_id, event["target_ids"][0]),
                )
            self.connection.execute(
                "INSERT INTO session_objects VALUES(?,?,?,?,?,?,?,?)",
                (candidate.tenant_id, session_id, candidate.reality_id, object_id, action or "claim", payload, 1, 1.0),
            )
            self.connection.execute(
                "INSERT INTO commits(transaction_id,tenant_id,reality_id,generation_id,receipt_json) VALUES(?,?,?,?,?)",
                (candidate.transaction_id, candidate.tenant_id, candidate.reality_id, generation_id, canonical_json(receipt)),
            )
        return receipt

    def session_rows(self, tenant_id: str, reality_id: str, session_id: str) -> tuple[dict, ...]:
        rows = self.connection.execute(
            "SELECT payload_json,authority,object_kind,object_id FROM session_objects WHERE tenant_id=? AND reality_id=? AND session_id=? AND active=1 ORDER BY rowid",
            (tenant_id, reality_id, session_id),
        ).fetchall()
        return tuple({**json.loads(payload), "authority": authority, "object_kind": kind, "object_id": object_id} for payload, authority, kind, object_id in rows)

    def store_assistant_response(self, tenant_id: str, reality_id: str, session_id: str, response_text: str, query_id: str) -> None:
        object_id = stable_id("assistant-response", tenant_id, session_id, query_id, response_text)
        payload = canonical_json({"content": response_text, "non_evidence": True, "query_id": query_id})
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO session_objects VALUES(?,?,?,?,?,?,?,?)",
                (tenant_id, session_id, reality_id, object_id, "assistant_response", payload, 1, 0.25),
            )

    def clear_session(self, tenant_id: str, session_id: str) -> int:
        with self.connection:
            cursor = self.connection.execute("UPDATE session_objects SET active=0 WHERE tenant_id=? AND session_id=? AND active=1", (tenant_id, session_id))
        return int(cursor.rowcount)

    def delete_session_object(self, tenant_id: str, reality_id: str, object_id: str) -> bool:
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE session_objects SET active=0 WHERE tenant_id=? AND reality_id=? AND object_id=? AND active=1",
                (tenant_id, reality_id, object_id),
            )
        return bool(cursor.rowcount)

    def inspect(self, tenant_id: str, reality_id: str) -> dict:
        loaded = self.load(tenant_id, reality_id)
        sessions = self.connection.execute(
            "SELECT COUNT(*) FROM session_objects WHERE tenant_id=? AND reality_id=? AND active=1", (tenant_id, reality_id)
        ).fetchone()[0]
        return {
            "tenant_id": tenant_id, "reality_id": reality_id, "generation_id": None if loaded is None else loaded.generation_id,
            "nodes": 0 if loaded is None else len(loaded.nodes), "relations": 0 if loaded is None else len(loaded.relations),
            "equilibrium_atoms": 0 if loaded is None else len(loaded.atoms), "equilibrium_factors": 0 if loaded is None else len(loaded.factors),
            "active_session_objects": sessions,
        }
