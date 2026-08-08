"""Mechanical G2.9 safety, topology, and routing measurements."""

from __future__ import annotations

from collections import Counter


def evaluate(gold, artifacts) -> dict[str, float | int]:
    expected = {item.source_id: item for item in gold}
    if set(expected) != {item.source_id for item in artifacts}:
        raise ValueError("gold and runtime source IDs differ")
    accepted_gold = [item for item in gold if item.disposition == "accept"]
    exact = relation_exact = role_exact = disposition_exact = accepted_predictions = 0
    invalid = reversals = 0
    counts: Counter[str] = Counter(); correct: Counter[str] = Counter()
    top3 = 0
    for artifact in artifacts:
        target = expected[artifact.source_id]
        prediction = artifact.prediction
        disposition_exact += artifact.disposition == target.disposition
        if artifact.disposition == "accept":
            accepted_predictions += 1
        if target.disposition != "accept":
            continue
        predicted_relations = tuple(sorted(prediction.relation_types)) if prediction else ()
        predicted_bindings = tuple(sorted(prediction.role_bindings)) if prediction else ()
        target_relations = tuple(sorted(target.relation_types))
        target_bindings = tuple(sorted(target.role_bindings))
        relations_ok = predicted_relations == target_relations
        roles_ok = relations_ok and predicted_bindings == target_bindings
        relation_exact += relations_ok; role_exact += roles_ok
        exact_case = roles_ok and artifact.disposition == "accept"
        exact += exact_case
        for relation in target.relation_types:
            counts[relation] += 1; correct[relation] += relation in predicted_relations
        ranked = sorted(artifact.operator_matches, key=lambda item: (-item.activation, item.relation_type))[:3]
        top3 += all(relation in {item.relation_type for item in ranked} for relation in target.relation_types)
        if artifact.disposition == "accept" and relations_ok and not roles_ok:
            reversals += 1
        if artifact.disposition == "accept" and artifact.accepted_field_program is None:
            invalid += 1
    rejections = sum(artifact.disposition == expected[artifact.source_id].disposition for artifact in artifacts if expected[artifact.source_id].disposition != "accept")
    macro = sum(correct[name] / count for name, count in counts.items()) / max(1, len(counts))
    return {
        "cases": len(gold), "accepted_cases": len(accepted_gold),
        "accepted_complete_graph_precision": exact / max(1, accepted_predictions),
        "safe_coverage": exact / max(1, len(accepted_gold)),
        "all_case_exact_topology": (exact + rejections) / max(1, len(gold)),
        "operator_macro_f1": macro,
        "correct_operator_recall_at_3": top3 / max(1, len(accepted_gold)),
        "relation_set_exactness": relation_exact / max(1, len(accepted_gold)),
        "named_role_exactness": role_exact / max(1, len(accepted_gold)),
        "context_disposition_accuracy": disposition_exact / max(1, len(gold)),
        "direction_polarity_accuracy": 1.0 - reversals / max(1, len(accepted_gold)),
        "accepted_reversal_or_polarity_errors": reversals,
        "invalid_g1_insertions": invalid,
        "g1_fieldir_round_trip": 1.0 if invalid == 0 else 0.0,
    }


def kernel_passes(metrics: dict[str, float | int]) -> bool:
    return (
        float(metrics["accepted_complete_graph_precision"]) >= .95
        and float(metrics["safe_coverage"]) >= .95
        and float(metrics["all_case_exact_topology"]) >= .90
        and float(metrics["operator_macro_f1"]) >= .95
        and float(metrics["correct_operator_recall_at_3"]) >= .99
        and float(metrics["named_role_exactness"]) >= .95
        and float(metrics["context_disposition_accuracy"]) >= .95
        and float(metrics["direction_polarity_accuracy"]) >= .995
        and int(metrics["accepted_reversal_or_polarity_errors"]) == 0
        and int(metrics["invalid_g1_insertions"]) == 0
        and float(metrics["g1_fieldir_round_trip"]) == 1.0
    )


def full_passes(metrics: dict[str, float | int]) -> bool:
    return kernel_passes(metrics)
