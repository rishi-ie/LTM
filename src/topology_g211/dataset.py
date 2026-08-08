"""Semantic-program-first atomic-coordinate dataset."""

from __future__ import annotations

import hashlib
import json
import random
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from topology_g1.registry import REGISTRY

from .basis import build_basis, coordinates_for_relation

SIZES = {
    "train": 18_000,
    "development": 3_600,
    "kernel_locked": 3_600,
    "locked": 6_000,
}
SEEDS = {"train": 1821, "development": 1822, "kernel_locked": 20261101, "locked": 20261102}
PREFIX = {"train": "T", "development": "D", "kernel_locked": "K", "locked": "L"}
PHRASES = {
    "train": {
        "after": "follows after", "assistant_derived_from": "assistant response comes from", "before": "comes before",
        "causes_hypothetically": "might cause", "conjoins": "joins with", "derived_from": "is derived from",
        "equals": "is equal to", "excludes": "cannot coexist with", "fictional_rule": "fictionally permits",
        "implies": "therefore implies", "opposes": "argues against", "prefers": "prefers", "refers_to": "refers to",
        "requires": "depends on", "scoped_to": "is scoped to", "supersedes": "replaces", "supports": "supports",
        "uncertainty": "is uncertain from",
    },
    "development": {
        "after": "occurs later than", "assistant_derived_from": "assistant answer cites", "before": "precedes",
        "causes_hypothetically": "could lead to", "conjoins": "is combined with", "derived_from": "originates in",
        "equals": "corresponds exactly to", "excludes": "rules out", "fictional_rule": "within the fiction allows",
        "implies": "entails", "opposes": "challenges", "prefers": "favors", "refers_to": "points to",
        "requires": "has a prerequisite", "scoped_to": "applies within", "supersedes": "takes the place of", "supports": "backs",
        "uncertainty": "leaves uncertain from",
    },
    "kernel_locked": {
        "after": "is later than", "assistant_derived_from": "assistant statement is sourced from", "before": "is earlier than",
        "causes_hypothetically": "may produce", "conjoins": "forms a conjunction with", "derived_from": "has origin in",
        "equals": "matches exactly", "excludes": "is incompatible with", "fictional_rule": "in the imagined scope allows",
        "implies": "logically entails", "opposes": "raises doubt about", "prefers": "would choose", "refers_to": "identifies",
        "requires": "cannot proceed without", "scoped_to": "holds within", "supersedes": "replaces", "supports": "adds evidence for",
        "uncertainty": "has uncertain support from",
    },
    "locked": {
        "after": "happens after", "assistant_derived_from": "assistant response is based on", "before": "happens before",
        "causes_hypothetically": "might result in", "conjoins": "is stated together with", "derived_from": "comes from",
        "equals": "is the same as", "excludes": "cannot coexist with", "fictional_rule": "under the fictional rule permits",
        "implies": "means that", "opposes": "gives evidence against", "prefers": "chooses over", "refers_to": "identifies",
        "requires": "requires", "scoped_to": "is valid only in", "supersedes": "becomes the replacement for", "supports": "gives evidence for",
        "uncertainty": "does not establish from",
    },
}


@dataclass(frozen=True, slots=True)
class SpanGold:
    span_id: str
    kind: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class AtomicExample:
    source_id: str
    text: str
    source_hash: str
    relation_type: str | None
    spans: tuple[SpanGold, ...]
    feature_ids: tuple[str, ...]
    disposition: str


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _render(split: str, index: int, relation: str | None) -> AtomicExample:
    prefix = PREFIX[split]
    if relation is None:
        left = f"claim_{prefix}{index:05d}_a"
        right = f"claim_{prefix}{index:05d}_b"
        text = f"{left} may connect to {right}, but the relation is not specified."
        disposition = "clarification_required"
        spans = (
            SpanGold("a", "claim", text.index(left), text.index(left) + len(left)),
            SpanGold("b", "claim", text.index(right), text.index(right) + len(right)),
        )
        return AtomicExample(f"g211-{split}-{index:06d}", text, _hash(text), None, spans, (), disposition)
    spec = REGISTRY[relation]
    span_texts = [f"{role.name}_{prefix}{index:05d}" for role in spec.roles]
    phrase = PHRASES[split][relation]
    text = (phrase + " " + " ".join(span_texts) + ".").strip()
    spans = tuple(
        SpanGold(f"s{role_index}", role.allowed_kinds[0].value, text.index(value), text.index(value) + len(value))
        for role_index, (role, value) in enumerate(zip(spec.roles, span_texts, strict=True))
    )
    features = tuple(sorted({f"feature:{coordinate.basis_id.removeprefix('feature:')}" for coordinate in coordinates_for_relation(relation)}))
    return AtomicExample(f"g211-{split}-{index:06d}", text, _hash(text), relation, spans, features, "accept")


def generate(split: str) -> tuple[AtomicExample, ...]:
    count = SIZES[split]
    relation_names = tuple(sorted(REGISTRY))
    rows: list[AtomicExample] = [_render(split, index, relation_names[index % len(relation_names)]) for index in range(count - count // 10)]
    rows.extend(_render(split, index + len(rows), None) for index in range(count // 10))
    random.Random(SEEDS[split]).shuffle(rows)
    return tuple(rows)


def _write(path: Path, rows: tuple[AtomicExample, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(asdict(row), sort_keys=True) for row in rows) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    temporary.replace(path)


def build_split(workspace: Path, split: str) -> dict[str, int]:
    path = workspace / "datasets" / split / "inputs.jsonl"
    if path.exists():
        raise RuntimeError(f"{split} already exists")
    rows = generate(split)
    _write(path, rows)
    return {
        "cases": len(rows),
        "accepted": sum(row.disposition == "accept" for row in rows),
        "ambiguous": sum(row.disposition == "clarification_required" for row in rows),
        "feature_count": len(build_basis().features),
    }


def load(path: Path) -> tuple[AtomicExample, ...]:
    if "gold" in path.parts:
        raise PermissionError("runtime cannot read evaluator gold")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        rows.append(AtomicExample(
            value["source_id"], value["text"], value["source_hash"], value["relation_type"],
            tuple(SpanGold(**span) for span in value["spans"]), tuple(value["feature_ids"]), value["disposition"],
        ))
    return tuple(rows)
