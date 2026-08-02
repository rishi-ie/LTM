from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import numpy as np

from .oracle import label_for
from .schemas import Label, MicroProblem, Rule, SignedLiteral, problem_to_dict


def _stable_seed(seed: int, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "little") % (2**63 - 1)


def _lit(prop: int, polarity: int) -> SignedLiteral:
    return SignedLiteral(int(prop), 1 if polarity >= 0 else -1)


def _random_rules(
    rng: np.random.Generator,
    propositions: int,
    count: int,
    forbidden_targets: set[SignedLiteral],
    start_id: int = 0,
) -> list[Rule]:
    rules: list[Rule] = []
    for i in range(count * 5):
        if len(rules) >= count:
            break
        a, b, c = rng.choice(propositions, size=3, replace=False)
        premises = (_lit(int(a), int(rng.choice([-1, 1]))),)
        if rng.random() < 0.4:
            premises = (premises[0], _lit(int(b), int(rng.choice([-1, 1]))))
        conclusion = _lit(int(c), int(rng.choice([-1, 1])))
        if conclusion in forbidden_targets:
            continue
        rule = Rule(f"r-{start_id + len(rules):04d}", tuple(premises), conclusion)
        if rule not in rules:
            rules.append(rule)
    return rules


def _make_base(
    rng: np.random.Generator,
    problem_id: str,
    codebook_seed: int,
    label: Label,
    depth: int,
    propositions: int,
) -> MicroProblem:
    for attempt in range(200):
        order = list(rng.permutation(propositions))
        path_nodes = [int(x) for x in order[: depth + 1]]
        target = path_nodes[-1]
        target_pol = 1 if label == "entailed" else -1
        path_literals = [_lit(path_nodes[0], 1)]
        for node in path_nodes[1:]:
            path_literals.append(_lit(node, target_pol if node == target else 1))
        facts = list(path_literals[:1])
        facts.extend(
            _lit(int(x), int(rng.choice([-1, 1])))
            for x in order[depth + 1 : depth + 4]
        )
        facts = list(dict.fromkeys(facts))[:5]
        rules: list[Rule] = []
        for idx in range(depth):
            rules.append(
                Rule(
                    f"path-{idx:04d}",
                    (path_literals[idx],),
                    path_literals[idx + 1],
                )
            )
        target_lit = _lit(target, target_pol)
        forbidden = {target_lit, _lit(target, -target_pol)}
        rules.extend(
            _random_rules(
                rng,
                propositions,
                int(rng.integers(10 - depth, 17 - depth)),
                forbidden,
                depth,
            )
        )
        query = target
        if label == "unknown":
            # Replace the constructed chain with a matched near-miss ending elsewhere.
            rules = [r for r in rules if not r.rule_id.startswith("path-")]
            near_target = int(order[depth + 1])
            near_lits = [_lit(path_nodes[0], 1)] + [_lit(int(x), 1) for x in path_nodes[1:depth]] + [_lit(near_target, 1)]
            for idx in range(len(near_lits) - 1):
                rules.append(Rule(f"near-{idx:04d}", (near_lits[idx],), near_lits[idx + 1]))
            target_lit = _lit(query, 1)
        candidate = MicroProblem(
            problem_id=problem_id,
            codebook_seed=codebook_seed,
            facts=tuple(facts),
            rules=tuple(rules),
            query_proposition=query,
            gold_label=label,
            proof_depth=depth,
        )
        try:
            actual = label_for(candidate)
        except ValueError:
            continue
        if actual != label:
            continue
        decisive = None
        if label != "unknown":
            target_candidates = [r for r in candidate.rules if r.conclusion == target_lit]
            if len(target_candidates) != 1:
                continue
            decisive = target_candidates[0].rule_id
        return replace(candidate, decisive_rule_id=decisive)
    raise RuntimeError(f"could not generate {problem_id}")


def _twin(base: MicroProblem) -> MicroProblem:
    rules = list(base.rules)
    target = base.query_proposition
    if base.gold_label == "entailed":
        rules = [r for r in rules if r.rule_id != base.decisive_rule_id]
        operation = "remove_decisive_rule"
        label: Label = "unknown"
    elif base.gold_label == "unknown":
        premise = base.facts[0]
        rules.append(Rule("twin-added-negative", (premise,), _lit(target, -1)))
        operation = "add_negative_rule"
        label = "contradicted"
    else:
        rules = [
            Rule(r.rule_id, r.premises, _lit(target, 1))
            if r.rule_id == base.decisive_rule_id
            else r
            for r in rules
        ]
        operation = "flip_decisive_polarity"
        label = "entailed"
    twin = MicroProblem(
        problem_id=f"{base.problem_id}-twin",
        codebook_seed=base.codebook_seed,
        facts=base.facts,
        rules=tuple(rules),
        query_proposition=target,
        gold_label=label,
        proof_depth=base.proof_depth,
        decisive_rule_id=None,
        twin_id=base.problem_id,
        twin_operation=operation,
    )
    if label_for(twin) != label:
        raise RuntimeError("invalid counterfactual twin")
    return twin


def generate_split(name: str, count: int, seed: int, propositions: int, depth_range: range, twins: bool) -> list[MicroProblem]:
    labels: list[Label] = ["entailed", "contradicted", "unknown"] * (count // 3)
    rng = np.random.default_rng(seed)
    out: list[MicroProblem] = []
    for i, label in enumerate(labels):
        depth = int(rng.integers(depth_range.start, depth_range.stop))
        base = _make_base(rng, f"{name}-{i:05d}", _stable_seed(seed, i), label, depth, propositions)
        out.append(base)
        if twins:
            out.append(_twin(base))
    return out


def save_jsonl(path: Path, problems: Iterable[MicroProblem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for problem in problems:
            row = problem_to_dict(problem)
            row["facts"] = [{"proposition": x.proposition, "polarity": x.polarity} for x in problem.facts]
            row["rules"] = [
                {
                    "rule_id": r.rule_id,
                    "premises": [{"proposition": x.proposition, "polarity": x.polarity} for x in r.premises],
                    "conclusion": {"proposition": r.conclusion.proposition, "polarity": r.conclusion.polarity},
                }
                for r in problem.rules
            ]
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _problem(row: dict) -> MicroProblem:
    facts = tuple(SignedLiteral(**x) for x in row["facts"])
    rules = tuple(
        Rule(
            x["rule_id"],
            tuple(SignedLiteral(**p) for p in x["premises"]),
            SignedLiteral(**x["conclusion"]),
        )
        for x in row["rules"]
    )
    return MicroProblem(
        row["problem_id"], row["codebook_seed"], facts, rules,
        row["query_proposition"], row["gold_label"], row["proof_depth"],
        row.get("decisive_rule_id"), row.get("twin_id"), row.get("twin_operation"),
    )


def load_jsonl(path: Path) -> list[MicroProblem]:
    return [_problem(json.loads(line)) for line in path.read_text().splitlines() if line.strip()]
