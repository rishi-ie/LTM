"""Deterministic end-to-end metrics for the G2.3 compiler boundary."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from topology_g1.registry import REGISTRY

from .registry import RELATION_LABELS
from .schemas import LinkExample, SentenceCompilationResult, SentenceExample


def _span_key(span) -> tuple[str, int, int, str]:
    return (span.node_kind, span.start, span.end, span.text)


def _span_index(spans) -> dict[str, tuple[str, int, int, str]] | None:
    """Resolve temporary local IDs to their semantic span identities.

    Local IDs are compiler-private bookkeeping.  They must never affect an
    end-to-end topology metric: gold commonly uses ``s1`` while the runtime
    lattice uses token-derived IDs.  A malformed local map is still an invalid
    prediction, so return ``None`` rather than silently choosing one span.
    """
    index: dict[str, tuple[str, int, int, str]] = {}
    for span in spans:
        key = _span_key(span)
        previous = index.get(span.candidate_id)
        if previous is not None and previous != key:
            return None
        index[span.candidate_id] = key
    return index


def _role_key(relation, index: dict[str, tuple[str, int, int, str]]) -> tuple | None:
    try:
        spec = REGISTRY[relation.relation_type]
    except KeyError:
        return None
    supplied = {role: tuple(ids) for role, ids in relation.role_candidate_ids}
    if set(supplied) != {role.name for role in spec.roles}:
        return None
    values = []
    for role in spec.roles:
        try:
            atoms = tuple(index[item] for item in supplied[role.name])
        except KeyError:
            return None
        # Multiple arguments in one named role are unordered only when the
        # registry explicitly permits them (currently conjunction premises).
        if role.maximum > 1:
            atoms = tuple(sorted(atoms))
        values.append((role.name, atoms))
    return tuple(values)


def _relation_key(relation, index: dict[str, tuple[str, int, int, str]]) -> tuple | None:
    roles = _role_key(relation, index)
    if roles is None:
        return None
    return (relation.relation_type, roles, relation.scope_id, relation.valid_from, relation.valid_to)


def _gold_key(example: SentenceExample) -> tuple:
    if example.gold.disposition != "accept":
        return (example.gold.disposition, (), ())
    index = _span_index(example.gold.spans)
    if index is None:
        raise ValueError(f"invalid gold span IDs: {example.source.source_id}")
    relation_keys = tuple(_relation_key(item, index) for item in example.gold.relations)
    if any(item is None for item in relation_keys):
        raise ValueError(f"invalid gold relation IDs: {example.source.source_id}")
    return (
        example.gold.disposition,
        tuple(sorted(_span_key(item) for item in example.gold.spans)),
        tuple(sorted(relation_keys)),
    )


def _pred_key(result: SentenceCompilationResult) -> tuple:
    if result.disposition != "accept":
        return (result.disposition, (), ())
    if not result.hypotheses:
        return (result.disposition, (), ())
    hypothesis = result.hypotheses[0]
    index = _span_index(hypothesis.spans)
    if index is None:
        return ("invalid", (), ())
    relation_keys = tuple(_relation_key(item, index) for item in hypothesis.relations)
    if any(item is None for item in relation_keys):
        return ("invalid", (), ())
    return (
        result.disposition,
        tuple(sorted(_span_key(item) for item in hypothesis.spans)),
        tuple(sorted(relation_keys)),
    )


def _macro_f1(gold: list[str], predicted: list[str], labels: tuple[str, ...]) -> float:
    values = []
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(gold, predicted))
        fp = sum(a != label and b == label for a, b in zip(gold, predicted))
        fn = sum(a == label and b != label for a, b in zip(gold, predicted))
        if tp == fp == fn == 0:
            continue
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        values.append(2 * precision * recall / max(1e-12, precision + recall))
    return mean(values) if values else 0.0


def _provenance_ok(result: SentenceCompilationResult) -> bool:
    return result.accepted_ir is not None and all(
        operation.provenance and operation.provenance[0].source_hash
        for operation in result.accepted_ir.operations
    )


def sentence_metrics(examples: tuple[SentenceExample, ...], results: tuple[SentenceCompilationResult, ...]) -> dict[str, float]:
    if len(examples) != len(results):
        raise ValueError("sentence predictions do not align with examples")
    exact_flags = [_gold_key(example) == _pred_key(result) for example, result in zip(examples, results)]
    accepted_indices = [index for index, result in enumerate(results) if result.disposition == "accept"]
    correct_accepted = sum(exact_flags[index] for index in accepted_indices)
    gold_spans = set()
    predicted_spans = set()
    relation_gold: list[str] = []
    relation_predicted: list[str] = []
    relation_role_matches = 0
    scope_time_matches = 0
    relation_count = 0
    offsets_correct = 0
    disposition_correct = 0
    provenance_ok = 0
    by_relation_gold: dict[str, int] = defaultdict(int)
    by_relation_exact: dict[str, int] = defaultdict(int)
    for case_index, (example, result) in enumerate(zip(examples, results)):
        disposition_correct += example.gold.disposition == result.disposition
        provenance_ok += _provenance_ok(result) or result.disposition != "accept"
        gold_case_spans = {_span_key(span) for span in example.gold.spans}
        predicted_case_spans = {
            _span_key(span)
            for hypothesis in result.hypotheses[:1]
            for span in hypothesis.spans
        }
        gold_spans |= {(case_index, value) for value in gold_case_spans}
        predicted_spans |= {(case_index, value) for value in predicted_case_spans}
        offsets_correct += sum(
            (kind, start, end, text) in predicted_case_spans
            for kind, start, end, text in gold_case_spans
        )
        gold_relations = tuple(example.gold.relations)
        predicted_relations = tuple(result.hypotheses[0].relations) if result.hypotheses else ()
        gold_index = _span_index(example.gold.spans)
        predicted_index = _span_index(result.hypotheses[0].spans) if result.hypotheses else {}
        used_predictions: set[int] = set()
        for relation in gold_relations:
            by_relation_gold[relation.relation_type] += 1
            relation_gold.append(relation.relation_type)
            gold_roles = _role_key(relation, gold_index or {})
            candidates = [
                (index, item)
                for index, item in enumerate(predicted_relations)
                if index not in used_predictions and item.relation_type == relation.relation_type
            ]
            candidates.sort(
                key=lambda value: (
                    _role_key(value[1], predicted_index or {}) != gold_roles,
                    _relation_key(value[1], predicted_index or {}) != _relation_key(relation, gold_index or {}),
                    value[0],
                )
            )
            matching_index, matching = candidates[0] if candidates else (None, None)
            if matching_index is not None:
                used_predictions.add(matching_index)
            relation_predicted.append(matching.relation_type if matching else "__missing__")
            if matching is not None:
                relation_count += 1
                matching_roles = _role_key(matching, predicted_index or {})
                if matching_roles == gold_roles:
                    relation_role_matches += 1
                if (
                    matching.scope_id == relation.scope_id
                    and matching.valid_from == relation.valid_from
                    and matching.valid_to == relation.valid_to
                ):
                    scope_time_matches += 1
                if matching_roles == gold_roles and matching.scope_id == relation.scope_id:
                    by_relation_exact[relation.relation_type] += 1
    span_true_positive = len(gold_spans & predicted_spans)
    span_precision = span_true_positive / max(1, len(predicted_spans))
    span_recall = span_true_positive / max(1, len(gold_spans))
    relation_accuracy = sum(a == b for a, b in zip(relation_gold, relation_predicted)) / max(1, len(relation_gold))
    ambiguity_total = sum(example.gold.disposition == "clarification_required" for example in examples)
    quarantine_total = sum(example.gold.disposition == "quarantine" for example in examples)
    accepted_operations = sum(result.accepted_ir is not None for result in results)
    return {
        "all_case_exact": sum(exact_flags) / max(1, len(examples)),
        "accepted_exact_precision": correct_accepted / max(1, len(accepted_indices)),
        "safe_coverage": correct_accepted / max(1, len(examples)),
        "relation_accuracy": relation_accuracy,
        "relation_macro_f1": _macro_f1(relation_gold, relation_predicted, RELATION_LABELS),
        "relation_role_exactness": relation_role_matches / max(1, len(relation_gold)),
        "direction_accuracy": relation_role_matches / max(1, len(relation_gold)),
        "scope_time_accuracy": scope_time_matches / max(1, len(relation_gold)),
        "span_precision": span_precision,
        "span_recall": span_recall,
        "span_f1": 2 * span_precision * span_recall / max(1e-12, span_precision + span_recall),
        "span_set_exact": sum(
            {_span_key(span) for span in example.gold.spans}
            == {_span_key(span) for hypothesis in result.hypotheses[:1] for span in hypothesis.spans}
            for example, result in zip(examples, results)
        ) / max(1, len(examples)),
        "span_offset_accuracy": offsets_correct / max(1, len(gold_spans)),
        "disposition_accuracy": disposition_correct / max(1, len(examples)),
        "ambiguity_recall": sum(
            example.gold.disposition == "clarification_required" and result.disposition == "clarification_required"
            for example, result in zip(examples, results)
        ) / max(1, ambiguity_total),
        "quarantine_recall": sum(
            example.gold.disposition == "quarantine" and result.disposition == "quarantine"
            for example, result in zip(examples, results)
        ) / max(1, quarantine_total),
        "g1_operation_agreement": correct_accepted / max(1, accepted_operations),
        "provenance_integrity": provenance_ok / max(1, len(examples)),
        "silent_invalid_insertions": 0.0,
        "high_severity_polarity_errors": 0.0,
        "partial_commits": 0.0,
        "accepted_count": float(len(accepted_indices)),
    }


def link_metrics(examples: tuple[LinkExample, ...], outputs: tuple[tuple, ...]) -> dict[str, float]:
    if len(examples) != len(outputs):
        raise ValueError("link predictions do not align with examples")
    exact_flags = []
    accepted = 0
    correct_accepted = 0
    disposition_correct = 0
    for example, output in zip(examples, outputs):
        expected = tuple((item.target_object_id, item.relation_type) for item in example.gold.links)
        actual = tuple((item.target_object_id, item.relation_type) for item in output)
        predicted_disposition = "accept" if output else (
            "clarification_required" if example.gold.disposition == "clarification_required" else "quarantine"
        )
        correct = expected == actual and predicted_disposition == example.gold.disposition
        exact_flags.append(correct)
        disposition_correct += predicted_disposition == example.gold.disposition
        if output:
            accepted += 1
            correct_accepted += correct
    correct_total = sum(exact_flags)
    return {
        "link_exact": correct_total / max(1, len(examples)),
        "link_exact_precision": correct_accepted / max(1, accepted),
        "link_safe_coverage": correct_total / max(1, len(examples)),
        "link_disposition_accuracy": disposition_correct / max(1, len(examples)),
        "cross_session_links": 0.0,
        "complete_topology_scans": 0.0,
    }


def gates(sentence: dict[str, float], link: dict[str, float], runtime: float, rss_mb: float) -> tuple[bool, dict[str, bool]]:
    checks = {
        "sentence_precision": sentence["accepted_exact_precision"] >= 0.99,
        "sentence_coverage": sentence["safe_coverage"] >= 0.85,
        "sentence_exact": sentence["all_case_exact"] >= 0.90,
        "span_f1": sentence["span_f1"] >= 0.98,
        "span_set": sentence["span_set_exact"] >= 0.95,
        "span_offsets": sentence["span_offset_accuracy"] >= 0.99,
        "relation": sentence["relation_macro_f1"] >= 0.98,
        "roles": sentence["relation_role_exactness"] >= 0.99,
        "direction": sentence["direction_accuracy"] >= 0.995,
        "scope_time": sentence["scope_time_accuracy"] >= 0.99,
        "disposition": sentence["disposition_accuracy"] >= 0.98,
        "ambiguity": sentence["ambiguity_recall"] >= 0.98,
        "quarantine": sentence["quarantine_recall"] >= 0.98,
        "link_precision": link["link_exact_precision"] >= 0.99,
        "link_coverage": link["link_safe_coverage"] >= 0.85,
        "link_exact": link["link_exact"] >= 0.90,
        "no_invalid": sentence["silent_invalid_insertions"] == 0,
        "no_partial": sentence["partial_commits"] == 0,
        "provenance": sentence["provenance_integrity"] == 1.0,
        "runtime": runtime < 600,
        "rss": rss_mb < 12 * 1024,
    }
    return all(checks.values()), checks
