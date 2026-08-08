"""Mechanical G2.8 graph, safety, and coverage metrics."""

from __future__ import annotations

from collections import Counter


def evaluate(gold, artifacts) -> dict[str, float | int]:
    by_id = {item.source_id: item for item in gold}
    if set(by_id) != {item.source_id for item in artifacts}:
        raise ValueError("prediction and gold source IDs differ")
    accepted_gold = [item for item in gold if item.disposition == "accept"]
    exact = relation_ok = role_ok = disposition_ok = 0
    accepted_predictions = 0
    operator_counts: Counter[str] = Counter()
    operator_correct: Counter[str] = Counter()
    reversal_errors = invalid_insertions = 0
    for artifact in artifacts:
        expected = by_id[artifact.source_id]
        candidate = artifact.candidates[0] if artifact.candidates else None
        predicted_disposition = artifact.disposition
        disposition_ok += predicted_disposition == expected.disposition
        if predicted_disposition == "accept":
            accepted_predictions += 1
        if expected.disposition != "accept":
            continue
        predicted_relations = tuple(sorted(candidate.relation_types)) if candidate else ()
        expected_relations = tuple(sorted(expected.relation_types))
        current_relation_ok = predicted_relations == expected_relations
        current_role_ok = current_relation_ok and candidate is not None and tuple(sorted(candidate.role_bindings)) == tuple(sorted(expected.role_bindings))
        relation_ok += current_relation_ok
        role_ok += current_role_ok
        current_exact = current_role_ok and predicted_disposition == "accept"
        exact += current_exact
        for relation in expected.relation_types:
            operator_counts[relation] += 1
            operator_correct[relation] += relation in predicted_relations
        if predicted_disposition == "accept" and current_relation_ok and not current_role_ok:
            reversal_errors += 1
        if predicted_disposition == "accept" and artifact.accepted_field_program is None:
            invalid_insertions += 1
    correct_rejections = sum(
        artifact.disposition == by_id[artifact.source_id].disposition
        for artifact in artifacts
        if by_id[artifact.source_id].disposition != "accept"
    )
    macro = sum(operator_correct[name] / count for name, count in operator_counts.items()) / max(1, len(operator_counts))
    all_case = (exact + correct_rejections) / max(1, len(gold))
    return {
        "cases": len(gold),
        "accepted_cases": len(accepted_gold),
        "accepted_exact_precision": exact / max(1, accepted_predictions),
        "safe_coverage": exact / max(1, len(accepted_gold)),
        "all_case_exact": all_case,
        "operator_macro_f1": macro,
        "relation_set_exact": relation_ok / max(1, len(accepted_gold)),
        "named_role_exact": role_ok / max(1, len(accepted_gold)),
        "disposition_accuracy": disposition_ok / max(1, len(gold)),
        "reversal_or_polarity_errors": reversal_errors,
        "invalid_insertions": invalid_insertions,
        "field_round_trip": 1.0 if invalid_insertions == 0 else 0.0,
    }


def kernel_passes(metrics: dict[str, float | int]) -> bool:
    return (
        float(metrics["accepted_exact_precision"]) >= .97
        and float(metrics["safe_coverage"]) >= .95
        and float(metrics["all_case_exact"]) >= .95
        and float(metrics["operator_macro_f1"]) >= .97
        and float(metrics["named_role_exact"]) >= .97
        and float(metrics["disposition_accuracy"]) >= .97
        and int(metrics["reversal_or_polarity_errors"]) == 0
        and int(metrics["invalid_insertions"]) == 0
        and float(metrics["field_round_trip"]) == 1.0
    )


def full_passes(metrics: dict[str, float | int]) -> bool:
    return (
        float(metrics["accepted_exact_precision"]) >= .95
        and float(metrics["safe_coverage"]) >= .90
        and float(metrics["all_case_exact"]) >= .90
        and float(metrics["named_role_exact"]) >= .95
        and int(metrics["reversal_or_polarity_errors"]) == 0
        and int(metrics["invalid_insertions"]) == 0
    )
