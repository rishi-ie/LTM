from __future__ import annotations

from ltm.execution import _rule_rows
from topology_g6.engine import execute
from topology_g6.schemas import ReasoningProblem


def legacy_problem(program, request):
    rows = _rule_rows(program)
    rules = tuple(item for _identifier, item in rows)
    conclusions = {rule.conclusion for rule in rules if rule.conclusion}
    facts = tuple(sorted(atom.atom_id for atom in program.atoms if atom.atom_id not in conclusions))
    return ReasoningProblem(request.request_id, "legacy", facts, rules, request.target_atom_id, request.scope_key)


def hard_signature(problem):
    return execute(problem)
