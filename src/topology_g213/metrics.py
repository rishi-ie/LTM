from __future__ import annotations

from .inference import Prediction
from .registry import ACTIONS, ACTS
from .schemas import ConversationCase


def _macro_f1(gold: list[str], pred: list[str], labels: tuple[str, ...]) -> float:
    scores = []
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(gold, pred))
        fp = sum(a != label and b == label for a, b in zip(gold, pred))
        fn = sum(a == label and b != label for a, b in zip(gold, pred))
        scores.append(2 * tp / max(1, 2 * tp + fp + fn))
    return sum(scores) / len(scores)


def score_kernel(cases: tuple[ConversationCase, ...], predictions: tuple[Prediction, ...], gates: dict[str, float]) -> dict[str, object]:
    gold_act = [case.act for case in cases]
    pred_act = [prediction.act for prediction in predictions]
    gold_action = [case.action for case in cases]
    pred_action = [prediction.action for prediction in predictions]
    exact = [
        case.act == prediction.act
        and case.action == prediction.action
        and case.reference_state == prediction.reference_state
        and case.polarity == prediction.polarity
        and case.modality == prediction.modality
        and case.scope_id == prediction.scope_id
        and case.disposition == prediction.disposition
        for case, prediction in zip(cases, predictions)
    ]
    accepted = [index for index, prediction in enumerate(predictions) if prediction.disposition == "accept"]
    accepted_exact = [index for index in accepted if exact[index]]
    unsafe = sum(predictions[index].disposition == "accept" and not exact[index] for index in range(len(cases)))
    result = {
        "cases": len(cases),
        "accepted": len(accepted),
        "accepted_exact": len(accepted_exact),
        "accepted_precision": len(accepted_exact) / max(1, len(accepted)),
        "safe_coverage": sum(exact) / max(1, len(cases)),
        "all_case_exactness": sum(exact) / max(1, len(cases)),
        "act_macro_f1": _macro_f1(gold_act, pred_act, ACTS),
        "action_macro_f1": _macro_f1(gold_action, pred_action, ACTIONS),
        "reference_accuracy": sum(case.reference_state == prediction.reference_state for case, prediction in zip(cases, predictions)) / max(1, len(cases)),
        "context_accuracy": sum(case.polarity == prediction.polarity and case.modality == prediction.modality and case.scope_id == prediction.scope_id for case, prediction in zip(cases, predictions)) / max(1, len(cases)),
        "disposition_accuracy": sum(case.disposition == prediction.disposition for case, prediction in zip(cases, predictions)) / max(1, len(cases)),
        "unsafe_mutations": unsafe,
    }
    result["kernel_passed"] = bool(
        result["accepted_precision"] >= gates["accepted_precision"]
        and result["safe_coverage"] >= gates["safe_coverage"]
        and result["act_macro_f1"] >= gates["act_macro_f1"]
        and result["action_macro_f1"] >= gates["action_macro_f1"]
        and result["context_accuracy"] >= gates["context_accuracy"]
        and result["disposition_accuracy"] >= gates["disposition_accuracy"]
        and result["unsafe_mutations"] == 0
    )
    return result


def classify(result: dict[str, object]) -> str:
    if not result.get("kernel_passed", False):
        return "G2.13-B — CONVERSATIONAL KERNEL FAILURE"
    return "G2.13-A — CONTROLLED CONVERSATION COMPILER PASS"
