from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .generator import claim, stable_id
from .schemas import (
    AssistantEvent,
    ConversationEvent,
    EpisodeSummary,
    MemoryQuery,
    MemoryResult,
    SessionClaim,
)


class MemoryStore:
    def __init__(self, base_path: Path, session_path: Path) -> None:
        self.base = sqlite3.connect(base_path)
        self.session = sqlite3.connect(session_path)
        self.base.execute("PRAGMA foreign_keys=ON")
        self.session.execute("PRAGMA foreign_keys=ON")
        self.base.execute("CREATE TABLE IF NOT EXISTS base_claims (claim_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.session.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_meta (session_id TEXT PRIMARY KEY, generation INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS raw_events (event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, turn_index INTEGER NOT NULL, event_type TEXT NOT NULL, episode_id TEXT NOT NULL, payload TEXT NOT NULL, source_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS session_operations (operation_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, operation_type TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS session_claims (claim_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL, subject TEXT NOT NULL, predicate TEXT NOT NULL, object_value TEXT NOT NULL, polarity TEXT NOT NULL, scope_id TEXT NOT NULL, valid_from INTEGER NOT NULL, valid_to INTEGER, source_event_id TEXT NOT NULL, provenance TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reference_bindings (session_id TEXT NOT NULL, generation INTEGER NOT NULL, mention TEXT NOT NULL, entity TEXT NOT NULL, PRIMARY KEY(session_id, generation, mention));
            CREATE TABLE IF NOT EXISTS preferences (session_id TEXT NOT NULL, generation INTEGER NOT NULL, pref_key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(session_id, generation, pref_key));
            CREATE TABLE IF NOT EXISTS conflicts (conflict_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL, subject TEXT NOT NULL, predicate TEXT NOT NULL, scope_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assistant_events (event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS episodes (session_id TEXT NOT NULL, generation INTEGER NOT NULL, episode_id TEXT NOT NULL, state TEXT NOT NULL, PRIMARY KEY(session_id, generation, episode_id));
            CREATE TABLE IF NOT EXISTS episode_summaries (summary_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL, episode_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tombstones (session_id TEXT NOT NULL, generation INTEGER NOT NULL, object_id TEXT NOT NULL, PRIMARY KEY(session_id, generation, object_id));
            CREATE TABLE IF NOT EXISTS query_cache (query_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, generation INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS claim_lookup ON session_claims(session_id, generation, subject, predicate, scope_id);
            CREATE INDEX IF NOT EXISTS event_lookup ON raw_events(session_id, turn_index);
            """
        )
        self.base.commit()
        self.session.commit()

    def close(self) -> None:
        self.base.close()
        self.session.close()

    def seed_base(self, item: SessionClaim) -> None:
        payload = json.dumps(asdict(item), sort_keys=True)
        existing = self.base.execute("SELECT payload FROM base_claims WHERE claim_id=?", (item.claim_id,)).fetchone()
        if existing is not None and existing[0] != payload:
            raise ValueError("BASE_ID_CONFLICT")
        self.base.execute("INSERT OR IGNORE INTO base_claims VALUES (?, ?)", (item.claim_id, payload))
        self.base.commit()

    def base_hash(self) -> str:
        rows = self.base.execute("SELECT claim_id, payload FROM base_claims ORDER BY claim_id").fetchall()
        return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()

    def _generation(self, session_id: str) -> int:
        row = self.session.execute("SELECT generation FROM session_meta WHERE session_id=?", (session_id,)).fetchone()
        if row is None:
            self.session.execute("INSERT INTO session_meta VALUES (?, 0)", (session_id,))
            return 0
        return int(row[0])

    def _operation(self, session_id: str, operation_type: str, payload: dict[str, object]) -> None:
        serialized = json.dumps(payload, sort_keys=True)
        operation_id = stable_id(session_id, operation_type, serialized)
        existing = self.session.execute("SELECT payload FROM session_operations WHERE operation_id=?", (operation_id,)).fetchone()
        if existing is not None and existing[0] != serialized:
            raise ValueError("OPERATION_ID_CONFLICT")
        self.session.execute("INSERT OR IGNORE INTO session_operations VALUES (?, ?, ?, ?)", (operation_id, session_id, operation_type, serialized))

    def _event(self, event: ConversationEvent) -> None:
        payload = json.dumps(dict(event.payload), sort_keys=True)
        existing = self.session.execute("SELECT source_hash, payload FROM raw_events WHERE event_id=?", (event.event_id,)).fetchone()
        if existing is not None and existing != (event.source_hash, payload):
            raise ValueError("EVENT_ID_CONFLICT")
        self.session.execute("INSERT OR IGNORE INTO raw_events VALUES (?, ?, ?, ?, ?, ?, ?)", (event.event_id, event.session_id, event.turn_index, event.event_type, event.episode_id, payload, event.source_hash))

    def _insert_claim(self, item: SessionClaim, generation: int) -> None:
        payload = json.dumps(asdict(item), sort_keys=True)
        row = self.session.execute("SELECT payload FROM session_claims WHERE claim_id=?", (item.claim_id,)).fetchone()
        if row is not None and row[0] != payload:
            raise ValueError("CLAIM_ID_CONFLICT")
        self.session.execute("INSERT OR IGNORE INTO session_claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item.claim_id, item.session_id, generation, item.subject, item.predicate, item.object, item.polarity, item.scope_id, item.valid_from_turn, item.valid_to_turn, item.source_event_id, json.dumps(item.provenance_ids), payload))

    def apply(self, event: ConversationEvent, case_id: str) -> None:
        with self.session:
            generation = self._generation(event.session_id)
            self._event(event)
            payload = dict(event.payload)
            self._operation(event.session_id, f"append_{event.event_type}", {"event_id": event.event_id, **payload})
            if event.event_type == "fact":
                item = claim(case_id, event.session_id, payload["tag"], payload["subject"], payload["predicate"], payload["object"], payload["polarity"], payload["scope"], event.turn_index, event.event_id)
                self._insert_claim(item, generation)
            elif event.event_type == "correction":
                self.session.execute("UPDATE session_claims SET valid_to=? WHERE claim_id=? AND session_id=? AND generation=?", (event.turn_index - 1, payload["old_claim_id"], event.session_id, generation))
                item = claim(case_id, event.session_id, payload["tag"], payload["subject"], payload["predicate"], payload["object"], payload["polarity"], payload["scope"], event.turn_index, event.event_id)
                self._insert_claim(item, generation)
                self._operation(event.session_id, "supersede_claim", {"old": payload["old_claim_id"], "new": item.claim_id})
            elif event.event_type == "bind_reference":
                self.session.execute("INSERT OR REPLACE INTO reference_bindings VALUES (?, ?, ?, ?)", (event.session_id, generation, payload["mention"], payload["entity"]))
            elif event.event_type == "preference":
                self.session.execute("INSERT OR REPLACE INTO preferences VALUES (?, ?, ?, ?)", (event.session_id, generation, payload["key"], payload["value"]))
            elif event.event_type == "conflict":
                conflict_id = stable_id(event.session_id, "conflict", payload["subject"], payload["predicate"], payload["scope"])
                self.session.execute("INSERT OR IGNORE INTO conflicts VALUES (?, ?, ?, ?, ?, ?)", (conflict_id, event.session_id, generation, payload["subject"], payload["predicate"], payload["scope"]))
            elif event.event_type == "fold_episode":
                self._fold(event.session_id, generation, payload["folded_episode"])
            self.session.execute("DELETE FROM query_cache WHERE session_id=?", (event.session_id,))

    def _fold(self, session_id: str, generation: int, episode_id: str) -> EpisodeSummary:
        claims = self._claims(session_id, generation, None, None, "global", include_base=False)[0]
        events = [row[0] for row in self.session.execute("SELECT event_id FROM raw_events WHERE session_id=? AND episode_id=? ORDER BY turn_index", (session_id, episode_id)).fetchall()]
        preferences = [row[0] for row in self.session.execute("SELECT pref_key FROM preferences WHERE session_id=? AND generation=?", (session_id, generation)).fetchall()]
        conflict_ids = [row[0] for row in self.session.execute("SELECT conflict_id FROM conflicts WHERE session_id=? AND generation=?", (session_id, generation)).fetchall()]
        claim_ids = tuple(item.claim_id for item in claims)
        provenance = tuple(sorted({source for item in claims for source in item.provenance_ids}))
        summary_id = stable_id(session_id, "summary", episode_id, ",".join(claim_ids))
        digest = hashlib.sha256("|".join(claim_ids + provenance + tuple(events)).encode()).hexdigest()
        summary = EpisodeSummary(summary_id, session_id, episode_id, claim_ids, (), tuple(preferences), tuple(conflict_ids), provenance, tuple(events), digest)
        self.session.execute("INSERT OR REPLACE INTO episode_summaries VALUES (?, ?, ?, ?, ?)", (summary_id, session_id, generation, episode_id, json.dumps(asdict(summary), sort_keys=True)))
        self.session.execute("INSERT OR REPLACE INTO episodes VALUES (?, ?, ?, ?)", (session_id, generation, episode_id, "folded"))
        self._operation(session_id, "fold_episode", {"summary_id": summary_id, "episode_id": episode_id})
        return summary

    def _claims(self, session_id: str, generation: int, subject: str | None, predicate: str | None, scope_id: str, *, include_base: bool = True) -> tuple[list[SessionClaim], int]:
        rows_read = 0
        query = "SELECT payload FROM session_claims WHERE session_id=? AND generation=?"
        values: list[object] = [session_id, generation]
        if subject is not None:
            query += " AND subject=?"; values.append(subject)
        if predicate is not None:
            query += " AND predicate=?"; values.append(predicate)
        current_turn = self.session.execute("SELECT COALESCE(MAX(turn_index), 0) FROM raw_events WHERE session_id=?", (session_id,)).fetchone()[0]
        query += " AND scope_id=? AND (valid_to IS NULL OR valid_to>=?) ORDER BY claim_id"; values.extend((scope_id, current_turn))
        session_rows = self.session.execute(query, tuple(values)).fetchall(); rows_read += len(session_rows)
        tombstones = {row[0] for row in self.session.execute("SELECT object_id FROM tombstones WHERE session_id=? AND generation=?", (session_id, generation)).fetchall()}
        claims = [SessionClaim(**json.loads(payload)) for (payload,) in session_rows if json.loads(payload)["claim_id"] not in tombstones]
        if include_base and scope_id == "global":
            base_rows = self.base.execute("SELECT payload FROM base_claims").fetchall()
            for (payload,) in base_rows:
                item = SessionClaim(**json.loads(payload))
                if (subject is None or item.subject == subject) and (predicate is None or item.predicate == predicate):
                    claims.append(item); rows_read += 1
        return claims, rows_read

    def query(self, query: MemoryQuery, *, assistant_as_evidence: bool = False, summary_without_provenance: bool = False) -> MemoryResult:
        with self.session:
            generation = self._generation(query.session_id)
            subject, rows_read = query.subject, 0
            bindings = self.session.execute("SELECT mention, entity FROM reference_bindings WHERE session_id=? AND generation=? ORDER BY mention", (query.session_id, generation)).fetchall(); rows_read += len(bindings)
            if not subject:
                matches = [entity for mention, entity in bindings if mention == "it"]
                subject = matches[0] if len(matches) == 1 else None
            reopened: tuple[str, ...] = ()
            if query.episode_reference:
                row = self.session.execute("SELECT payload FROM episode_summaries WHERE session_id=? AND generation=? AND episode_id=?", (query.session_id, generation, query.episode_reference)).fetchone(); rows_read += int(row is not None)
                if row is not None:
                    summary = EpisodeSummary(**json.loads(row[0]))
                    if summary_without_provenance or not summary.provenance_ids:
                        return MemoryResult(query.query_id, "unknown", (), tuple(bindings), (), (), (), (), rows_read)
                    reopened = (query.episode_reference,)
                    self.session.execute("INSERT OR REPLACE INTO episodes VALUES (?, ?, ?, ?)", (query.session_id, generation, query.episode_reference, "reopened"))
                    self._operation(query.session_id, "reopen_episode", {"episode_id": query.episode_reference})
            if subject is None:
                return MemoryResult(query.query_id, "unknown", (), tuple(bindings), (), (), (), reopened, rows_read)
            claims, read = self._claims(query.session_id, generation, subject, query.predicate, query.scope_id); rows_read += read
            if assistant_as_evidence and not claims:
                assistant_rows = self.session.execute("SELECT payload FROM assistant_events WHERE session_id=? AND generation=?", (query.session_id, generation)).fetchall(); rows_read += len(assistant_rows)
                for (payload,) in assistant_rows:
                    event = AssistantEvent(**json.loads(payload))
                    if event.authorized_claim_ids:
                        claims = [SessionClaim(stable_id(event.event_id, "promoted"), query.session_id, subject, query.predicate, "assistant-memory", "positive", query.scope_id, 0, None, event.event_id, event.decisive_provenance_ids)]
                        break
            prefs = tuple(row[1] for row in self.session.execute("SELECT pref_key, value FROM preferences WHERE session_id=? AND generation=? ORDER BY pref_key", (query.session_id, generation)).fetchall())
            conflicts = tuple(row[0] for row in self.session.execute("SELECT conflict_id FROM conflicts WHERE session_id=? AND generation=? AND subject=? AND predicate=? AND scope_id=?", (query.session_id, generation, subject, query.predicate, query.scope_id)).fetchall())
            status = "conflict" if conflicts else "verified" if claims else "unknown"
            provenance = tuple(sorted({source for item in claims for source in item.provenance_ids}))
            result = MemoryResult(query.query_id, status, tuple(claims), tuple(bindings), prefs, conflicts, provenance, reopened, rows_read)
            self.session.execute("INSERT OR REPLACE INTO query_cache VALUES (?, ?, ?, ?)", (query.query_id, query.session_id, generation, json.dumps(asdict(result), sort_keys=True)))
            return result

    def store_assistant(self, result: MemoryResult, session_id: str) -> AssistantEvent:
        with self.session:
            generation = self._generation(session_id)
            event_id = stable_id(session_id, "assistant", result.query_id, ",".join(item.claim_id for item in result.claims))
            text = "I don't have enough verified information." if result.status == "unknown" else f"Verified: {result.status}."
            event = AssistantEvent(event_id, session_id, text, tuple(item.claim_id for item in result.claims), result.decisive_provenance_ids, False, 0.25)
            self.session.execute("INSERT OR REPLACE INTO assistant_events VALUES (?, ?, ?, ?)", (event.event_id, session_id, generation, json.dumps(asdict(event), sort_keys=True)))
            self._operation(session_id, "append_assistant_event", {"event_id": event.event_id, "independent_evidence": False})
            return event

    def delete(self, session_id: str, claim_id: str) -> None:
        with self.session:
            generation = self._generation(session_id)
            self.session.execute("INSERT OR IGNORE INTO tombstones VALUES (?, ?, ?)", (session_id, generation, claim_id))
            self.session.execute("DELETE FROM query_cache WHERE session_id=?", (session_id,))
            self._operation(session_id, "delete_session_object", {"claim_id": claim_id})

    def clear(self, session_id: str) -> None:
        with self.session:
            generation = self._generation(session_id)
            self.session.execute("UPDATE session_meta SET generation=? WHERE session_id=?", (generation + 1, session_id))
            self.session.execute("DELETE FROM query_cache WHERE session_id=?", (session_id,))
            self._operation(session_id, "clear_session", {"old_generation": generation, "new_generation": generation + 1})

    def session_hash(self) -> str:
        tables = ("session_meta", "raw_events", "session_operations", "session_claims", "reference_bindings", "preferences", "conflicts", "assistant_events", "episodes", "episode_summaries", "tombstones", "query_cache")
        rows = [(table, self.session.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()) for table in tables]
        return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
