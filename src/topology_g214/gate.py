from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace

import torch

from topology_g213.inference import Prediction
from topology_g213.model import ConversationCompiler
from topology_g213.registry import (
    ACTIONS,
    ACTS,
    DISPOSITIONS,
    MODALITIES,
    POLARITIES,
    REFERENCE_STATES,
    SCOPES,
)
from topology_g213.training import make_batch

from .schemas import (
    AcceptanceEvidence,
    CandidateResolution,
    GateCase,
    GatedConversationPrediction,
    HeadConfidence,
)


def _top(values: torch.Tensor, labels: tuple[str, ...]) -> tuple[str, float, float]:
    probabilities = torch.softmax(values, -1)
    ordered = torch.sort(probabilities, descending=True).values
    index = int(probabilities.argmax())
    return labels[index], float(ordered[0]), float(ordered[0] - ordered[1])


def _predict(model: ConversationCompiler, item: GateCase) -> tuple[Prediction, tuple[HeadConfidence, ...]]:
    tokens, masks = make_batch(model, [item.case])
    with torch.no_grad():
        output = model(tokens, masks)
    labels = {
        "act": ACTS,
        "action": ACTIONS,
        "reference": REFERENCE_STATES,
        "polarity": POLARITIES,
        "modality": MODALITIES,
        "scope": SCOPES,
        "disposition": DISPOSITIONS,
    }
    selected: dict[str, tuple[str, float, float]] = {name: _top(output[f"{name}_logits"][0], values) for name, values in labels.items()}
    slot = output["slot_logits"][0].softmax(-1).argmax(-1)
    slot_types = tuple((span.span_id, ("content", "preference_key", "preference_value", "correction", "reference")[int(slot[index])]) for index, span in enumerate(item.case.spans[:8]))
    confidence = min(value[1] for value in selected.values())
    prediction = Prediction(item.case.source.source_id, selected["act"][0], selected["action"][0], selected["reference"][0], selected["polarity"][0], selected["modality"][0], selected["scope"][0], selected["disposition"][0], tuple(span.span_id for span in item.case.spans), slot_types, confidence)
    heads = tuple(HeadConfidence(name, value[0], value[1], value[2]) for name, value in selected.items())
    return prediction, heads


def _resolve(item: GateCase, prediction: Prediction, operation: str, confidence: float, margin: float) -> CandidateResolution:
    span = next((span for span in item.case.spans if span.slot_type in {"reference", "correction"}), None)
    if span is None:
        return CandidateResolution(operation, "new", None, (), 0.0, 1.0, 0)
    query = span.text.casefold()
    eligible = [candidate for candidate in item.candidates if candidate.active and not candidate.expired and not candidate.superseded and not candidate.deleted and candidate.session_id == item.case.source.session_id and candidate.scope_id in {"session", item.case.source.episode_id} and candidate.alias.casefold() in query]
    eligible.sort(key=lambda candidate: (-candidate.recency, candidate.object_id))
    if not eligible:
        return CandidateResolution(operation, "new", None, (), 0.0, 1.0, len(item.candidates))
    # Equal aliases are intentionally indistinguishable; the margin gate must retain ambiguity.
    best_score = 1.0
    next_score = 1.0 if len(eligible) > 1 else 0.0
    resolved_margin = best_score - next_score
    if len(eligible) > 1 or best_score < confidence or resolved_margin < margin:
        return CandidateResolution(operation, "ambiguous", None, tuple(candidate.object_id for candidate in eligible), best_score, resolved_margin, len(item.candidates))
    return CandidateResolution(operation, "existing", eligible[0].object_id, (), best_score, resolved_margin, len(item.candidates))


