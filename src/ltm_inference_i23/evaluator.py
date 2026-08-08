"""Evaluator-only scoring. Runtime modules never import this module."""

from __future__ import annotations

from .schemas import RuntimeResult


def score(public_rows: tuple[dict[str, object], ...], results: dict[str, RuntimeResult], gold_rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    gold = {str(row["prompt_id"]): row for row in gold_rows}
    exact: list[bool] = []
    answerable: list[bool] = []
    accepted: list[bool] = []
    frontier: list[bool] = []
    by_depth: dict[str, list[bool]] = {}
    energy_increases = 0
    for row in public_rows:
        result = results[str(row["prompt_id"])]
        expected = gold[str(row["prompt_id"])]
        target = expected["gold_candidate_id"]
        is_answerable = target is not None
        correct = result.selected_candidate_id == target if is_answerable else result.disposition == "unknown"
        exact.append(correct)
        accepted.append(result.disposition == "candidate")
        if is_answerable:
            answerable.append(correct)
            by_depth.setdefault(str(len(expected["required_body_ids"])), []).append(correct)
        required = set(expected["required_body_ids"])
        frontier.append(required.issubset(set(result.supporting_body_ids)) if required else True)
        energy_increases += int(any(current.energy > previous.energy + 1e-7 for previous, current in zip(result.trajectory, result.trajectory[1:], strict=False)))
    accepted_correct = sum(item and correct for item, correct in zip(accepted, exact, strict=True))
    return {
        "cases": len(public_rows),
        "accepted": sum(accepted),
        "accepted_precision": accepted_correct / max(1, sum(accepted)),
        "safe_coverage": accepted_correct / max(1, len(public_rows)),
        "all_case_exactness": sum(exact) / max(1, len(exact)),
        "answerable_exactness": sum(answerable) / max(1, len(answerable)),
        "required_body_frontier_recall": sum(frontier) / max(1, len(frontier)),
        "incorrect_accepted": sum(accepted) - accepted_correct,
        "energy_increases": energy_increases,
        "by_required_depth": {key: sum(values) / max(1, len(values)) for key, values in sorted(by_depth.items(), key=lambda item: int(item[0]))},
    }
