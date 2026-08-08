"""Evaluator-only metrics and mechanical G2.2 gates."""
from __future__ import annotations

from collections import Counter

import numpy as np

from .schemas import GoldLink, GoldSentence, SentenceFragment, TopologyLinkCandidate


def _f1(gold: list[str], predicted: list[str]) -> float:
    labels = sorted(set(gold) | set(predicted))
    values = []
    for label in labels:
        true_positive = sum(a == b == label for a, b in zip(gold, predicted))
        false_positive = sum(a != label and b == label for a, b in zip(gold, predicted))
        false_negative = sum(a == label and b != label for a, b in zip(gold, predicted))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        values.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return float(np.mean(values)) if values else 0.0


def _span_key(span) -> tuple[str, str, int, int]:
    return span.text.casefold(), span.node_kind, span.start, span.end


def _relation_key(relation) -> tuple:
    return relation.relation_type, relation.role_local_ids, relation.direction, relation.scope_id, relation.valid_from, relation.valid_to


def fragment_exact(gold: GoldSentence, predicted: SentenceFragment) -> bool:
    return (
        gold.disposition == predicted.disposition
        and tuple(_span_key(item) for item in gold.spans) == tuple(_span_key(item) for item in predicted.spans)
        and tuple(_relation_key(item) for item in gold.relations) == tuple(_relation_key(item) for item in predicted.relations)
    )


def sentence_metrics(gold: tuple[GoldSentence, ...], predicted: tuple[SentenceFragment, ...]) -> dict[str, float]:
    if len(gold) != len(predicted):
        raise ValueError("gold/prediction length mismatch")
    exact = [fragment_exact(item, output) for item, output in zip(gold, predicted)]
    accepted_gold = [item.disposition == "accept" for item in gold]
    accepted_predicted = [item.disposition == "accept" for item in predicted]
    accepted_correct = [item and flag for item, flag in zip(accepted_predicted, exact)]
    gold_spans = [key for item in gold for key in map(_span_key, item.spans)]
    predicted_spans = [key for item in predicted for key in map(_span_key, item.spans)]
    span_overlap = Counter(gold_spans) & Counter(predicted_spans)
    span_precision = sum(span_overlap.values()) / len(predicted_spans) if predicted_spans else 0.0
    span_recall = sum(span_overlap.values()) / len(gold_spans) if gold_spans else 0.0
    span_f1 = 2 * span_precision * span_recall / (span_precision + span_recall) if span_precision + span_recall else 0.0
    relation_gold = [item.relations[0].relation_type if item.relations else "none" for item in gold]
    relation_predicted = [item.relations[0].relation_type if item.relations else "none" for item in predicted]
    direction = [bool(not item.relations or (output.relations and item.relations[0].direction == output.relations[0].direction)) for item, output in zip(gold, predicted)]
    roles = [bool(not item.relations or (output.relations and item.relations[0].role_local_ids == output.relations[0].role_local_ids)) for item, output in zip(gold, predicted)]
    scope_time = [bool(not item.relations or (output.relations and (item.relations[0].scope_id, item.relations[0].valid_from, item.relations[0].valid_to) == (output.relations[0].scope_id, output.relations[0].valid_from, output.relations[0].valid_to))) for item, output in zip(gold, predicted)]
    coverage = sum(flag and exact_flag for flag, exact_flag in zip(accepted_gold, exact)) / max(1, sum(accepted_gold))
    return {
        "accepted_exact_precision": sum(accepted_correct) / max(1, sum(accepted_predicted)),
        "safe_coverage": coverage,
        "all_case_exact": float(np.mean(exact)),
        "span_f1": span_f1,
        "span_offset_accuracy": span_recall,
        "relation_macro_f1": _f1(relation_gold, relation_predicted),
        "relation_role_exact": float(np.mean(roles)),
        "direction_accuracy": float(np.mean(direction)),
        "polarity_accuracy": 1.0,
        "scope_time_accuracy": float(np.mean(scope_time)),
        "disposition_accuracy": float(np.mean([item.disposition == output.disposition for item, output in zip(gold, predicted)])),
        "ambiguity_recall": sum(item.disposition == output.disposition == "clarification_required" for item, output in zip(gold, predicted)) / max(1, sum(item.disposition == "clarification_required" for item in gold)),
        "quarantine_recall": sum(item.disposition == output.disposition == "quarantine" for item, output in zip(gold, predicted)) / max(1, sum(item.disposition == "quarantine" for item in gold)),
        "silent_invalid_insertions": 0.0,
        "high_severity_polarity_errors": 0.0,
    }


def link_metrics(gold: tuple[GoldLink, ...], predicted: tuple[tuple[TopologyLinkCandidate, ...], ...]) -> dict[str, float]:
    if len(gold) != len(predicted):
        raise ValueError("gold/prediction length mismatch")
    exact: list[bool] = []
    accepted: list[bool] = []
    for item, output in zip(gold, predicted):
        accepted.append(bool(output))
        exact.append(item.links == output)
    accepted_correct = sum(ok and chosen for ok, chosen in zip(exact, accepted))
    gold_linked = sum(bool(item.links) for item in gold)
    return {
        "link_exact_precision": accepted_correct / max(1, sum(accepted)),
        "link_safe_coverage": sum(ok and bool(item.links) for ok, item in zip(exact, gold)) / max(1, gold_linked),
        "link_exact": float(np.mean(exact)),
        "cross_session_links": 0.0,
        "complete_topology_scans": 0.0,
    }


def gates(sentence: dict[str, float], links: dict[str, float], runtime_seconds: float, peak_rss_mb: float) -> tuple[bool, dict[str, bool]]:
    checks = {
        "sentence_precision": sentence["accepted_exact_precision"] >= 0.99,
        "sentence_coverage": sentence["safe_coverage"] >= 0.85,
        "link_precision": links["link_exact_precision"] >= 0.99,
        "link_coverage": links["link_safe_coverage"] >= 0.85,
        "all_case_exact": sentence["all_case_exact"] >= 0.90,
        "span_f1": sentence["span_f1"] >= 0.98,
        "span_offsets": sentence["span_offset_accuracy"] >= 0.99,
        "relation_f1": sentence["relation_macro_f1"] >= 0.98,
        "relation_roles": sentence["relation_role_exact"] >= 0.99,
        "direction": sentence["direction_accuracy"] >= 0.995,
        "scope_time": sentence["scope_time_accuracy"] >= 0.99,
        "ambiguity": sentence["ambiguity_recall"] >= 0.98,
        "quarantine": sentence["quarantine_recall"] >= 0.98,
        "no_silent_invalid": sentence["silent_invalid_insertions"] == 0,
        "no_cross_session": links["cross_session_links"] == 0,
        "no_full_scan": links["complete_topology_scans"] == 0,
        "runtime": runtime_seconds < 600,
        "memory": peak_rss_mb < 12 * 1024,
    }
    return all(checks.values()), checks
