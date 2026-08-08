from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .schemas import BenchmarkGold, BenchmarkQuery, BenchmarkTurn

FAMILIES = (
    "direct", "reference_preference", "correction", "scope", "depth_two",
    "depth_six", "conflict", "constraint_exception", "old_context", "unsupported",
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def build(seed: int, conversations: int, turns: int) -> tuple[tuple[BenchmarkTurn, ...], tuple[BenchmarkQuery, ...]]:
    events: list[BenchmarkTurn] = []; queries: list[BenchmarkQuery] = []
    for conversation in range(conversations):
        family = FAMILIES[conversation % len(FAMILIES)]
        conversation_id = f"conv-{seed:x}-{conversation:03d}"
        for turn in range(turns):
            speaker = "user" if turn % 2 == 0 else "assistant"
            text = f"{speaker} {family} opaque-{seed:x}-{conversation}-{turn}"
            events.append(BenchmarkTurn(f"{conversation_id}-turn-{turn:02d}", conversation_id, turn, speaker, text, digest(text)))
        for slot in (3, 7, 11, 5, 9, 1):
            number = len(queries); gold = ("entailed", "contradicted", "unknown", "conflict")[number % 4]
            if family == "unsupported": gold = "unknown"
            depth = 6 if family == "depth_six" else 2 if family == "depth_two" else 1
            prompt = f"What is the verified {family} state for opaque-{seed:x}-{conversation}?"
            query_id = f"{conversation_id}-query-{slot:02d}"
            target = f"target:{query_id}"
            facts = [f"fact:{query_id}:0"]
            rules: list[tuple[str, tuple[str, ...], str]] = []
            if gold != "unknown":
                prior = facts[0]
                for step in range(depth):
                    conclusion = target if step == depth - 1 else f"fact:{query_id}:{step + 1}"
                    if gold == "contradicted" and step == depth - 1:
                        conclusion = f"not:{target}"
                    rules.append((f"rule:{query_id}:{step}", (prior,), conclusion))
                    prior = conclusion
                if gold == "conflict":
                    facts.append(f"opposite:{query_id}")
                    rules.append((f"opposite-rule:{query_id}", (facts[-1],), f"not:{target}"))
            queries.append(BenchmarkQuery(query_id, conversation_id, family, prompt, depth,
                family in {"reference_preference", "correction", "old_context"},
                family in {"constraint_exception", "old_context"}, tuple(facts), tuple(rules)))
    return tuple(events), tuple(queries)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True)); temporary.replace(path)


def materialize(root: Path, turns: tuple[BenchmarkTurn, ...], queries: tuple[BenchmarkQuery, ...], *, include_gold: bool) -> None:
    write_json(root / "runtime" / "turns.json", [asdict(item) for item in turns])
    write_json(root / "runtime" / "queries.json", [asdict(item) for item in queries])
    if include_gold:
        gold: list[BenchmarkGold] = []
        for number, item in enumerate(queries):
            label = ("entailed", "contradicted", "unknown", "conflict")[number % 4]
            if item.family == "unsupported":
                label = "unknown"
            # An unknown case has no decisive derivation. It must not turn a
            # harmless seed fact into a required proof factor.
            required = ()
            if item.rules:
                required = tuple(f"factor:{item.query_id}:fact:{index}" for index, _ in enumerate(item.facts))
                required += tuple(f"factor:{item.query_id}:{rule_id}" for rule_id, _premises, _conclusion in item.rules)
            gold.append(BenchmarkGold(item.query_id, label, required))
        write_json(root / "gold" / "outcomes.json", [asdict(item) for item in gold])


def load_queries(root: Path) -> tuple[BenchmarkQuery, ...]:
    return tuple(BenchmarkQuery(**item) for item in json.loads((root / "runtime" / "queries.json").read_text()))


def load_gold(root: Path) -> tuple[BenchmarkGold, ...]:
    return tuple(BenchmarkGold(**item) for item in json.loads((root / "gold" / "outcomes.json").read_text()))
