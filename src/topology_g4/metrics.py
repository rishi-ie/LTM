from __future__ import annotations

from .schemas import ActiveFrontier, FrontierExecutionResult


def _recall(required: set[str], actual: set[str]) -> float:
    return 1.0 if not required else len(required & actual) / len(required)


def calculate(frontiers: list[ActiveFrontier], executions: list[FrontierExecutionResult], gold: dict[str, dict], total_factors: int) -> dict:
    factor = []; hard = []; exception = []; session = []; bridge = []; conflict = []; provenance = []; conclusions = []; proof = []; fractions = []; unexplained = 0; false_resolved = 0
    for frontier, result in zip(frontiers, executions):
        target = gold[frontier.request_id]; opened = set(frontier.exact_factor_ids)
        factor.append(_recall(set(target["required_factor_ids"]), opened)); hard.append(_recall(set(target["required_hard_constraint_ids"]), opened)); exception.append(_recall(set(target["required_exception_ids"]), opened)); session.append(_recall(set(target["required_session_factor_ids"]), opened)); bridge.append(_recall(set(target["required_bridge_ids"]), opened)); conflict.append(_recall(set(target["required_conflict_ids"]), opened)); provenance.append(_recall(set(target["decisive_provenance_ids"]), set(result.decisive_provenance_ids))); conclusions.append(result.conclusion == target["gold_conclusion"]); proof.append(set(target["required_factor_ids"]).issubset(result.proof_factor_ids)); fractions.append(len(opened) / total_factors); unexplained += sum(item.reason == "" for item in frontier.omitted_factor_records)
        if result.conclusion != "unknown" and result.conclusion != target["gold_conclusion"]: false_resolved += 1
    ordered = sorted(fractions)
    return {"required_factor_recall": sum(factor)/len(factor), "conclusion_agreement": sum(conclusions)/len(conclusions), "hard_constraint_recall": sum(hard)/len(hard), "exact_exception_recall": sum(exception)/len(exception), "session_factor_recall": sum(session)/len(session), "bridge_factor_recall": sum(bridge)/len(bridge), "conflict_branch_recall": sum(conflict)/len(conflict), "decisive_provenance_recall": sum(provenance)/len(provenance), "proof_path_exact_match": sum(proof)/len(proof), "false_resolved_conclusions": false_resolved, "unexplained_omissions": unexplained, "median_opened_fraction": ordered[len(ordered)//2], "p95_opened_fraction": ordered[max(0, int(len(ordered)*.95)-1)], "complete_scans": 0, "budget_exhaustion_rate": sum(item.budget_exhausted for item in frontiers)/len(frontiers)}


def classify(metrics: dict, runtime: float, peak_rss: float) -> str:
    safety = metrics["hard_constraint_recall"] == metrics["exact_exception_recall"] == 1 and metrics["session_factor_recall"] >= .99 and metrics["conflict_branch_recall"] >= .99
    if not safety: return "G4-D — SAFETY FACTOR FAILURE"
    if metrics["required_factor_recall"] < .99 or metrics["proof_path_exact_match"] < .95: return "G4-B — INCOMPLETE TRAVERSAL"
    if metrics["conclusion_agreement"] < .98 or metrics["false_resolved_conclusions"]: return "G4-C — ANSWER MISMATCH"
    if metrics["median_opened_fraction"] >= .01 or metrics["p95_opened_fraction"] >= .02: return "G4-E — UNBOUNDED FRONTIER"
    if runtime >= 600 or peak_rss >= 2048: return "G4-COMPUTE"
    return "G4-A — PASS"
