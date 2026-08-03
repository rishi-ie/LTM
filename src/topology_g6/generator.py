from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .oracle import solve
from .schemas import ReasoningProblem, Rule

FAMILIES = ("implication", "conjunction", "requirement", "exclusion", "equality", "temporal", "supersession", "evidence", "preference", "reference", "scope", "causal", "uncertainty", "provenance")


def _problem(seed: int, index: int) -> ReasoningProblem:
    family = FAMILIES[index % len(FAMILIES)]; case = f"g6-{seed:x}-{index:03d}"; target = f"{case}:target"; fact = f"{case}:fact"; depth = index % 6 + 1; scope = f"world:{index}" if family == "scope" and index % 2 else "global"; rules: list[Rule] = []; facts = [fact]
    if family == "conjunction":
        other = f"{case}:other"; facts += [other] if index % 5 else []; rules.append(Rule(f"{case}:conjoin", "conjoins", (fact, other), target, scope)); depth = 2
    elif family == "requirement": rules.append(Rule(f"{case}:requires", "requires", (fact, f"{case}:need"), None, scope)); target = f"{case}:absent"
    elif family == "exclusion":
        neg = f"not:{target}"; facts.append(neg); rules.append(Rule(f"{case}:to-target", "implies", (fact,), target, scope)); rules.append(Rule(f"{case}:exclude", "excludes", (target, neg), None, scope))
    elif family == "supersession":
        neg = f"not:{target}"; facts += [neg]; rules += [Rule(f"{case}:to-target", "implies", (fact,), target, scope), Rule(f"{case}:supersede", "supersedes", (target, neg), None, scope)]
    elif family == "evidence": rules += [Rule(f"{case}:to-target", "implies", (fact,), target, scope), Rule(f"{case}:support", "supports" if index % 2 else "opposes", (fact, target), None, scope)]
    elif family == "preference": rules += [Rule(f"{case}:to-target", "implies", (fact,), target, scope), Rule(f"{case}:prefer", "prefers", (fact,), None, scope)]
    elif family == "reference": rules += [Rule(f"{case}:ref", "refers_to", (fact,), None, scope), Rule(f"{case}:to-target", "implies", (fact,), target, scope)]
    elif family == "scope": rules.append(Rule(f"{case}:fiction", "fictional_rule", (fact,), target, scope))
    elif family == "causal": rules += [Rule(f"{case}:to-target", "implies", (fact,), target, scope), Rule(f"{case}:cause", "causes_hypothetically", (fact, target), None, scope)]
    elif family == "uncertainty": rules += [Rule(f"{case}:to-target", "implies", (fact,), target, scope), Rule(f"{case}:uncertain", "uncertainty", (fact, target), None, scope)]
    elif family == "provenance": rules += [Rule(f"{case}:derive", "derived_from", (fact,), target, scope)]
    else:
        current = fact
        kind = "equals" if family == "equality" else "before" if family == "temporal" else "implies"
        for step in range(depth):
            nxt = target if step == depth - 1 else f"{case}:step:{step}"; rules.append(Rule(f"{case}:r:{step}", kind, (current,), nxt, scope)); current = nxt
    return ReasoningProblem(case, family, tuple(facts), tuple(rules), target, scope, depth)


def build(seed: int, count: int) -> tuple[list[ReasoningProblem], dict[str, dict]]:
    problems = [_problem(seed, index) for index in range(count)]; return problems, {item.problem_id: solve(item) for item in problems}


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp"); tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str)); tmp.replace(path)


def materialize(path: Path, problems: list[ReasoningProblem], gold: dict[str, dict]) -> None:
    write(path / "problems.json", [asdict(item) for item in problems]); write(path / "gold" / "gold.json", gold)


def load(path: Path) -> list[ReasoningProblem]:
    rows = json.loads((path / "problems.json").read_text()); return [ReasoningProblem(row["problem_id"], row["family"], tuple(row["facts"]), tuple(Rule(**{**item, "premises": tuple(item["premises"])}) for item in row["rules"]), row["target"], row["scope"], row["depth"]) for row in rows]
