from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import numpy as np

from micro_ltm.oracle import label_for
from micro_ltm.schemas import Label, MicroProblem, Rule, SignedLiteral


def _seed(seed: int, index: int) -> int:
    return int.from_bytes(hashlib.sha256(f"v2:{seed}:{index}".encode()).digest()[:8], "little")


def _lit(prop: int, polarity: int = 1) -> SignedLiteral:
    return SignedLiteral(int(prop), 1 if polarity >= 0 else -1)


def _random_rules(
    rng: np.random.Generator,
    propositions: int,
    count: int,
    forbidden: set[SignedLiteral],
    start: int,
) -> list[Rule]:
    rules: list[Rule] = []
    for _ in range(count * 30):
        if len(rules) >= count:
            break
        choices = rng.choice(propositions, size=3, replace=False)
        a, b, c = (int(x) for x in choices)
        premises = [_lit(a, int(rng.choice([-1, 1])))]
        if rng.random() < 0.4:
            premises.append(_lit(b, int(rng.choice([-1, 1]))))
        conclusion = _lit(c, int(rng.choice([-1, 1])))
        rule = Rule(f"noise-{start + len(rules):04d}", tuple(premises), conclusion)
        if conclusion not in forbidden and rule not in rules:
            rules.append(rule)
    return rules


def _make_base(rng: np.random.Generator, problem_id: str, seed: int, label: Label, depth: int) -> MicroProblem:
    for _ in range(300):
        order = [int(x) for x in rng.permutation(24)]
        path = order[: depth + 1]
        target = path[-1]
        target_polarity = 1 if label == "entailed" else -1
        path_literals = [_lit(path[0])] + [_lit(x, target_polarity if x == target else 1) for x in path[1:]]
        facts: list[SignedLiteral] = [path_literals[0]]
        rules: list[Rule] = []
        used_side: set[int] = set()
        conjunction_seen = False
        path_rules: list[Rule] = []
        for index in range(depth):
            conclusion = path_literals[index + 1]
            if depth >= 4 and index == depth // 2:
                use_conjunction = True
            else:
                use_conjunction = bool(rng.random() < 0.4)
            if use_conjunction:
                side = next(x for x in order[depth + 1 :] if x not in used_side)
                used_side.add(side)
                facts.append(_lit(side))
                premises = (path_literals[index], _lit(side))
                conjunction_seen = True
            else:
                premises = (path_literals[index],)
            path_rules.append(Rule(f"path-{index:04d}", premises, conclusion))
        if depth >= 4 and not conjunction_seen:
            continue
        facts.extend(_lit(x, int(rng.choice([-1, 1]))) for x in order[depth + 1 : depth + 5] if x not in used_side)
        facts = list(dict.fromkeys(facts))[:7]
        target_lit = _lit(target, target_polarity)
        forbidden = {target_lit, _lit(target, -target_polarity)}
        if label == "unknown":
            near_target = next(x for x in order if x not in path)
            near_literals = path_literals[:-1] + [_lit(near_target)]
            rules.extend(
                Rule(f"near-{index:04d}", (path_rules[index].premises), near_literals[index + 1])
                for index in range(depth)
            )
        else:
            rules.extend(path_rules)
        rules.extend(_random_rules(rng, 24, int(rng.integers(8, 14)), forbidden, depth))
        # A target-to-fact edge is harmless to the directed oracle, but is a
        # direction trap for the reverse/undirected controls.
        rules.append(Rule("direction-trap", (target_lit,), path_literals[0]))
        problem = MicroProblem(
            problem_id, seed, tuple(facts), tuple(rules), target, label, depth,
        )
        try:
            if label_for(problem) != label:
                continue
        except ValueError:
            continue
        target_rules = [r for r in problem.rules if r.conclusion == target_lit]
        if label != "unknown" and len(target_rules) != 1:
            continue
        return replace(problem, decisive_rule_id=target_rules[0].rule_id if target_rules else None)
    raise RuntimeError(f"could not generate {problem_id}")


def _twin(base: MicroProblem) -> MicroProblem:
    target = base.query_proposition
    rules = list(base.rules)
    if base.gold_label == "entailed":
        rules = [r for r in rules if r.rule_id != base.decisive_rule_id]
        label: Label = "unknown"
        operation = "remove_decisive_rule"
    elif base.gold_label == "contradicted":
        rules = [
            Rule(r.rule_id, r.premises, _lit(target, 1)) if r.rule_id == base.decisive_rule_id else r
            for r in rules
        ]
        label = "entailed"
        operation = "reverse_decisive_polarity"
    else:
        rules.append(Rule("twin-negative", (base.facts[0],), _lit(target, -1)))
        label = "contradicted"
        operation = "add_negative_rule"
    twin = MicroProblem(
        f"{base.problem_id}-twin", base.codebook_seed, base.facts, tuple(rules), target,
        label, base.proof_depth, None, base.problem_id, operation,
    )
    if label_for(twin) != label:
        raise RuntimeError(f"invalid twin for {base.problem_id}")
    return twin


def generate_split(name: str, count: int, seed: int, depth_range: range, twins: bool) -> list[MicroProblem]:
    if count % 3:
        raise ValueError("case count must be divisible by three")
    rng = np.random.default_rng(seed)
    labels: list[Label] = ["entailed", "contradicted", "unknown"] * (count // 3)
    output: list[MicroProblem] = []
    for index, label in enumerate(labels):
        depth = int(rng.integers(depth_range.start, depth_range.stop))
        base = _make_base(rng, f"{name}-{index:05d}", _seed(seed, index), label, depth)
        output.append(base)
        if twins:
            output.append(_twin(base))
    return output


def save_jsonl(path: Path, problems: Iterable[MicroProblem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for problem in problems:
            row = {
                "problem_id": problem.problem_id,
                "codebook_seed": problem.codebook_seed,
                "facts": [{"proposition": x.proposition, "polarity": x.polarity} for x in problem.facts],
                "rules": [
                    {
                        "rule_id": rule.rule_id,
                        "premises": [{"proposition": x.proposition, "polarity": x.polarity} for x in rule.premises],
                        "conclusion": {"proposition": rule.conclusion.proposition, "polarity": rule.conclusion.polarity},
                    }
                    for rule in problem.rules
                ],
                "query_proposition": problem.query_proposition,
                "gold_label": problem.gold_label,
                "proof_depth": problem.proof_depth,
                "decisive_rule_id": problem.decisive_rule_id,
                "twin_id": problem.twin_id,
                "twin_operation": problem.twin_operation,
            }
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[MicroProblem]:
    result: list[MicroProblem] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        facts = tuple(SignedLiteral(**x) for x in row["facts"])
        rules = tuple(
            Rule(x["rule_id"], tuple(SignedLiteral(**p) for p in x["premises"]), SignedLiteral(**x["conclusion"]))
            for x in row["rules"]
        )
        result.append(MicroProblem(
            row["problem_id"], row["codebook_seed"], facts, rules,
            row["query_proposition"], row["gold_label"], row["proof_depth"],
            row.get("decisive_rule_id"), row.get("twin_id"), row.get("twin_operation"),
        ))
    return result
