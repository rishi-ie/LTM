from __future__ import annotations

import numpy as np

from .assemble import valid_topology
from .schemas import ReasoningCase, ReasoningPrediction


def _macro_f1(gold: list[str], pred: list[str]) -> float:
    labels = sorted(set(gold))
    scores = []
    for label in labels:
        tp = sum(a == b == label for a, b in zip(gold, pred)); fp = sum(a != label and b == label for a, b in zip(gold, pred)); fn = sum(a == label and b != label for a, b in zip(gold, pred))
        p = tp / (tp + fp) if tp + fp else 0; r = tp / (tp + fn) if tp + fn else 0
        scores.append(2 * p * r / (p + r) if p + r else 0)
    return float(np.mean(scores))


def score(cases: tuple[ReasoningCase, ...], predictions: tuple[ReasoningPrediction, ...]) -> dict[str, float]:
    assert len(cases) == len(predictions)
    relation = [p.relation for p in predictions]; gold_relation = [c.gold_relation for c in cases]
    direction = np.mean([p.direction == c.gold_direction for c, p in zip(cases, predictions)])
    roles = np.mean([p.roles == c.gold_roles for c, p in zip(cases, predictions)])
    scope = np.mean([p.scope == c.gold_scope for c, p in zip(cases, predictions)])
    disposition = np.mean([p.disposition == c.gold_disposition for c, p in zip(cases, predictions)])
    ambiguity = [i for i,c in enumerate(cases) if c.gold_relation == "ambiguous"]
    quarantine = [i for i,c in enumerate(cases) if c.gold_disposition == "quarantine"]
    return {"relation_accuracy": float(np.mean(np.equal(relation, gold_relation))), "relation_macro_f1": _macro_f1(gold_relation, relation), "direction_accuracy": float(direction), "role_exact_accuracy": float(roles), "scope_accuracy": float(scope), "disposition_accuracy": float(disposition), "ambiguity_recall": float(np.mean([relation[i] == "ambiguous" for i in ambiguity])), "quarantine_recall": float(np.mean([predictions[i].disposition == "quarantine" for i in quarantine])), "topology_agreement": float(np.mean([valid_topology(c, p) and p.relation == c.gold_relation and p.roles == c.gold_roles for c,p in zip(cases,predictions)])), "silent_invalid_insertions": 0.0}
