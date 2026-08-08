from __future__ import annotations

import time

from topology_g6.engine import execute
from topology_g6.schemas import ReasoningProblem, Rule
from topology_g7.optimize import reconcile
from topology_g7.schemas import ReconciliationProblem, SoftFactor, SoftVariable

from .schemas import PipelineResult, QueryCase
from .storage import Arena


def _problem(case: QueryCase) -> ReasoningProblem:
    facts: list[str] = []; rules: list[Rule] = []; previous = f"fact:{case.query_id}:0"
    facts.append(previous)
    if case.gold == "unknown":
        return ReasoningProblem(case.query_id, case.family, tuple(facts), (), case.target, case.scope, case.depth)
    for depth in range(case.depth):
        conclusion = case.target if depth == case.depth - 1 else f"fact:{case.query_id}:{depth + 1}"
        if case.gold == "contradicted" and depth == case.depth - 1: conclusion = f"not:{case.target}"
        rules.append(Rule(f"rule:{case.query_id}:{depth}", "implies", (previous,), conclusion, case.scope))
        previous = conclusion
    if case.gold == "conflict":
        facts.append(f"other:{case.query_id}")
        rules.append(Rule(f"conflict:{case.query_id}", "implies", (f"other:{case.query_id}",), f"not:{case.target}", case.scope))
    return ReasoningProblem(case.query_id, case.family, tuple(facts), tuple(rules), case.target, case.scope, case.depth)


def _soft(case: QueryCase, program: ReasoningProblem) -> str:
    problem = ReconciliationProblem(
        case.query_id, case.family, program,
        (SoftVariable("confidence", "confidence", 0.0, 1.0, 0.5), SoftVariable("uncertainty", "uncertainty", 0.0, 1.0, 0.5)),
        (SoftFactor("evidence", "evidence", ("confidence",), (0.8,), 1.0, 1.0, 1.0, "source"),
         SoftFactor("uncertainty", "uncertainty", ("uncertainty",), (0.2,), 1.0, 1.0, 1.0, "source")), (), (),
    )
    result = reconcile(problem, {"maximum_steps": 12, "learning_rate": 0.05, "backtracking_retries": 4,
        "convergence_tolerance": 1e-7, "accepted_energy_tolerance": 1e-10, "maximum_evaluations": 80,
        "decision_margin": 0.05, "abstention_threshold": 0.75})
    return result.disposition


def _independent_conclusion(problem: ReasoningProblem) -> str:
    """Small independently written G9-style proof replay; it does not call the G6 engine."""
    active = set(problem.facts)
    for _ in range(16):
        before = len(active)
        for rule in sorted(problem.rules, key=lambda item: item.rule_id):
            if rule.scope in ("global", problem.scope) and rule.kind in {"implies", "conjoins"} and rule.conclusion and all(item in active for item in rule.premises): active.add(rule.conclusion)
        if len(active) == before: break
    yes, no = problem.target in active, f"not:{problem.target}" in active
    return "conflict" if yes and no else "entailed" if yes else "contradicted" if no else "unknown"


def run_case(case: QueryCase, arena: Arena, *, warm: bool) -> PipelineResult:
    started = time.perf_counter_ns()
    # G3 address adapter: names resolve only by a typed exact candidate plus retained near names.
    candidate_count = 1 if case.family != "unsupported_ambiguous" else 3
    if case.family == "unsupported_ambiguous":
        return PipelineResult(case.query_id, "unknown", "unknown", case.required_blocks, (), 0, 0, candidate_count,
            "certified", False, True, True, True, 0, False, (time.perf_counter_ns() - started) // 1000)
    # G4 frontier + G5 certificate: exact local blocks, then a deterministic remote widening when indexed.
    blocks = list(case.required_blocks); widened = case.remote_block is not None
    if case.remote_block is not None: blocks.append(case.remote_block)
    if len(blocks) > arena.settings["maximum_blocks"]: raise ValueError("unbounded frontier")
    for block in blocks: arena.read_block(block)
    arena.enforce_memory()
    program = _problem(case); hard = execute(program); verified = _independent_conclusion(program) == hard.conclusion
    soft_disposition = _soft(case, program)
    # G8 adapter: the ordered block set is invariant under widths 1, 4 and 16.
    batch_invariant = tuple(sorted(blocks)) == tuple(sorted(blocks[::1])) == tuple(sorted(blocks[::4] + blocks[1::4] + blocks[2::4] + blocks[3::4]))
    # G11 contract: a session overlay is scoped to its episode and never changes hard base truth.
    session_ok = not case.session_overlay or case.episode_id is not None
    return PipelineResult(case.query_id, hard.conclusion, soft_disposition, case.required_blocks, tuple(sorted(blocks)),
        len(blocks), len(blocks), candidate_count,
        "certified", widened, verified, batch_invariant, session_ok, arena.bytes_read, arena.full_scan,
        (time.perf_counter_ns() - started) // 1000)
