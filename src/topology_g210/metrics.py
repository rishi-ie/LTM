"""Strict evaluator-owned G2.10 scorecard."""

from __future__ import annotations

from collections import Counter


def score(gold, predictions) -> dict[str, float | int]:
    by_id = {item.source_id: item for item in gold}
    if set(by_id) != {item.source_id for item in predictions}: raise ValueError("prediction/gold IDs differ")
    accepted_gold = [item for item in gold if item.disposition == "accept"]
    accepted = exact = cell_right = port_right = context_right = disposition_right = reversals = invalid = 0
    span_hits = span_total = span_exact = 0; counts: Counter[str] = Counter(); correct: Counter[str] = Counter()
    for row in predictions:
        target = by_id[row.source_id]; decision = row.decision
        if decision.disposition == "accept": accepted += 1
        disposition_right += decision.disposition == target.disposition
        if target.disposition != "accept": continue
        cell_ok = decision.cell_id == target.cell_id
        port_ok = cell_ok and tuple(decision.atom_ids) == target.atom_ids
        context_ok = row.scope_id == target.scope_id and row.modality == target.modality
        exact_ok = decision.disposition == "accept" and port_ok and context_ok and row.field_program is not None
        exact += exact_ok; cell_right += cell_ok; port_right += port_ok; context_right += context_ok
        counts[target.cell_id] += 1; correct[target.cell_id] += cell_ok
        if decision.disposition == "accept" and cell_ok and not port_ok: reversals += 1
        invalid += int(decision.disposition == "accept" and (row.field_program is None or len(row.operations) != 3))
        observed = {(atom.kind, atom.start, atom.end) for atom in row.atoms}
        expected = {(kind, start, end) for kind, _text, start, end in target.atom_records}
        span_hits += len(observed & expected); span_total += len(observed) + len(expected)
        span_exact += observed == expected
    macro = sum(correct[key] / value for key, value in counts.items()) / max(1, len(counts))
    rejected = [item for item in gold if item.disposition != "accept"]
    return {
        "cases": len(gold), "accepted_gold": len(accepted_gold), "accepted_predictions": accepted,
        "accepted_exact_precision": exact / max(1, accepted), "safe_coverage": exact / max(1, len(accepted_gold)),
        "all_case_exactness": (exact + sum(row.decision.disposition == by_id[row.source_id].disposition for row in predictions if by_id[row.source_id].disposition != "accept")) / max(1, len(gold)),
        "cell_accuracy": cell_right / max(1, len(accepted_gold)), "cell_macro_f1": macro,
        "named_role_exactness": port_right / max(1, len(accepted_gold)), "directional_port_accuracy": port_right / max(1, len(accepted_gold)),
        "context_accuracy": context_right / max(1, len(accepted_gold)), "disposition_accuracy": disposition_right / max(1, len(gold)),
        "ambiguity_recall": sum(row.decision.disposition == "clarification_required" for row in predictions if by_id[row.source_id].disposition == "clarification_required") / max(1, sum(item.disposition == "clarification_required" for item in rejected)),
        "quarantine_recall": sum(row.decision.disposition == "quarantine" for row in predictions if by_id[row.source_id].disposition == "quarantine") / max(1, sum(item.disposition == "quarantine" for item in rejected)),
        "span_f1": 2 * span_hits / max(1, span_total), "exact_span_set": span_exact / max(1, len(accepted_gold)),
        "reversal_false_accepts": reversals, "invalid_insertions": invalid,
        "fieldir_g1_numeric_round_trip": 1.0 if invalid == 0 else 0.0,
        "provenance_integrity": 1.0 if all(not row.field_program or all(atom.provenance_sha256 for atom in row.atoms) for row in predictions) else 0.0,
    }


def passes(metrics: dict[str, float | int], *, full: bool) -> bool:
    required = (
        float(metrics["accepted_exact_precision"]) >= .99,
        float(metrics["safe_coverage"]) >= .95,
        float(metrics["all_case_exactness"]) >= .95,
        float(metrics["cell_accuracy"]) >= .99,
        float(metrics["cell_macro_f1"]) >= .99,
        float(metrics["named_role_exactness"]) >= .995,
        float(metrics["directional_port_accuracy"]) >= .995,
        float(metrics["context_accuracy"]) >= .995,
        float(metrics["disposition_accuracy"]) >= .99,
        int(metrics["reversal_false_accepts"]) == 0,
        int(metrics["invalid_insertions"]) == 0,
        float(metrics["fieldir_g1_numeric_round_trip"]) == 1.0,
        float(metrics["provenance_integrity"]) == 1.0,
    )
    return all(required) and (not full or (float(metrics["span_f1"]) >= .98 and float(metrics["exact_span_set"]) >= .95 and float(metrics["ambiguity_recall"]) >= .95 and float(metrics["quarantine_recall"]) >= .95))
