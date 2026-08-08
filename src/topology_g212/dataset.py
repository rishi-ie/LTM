"""Semantic-program-first, split-disjoint G2.12 cases."""

from __future__ import annotations

import json
import random
import tempfile
from dataclasses import asdict
from pathlib import Path

from topology_g1.registry import REGISTRY

from .registry import RELATIONS
from .schemas import AtomicCase, SpanCandidate, sha256_text

SIZES = {
    "train": (12600, 1800, 1800, 1800),
    "development": (2520, 360, 360, 360),
    "kernel_locked": (2520, 360, 360, 360),
    "locked": (3600, 1200, 600, 600),
}
SEEDS = {"train": 1830, "development": 1831, "kernel_locked": 20261120, "locked": 20261121}
PREFIX = {"train": "T", "development": "D", "kernel_locked": "K", "locked": "L"}

PHRASES = {
    "train": {
        "after": "happens after", "assistant_derived_from": "the response is derived from", "before": "happens before",
        "causes_hypothetically": "might cause", "conjoins": "is joined with", "derived_from": "is derived from",
        "equals": "is equivalent to", "excludes": "rules out", "fictional_rule": "under the fiction permits",
        "implies": "implies", "opposes": "opposes", "prefers": "prefers", "refers_to": "refers to",
        "requires": "requires", "scoped_to": "applies only to", "supersedes": "replaces", "supports": "supports",
        "uncertainty": "leaves uncertain",
    },
    "development": {
        "after": "occurs later than", "assistant_derived_from": "the answer cites", "before": "precedes",
        "causes_hypothetically": "could lead to", "conjoins": "is combined with", "derived_from": "originates in",
        "equals": "corresponds exactly to", "excludes": "is incompatible with", "fictional_rule": "within the story allows",
        "implies": "entails", "opposes": "challenges", "prefers": "favors", "refers_to": "points to",
        "requires": "has a prerequisite", "scoped_to": "holds within", "supersedes": "takes the place of", "supports": "backs",
        "uncertainty": "does not establish",
    },
    "kernel_locked": {
        "after": "is later than", "assistant_derived_from": "the assistant statement uses", "before": "is earlier than",
        "causes_hypothetically": "may produce", "conjoins": "forms a conjunction with", "derived_from": "has origin in",
        "equals": "matches exactly", "excludes": "is incompatible with", "fictional_rule": "in the imagined scope allows",
        "implies": "logically entails", "opposes": "raises doubt about", "prefers": "would choose", "refers_to": "identifies",
        "requires": "cannot proceed without", "scoped_to": "holds inside", "supersedes": "replaces", "supports": "adds evidence for",
        "uncertainty": "keeps unresolved",
    },
    "locked": {
        "after": "happens after", "assistant_derived_from": "the assistant response is based on", "before": "happens before",
        "causes_hypothetically": "might result in", "conjoins": "is stated together with", "derived_from": "comes from",
        "equals": "is the same as", "excludes": "cannot coexist with", "fictional_rule": "under the fictional rule permits",
        "implies": "means that", "opposes": "gives evidence against", "prefers": "chooses over", "refers_to": "identifies",
        "requires": "requires", "scoped_to": "is valid only in", "supersedes": "becomes the replacement for", "supports": "gives evidence for",
        "uncertainty": "does not establish",
    },
}


def _span_text(role: str, split: str, index: int, ordinal: int) -> str:
    return f"{role}_{PREFIX[split]}{index:05d}_{ordinal}"


def _single(split: str, index: int, relation: str) -> AtomicCase:
    spec = REGISTRY[relation]
    spans: list[SpanCandidate] = []
    role_bindings: list[tuple[str, str, tuple[str, ...]]] = []
    values: list[str] = []
    for ordinal, role in enumerate(spec.roles):
        for copy_index in range(role.minimum):
            span_id = f"s{len(spans)}"
            value = _span_text(role.name, split, index, ordinal + copy_index)
            spans.append(SpanCandidate(span_id, role.allowed_kinds[0].value, value, 0, 0))
            values.append(value)
            role_bindings.append((relation, role.name, (span_id,)))
    text = f"{PHRASES[split][relation]} " + " ".join(values) + "."
    cursor = 0
    corrected: list[SpanCandidate] = []
    for span in spans:
        start = text.index(span.text, cursor)
        corrected.append(SpanCandidate(span.span_id, span.node_kind, span.text, start, start + len(span.text)))
        cursor = start + len(span.text)
    modality = "conditional" if relation in {"implies", "conjoins", "fictional_rule"} else "asserted"
    scope = "fictional" if relation == "fictional_rule" else "global"
    return AtomicCase(
        f"g212-{split}-{index:06d}", text, sha256_text(text), tuple(corrected), (relation,),
        tuple(role_bindings), "positive", modality, scope, "accept",
    )


