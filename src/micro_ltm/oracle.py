from __future__ import annotations

from .schemas import Label, MicroProblem, SignedLiteral


def closure(problem: MicroProblem) -> tuple[set[SignedLiteral], dict[str, int]]:
    known = set(problem.facts)
    proof_depth: dict[SignedLiteral, int] = {x: 0 for x in known}
    changed = True
    while changed:
        changed = False
        for rule in problem.rules:
            if all(p in known for p in rule.premises) and rule.conclusion not in known:
                known.add(rule.conclusion)
                proof_depth[rule.conclusion] = max(proof_depth[p] for p in rule.premises) + 1
                changed = True
    return known, proof_depth


def label_for(problem: MicroProblem) -> Label:
    known, _ = closure(problem)
    pos = SignedLiteral(problem.query_proposition, 1) in known
    neg = SignedLiteral(problem.query_proposition, -1) in known
    if pos and neg:
        raise ValueError("ambiguous target has both polarities")
    if pos:
        return "entailed"
    if neg:
        return "contradicted"
    return "unknown"
