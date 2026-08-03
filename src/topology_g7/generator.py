from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from topology_g6.schemas import ReasoningProblem, Rule

from .oracle import solve
from .schemas import DiscreteAlternative, ReconciliationProblem, SoftFactor, SoftVariable

FAMILIES = ("authority_conflict", "ambiguous_reference", "observations", "preferences", "uncertainty", "mixed")


def _factor(case: str, kind: str, variable: str, target: float, authority: float = 1.0, confidence: float = 1.0, alternative: str | None = None, applicable: bool = True, base: float = 1.0) -> SoftFactor:
    return SoftFactor(f"{case}:{kind}:{variable}:{alternative or 'all'}:{target}", kind, (variable,), (target,), base, authority, confidence, f"source:{case}:{kind}", alternative, applicable)


def _problem(seed: int, number: int) -> ReconciliationProblem:
    family = FAMILIES[number % len(FAMILIES)]; case = f"g7-{seed:x}-{number:03d}"; hard_family = "implication" if family != "mixed" else "conjunction"
    hard = _problem_g6(seed, number, hard_family)
    variables = [SoftVariable("c:claim", "confidence", 0, 1, .5), SoftVariable("p:style", "preference", 0, 1, .5), SoftVariable("u:unknown", "uncertainty", 0, 1, .5)]
    factors: list[SoftFactor] = []; alternatives: list[DiscreteAlternative] = []; groups: list[tuple[str, ...]] = []
    if family == "authority_conflict":
        variables.append(SoftVariable("c:branch", "confidence", 0, 1, .5))
        left, right = f"{case}:left", f"{case}:right"; alternatives = [DiscreteAlternative(left, "conflict", ("c:branch",)), DiscreteAlternative(right, "conflict", ("c:branch",))]
        # One branch is internally coherent; the rival has incompatible sources.
        winner_left = (number // len(FAMILIES)) % 2 == 0
        good, bad = (left, right) if winner_left else (right, left)
        factors += [_factor(case, "branch", "c:branch", .90, 1.0, .95, good), _factor(case, "branch", "c:branch", .88, .9, .95, good), _factor(case, "branch", "c:branch", .10, .65, .8, bad), _factor(case, "branch", "c:branch", .90, .65, .8, bad), _factor(case, "uncertainty", "u:unknown", .15)]
    elif family == "ambiguous_reference":
        variables += [SoftVariable("r:alpha", "reference", 0, 1, .5, "r"), SoftVariable("r:beta", "reference", 0, 1, .5, "r")]; groups = [("r:alpha", "r:beta")]
        left, right = f"{case}:alpha", f"{case}:beta"; alternatives = [DiscreteAlternative(left, "reference", ("r:alpha",)), DiscreteAlternative(right, "reference", ("r:beta",))]
        tied = (number // len(FAMILIES)) % 2 == 1
        factors += [_factor(case, "reference", "r:alpha", 1.0, 1.0, .95, left), _factor(case, "reference", "r:beta", 1.0, 1.0 if tied else .4, .95, right), _factor(case, "uncertainty", "u:unknown", .2 if not tied else .4)]
    elif family == "observations":
        target = .75 if number % 2 else .45
        factors += [_factor(case, "evidence", "c:claim", target, .9, .9), _factor(case, "evidence", "c:claim", target + (.02 if number % 2 else -.02), .8, .9), _factor(case, "uncertainty", "u:unknown", 1.0 - target)]
    elif family == "preferences":
        active = number % 2 == 0
        factors += [_factor(case, "preference", "p:style", 1.0 if active else 0.0, 1.0, .95, applicable=active), _factor(case, "evidence", "c:claim", .8), _factor(case, "uncertainty", "u:unknown", .2)]
    elif family == "uncertainty":
        abstain = (number // len(FAMILIES)) % 2 == 0
        factors += [_factor(case, "evidence", "c:claim", .1 if abstain else .85, .8, .8), _factor(case, "uncertainty", "u:unknown", .95 if abstain else .15, base=8.0)]
    else:
        variables += [SoftVariable("r:alpha", "reference", 0, 1, .5, "r"), SoftVariable("r:beta", "reference", 0, 1, .5, "r"), SoftVariable("c:branch", "confidence", 0, 1, .5)]; groups = [("r:alpha", "r:beta")]
        left, right = f"{case}:coherent", f"{case}:rival"; alternatives = [DiscreteAlternative(left, "mixed", ("r:alpha", "c:branch")), DiscreteAlternative(right, "mixed", ("r:beta", "c:branch"))]
        factors += [_factor(case, "reference", "r:alpha", 1.0, 1, .9, left), _factor(case, "branch", "c:branch", .85, 1, .9, left), _factor(case, "reference", "r:beta", 1.0, .4, .8, right), _factor(case, "branch", "c:branch", .1, .5, .8, right), _factor(case, "branch", "c:branch", .9, .5, .8, right), _factor(case, "preference", "p:style", 1.0), _factor(case, "evidence", "c:claim", .8), _factor(case, "uncertainty", "u:unknown", .15)]
    # A weak neutral prior makes the quadratic strictly convex for every
    # continuous variable. It is a registered soft factor, not a hard rule.
    for variable in variables:
        kind = "reference" if variable.variable_type == "reference" else "preference" if variable.variable_type == "preference" else "uncertainty" if variable.variable_type == "uncertainty" else "evidence"
        factors.append(_factor(case, kind, variable.variable_id, .5, 1.0, 1.0, base=4.0))
    return ReconciliationProblem(case, family, hard, tuple(variables), tuple(factors), tuple(alternatives), tuple(groups))


def _problem_g6(seed: int, number: int, family: str) -> ReasoningProblem:
    # Use G6's registered relation contract with a controlled depth up to six.
    case = f"g7-hard-{seed:x}-{number:03d}"; target = f"{case}:target"; fact = f"{case}:fact"; depth = number % 6 + 1
    if family == "conjunction":
        other = f"{case}:other"; return ReasoningProblem(case, family, (fact, other), (Rule(f"{case}:rule", "conjoins", (fact, other), target),), target, depth=2)
    current = fact; rules = []
    for step in range(depth):
        nxt = target if step == depth - 1 else f"{case}:step:{step}"; rules.append(Rule(f"{case}:r:{step}", "implies", (current,), nxt)); current = nxt
    return ReasoningProblem(case, family, (fact,), tuple(rules), target, depth=depth)


def build(seed: int, count: int, settings: dict) -> tuple[list[ReconciliationProblem], dict[str, dict]]:
    problems = [_problem(seed, number) for number in range(count)]
    gold = {problem.problem_id: solve(problem, settings) for problem in problems}
    return problems, gold


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str)); temp.replace(path)


def materialize(path: Path, problems: list[ReconciliationProblem], gold: dict[str, dict]) -> None:
    write(path / "problems.json", [asdict(problem) for problem in problems]); write(path / "gold" / "gold.json", gold)


def load(path: Path) -> list[ReconciliationProblem]:
    rows = json.loads((path / "problems.json").read_text()); output = []
    for row in rows:
        program = row["g6_program"]
        g6 = ReasoningProblem(program["problem_id"], program["family"], tuple(program["facts"]), tuple(Rule(**{**rule, "premises": tuple(rule["premises"])}) for rule in program["rules"]), program["target"], program["scope"], program["depth"])
        variables = tuple(SoftVariable(**item) for item in row["soft_variables"]); factors = tuple(SoftFactor(**{**item, "variable_ids": tuple(item["variable_ids"]), "target_values": tuple(item["target_values"])}) for item in row["soft_factors"]); alternatives = tuple(DiscreteAlternative(**{**item, "affected_ids": tuple(item["affected_ids"]), "incompatible_hard_ids": tuple(item["incompatible_hard_ids"])}) for item in row["alternatives"])
        output.append(ReconciliationProblem(row["problem_id"], row["family"], g6, variables, factors, alternatives, tuple(tuple(item) for item in row["reference_groups"])))
    return output
