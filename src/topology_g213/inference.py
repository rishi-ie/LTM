from __future__ import annotations

from dataclasses import dataclass

import torch

from .dataset import ConversationCase
from .model import ConversationCompiler
from .registry import ACTIONS, ACTS, DISPOSITIONS, MODALITIES, POLARITIES, REFERENCE_STATES, SCOPES
from .schemas import (
    ConversationContext,
    ConversationSpan,
    CorrectionDecision,
    DiscourseDecision,
    MemoryActionDecision,
    PreferenceDecision,
    ReferenceDecision,
)
from .training import make_batch


@dataclass(frozen=True, slots=True)
class Prediction:
    source_id: str
    act: str
    action: str
    reference_state: str
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    span_ids: tuple[str, ...]
    slot_types: tuple[tuple[str, str], ...]
    confidence: float


def load_checkpoint(path, device: str = "cpu") -> ConversationCompiler:
    model = ConversationCompiler()
    state = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(state["model"])
    return model.eval()


def predict_case(model: ConversationCompiler, case: ConversationCase) -> Prediction:
    tokens, masks = make_batch(model, [case])
    with torch.no_grad():
        output = model(tokens, masks)
    def choose(name: str, values: tuple[str, ...]) -> tuple[str, float]:
        probabilities = torch.softmax(output[f"{name}_logits"][0], -1)
        index = int(probabilities.argmax())
        return values[index], float(probabilities[index])
    act, act_p = choose("act", ACTS)
    action, action_p = choose("action", ACTIONS)
    reference, ref_p = choose("reference", REFERENCE_STATES)
    polarity, _ = choose("polarity", POLARITIES)
    modality, _ = choose("modality", MODALITIES)
    scope, _ = choose("scope", SCOPES)
    disposition, disp_p = choose("disposition", DISPOSITIONS)
    slot = output["slot_logits"][0].softmax(-1).argmax(-1)
    slot_types = tuple((span.span_id, ("content", "preference_key", "preference_value", "correction", "reference")[int(slot[index])]) for index, span in enumerate(case.spans[:8]))
    return Prediction(case.source.source_id, act, action, reference, polarity, modality, scope, disposition, tuple(span.span_id for span in case.spans), slot_types, min(act_p, action_p, ref_p, disp_p))


def compile_prediction(case: ConversationCase, prediction: Prediction) -> tuple[DiscourseDecision, MemoryActionDecision, ReferenceDecision, CorrectionDecision, PreferenceDecision, ConversationContext, tuple[ConversationSpan, ...], tuple[str, ...]]:
    content = tuple(span for span in case.spans if span.slot_type == "content")
    failures: list[str] = []
    reference_ids = tuple(span.span_id for span in case.spans if span.slot_type == "reference")
    reference = ReferenceDecision(prediction.reference_state, case.target_id if prediction.reference_state == "unique" else None, tuple(reference_ids), prediction.confidence, prediction.confidence)
    correction = CorrectionDecision(case.target_id if prediction.action == "correct" else None, prediction.confidence, prediction.confidence)
    key = next((span.text for span in case.spans if span.slot_type == "preference_key"), None)
    value = next((span.text for span in case.spans if span.slot_type == "preference_value"), None)
    preference = PreferenceDecision(key if prediction.action == "set_preference" else None, value if prediction.action == "set_preference" else None, prediction.confidence)
    context = ConversationContext(prediction.polarity, prediction.modality, prediction.scope_id, prediction.confidence)
    if prediction.reference_state == "ambiguous":
        failures.append("AMBIGUOUS_REFERENCE")
    if prediction.disposition == "quarantine":
        failures.append("UNSUPPORTED_INPUT")
    return (DiscourseDecision(prediction.act, prediction.confidence, prediction.confidence), MemoryActionDecision(prediction.action, prediction.confidence, prediction.confidence), reference, correction, preference, context, content, tuple(failures))
