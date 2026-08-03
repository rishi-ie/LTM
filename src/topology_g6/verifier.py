from __future__ import annotations

from .schemas import ProgramResult, ReasoningProblem


def verify(problem: ReasoningProblem, result: ProgramResult) -> tuple[bool, str | None]:
    rules = {rule.rule_id: rule for rule in problem.rules}; known = set(problem.facts)
    for step in result.proofs:
        rule = rules.get(step.rule_id)
        if rule is None: return False, "UNKNOWN_RELATION"
        if rule.conclusion != step.conclusion or rule.premises != step.premises: return False, "REVERSED_RELATION"
        if rule.scope not in ("global", problem.scope): return False, "SCOPE_VIOLATION"
        if not all(item in known for item in step.premises): return False, "MISSING_PREMISE"
        if rule.kind == "assistant_derived_from": return False, "ASSISTANT_SELF_EVIDENCE"
        known.add(step.conclusion)
    if result.conclusion == "entailed" and problem.target not in known: return False, "INVALID_CONCLUSION"
    if result.conclusion == "contradicted" and f"not:{problem.target}" not in known: return False, "INVALID_CONCLUSION"
    return True, None
