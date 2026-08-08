"""Evaluator-only scoring and exact proof replay for I3.1."""

from __future__ import annotations

from .dataset import body_from_obj, problem_from_obj
from .formal import verify_proof
from .schemas import MathematicalInferenceResult


def score(public: tuple[dict[str, object], ...], results: dict[str, MathematicalInferenceResult], gold: tuple[dict[str, object], ...], bodies: tuple[dict[str, object], ...]) -> dict[str, object]:
    body_index = {item.body_id: item for item in map(body_from_obj, bodies)}
    gold_by_id = {str(item["problem_id"]): item for item in gold}
    accepted = correct = replayed = 0; exact: list[bool] = []; frontier: list[bool] = []
    depths: dict[str, list[bool]] = {}
    for row in public:
        problem = problem_from_obj(row); expected = gold_by_id[problem.problem_id]; result = results[problem.problem_id]
        valid = result.disposition == "proved" and verify_proof(problem.source, problem.goal, result.proof, body_index, problem.reality_key)
        if result.disposition == "proved":
            accepted += 1
        expected_status = str(expected["status"])
        right = valid if expected_status == "proved" else result.disposition == expected_status
        correct += int(result.disposition == "proved" and right); replayed += int(valid); exact.append(right)
        required = {str(item) for item in expected["required_body_ids"]}
        frontier.append(required.issubset(set(result.opened_body_ids)))
        if expected_status == "proved":
            depths.setdefault(str(expected["depth"]), []).append(right)
    return {"cases": len(public), "accepted": accepted, "accepted_precision": correct / max(accepted, 1), "incorrect_accepted": accepted - correct, "safe_coverage": correct / max(1, len(public)), "all_case_exactness": sum(exact) / max(1, len(exact)), "proof_replay": replayed / max(1, accepted), "required_body_frontier_recall": sum(frontier) / max(1, len(frontier)), "by_depth": {key: sum(values) / len(values) for key, values in sorted(depths.items(), key=lambda item: int(item[0]))}}
