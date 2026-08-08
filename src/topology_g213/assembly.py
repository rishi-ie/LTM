"""Safe, minimal event assembly. Deep reasoning is intentionally absent."""

from __future__ import annotations

from topology_g11.schemas import ConversationEvent

from .inference import Prediction, compile_prediction
from .schemas import CompiledConversationTurn, ConversationCase


def assemble(case: ConversationCase, prediction: Prediction) -> CompiledConversationTurn:
    discourse, action, reference, correction, preference, context, content, failures = compile_prediction(case, prediction)
    if prediction.disposition != "accept":
        failures = tuple(failures) + (("UNSUPPORTED_INPUT",) if prediction.disposition == "quarantine" else ())
    event_payload = (("text", case.source.text), ("act", prediction.act), ("action", prediction.action), ("scope", prediction.scope_id))
    event = ConversationEvent(case.source.source_id, case.source.session_id, case.source.turn_index, case.source.speaker, "utterance", event_payload, case.source.source_hash, case.source.episode_id)
    disposition = prediction.disposition if not failures else ("quarantine" if "UNSUPPORTED_INPUT" in failures else "clarification_required")
    return CompiledConversationTurn(case.source.source_id, discourse, action, content, reference, correction, preference, context, disposition, tuple(dict.fromkeys(failures)), 0.0, event)
