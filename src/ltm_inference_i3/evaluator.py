"""Evaluator-only proof replay and scoring; it never calls the learned runtime."""

from __future__ import annotations

from .dataset import expr_from_obj, proposition_from_obj
from .formal import standard_axioms, verify_proof
from .schemas import FormalProofStep, MathematicalInferenceResult


def result_from_obj(value: dict[str, object]) -> MathematicalInferenceResult:
    proof = tuple(FormalProofStep(str(item["axiom_id"]), tuple(item["path"]), bool(item["reverse"]), expr_from_obj(item["before"]), expr_from_obj(item["after"])) for item in value["proof"])
    return MathematicalInferenceResult(str(value["problem_id"]), str(value["disposition"]), proof, tuple(value["opened_body_ids"]), int(value["states_visited"]), tuple(float(item) for item in value["energy_trace"]), tuple(value["failure_codes"]))


def score(public: tuple[dict[str, object], ...], results: dict[str, MathematicalInferenceResult], gold: tuple[dict[str, object], ...]) -> dict[str, object]:
    gold_by_id = {str(item["problem_id"]): item for item in gold}
    schemas = {item.axiom_id: item for item in standard_axioms()}
    accepted = correct = replayed = 0
    exact: list[bool] = []
    frontier: list[bool] = []
    by_depth: dict[str, list[bool]] = {}
    by_family: dict[str, list[bool]] = {}
    energy_increases = 0
    for row in public:
        problem_id = str(row["problem_id"])
        result = results[problem_id]
        expected = gold_by_id[problem_id]
        status = str(expected["status"])
        proposition = proposition_from_obj(row["goal"])
        valid = result.disposition == "proved" and verify_proof(proposition, result.proof, schemas)
        if result.disposition == "proved":
            accepted += 1
        answer_correct = valid if status == "proved" else result.disposition == status
        if result.disposition == "proved" and valid:
            replayed += 1
        if result.disposition == "proved" and answer_correct:
            correct += 1
        exact.append(answer_correct)
        frontier.append(set(expected["required_axiom_ids"]).issubset(set(result.opened_body_ids)))
        if status == "proved":
            by_depth.setdefault(str(expected["depth"]), []).append(answer_correct)
        by_family.setdefault(str(expected["family"]), []).append(answer_correct)
        if result.disposition == "proved":
            energy_increases += int(any(right > left + 1e-8 for left, right in zip(result.energy_trace, result.energy_trace[1:], strict=False)))
    proved_count = sum(item["status"] == "proved" for item in gold)
    unknown_refuted = [item for item in gold if item["status"] != "proved"]
    unknown_recall = sum(results[str(item["problem_id"])].disposition == item["status"] for item in unknown_refuted) / max(1, len(unknown_refuted))
    return {
        "cases": len(public),
        "accepted": accepted,
        "accepted_precision": correct / max(1, accepted),
        "incorrect_accepted": accepted - correct,
        "safe_coverage": correct / max(1, len(public)),
        "all_case_exactness": sum(exact) / max(1, len(exact)),
        "proved_exactness": sum(item for item, gold_item in zip(exact, gold, strict=True) if gold_item["status"] == "proved") / max(1, proved_count),
        "unknown_refuted_recall": unknown_recall,
        "proof_replay": replayed / max(1, accepted),
        "required_axiom_frontier_recall": sum(frontier) / max(1, len(frontier)),
        "energy_increases": energy_increases,
        "by_depth": {key: sum(values) / len(values) for key, values in sorted(by_depth.items(), key=lambda item: int(item[0]))},
        "domain_macro_exactness": sum(sum(values) / len(values) for values in by_family.values()) / max(1, len(by_family)),
    }
