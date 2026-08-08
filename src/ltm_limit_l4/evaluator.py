"""Evaluator-only proof replay and hidden-gold scoring for L4."""

from __future__ import annotations

from collections import defaultdict

from ltm_inference_i3.formal import apply_schema, expression_hash

from .axioms import REALITY, executable_axioms
from .codec import problem_from_obj, result_from_obj, step_from_obj
from .schemas import L4InferenceResult, L4Problem


def verify_result(problem: L4Problem, result: L4InferenceResult) -> bool:
    if result.problem_id != problem.problem_id or problem.reality_key != REALITY:
        return False
    if result.disposition == "refuted":
        return (
            problem.source.op == "neq"
            and problem.goal.op == "eq"
            and problem.source.args == problem.goal.args
            and not result.proof
        )
    if result.disposition != "proved":
        return False
    schemas = {item.axiom_id: item for item in executable_axioms()}
    current = problem.source
    for step in result.proof:
        application = step.application
        schema = schemas.get(application.axiom_id)
        if schema is None or application.body_id != f"{REALITY}:axiom:{application.axiom_id}":
            return False
        if application.reverse and not schema.reversible:
            return False
        if step.before != current or expression_hash(step.before) != application.before_hash:
            return False
        after = apply_schema(step.before, schema, application.site_path, application.reverse)
        if after != step.after or expression_hash(step.after) != application.after_hash:
            return False
        current = step.after
    return current == problem.goal


def _band(depth: int) -> str:
    if depth <= 4:
        return "2_4"
    if depth <= 8:
        return "5_8"
    if depth <= 12:
        return "9_12"
    if depth <= 16:
        return "13_16"
    if depth <= 24:
        return "17_24"
    if depth <= 32:
        return "25_32"
    if depth <= 40:
        return "33_40"
    return "41_45"


def score_rows(
    public_rows: tuple[dict[str, object], ...],
    gold_rows: tuple[dict[str, object], ...],
    prediction_rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    public = {str(item["problem_id"]): problem_from_obj(item) for item in public_rows}
    gold = {str(item["problem_id"]): item for item in gold_rows}
    predictions = {str(item["problem_id"]): result_from_obj(item) for item in prediction_rows}
    if public.keys() != gold.keys() or public.keys() != predictions.keys():
        raise RuntimeError("PUBLIC_GOLD_PREDICTION_ID_MISMATCH")
    observations = []
    by_depth: dict[str, list[bool]] = defaultdict(list)
    by_branch: dict[str, list[bool]] = defaultdict(list)
    by_family: dict[str, list[bool]] = defaultdict(list)
    accepted = 0
    accepted_correct = 0
    proved_total = 0
    proved_correct = 0
    safe_correct = 0
    proposal_hits = 0
    proposal_total = 0
    beam_hits = 0
    beam_total = 0
    deepest = 0
    for problem_id in sorted(public):
        problem = public[problem_id]
        expected = gold[problem_id]
        result = predictions[problem_id]
        replay = verify_result(problem, result)
        status = str(expected["status"])
        correct = (status == "proved" and replay) or (status == "refuted" and replay) or (
            status == "unknown" and result.disposition == "unknown"
        )
        if result.disposition in {"proved", "refuted"}:
            accepted += 1
            accepted_correct += int(correct)
        safe_correct += int(correct)
        depth = int(expected["depth"])
        if status == "proved":
            proved_total += 1
            proved_correct += int(correct)
            by_depth[_band(depth)].append(correct)
            by_branch[str(expected["branching"])].append(correct)
            by_family[str(expected["family"])].append(correct)
            if correct:
                deepest = max(deepest, len(result.proof))
            gold_proof = tuple(step_from_obj(item) for item in expected["proof"])
            traces_by_state = {item.state_hash: item for item in result.traces}
            for step in gold_proof:
                trace = traces_by_state.get(expression_hash(step.before))
                proposal_total += 1
                beam_total += 1
                if trace is not None:
                    retained_hashes = {item.after_hash for item in trace.retained_proposals}
                    hit = step.application.after_hash in retained_hashes
                    proposal_hits += int(hit)
                    beam_hits += int(hit)
        observations.append(
            {
                "problem_id": problem_id,
                "expected_status": status,
                "disposition": result.disposition,
                "correct": correct,
                "replay_valid": replay,
                "expected_depth": depth,
                "proof_depth": len(result.proof),
                "states_explored": result.states_explored,
            }
        )
    cases = len(public)
    return {
        "cases": cases,
        "accepted_precision": accepted_correct / accepted if accepted else 1.0,
        "incorrect_accepted_conclusions": accepted - accepted_correct,
        "proof_replay": accepted_correct / accepted if accepted else 1.0,
        "safe_coverage": safe_correct / cases if cases else 0.0,
        "all_case_exactness": safe_correct / cases if cases else 0.0,
        "answerable_success": proved_correct / proved_total if proved_total else 0.0,
        "depth_success": {key: sum(rows) / len(rows) for key, rows in sorted(by_depth.items())},
        "branching_success": {key: sum(rows) / len(rows) for key, rows in sorted(by_branch.items())},
        "family_success": {key: sum(rows) / len(rows) for key, rows in sorted(by_family.items())},
        "proposal_recall_at_16": proposal_hits / proposal_total if proposal_total else 1.0,
        "correct_state_beam_survival": beam_hits / beam_total if beam_total else 1.0,
        "deepest_verified_proof": deepest,
        "observations": observations,
    }


def classification(config: dict[str, object], metrics: dict[str, object], controls: dict[str, object] | None, audit: dict[str, object]) -> str:
    gates = config["gates"]
    if not audit.get("integrity_passed", False) or metrics.get("incorrect_accepted_conclusions"):
        return "L4-G — INTEGRITY OR LEAKAGE FAILURE"
    if not audit.get("corpus_passed", False) or audit.get("executable_axioms") != 39:
        return "L4-B — AXIOM OR CORPUS VALIDITY FAILURE"
    if metrics.get("proposal_recall_at_16", 0.0) < gates["proposal_recall_at_16"]:
        return "L4-C — LOCAL PROPOSAL FAILURE"
    if not controls or not controls.get("causal_gates_passed", False):
        return "L4-D — LEARNED MECHANISM NOT CAUSAL"
    depth = metrics.get("depth_success", {})
    branching = metrics.get("branching_success", {})
    correctness = (
        metrics.get("accepted_precision", 0.0) >= gates["accepted_precision"]
        and metrics.get("proof_replay", 0.0) >= gates["proof_replay"]
        and metrics.get("all_case_exactness", 0.0) >= gates["all_case_exactness"]
        and metrics.get("answerable_success", 0.0) >= gates["answerable_success"]
        and depth.get("2_4", 0.0) >= gates["depth_2_4"]
        and depth.get("5_8", 0.0) >= gates["depth_5_8"]
        and depth.get("9_12", 0.0) >= gates["depth_9_12"]
        and depth.get("13_16", 0.0) >= gates["depth_13_16"]
        and branching.get("16", 0.0) >= gates["branching_16"]
        and branching.get("32", 0.0) >= gates["branching_32"]
    )
    if not correctness:
        if metrics.get("accepted_precision", 0.0) == 1.0:
            return "L4-S — SAFE BUT LOW COVERAGE"
        return "L4-E — BRANCHING PROOF COMPOSITION FAILURE"
    return "L4-A — UNSEEN BRANCHING PROOF DISCOVERY PASS"
