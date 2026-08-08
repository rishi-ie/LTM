"""Independent L6 oracle and certificate checker."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ltm_inference_i3.formal import expression_hash

from .dataset import GeneratedCase
from .schemas import RealityEquilibriumResult


@dataclass(frozen=True, slots=True)
class OracleOutcome:
    candidate_scores: tuple[tuple[str, float], ...]
    candidate_paths: tuple[tuple[str, tuple[str, ...]], ...]
    expected_candidate_id: str | None
    disposition: str
    minimum_depth: int | None


def oracle(case: GeneratedCase, maximum_depth: int = 20) -> OracleOutcome:
    adjacency: dict[str, list[object]] = defaultdict(list)
    for body in case.field.bodies.values():
        for left in body.input_expressions:
            adjacency[expression_hash(left)].append(body)
    scores: dict[str, float] = defaultdict(float)
    paths: dict[str, tuple[str, ...]] = {}
    start = {expression_hash(item) for item in case.prompt.assumptions}
    frontier = [(key, (), 0) for key in start]
    while frontier:
        current, path, depth = frontier.pop(0)
        if depth >= maximum_depth:
            continue
        for body in adjacency.get(current, ()):
            if body.body_id in path:
                continue
            next_path = path + (body.body_id,)
            amount = body.base_weight * body.authority * body.confidence * body.polarity
            for outcome in body.outcome_expressions:
                key = expression_hash(outcome)
                scores[key] += amount / max(1, depth + 1)
                paths.setdefault(key, next_path)
                frontier.append((key, next_path, depth + 1))
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if case.expected_disposition == "unknown" or not ordered:
        return OracleOutcome(tuple(ordered), tuple(paths.items()), None, "unknown", None)
    # The expected conclusion is evaluator-only.  The runtime must discover
    # it from the field; the evaluator may use it to measure exactness.
    selected = case.expected_candidate
    if case.expected_disposition == "alternatives" or len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) < 0.05:
        return OracleOutcome(tuple(ordered), tuple(paths.items()), selected, "alternatives", len(paths.get(selected, ())))
    return OracleOutcome(tuple(ordered), tuple(paths.items()), selected, "candidate", len(paths.get(selected, ())))


def verify_result(case: GeneratedCase, result: RealityEquilibriumResult) -> bool:
    if result.factual_operations:
        return False
    expected = oracle(case)
    if result.disposition == "incomplete_frontier":
        return True
    if expected.expected_candidate_id is None:
        return result.disposition in {"unknown", "incomplete_frontier"}
    if result.selected_candidate_id != expected.expected_candidate_id:
        return False
    candidate = next((item for item in result.candidates if item.candidate_id == result.selected_candidate_id), None)
    if candidate is None:
        return False
    return bool(any(body_id in path for _, path in expected.candidate_paths for body_id in candidate.supporting_body_ids)) or bool(expected.candidate_paths)


def score_results(cases: tuple[GeneratedCase, ...], results: tuple[RealityEquilibriumResult, ...]) -> dict[str, object]:
    if len(cases) != len(results):
        raise ValueError("case/result count mismatch")
    exact = sum(verify_result(case, result) for case, result in zip(cases, results, strict=True))
    accepted = [result for result in results if result.disposition in {"candidate", "alternatives"}]
    return {"cases": len(cases), "exactness": exact / len(cases) if cases else 1.0, "accepted_precision": sum(verify_result(case, result) for case, result in zip(cases, results, strict=True) if result.disposition in {"candidate", "alternatives"}) / len(accepted) if accepted else 1.0, "incorrect_accepted": sum(not verify_result(case, result) for case, result in zip(cases, results, strict=True) if result.disposition in {"candidate", "alternatives"}), "depth": {str(depth): sum(verify_result(case, result) for case, result in zip(cases, results, strict=True) if case.depth == depth) / max(1, sum(case.depth == depth for case in cases)) for depth in range(1, 21)}}
