from __future__ import annotations

from .schemas import ReasoningProblem


def solve(problem: ReasoningProblem) -> dict:
    active = set(problem.facts); inactive = set(); conflicts = set(); obligations = set(); messages = set(); constraints = set(); bindings = set(); proofs = []; rules = sorted(problem.rules, key=lambda item: item.rule_id)
    for _ in range(16):
        changed = False
        for rule in rules:
            if rule.scope not in ("global", problem.scope): continue
            if rule.kind == "supersedes" and rule.premises[1] in active: inactive.add(rule.premises[0]); active.discard(rule.premises[0])
            elif rule.kind == "requires" and rule.premises[0] in active and rule.premises[1] not in active: obligations.add(f"requires:{rule.rule_id}")
            elif rule.kind == "excludes" and all(item in active for item in rule.premises): conflicts.add(rule.rule_id)
            elif rule.kind in ("supports", "opposes", "causes_hypothetically", "uncertainty") and all(item in active for item in rule.premises): messages.add(f"{rule.kind}:{rule.rule_id}")
            elif rule.kind == "prefers" and all(item in active for item in rule.premises): constraints.add(rule.rule_id)
            elif rule.kind == "refers_to" and all(item in active for item in rule.premises): bindings.add(rule.rule_id)
            elif rule.kind in {"implies", "fictional_rule", "conjoins", "equals", "before", "after", "derived_from"} and rule.conclusion and all(item in active for item in rule.premises) and rule.conclusion not in active and rule.conclusion not in inactive:
                active.add(rule.conclusion); proofs.append(rule.rule_id); changed = True
        if not changed: break
    target = problem.target; positive = target in active; negative = f"not:{target}" in active
    conclusion = "conflict" if conflicts or (positive and negative) else "entailed" if positive else "contradicted" if negative else "unknown"
    return {"conclusion": conclusion, "active": sorted(active), "inactive": sorted(inactive), "conflicts": sorted(conflicts), "obligations": sorted(obligations), "messages": sorted(messages), "constraints": sorted(constraints), "bindings": sorted(bindings), "proof_rules": sorted(proofs)}