def _multi(split: str, index: int, first: str, second: str) -> AtomicCase:
    left = _single(split, index * 2, first)
    right = _single(split, index * 2 + 1, second)
    text = left.text[:-1] + " and " + right.text[:1].lower() + right.text[1:]
    spans: list[SpanCandidate] = []
    for source in left.spans:
        start = text.index(source.text)
        spans.append(SpanCandidate(f"a{source.span_id}", source.node_kind, source.text, start, start + len(source.text)))
    offset = len(left.text[:-1]) + 5
    for source in right.spans:
        start = text.index(source.text, offset)
        spans.append(SpanCandidate(f"b{source.span_id}", source.node_kind, source.text, start, start + len(source.text)))
        offset = start + len(source.text)
    bindings = tuple(
        (relation, role, tuple(f"a{span_id}" for span_id in ids))
        for relation, role, ids in left.role_bindings
    ) + tuple(
        (relation, role, tuple(f"b{span_id}" for span_id in ids))
        for relation, role, ids in right.role_bindings
    )
    return AtomicCase(f"g212-{split}-m{index:06d}", text, sha256_text(text), tuple(spans), (first, second), bindings, "positive", "asserted", "global", "accept")


def _rejected(split: str, index: int, disposition: str) -> AtomicCase:
    left = f"unknown_{PREFIX[split]}{index:05d}_a"
    right = f"unknown_{PREFIX[split]}{index:05d}_b"
    text = f"{left} may relate to {right}, but the topology is unspecified."
    spans = (
        SpanCandidate("s0", "claim", left, text.index(left), text.index(left) + len(left)),
        SpanCandidate("s1", "claim", right, text.index(right), text.index(right) + len(right)),
    )
    return AtomicCase(f"g212-{split}-r{index:06d}", text, sha256_text(text), spans, (), (), "positive", "uncertain", "global", disposition)


def generate(split: str) -> tuple[AtomicCase, ...]:
    single, multi, ambiguous, quarantine = SIZES[split]
    rows = [_single(split, index, RELATIONS[index % len(RELATIONS)]) for index in range(single)]
    rows.extend(_multi(split, index, RELATIONS[(2 * index) % len(RELATIONS)], RELATIONS[(2 * index + 1) % len(RELATIONS)]) for index in range(multi))
    rows.extend(_rejected(split, single + multi + index, "clarification_required") for index in range(ambiguous))
    rows.extend(_rejected(split, single + multi + ambiguous + index, "quarantine") for index in range(quarantine))
    random.Random(SEEDS[split]).shuffle(rows)
    return tuple(rows)


def _write(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    temporary.replace(path)


def _public(row: AtomicCase) -> dict[str, object]:
    return {"source_id": row.source_id, "text": row.text, "source_hash": row.source_hash, "spans": [asdict(span) for span in row.spans]}


def _gold(row: AtomicCase) -> dict[str, object]:
    return {"source_id": row.source_id, "relations": row.relations, "role_bindings": row.role_bindings, "polarity": row.polarity, "modality": row.modality, "scope_id": row.scope_id, "disposition": row.disposition}


def build_split(workspace: Path, split: str) -> dict[str, int]:
    rows = generate(split)
    root = workspace / "datasets" / split
    _write(root / "public.jsonl", tuple(_public(row) for row in rows))
    _write(root / "gold.jsonl", tuple(_gold(row) for row in rows))
    _write(root / "training.jsonl", tuple(asdict(row) for row in rows))
    return {"cases": len(rows), "accepted": sum(row.disposition == "accept" for row in rows), "ambiguous": sum(row.disposition == "clarification_required" for row in rows), "quarantine": sum(row.disposition == "quarantine" for row in rows)}


def load_training(path: Path) -> tuple[AtomicCase, ...]:
    return tuple(_decode(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line)


def load_public(path: Path) -> tuple[AtomicCase, ...]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        rows.append(AtomicCase(value["source_id"], value["text"], value["source_hash"], tuple(SpanCandidate(**span) for span in value["spans"]), (), (), "positive", "asserted", "global", "accept"))
    return tuple(rows)


def load_evaluation(root: Path) -> tuple[AtomicCase, ...]:
    public = load_public(root / "public.jsonl")
    gold_rows = [json.loads(line) for line in (root / "gold.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return tuple(
        AtomicCase(case.source_id, case.text, case.source_hash, case.spans, tuple(gold["relations"]), tuple(tuple(item) for item in gold["role_bindings"]), gold["polarity"], gold["modality"], gold["scope_id"], gold["disposition"])
        for case, gold in zip(public, gold_rows, strict=True)
    )


def _decode(value: dict[str, object]) -> AtomicCase:
    return AtomicCase(
        value["source_id"], value["text"], value["source_hash"], tuple(SpanCandidate(**span) for span in value["spans"]), tuple(value["relations"]), tuple(tuple(item) for item in value["role_bindings"]), value["polarity"], value["modality"], value["scope_id"], value["disposition"],
    )