def gate_case(model: ConversationCompiler, item: GateCase, *, confidence_threshold: float, margin_threshold: float, identity_confidence: float, identity_margin: float) -> GatedConversationPrediction:
    prediction, heads = _predict(model, item)
    resolutions: list[CandidateResolution] = []
    if prediction.reference_state in {"unique", "ambiguous"}:
        resolutions.append(_resolve(item, prediction, "reference", identity_confidence, identity_margin))
    if prediction.action in {"correct", "retract"}:
        resolutions.append(_resolve(item, prediction, prediction.action, identity_confidence, identity_margin))
    probabilities = [head.probability for head in heads]
    margins = [head.margin for head in heads]
    minimum_probability, minimum_margin = min(probabilities), min(margins)
    passed: list[str] = []
    failed: list[str] = []
    if prediction.disposition != "accept":
        failed.append("MODEL_NOT_ACCEPT")
    if minimum_probability < confidence_threshold:
        failed.append("HEAD_CONFIDENCE")
    else:
        passed.append("HEAD_CONFIDENCE")
    if minimum_margin < margin_threshold:
        failed.append("HEAD_MARGIN")
    else:
        passed.append("HEAD_MARGIN")
    if prediction.action == "set_preference" and not {"preference_key", "preference_value"}.issubset({kind for _, kind in prediction.slot_types}):
        failed.append("PREFERENCE_SLOTS")
    for resolution in resolutions:
        if resolution.disposition != "existing":
            failed.append(f"{resolution.operation.upper()}_AMBIGUOUS")
        elif resolution.confidence < identity_confidence or resolution.margin < identity_margin:
            failed.append(f"{resolution.operation.upper()}_MARGIN")
        else:
            passed.append(f"{resolution.operation.upper()}_RESOLVED")
    if prediction.reference_state == "ambiguous" and not any(resolution.disposition == "ambiguous" for resolution in resolutions):
        failed.append("REFERENCE_STATE_MISMATCH")
    final = "quarantine" if prediction.disposition == "quarantine" else "accept" if not failed else "clarification_required"
    targets = tuple(resolution.selected_object_id for resolution in resolutions if resolution.selected_object_id is not None)
    evidence_payload = json.dumps({"source": item.case.source.source_id, "heads": [asdict(head) for head in heads], "resolutions": [asdict(resolution) for resolution in resolutions], "failed": failed}, sort_keys=True)
    evidence = AcceptanceEvidence(item.case.source.source_id, heads, tuple(resolutions), minimum_probability, minimum_margin, tuple(passed), tuple(failed), "g2.14-gate/1", hashlib.sha256(evidence_payload.encode()).hexdigest())
    return GatedConversationPrediction(item.case.source.source_id, prediction, evidence, final, targets, tuple(dict.fromkeys(failed)))


def gate_cases(model: ConversationCompiler, cases: tuple[GateCase, ...], thresholds: dict[str, float]) -> tuple[GatedConversationPrediction, ...]:
    return tuple(gate_case(model, item, confidence_threshold=thresholds["confidence"], margin_threshold=thresholds["margin"], identity_confidence=thresholds["identity_confidence"], identity_margin=thresholds["identity_margin"]) for item in cases)


def regrade(result: GatedConversationPrediction, *, confidence_threshold: float, margin_threshold: float, identity_confidence: float, identity_margin: float) -> GatedConversationPrediction:
    prediction = result.original_prediction
    evidence = result.acceptance_evidence
    failed: list[str] = []
    if prediction.disposition != "accept":
        failed.append("MODEL_NOT_ACCEPT")
    if evidence.minimum_probability < confidence_threshold:
        failed.append("HEAD_CONFIDENCE")
    if evidence.minimum_margin < margin_threshold:
        failed.append("HEAD_MARGIN")
    for resolution in evidence.resolutions:
        if resolution.disposition != "existing" or resolution.confidence < identity_confidence or resolution.margin < identity_margin:
            failed.append(f"{resolution.operation.upper()}_MARGIN")
    if prediction.reference_state == "ambiguous" and not any(resolution.disposition == "ambiguous" for resolution in evidence.resolutions):
        failed.append("REFERENCE_STATE_MISMATCH")
    final = "quarantine" if prediction.disposition == "quarantine" else "accept" if not failed else "clarification_required"
    return replace(result, acceptance_evidence=replace(evidence, failed_checks=tuple(dict.fromkeys(failed))), final_disposition=final, authorized_target_ids=tuple(resolution.selected_object_id for resolution in evidence.resolutions if resolution.selected_object_id is not None) if final == "accept" else (), failure_codes=tuple(dict.fromkeys(failed)))
