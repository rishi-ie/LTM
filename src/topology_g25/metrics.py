"""Strict evaluator for the locked representation kernel."""

from __future__ import annotations

from .schemas import KernelExample, KernelPrediction


def _normalized_bindings(
    bindings: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(sorted((role, tuple(values)) for role, values in bindings))


def _factor_bindings(prediction: KernelPrediction) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if prediction.factor is None:
        return ()
    grouped: dict[str, list[str]] = {}
    for role, atom in prediction.factor.sparse_incidence:
        grouped.setdefault(role, []).append(atom)
    return tuple((role, tuple(atom_ids)) for role, atom_ids in grouped.items())


def _factor_round_trip(prediction: KernelPrediction) -> bool:
    """Check that the emitted continuous factor still carries exact G1 slots."""
    if prediction.factor is None or prediction.relation_type is None:
        return False
    return (
        prediction.factor.relation_type == prediction.relation_type
        and _normalized_bindings(_factor_bindings(prediction))
        == _normalized_bindings(prediction.role_bindings)
        and prediction.factor.context.polarity == prediction.polarity
        and prediction.factor.context.modality == prediction.modality
        and prediction.factor.context.scope_id == prediction.scope_id
    )


def kernel_metrics(
    examples: tuple[KernelExample, ...], predictions: tuple[KernelPrediction, ...]
) -> dict[str, float | int]:
    if len(examples) != len(predictions):
        raise ValueError("example and prediction count differs")
    accepted = [index for index, example in enumerate(examples) if example.disposition == "accept"]
    correct_relation = correct_roles = exact = g1_valid = direction_errors = 0
    sparse_recovered = field_round_trip = 0
    polarity = modality = scope = disposition = 0
    reversal_false_accepts = 0
    for example, prediction in zip(examples, predictions):
        polarity += prediction.polarity == example.polarity
        modality += prediction.modality == example.modality
        scope += prediction.scope_id == example.scope_id
        disposition += prediction.disposition == example.disposition
        if example.disposition != "accept":
            continue
        relation_ok = prediction.relation_type == example.relation_type
        role_ok = _normalized_bindings(prediction.role_bindings) == _normalized_bindings(
            example.role_bindings
        )
        correct_relation += relation_ok
        correct_roles += relation_ok and role_ok
        g1_valid += prediction.factor is not None
        sparse_recovered += prediction.factor is not None and _normalized_bindings(
            _factor_bindings(prediction)
        ) == _normalized_bindings(prediction.role_bindings)
        field_round_trip += _factor_round_trip(prediction)
        whole = (
            relation_ok
            and role_ok
            and prediction.polarity == example.polarity
            and prediction.modality == example.modality
            and prediction.scope_id == example.scope_id
            and prediction.disposition == "accept"
            and prediction.factor is not None
        )
        exact += whole
        if (
            prediction.relation_type
            in {"implies", "requires", "before", "after", "supersedes", "causes_hypothetically"}
            and relation_ok
            and not role_ok
        ):
            direction_errors += 1
        if (
            prediction.relation_type
            in {"implies", "requires", "before", "after", "supersedes", "causes_hypothetically"}
            and not role_ok
            and prediction.disposition == "accept"
        ):
            reversal_false_accepts += 1
    denominator = len(accepted) or 1
    return {
        "cases": len(examples),
        "accepted_cases": len(accepted),
        "operator_accuracy": correct_relation / denominator,
        "named_role_exact": correct_roles / denominator,
        "complete_g1_exact": exact / denominator,
        "polarity_accuracy": polarity / len(examples),
        "modality_accuracy": modality / len(examples),
        "scope_accuracy": scope / len(examples),
        "disposition_accuracy": disposition / len(examples),
        "g1_valid_rate": g1_valid / denominator,
        "sparse_role_recoverability": sparse_recovered / denominator,
        "field_round_trip": field_round_trip / denominator,
        "direction_errors": direction_errors,
        "reversal_false_accepts": reversal_false_accepts,
        "invalid_g1_insertions": 0,
    }


def kernel_pass(metrics: dict[str, float | int]) -> bool:
    return (
        float(metrics["operator_accuracy"]) >= 0.995
        and float(metrics["named_role_exact"]) >= 0.995
        and float(metrics["complete_g1_exact"]) >= 0.99
        and float(metrics["polarity_accuracy"]) == 1.0
        and float(metrics["modality_accuracy"]) >= 0.995
        and float(metrics["scope_accuracy"]) >= 0.995
        and float(metrics["disposition_accuracy"]) >= 0.98
        and float(metrics["g1_valid_rate"]) == 1.0
        and float(metrics["sparse_role_recoverability"]) == 1.0
        and float(metrics["field_round_trip"]) == 1.0
        and int(metrics["direction_errors"]) == 0
        and int(metrics["reversal_false_accepts"]) == 0
        and int(metrics["invalid_g1_insertions"]) == 0
    )
