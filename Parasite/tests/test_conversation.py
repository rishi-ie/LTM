from __future__ import annotations

import hashlib
from pathlib import Path

from parasite.contracts import IngestRequest, QueryRequest
from parasite.runtime import ParasiteRuntime

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "Parasite/config/runtime-v1.json"


def test_frozen_g214_preference_and_ambiguous_no_mutation(tmp_path):
    text = "For this session, I prefer style_7 to be value_00007."
    spans = []
    for identifier, value, kind in (("key", "style_7", "preference_key"), ("value", "value_00007", "preference_value")):
        start = text.index(value)
        spans.append({"id": identifier, "text": value, "start": start, "end": start + len(value), "slot_type": kind})
    request = IngestRequest(
        "tenant", "conversation", "turn-1", hashlib.sha256(text.encode()).hexdigest(), "conversation_turn",
        {"source_text": text, "semantic_spans": spans}, session_id="session-1",
    )
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        result = runtime.ingest(request)
        assert result.disposition == "accept"
        assert runtime.ingest(request) == result
        assert runtime.inspect("tenant", "conversation")["active_session_objects"] == 1
        context = runtime.ask(QueryRequest("tenant", "conversation", "context", "conversation_memory", "context", {}, session_id="session-1"))
        assert "style_7=value_00007" in context.response_text
        before = runtime.inspect("tenant", "conversation")["active_session_objects"]

        ambiguous_text = "Use mention_00001 to refer to either entity_00001 or entity_other_00001."
        ambiguous_spans = []
        for index, value, kind in ((0, "mention_00001", "reference"), (1, "entity_00001", "content"), (2, "entity_other_00001", "content")):
            start = ambiguous_text.index(value)
            ambiguous_spans.append({"id": f"a{index}", "text": value, "start": start, "end": start + len(value), "slot_type": kind})
        candidates = [
            {"object_id": "e1", "object_kind": "entity", "alias": "mention_00001", "session_id": "session-1", "episode_id": "session-1", "scope_id": "session", "recency": 2},
            {"object_id": "e2", "object_kind": "entity", "alias": "mention_00001", "session_id": "session-1", "episode_id": "session-1", "scope_id": "session", "recency": 1},
        ]
        ambiguous = runtime.ingest(IngestRequest(
            "tenant", "conversation", "turn-2", hashlib.sha256(ambiguous_text.encode()).hexdigest(), "conversation_turn",
            {"source_text": ambiguous_text, "semantic_spans": ambiguous_spans, "candidates": candidates}, session_id="session-1",
        ))
        assert ambiguous.disposition in {"clarification_required", "quarantine"}
        assert runtime.inspect("tenant", "conversation")["active_session_objects"] == before


def test_frozen_g214_claim_correction_reference_delete_restart(tmp_path):
    def turn(source: str, text: str, spans: list[dict], candidates: list[dict] | None = None):
        return IngestRequest(
            "tenant", "conversation", source, hashlib.sha256(text.encode()).hexdigest(), "conversation_turn",
            {"source_text": text, "semantic_spans": spans, "candidates": candidates or []}, session_id="session-2",
        )

    old_value = "development_entity_00000"
    claim_text = f"I am tracking {old_value}."
    old_start = claim_text.index(old_value)
    claim = turn("claim-turn", claim_text, [{"id": "old", "text": old_value, "start": old_start, "end": old_start + len(old_value), "slot_type": "content"}])
    with ParasiteRuntime.open(tmp_path, CONFIG) as runtime:
        created = runtime.ingest(claim)
        assert created.disposition == "accept"
        old_id = dict(created.evidence)["object_ids"][0]

        correction_text = f"Correction: replace {old_value} with new_value_00001."
        correction_spans = []
        for identifier, value, kind in (("old", old_value, "correction"), ("new", "new_value_00001", "content")):
            start = correction_text.index(value)
            correction_spans.append({"id": identifier, "text": value, "start": start, "end": start + len(value), "slot_type": kind})
        candidate = {"object_id": old_id, "object_kind": "claim", "alias": old_value, "session_id": "session-2", "episode_id": "session-2", "scope_id": "session", "recency": 1}
        corrected = runtime.ingest(turn("correction-turn", correction_text, correction_spans, [candidate]))
        assert corrected.disposition == "accept"
        new_id = dict(corrected.evidence)["object_ids"][0]
        rows = runtime.field.session_rows("tenant", "conversation", "session-2")
        assert old_id not in {row["object_id"] for row in rows}
        assert new_id in {row["object_id"] for row in rows}

        reference_text = "Use mention_00001 to refer to entity_00001."
        reference_spans = []
        for identifier, value, kind in (("mention", "mention_00001", "reference"), ("entity", "entity_00001", "content")):
            start = reference_text.index(value)
            reference_spans.append({"id": identifier, "text": value, "start": start, "end": start + len(value), "slot_type": kind})
        ref_candidate = {"object_id": new_id, "object_kind": "claim", "alias": "mention_00001", "session_id": "session-2", "episode_id": "session-2", "scope_id": "session", "recency": 2}
        reference = runtime.ingest(turn("reference-turn", reference_text, reference_spans, [ref_candidate]))
        assert reference.disposition == "accept"
        assert runtime.delete("tenant", "conversation", new_id) is True
    with ParasiteRuntime.open(tmp_path, CONFIG) as restarted:
        assert new_id not in {row["object_id"] for row in restarted.field.session_rows("tenant", "conversation", "session-2")}
        assert restarted.clear_session("tenant", "session-2") >= 1
