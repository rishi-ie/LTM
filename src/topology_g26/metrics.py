"""Safety-first metrics for the G2.6 representation kernel."""

from __future__ import annotations

from .schemas import KernelGold, KernelPrediction


def exact_candidate(gold, predicted) -> bool:
    return (
        gold.relation_type == predicted.relation_type
        and tuple(sorted(gold.role_bindings)) == tuple(sorted(predicted.role_bindings))
        and gold.disposition == predicted.disposition
    )


def reversal_false_accept(gold, predicted) -> bool:
    directional = {"implies", "requires", "before", "after", "supersedes", "causes_hypothetically", "fictional_rule"}
    return (
        gold.relation_type in directional
        and predicted.relation_type == gold.relation_type
        and predicted.disposition == "accept"
        and tuple(sorted(gold.role_bindings)) != tuple(sorted(predicted.role_bindings))
    )


def evaluate(gold_rows: tuple[KernelGold, ...], predictions: tuple[KernelPrediction, ...]) -> dict[str, float | int]:
    """Compute frozen, safety-first kernel metrics without accessing model state."""
    if len(gold_rows) != len(predictions):
        raise ValueError("prediction count differs from evaluator gold")
    gold_by_id = {item.source_id: item for item in gold_rows}
    if set(gold_by_id) != {item.source_id for item in predictions}:
        raise ValueError("prediction identities differ from evaluator gold")
    accepted = [item for item in gold_rows if item.candidate.disposition == "accept"]
    relation_correct = roles_correct = whole_correct = 0
    modality_correct = scope_correct = disposition_correct = polarity_correct = 0
    accepted_predictions = reversal = invalid = fieldir = g1 = 0
    per_relation: dict[str, list[int]] = {}
    for prediction in predictions:
        gold = gold_by_id[prediction.source_id]
        polarity_correct += prediction.polarity == gold.polarity
        modality_correct += prediction.modality == gold.modality
        scope_correct += prediction.scope_id == gold.scope_id
        disposition_correct += prediction.candidate.disposition == gold.candidate.disposition
        fieldir += prediction.fieldir_valid or prediction.candidate.disposition != "accept"
        g1 += prediction.g1_valid or prediction.candidate.disposition != "accept"
        if prediction.candidate.disposition == "accept":
            accepted_predictions += 1
        if reversal_false_accept(gold.candidate, prediction.candidate):
            reversal += 1
        if prediction.candidate.disposition == "accept" and not prediction.g1_valid:
            invalid += 1
        if gold.candidate.disposition != "accept":
            continue
        relation_ok = prediction.candidate.relation_type == gold.candidate.relation_type
        roles_ok = relation_ok and tuple(sorted(prediction.candidate.role_bindings)) == tuple(sorted(gold.candidate.role_bindings))
        relation_correct += relation_ok
        roles_correct += roles_ok
        full = roles_ok and prediction.polarity == gold.polarity and prediction.modality == gold.modality and prediction.scope_id == gold.scope_id and prediction.candidate.disposition == "accept" and prediction.g1_valid and prediction.fieldir_valid
        whole_correct += full
        relation = gold.candidate.relation_type
        if relation:
            per_relation.setdefault(relation, [0, 0])
            per_relation[relation][0] += relation_ok
            per_relation[relation][1] += 1
    macro_f1 = sum(correct / total for correct, total in per_relation.values()) / max(1, len(per_relation))
    exact_accepts = sum(
        exact_candidate(gold_by_id[item.source_id].candidate, item.candidate)
        for item in predictions
        if item.candidate.disposition == "accept"
    )
    safe = whole_correct / max(1, len(accepted))
    return {
        "cases": len(gold_rows),
        "operator_macro_f1": macro_f1,
        "named_role_exact": roles_correct / max(1, len(accepted)),
        "complete_exact": whole_correct / max(1, len(accepted)),
        "safe_coverage": safe,
        "accepted_exact_precision": exact_accepts / max(1, accepted_predictions),
        "polarity_accuracy": polarity_correct / len(gold_rows),
        "modality_accuracy": modality_correct / len(gold_rows),
        "scope_accuracy": scope_correct / len(gold_rows),
        "disposition_accuracy": disposition_correct / len(gold_rows),
        "reversal_false_accepts": reversal,
        "invalid_insertions": invalid,
        "fieldir_valid_rate": fieldir / len(gold_rows),
        "g1_valid_rate": g1 / len(gold_rows),
    }


def passes(metrics: dict[str, float | int]) -> bool:
    return (
        float(metrics["operator_macro_f1"]) >= .95
        and float(metrics["named_role_exact"]) >= .95
        and float(metrics["complete_exact"]) >= .95
        and float(metrics["safe_coverage"]) >= .90
        and float(metrics["accepted_exact_precision"]) >= .95
        and float(metrics["polarity_accuracy"]) == 1.0
        and float(metrics["modality_accuracy"]) >= .95
        and float(metrics["scope_accuracy"]) >= .95
        and float(metrics["disposition_accuracy"]) >= .95
        and float(metrics["fieldir_valid_rate"]) == 1.0
        and float(metrics["g1_valid_rate"]) == 1.0
        and int(metrics["reversal_false_accepts"]) == 0
        and int(metrics["invalid_insertions"]) == 0
    )
