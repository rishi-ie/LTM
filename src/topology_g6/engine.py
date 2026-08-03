from __future__ import annotations

from .schemas import ProgramResult, ProofStep, ReasoningProblem

HARD = {"implies", "fictional_rule", "conjoins", "equals", "before", "after", "derived_from", "assistant_derived_from"}


def _residual(rule, active: set[str]) -> float:
    if rule.kind in ("implies", "fictional_rule", "conjoins", "derived_from", "assistant_derived_from"):
        return 0.0 if not all(item in active for item in rule.premises) or rule.conclusion in active else 1.0
    if rule.kind == "requires": return 1.0 if rule.premises[0] in active and rule.premises[1] not in active else 0.0
    if rule.kind == "excludes": return 1.0 if all(item in active for item in rule.premises) else 0.0
    return 0.0


def execute(problem: ReasoningProblem, *, shuffled_roles: bool = False, composition: bool = True, undirected: bool = False) -> ProgramResult:
    active = set(problem.facts); inactive: set[str] = set(); proofs: list[ProofStep] = []; conflicts: set[str] = set(); obligations: set[str] = set(); messages: set[str] = set(); constraints: set[str] = set(); bindings: set[str] = set(); depths = {item: 0 for item in active}; residuals = []
    rules = tuple(sorted(problem.rules, key=lambda item: item.rule_id))
    for round_id in range(1, 17):
        changed = False
        for rule in rules:
            if rule.scope not in ("global", problem.scope):
                if rule.kind in HARD | {"supersedes", "scoped_to"}: obligations.add(f"scope:{rule.rule_id}")
                continue
            premises = tuple(reversed(rule.premises)) if shuffled_roles else rule.premises
            residuals.append((rule.rule_id, _residual(rule, active)))
            if rule.kind == "supersedes" and len(premises) == 2 and premises[1] in active:
                inactive.add(premises[0]); active.discard(premises[0]); changed = True
            elif rule.kind == "requires" and len(premises) == 2 and premises[0] in active and premises[1] not in active:
                obligations.add(f"requires:{rule.rule_id}")
            elif rule.kind == "excludes" and all(item in active for item in premises):
                conflicts.add(rule.rule_id)
            elif rule.kind in ("supports", "opposes", "causes_hypothetically", "uncertainty") and all(item in active for item in premises):
                messages.add(f"{rule.kind}:{rule.rule_id}")
            elif rule.kind == "prefers" and all(item in active for item in premises): constraints.add(rule.rule_id)
            elif rule.kind == "refers_to" and all(item in active for item in premises): bindings.add(rule.rule_id)
            elif rule.kind == "scoped_to" and rule.scope != problem.scope: obligations.add(f"scope:{rule.rule_id}")
            elif rule.kind in HARD and rule.conclusion and all(item in active for item in premises) and rule.conclusion not in active and rule.conclusion not in inactive:
                active.add(rule.conclusion); depths[rule.conclusion] = 1 + max(depths.get(item, 0) for item in premises); proofs.append(ProofStep(rule.conclusion, rule.rule_id, premises, depths[rule.conclusion])); changed = True
                if undirected:
                    for premise in premises:
                        if premise not in active: active.add(premise); changed = True
        if not composition or not changed: break
    positive = problem.target in active; negative = f"not:{problem.target}" in active
    conclusion = "conflict" if conflicts or (positive and negative) else "entailed" if positive else "contradicted" if negative else "unknown"
    return ProgramResult(problem.problem_id, conclusion, tuple(sorted(active)), tuple(sorted(inactive)), tuple(sorted(proofs, key=lambda item: (item.depth, item.rule_id))), tuple(sorted(conflicts)), tuple(sorted(obligations)), tuple(sorted(messages)), tuple(sorted(constraints)), tuple(sorted(bindings)), tuple(sorted(set(residuals))), round_id)
