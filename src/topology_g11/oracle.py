from __future__ import annotations

from dataclasses import asdict

from .generator import claim, stable_id
from .schemas import ConversationCase, MemoryQuery, SessionClaim


def _result(query: MemoryQuery, claims: dict[str, SessionClaim], refs: dict[str, str], prefs: dict[str, str], conflicts: set[tuple[str, str, str]], base: SessionClaim, turn: int, folded: set[str]) -> dict:
    subject = query.subject or refs.get("it")
    selected = [item for item in claims.values() if item.subject == subject and item.predicate == query.predicate and item.scope_id == query.scope_id and (item.valid_to_turn is None or item.valid_to_turn >= turn)]
    if query.scope_id == "global" and base.subject == subject and base.predicate == query.predicate:
        selected.append(base)
    status = "conflict" if (subject, query.predicate, query.scope_id) in conflicts else "verified" if selected else "unknown"
    return {"status": status, "claims": [asdict(item) for item in selected], "reference_bindings": sorted(refs.items()), "preferences": [prefs[key] for key in sorted(prefs)], "conflicts": ["conflict"] if status == "conflict" else [], "decisive_provenance_ids": sorted({source for item in selected for source in item.provenance_ids}), "reopened_episode_ids": [query.episode_reference] if query.episode_reference in folded else []}


def run_case(case: ConversationCase) -> dict:
    claims: dict[str, SessionClaim] = {}
    refs: dict[str, str] = {}
    prefs: dict[str, str] = {}
    conflicts: set[tuple[str, str, str]] = set()
    folded: set[str] = set()
    records: list[dict] = []
    for event in case.events:
        payload = dict(event.payload)
        if event.event_type == "fact":
            item = claim(case.conversation_id, case.session_id, payload["tag"], payload["subject"], payload["predicate"], payload["object"], payload["polarity"], payload["scope"], event.turn_index, event.event_id)
            claims[item.claim_id] = item
        elif event.event_type == "correction":
            old = claims[payload["old_claim_id"]]
            claims[old.claim_id] = SessionClaim(old.claim_id, old.session_id, old.subject, old.predicate, old.object, old.polarity, old.scope_id, old.valid_from_turn, event.turn_index - 1, old.source_event_id, old.provenance_ids)
            item = claim(case.conversation_id, case.session_id, "corrected", payload["subject"], payload["predicate"], payload["object"], payload["polarity"], payload["scope"], event.turn_index, event.event_id)
            claims[item.claim_id] = item
        elif event.event_type == "bind_reference":
            refs[payload["mention"]] = payload["entity"]
        elif event.event_type == "preference":
            prefs[payload["key"]] = payload["value"]
        elif event.event_type == "conflict":
            conflicts.add((payload["subject"], payload["predicate"], payload["scope"]))
        elif event.event_type == "fold_episode":
            folded.add(payload["folded_episode"])
        elif event.event_type == "query":
            query = MemoryQuery(stable_id(case.conversation_id, "oracle", event.event_id), case.session_id, payload.get("subject") or None, payload["predicate"], payload["scope"], payload.get("episode_reference"), None)
            records.append({"kind": payload["query"], "result": _result(query, claims, refs, prefs, conflicts, case.base_claim, event.turn_index, folded)})
    corrected_event = next(event for event in case.events if event.event_type == "correction")
    corrected = claim(case.conversation_id, case.session_id, "corrected", corrected_event.value("subject"), corrected_event.value("predicate"), corrected_event.value("object"), corrected_event.value("polarity"), corrected_event.value("scope"), corrected_event.turn_index, corrected_event.event_id)
    episode_event = next(event for event in case.events if event.event_type == "query" and event.value("query") == "episode")
    episode_payload = dict(episode_event.payload)
    uncompressed_episode = _result(MemoryQuery("oracle-uncompressed", case.session_id, episode_payload.get("subject") or None, episode_payload["predicate"], episode_payload["scope"], None, None), claims, refs, prefs, conflicts, case.base_claim, episode_event.turn_index, folded)
    claims.pop(corrected.claim_id)
    delete_event = next(event for event in case.events if event.event_type == "query" and event.value("query") == "correction")
    deleted = _result(MemoryQuery("oracle-delete", case.session_id, corrected.subject, "holds", "global", None, None), claims, refs, prefs, conflicts, case.base_claim, delete_event.turn_index, folded)
    claims, refs, prefs, conflicts, folded = {}, {}, {}, set(), set()
    base_result = _result(MemoryQuery("oracle-base", case.session_id, case.base_claim.subject, "holds", "global", None, None), claims, refs, prefs, conflicts, case.base_claim, 99, folded)
    session_result = _result(MemoryQuery("oracle-session", case.session_id, corrected.subject, "holds", "global", None, None), claims, refs, prefs, conflicts, case.base_claim, 99, folded)
    return {"conversation_id": case.conversation_id, "records": records, "deleted": deleted, "post_clear_base": base_result, "post_clear_session": session_result, "uncompressed_episode": uncompressed_episode}


def run(cases: list[ConversationCase]) -> list[dict]:
    return [run_case(case) for case in cases]
