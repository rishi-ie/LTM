from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .generator import claim, stable_id
from .schemas import ConversationCase, MemoryQuery
from .store import MemoryStore


def _query(case: ConversationCase, event, *, subject: str | None = None, assistant_as_evidence: bool = False, summary_without_provenance: bool = False) -> MemoryQuery:
    payload = dict(event.payload)
    return MemoryQuery(stable_id(case.conversation_id, "query", event.event_id, str(assistant_as_evidence), str(summary_without_provenance)), case.session_id, subject if subject is not None else (payload.get("subject") or None), payload["predicate"], payload["scope"], payload.get("episode_reference"), None)


def run_case(case: ConversationCase, root: Path, *, controls: bool = False) -> dict:
    base_path, session_path = root / "base.sqlite", root / f"{case.session_id}.sqlite"
    store = MemoryStore(base_path, session_path)
    store.seed_base(case.base_claim)
    base_hash = store.base_hash()
    records: list[dict] = []
    restart_equal = False
    for event in case.events:
        store.apply(event, case.conversation_id)
        if event.turn_index == 6:
            before = store.session_hash()
            store.close()
            store = MemoryStore(base_path, session_path)
            after = store.session_hash()
            restart_equal = before == after
            records.append({"kind": "restart", "equal": restart_equal})
        if event.event_type == "query":
            result = store.query(_query(case, event))
            assistant = store.store_assistant(result, case.session_id)
            records.append({"kind": dict(event.payload)["query"], "result": asdict(result), "assistant": asdict(assistant)})
    corrected_event = next(event for event in case.events if event.event_type == "correction")
    corrected = claim(case.conversation_id, case.session_id, "corrected", corrected_event.value("subject"), corrected_event.value("predicate"), corrected_event.value("object"), corrected_event.value("polarity"), corrected_event.value("scope"), corrected_event.turn_index, corrected_event.event_id)
    delete_query_event = next(event for event in case.events if event.event_type == "query" and event.value("query") == "correction")
    episode_event = next(event for event in case.events if event.event_type == "query" and event.value("query") == "episode")
    summary_control = store.query(_query(case, episode_event, summary_without_provenance=True), summary_without_provenance=True) if controls else None
    uncompressed_episode = store.query(MemoryQuery(stable_id(case.conversation_id, "uncompressed", episode_event.event_id), case.session_id, episode_event.value("subject"), episode_event.value("predicate"), episode_event.value("scope"), None, None))
    store.delete(case.session_id, corrected.claim_id)
    deleted = store.query(_query(case, delete_query_event))
    promoted = store.query(_query(case, delete_query_event, assistant_as_evidence=True), assistant_as_evidence=True)
    store.clear(case.session_id)
    base_query = MemoryQuery(stable_id(case.conversation_id, "base-after-clear"), case.session_id, case.base_claim.subject, "holds", "global", None, None)
    session_query = MemoryQuery(stable_id(case.conversation_id, "session-after-clear"), case.session_id, corrected.subject, "holds", "global", None, None)
    post_clear_base, post_clear_session = store.query(base_query), store.query(session_query)
    final_hash = store.session_hash()
    base_unchanged = store.base_hash() == base_hash
    store.close()
    return {"conversation_id": case.conversation_id, "family": case.family, "records": records, "deleted": asdict(deleted), "assistant_promoted": asdict(promoted), "post_clear_base": asdict(post_clear_base), "post_clear_session": asdict(post_clear_session), "summary_control": asdict(summary_control) if summary_control else None, "uncompressed_episode": asdict(uncompressed_episode), "restart_equal": restart_equal, "base_unchanged": base_unchanged, "final_session_hash": final_hash}


def run(cases: list[ConversationCase], root: Path, *, controls: bool = False) -> list[dict]:
    root.mkdir(parents=True, exist_ok=True)
    return [run_case(case, root, controls=controls) for case in cases]
