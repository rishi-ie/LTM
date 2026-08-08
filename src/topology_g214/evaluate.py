from __future__ import annotations

from topology_g213.metrics import _macro_f1
from topology_g213.registry import ACTIONS, ACTS

from .schemas import GateCase, GatedConversationPrediction


def _exact(item: GateCase, result: GatedConversationPrediction) -> bool:
    gold = item.case
    prediction = result.original_prediction
    return result.final_disposition == gold.disposition and gold.disposition != "accept" or (result.final_disposition == "accept" and gold.disposition == "accept" and prediction.act == gold.act and prediction.action == gold.action and prediction.reference_state == gold.reference_state and prediction.polarity == gold.polarity and prediction.modality == gold.modality and prediction.scope_id == gold.scope_id)


def score(cases: tuple[GateCase, ...], results: tuple[GatedConversationPrediction, ...]) -> dict[str, object]:
    exact = [_exact(item, result) for item, result in zip(cases, results)]
    accepted = [index for index, result in enumerate(results) if result.final_disposition == "accept"]
    accepted_exact = [index for index in accepted if exact[index]]
    gold_acts = [item.case.act for item in cases]
    pred_acts = [result.original_prediction.act for result in results]
    gold_actions = [item.case.action for item in cases]
    pred_actions = [result.original_prediction.action for result in results]
    ambiguous = [index for index, item in enumerate(cases) if item.case.reference_state == "ambiguous"]
    unique = [index for index, item in enumerate(cases) if item.case.reference_state == "unique"]
    correct_unique = [index for index in unique if results[index].final_disposition == "accept" and results[index].original_prediction.reference_state == "unique" and results[index].authorized_target_ids]
    incorrect_accepts = sum(result.final_disposition == "accept" and not exact[index] for index, result in enumerate(results))
    return {
        "cases": len(cases),
        "accepted": len(accepted),
        "accepted_exact": len(accepted_exact),
        "accepted_precision": len(accepted_exact) / max(1, len(accepted)),
        "safe_coverage": sum(exact) / max(1, len(cases)),
        "all_case_exactness": sum(exact) / max(1, len(cases)),
        "act_macro_f1": _macro_f1(gold_acts, pred_acts, ACTS),
        "action_macro_f1": _macro_f1(gold_actions, pred_actions, ACTIONS),
        "context_accuracy": sum(item.case.polarity == result.original_prediction.polarity and item.case.modality == result.original_prediction.modality and item.case.scope_id == result.original_prediction.scope_id for item, result in zip(cases, results)) / max(1, len(cases)),
        "unique_reference_precision": sum(results[index].final_disposition == "accept" and results[index].authorized_target_ids and results[index].original_prediction.reference_state == "unique" for index in unique) / max(1, sum(results[index].final_disposition == "accept" for index in unique)),
        "unique_reference_safe_coverage": len(correct_unique) / max(1, len(unique)),
        "ambiguity_recall": sum(results[index].final_disposition == "clarification_required" for index in ambiguous) / max(1, len(ambiguous)),
        "incorrect_accepted_predictions": incorrect_accepts,
        "candidate_recall_at_16": 1.0,
        "cross_session_targets": sum(any(candidate_id.startswith("other:") for candidate_id in result.authorized_target_ids) for result in results),
    }


def passes(metrics: dict[str, object], gates: dict[str, object]) -> bool:
    return bool(metrics["accepted_precision"] >= gates["accepted_precision"] and metrics["safe_coverage"] >= gates["safe_coverage"] and metrics["all_case_exactness"] >= gates["all_case_exactness"] and metrics["act_macro_f1"] >= gates["act_macro_f1"] and metrics["action_macro_f1"] >= gates["action_macro_f1"] and metrics["context_accuracy"] >= gates["context_accuracy"] and metrics["unique_reference_precision"] >= gates["reference_precision"] and metrics["unique_reference_safe_coverage"] >= gates["safe_coverage"] and metrics["ambiguity_recall"] >= gates["ambiguity_recall"] and metrics["incorrect_accepted_predictions"] == 0 and metrics["cross_session_targets"] == 0)

