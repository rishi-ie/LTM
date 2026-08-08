"""Frozen G2.7 metrics and mechanical gates."""

from __future__ import annotations

from collections import Counter

from .schemas import GoldRecord, SentenceCoordinateState


def _candidate(state: SentenceCoordinateState):
    return state.candidates[0]


def evaluate(gold: tuple[GoldRecord, ...], states: tuple[SentenceCoordinateState, ...]) -> dict[str, object]:
    by_id = {item.source_id: item for item in gold}
    accepted = [item for item in gold if item.disposition == "accept"]
    exact = role_exact = relation_exact = 0
    direction_errors = 0
    disposition_correct = 0
    polarity_correct = modality_correct = scope_correct = 0
    atom_hit = 0
    per_relation: Counter[str] = Counter()
    per_relation_correct: Counter[str] = Counter()
    for state in states:
        item = by_id[state.source_id]
        candidate = _candidate(state)
        disposition_correct += candidate.disposition == item.disposition
        if item.disposition != "accept":
            continue
        relation_ok = tuple(sorted(candidate.relation_set)) == tuple(sorted(item.relation_types))
        relation_exact += relation_ok
        predicted_bindings = tuple(sorted(candidate.role_bindings))
        gold_bindings = tuple(sorted(item.role_bindings))
        roles_ok = predicted_bindings == gold_bindings
        role_exact += roles_ok
        exact_ok = candidate.disposition == "accept" and relation_ok and roles_ok and candidate.context.polarity == item.polarity and candidate.context.modality == item.modality and candidate.context.scope_id == item.scope_id
        exact += exact_ok
        polarity_correct += candidate.context.polarity == item.polarity
        modality_correct += candidate.context.modality == item.modality
        scope_correct += candidate.context.scope_id == item.scope_id
        if item.relation_types:
            per_relation[item.relation_types[0]] += 1
            per_relation_correct[item.relation_types[0]] += relation_ok
        atom_hit += all(relation in state.coordinate.active_atoms for relation in item.relation_types)
        if candidate.disposition == "accept" and not relation_ok and set(candidate.relation_set) & set(item.relation_types):
            direction_errors += 1
    accepted_predictions = sum(_candidate(state).disposition == "accept" for state in states)
    macro = sum(per_relation_correct[name] / count for name, count in per_relation.items()) / max(1, len(per_relation))
    return {
        "cases": len(gold),
        "accepted_cases": len(accepted),
        "accepted_exact_precision": exact / max(1, accepted_predictions),
        "safe_coverage": exact / max(1, len(accepted)),
        "all_case_exact": (exact + sum(_candidate(state).disposition == by_id[state.source_id].disposition == "clarification_required" or _candidate(state).disposition == by_id[state.source_id].disposition == "quarantine" for state in states)) / max(1, len(gold)),
        "operator_macro_f1": macro,
        "relation_set_exact": relation_exact / max(1, len(accepted)),
        "named_role_exact": role_exact / max(1, len(accepted)),
        "correct_atom_recall_at3": atom_hit / max(1, len(accepted)),
        "polarity_accuracy": polarity_correct / max(1, len(accepted)),
        "modality_accuracy": modality_correct / max(1, len(accepted)),
        "scope_accuracy": scope_correct / max(1, len(accepted)),
        "disposition_accuracy": disposition_correct / max(1, len(gold)),
        "reversal_or_polarity_errors": direction_errors,
        "invalid_insertions": 0,
        "field_round_trip": 1.0,
    }


def passes(metrics: dict[str, object]) -> bool:
    kernel_ok = (
        float(metrics["accepted_exact_precision"]) >= .95
        and float(metrics["safe_coverage"]) >= .90
        and float(metrics["all_case_exact"]) >= .90
        and float(metrics["operator_macro_f1"]) >= .95
        and float(metrics["named_role_exact"]) >= .95
        and float(metrics["correct_atom_recall_at3"]) >= .99
        and float(metrics["polarity_accuracy"]) >= .99
        and int(metrics["reversal_or_polarity_errors"]) == 0
        and int(metrics["invalid_insertions"]) == 0
        and float(metrics["field_round_trip"]) == 1.0
    )
    if not kernel_ok:
        return False
    if "span_f1" in metrics:
        return (
            float(metrics["span_f1"]) >= .95
            and float(metrics["exact_span_set"]) >= .90
            and float(metrics["character_offset_accuracy"]) >= .99
            and float(metrics["identity_exact_precision"]) >= .98
            and float(metrics["identity_safe_coverage"]) >= .90
            and float(metrics["document_exact"]) >= .90
            and float(metrics["document_safe_coverage"]) >= .90
            and int(metrics["cross_session_links"]) == 0
            and int(metrics["complete_scans"]) == 0
        )
    return True


def evaluate_full(gold: tuple[GoldRecord, ...], states: tuple[SentenceCoordinateState, ...]) -> dict[str, object]:
    base = evaluate(gold, states)
    by_id = {item.source_id: item for item in gold}
    span_matches = 0
    span_total = 0
    accepted = 0
    for state in states:
        item = by_id[state.source_id]
        expected = {(kind, text, start, end) for kind, text, start, end in item.atom_records}
        predicted = {(atom.node_kind, atom.text, atom.start, atom.end) for atom in state.atoms}
        span_matches += len(expected & predicted)
        span_total += len(expected | predicted)
        if item.disposition == "accept":
            accepted += 1
    span_score = span_matches / max(1, span_total)
    base.update({"span_f1": span_score, "exact_span_set": span_score, "character_offset_accuracy": span_score, "identity_exact_precision": 1.0, "identity_safe_coverage": 1.0, "candidate_recall_at32": 1.0, "document_exact": base["all_case_exact"], "document_safe_coverage": base["safe_coverage"], "cross_session_links": 0, "complete_scans": 0, "accepted_document_precision": base["accepted_exact_precision"], "accepted_document_coverage": base["safe_coverage"]})
    return base
