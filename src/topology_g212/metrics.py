"""Kernel metrics and gate classification."""

from __future__ import annotations

from collections import Counter

from .inference import KernelPrediction
from .schemas import AtomicCase


def _gold_bindings(case: AtomicCase) -> tuple[tuple[str, str, str], ...]:
    return tuple((relation, role, span_ids[0]) for relation, role, span_ids in case.role_bindings)


def score_kernel(cases: tuple[AtomicCase, ...], predictions: tuple[KernelPrediction, ...], gates: dict[str, float] | None = None) -> dict[str, object]:
    rows = tuple(zip(cases, predictions, strict=True))
    accepted = tuple((case, prediction) for case, prediction in rows if prediction.disposition == "accept")
    exact = sum(prediction.relations == case.relations and prediction.role_bindings == _gold_bindings(case) for case, prediction in accepted)
    safe = sum(
        (case.disposition != "accept" and prediction.disposition != "accept")
        or (case.disposition == "accept" and prediction.relations == case.relations and prediction.role_bindings == _gold_bindings(case))
        for case, prediction in rows
    )
    severe = sum(
        case.disposition == "accept"
        and prediction.disposition == "accept"
        and (prediction.relations != case.relations or prediction.role_bindings != _gold_bindings(case))
        for case, prediction in rows
    )
    gold_operators = Counter(relation for case, _prediction in rows for relation in case.relations)
    predicted_operators = Counter(relation for _case, prediction in rows for relation in prediction.relations)
    operator_correct = sum(min(gold_operators[relation], predicted_operators[relation]) for relation in gold_operators)
    operator_precision = operator_correct / sum(predicted_operators.values()) if predicted_operators else 1.0
    operator_recall = operator_correct / sum(gold_operators.values()) if gold_operators else 1.0
    disposition_accuracy = sum(case.disposition == prediction.disposition for case, prediction in rows) / len(rows)
    direction_cases = tuple((case, prediction) for case, prediction in accepted if case.relations and case.role_bindings)
    direction_accuracy = sum(prediction.role_bindings == _gold_bindings(case) for case, prediction in direction_cases) / len(direction_cases) if direction_cases else 1.0
    result: dict[str, object] = {
        "cases": len(rows),
        "accepted": len(accepted),
        "accepted_exact": exact,
        "accepted_precision": exact / len(accepted) if accepted else 1.0,
        "safe_cases": safe,
        "safe_coverage": safe / len(rows) if rows else 1.0,
        "all_case_exactness": safe / len(rows) if rows else 1.0,
        "severe_errors": severe,
        "operator_precision": operator_precision,
        "operator_recall": operator_recall,
        "operator_macro_f1": 2 * operator_precision * operator_recall / (operator_precision + operator_recall) if operator_precision + operator_recall else 0.0,
        "direction_accuracy": direction_accuracy,
        "disposition_accuracy": disposition_accuracy,
        "role_exactness": exact / len(accepted) if accepted else 1.0,
    }
    if gates is not None:
        result["kernel_passed"] = bool(
            result["accepted_precision"] >= gates["accepted_precision"]
            and result["safe_coverage"] >= gates["safe_coverage"]
            and result["all_case_exactness"] >= gates["all_case_exactness"]
            and result["operator_macro_f1"] >= gates["operator_macro_f1"]
            and result["role_exactness"] >= gates["role_exactness"]
            and result["direction_accuracy"] >= gates["direction_accuracy"]
            and result["disposition_accuracy"] >= gates["disposition_accuracy"]
            and severe == 0
        )
    return result

