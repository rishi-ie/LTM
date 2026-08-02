from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

import numpy as np

from micro_ltm.oracle import closure, label_for
from micro_ltm.schemas import Label, MicroProblem, Rule, SignedLiteral

from .schemas import CapacityCase


def _seed(seed: int, index: int) -> int:
    return int.from_bytes(hashlib.sha256(f"micro3:{seed}:{index}".encode()).digest()[:8], "little")


def _lit(prop: int, polarity: int = 1) -> SignedLiteral:
    return SignedLiteral(int(prop), 1 if polarity >= 0 else -1)


def _noise_rules(rng: np.random.Generator, propositions: int, count: int, forbidden: set[SignedLiteral], start: int) -> list[Rule]:
    rules: list[Rule] = []
    for _ in range(count * 30):
        if len(rules) >= count:
            break
        a, b, c = (int(x) for x in rng.choice(propositions, size=3, replace=False))
        premises = [_lit(a, int(rng.choice([-1, 1])))]
        if rng.random() < 0.4:
            premises.append(_lit(b, int(rng.choice([-1, 1]))))
        conclusion = _lit(c, int(rng.choice([-1, 1])))
        rule = Rule(f"noise-{start + len(rules):04d}", tuple(premises), conclusion)
        if conclusion not in forbidden and rule not in rules:
            rules.append(rule)
    return rules


