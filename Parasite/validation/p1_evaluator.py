"""Independent P1 scoring; deliberately does not import parasite.optimizer."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def _oracle(case: dict[str, Any]) -> dict[str, Any]:
    request = case["request"]
    if case["track"] in {"compiler", "conversation", "exact"}:
        return {"disposition": case.get("expected_disposition", ""), "claim": None}
    payload = request["payload"]
    atoms = payload["atoms"]
    factors = payload["factors"]
    expressions = {row["id"]: row["expression"] for row in atoms}
    ids = tuple(expressions)
    query = request.get("query", {})
    assumptions = tuple(next((item for item, expression in expressions.items() if expression == value), value) for value in query.get("assumptions", ()))
    positive = {item: 1.0 if item in assumptions else 0.0 for item in ids}
    negative = dict.fromkeys(ids, 0.0)
    selected = list(factors)
    for _ in range(len(ids) + 2):
        next_factors = {row["id"]: min(positive[item] for item in row["inputs"]) for row in selected}
        grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
        for row in selected:
            mass = float(row.get("authority", 1.0)) * float(row.get("confidence", 1.0)) * float(row.get("base_weight", 1.0))
            grouped[(row["outcome"], int(row.get("polarity", 1)), str(row.get("source_key", request["source_id"])))].append(mass * next_factors[row["id"]])
        normalized: dict[tuple[str, int], list[float]] = defaultdict(list)
        for (atom, polarity, _source), masses in grouped.items():
            normalized[(atom, polarity)].append(max(masses))
        next_positive = {item: 1.0 if item in assumptions else 0.0 for item in ids}
        next_negative = dict.fromkeys(ids, 0.0)
        for (atom, polarity), masses in normalized.items():
            value = 1.0 - math.prod(1.0 - max(0.0, min(1.0, mass)) for mass in masses)
            (next_positive if polarity > 0 else next_negative)[atom] = value
        delta = max((abs(next_positive[item] - positive[item]) for item in ids), default=0.0)
        positive, negative = next_positive, next_negative
        if delta <= 1e-12:
            break
    target = str(query.get("query_expression", ""))
    target_ids = [item for item in ids if expressions[item] == target]
    if not target_ids:
        return {"disposition": "unknown", "claim": None, "certificate_length": 0}
    target_id = target_ids[0]
    candidates = [(1, positive[target_id]), (-1, negative[target_id])]
    candidates = [(polarity, value) for polarity, value in candidates if value >= 0.5]
    if not candidates:
        disposition, claim = "unknown", None
    elif len(candidates) > 1 and abs(candidates[0][1] - candidates[1][1]) <= 0.05:
        disposition, claim = "alternatives", None
    else:
        polarity, _value = max(candidates, key=lambda row: row[1])
        disposition, claim = "candidate", ("not " if polarity < 0 else "") + target
    expected = dict(case.get("expected", {}))
    expected.update({"disposition": disposition, "claim": claim})
    return expected


def score(gold_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = {row["case_id"]: row for row in gold_rows}
    predictions = {row["case_id"]: row for row in prediction_rows}
    rows = []
    for case_id, expected in gold.items():
        actual = predictions.get(case_id, {"disposition": "missing", "claim": None})
        rows.append({"case_id": case_id, "expected": expected, "actual": actual,
                     "exact": expected.get("disposition") == actual.get("disposition") and expected.get("claim") == actual.get("claim")})
    exact = sum(row["exact"] for row in rows)
    return {"cases": len(rows), "exact": exact, "exactness": exact / len(rows) if rows else 0.0,
            "incorrect_accepted": sum(row["actual"].get("disposition") == "candidate" and not row["exact"] for row in rows),
            "rows": rows}