def _make_base(
    rng: np.random.Generator,
    name: str,
    codebook_seed: int,
    label: Label,
    depth: int,
    propositions: int,
    bucket: str,
) -> CapacityCase:
    for _ in range(500):
        order = [int(x) for x in rng.permutation(propositions)]
        path = order[: depth + 1]
        target = path[-1]
        target_polarity = 1 if label == "entailed" else -1
        path_literals = [_lit(path[0])] + [_lit(x, target_polarity if x == target else 1) for x in path[1:]]
        facts: list[SignedLiteral] = [path_literals[0]]
        path_rules: list[Rule] = []
        side_used: set[int] = set()
        conjunction_seen = False
        for index in range(depth):
            if depth >= 6 and index == depth // 2:
                conjunction = True
            else:
                conjunction = bool(rng.random() < 0.4)
            premises: list[SignedLiteral] = [path_literals[index]]
            if conjunction:
                side = next(x for x in order[depth + 1 :] if x not in side_used)
                side_used.add(side)
                facts.append(_lit(side))
                premises.append(_lit(side))
                conjunction_seen = True
            path_rules.append(Rule(f"path-{index:04d}", tuple(premises), path_literals[index + 1]))
        if depth >= 6 and not conjunction_seen:
            continue
        facts.extend(_lit(x, int(rng.choice([-1, 1]))) for x in order[depth + 1 : depth + 8] if x not in side_used)
        facts = list(dict.fromkeys(facts))[:10]
        target_lit = _lit(target, target_polarity)
        forbidden = {target_lit, _lit(target, -target_polarity)}
        if label == "unknown":
            near_target = next(x for x in order if x not in path)
            near_literals = path_literals[:-1] + [_lit(near_target)]
            rules = [Rule(f"near-{i:04d}", r.premises, near_literals[i + 1]) for i, r in enumerate(path_rules)]
        else:
            rules = list(path_rules)
        rules.extend(_noise_rules(rng, propositions, max(12, min(32, propositions // 4)), forbidden, depth))
        rules.append(Rule("direction-trap", (target_lit,), path_literals[0]))
        problem = MicroProblem(name, codebook_seed, tuple(facts), tuple(rules), target, label, depth)
        try:
            if label_for(problem) != label:
                continue
        except ValueError:
            continue
        known, _ = closure(problem)
        active = len(known)
        # Density is a measured property of the generated closure.  The
        # requested bucket is only a generation target; retain valid cases
        # even when stochastic distractors move a case across a boundary.
        if propositions > 24:
            if active <= 16:
                bucket = "low"
            elif active <= 32:
                bucket = "medium"
            elif active <= 48:
                bucket = "high"
            else:
                bucket = "dense"
        target_rules = [r for r in problem.rules if r.conclusion == target_lit]
        if label != "unknown" and len(target_rules) != 1:
            continue
        return CapacityCase(replace(problem, decisive_rule_id=target_rules[0].rule_id if target_rules else None), propositions, bucket)
    raise RuntimeError(f"could not generate {name}")


def _twin(case: CapacityCase) -> CapacityCase:
    p = case.problem
    target = p.query_proposition
    rules = list(p.rules)
    if p.gold_label == "entailed":
        rules = [r for r in rules if r.rule_id != p.decisive_rule_id]
        label: Label = "unknown"
        operation = "remove_decisive_rule"
    elif p.gold_label == "contradicted":
        rules = [Rule(r.rule_id, r.premises, _lit(target, 1)) if r.rule_id == p.decisive_rule_id else r for r in rules]
        label = "entailed"
        operation = "reverse_decisive_polarity"
    else:
        rules.append(Rule("twin-negative", (p.facts[0],), _lit(target, -1)))
        label = "contradicted"
        operation = "add_negative_rule"
    twin = replace(p, problem_id=f"{p.problem_id}-twin", rules=tuple(rules), gold_label=label, twin_id=p.problem_id, twin_operation=operation, decisive_rule_id=None)
    if label_for(twin) != label:
        raise RuntimeError(f"invalid twin {p.problem_id}")
    return CapacityCase(twin, case.proposition_count, case.density_bucket)


def generate_split(name: str, count: int, seed: int, propositions: int, depth_range: range, twins: bool) -> list[CapacityCase]:
    if count % 3:
        raise ValueError("case count must be divisible by three")
    rng = np.random.default_rng(seed)
    labels: list[Label] = ["entailed", "contradicted", "unknown"] * (count // 3)
    buckets = ["low", "medium", "high", "dense"] if propositions > 24 else ["micro"]
    result: list[CapacityCase] = []
    for index, label in enumerate(labels):
        depth = int(rng.integers(depth_range.start, depth_range.stop))
        bucket = buckets[index % len(buckets)]
        base = _make_base(rng, f"{name}-{index:05d}", _seed(seed, index), label, depth, propositions, bucket)
        result.append(base)
        if twins:
            result.append(_twin(base))
    return result


def save_jsonl(path: Path, cases: Iterable[CapacityCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for case in cases:
            p = case.problem
            row = {
                "proposition_count": case.proposition_count,
                "density_bucket": case.density_bucket,
                "problem_id": p.problem_id,
                "codebook_seed": p.codebook_seed,
                "facts": [{"proposition": x.proposition, "polarity": x.polarity} for x in p.facts],
                "rules": [{"rule_id": r.rule_id, "premises": [{"proposition": x.proposition, "polarity": x.polarity} for x in r.premises], "conclusion": {"proposition": r.conclusion.proposition, "polarity": r.conclusion.polarity}} for r in p.rules],
                "query_proposition": p.query_proposition,
                "gold_label": p.gold_label,
                "proof_depth": p.proof_depth,
                "decisive_rule_id": p.decisive_rule_id,
                "twin_id": p.twin_id,
                "twin_operation": p.twin_operation,
            }
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_jsonl(path: Path) -> list[CapacityCase]:
    result: list[CapacityCase] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        facts = tuple(SignedLiteral(**x) for x in row["facts"])
        rules = tuple(Rule(x["rule_id"], tuple(SignedLiteral(**q) for q in x["premises"]), SignedLiteral(**x["conclusion"])) for x in row["rules"])
        problem = MicroProblem(row["problem_id"], row["codebook_seed"], facts, rules, row["query_proposition"], row["gold_label"], row["proof_depth"], row.get("decisive_rule_id"), row.get("twin_id"), row.get("twin_operation"))
        result.append(CapacityCase(problem, row["proposition_count"], row["density_bucket"]))
    return result
