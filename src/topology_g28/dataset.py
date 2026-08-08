"""Semantic-program-first G2.8 fixtures with public/gold separation."""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import tempfile
from pathlib import Path

from topology_field_ir import FieldContext, GoldenAtom
from topology_g1.registry import REGISTRY

from .atom_bank import RELATIONS
from .schemas import GoldExample, SourceExample

SIZES = {
    "train": (25200, 5400, 2700, 2700),
    "development": (4320, 1440, 720, 720),
    "kernel_locked": (3600, 1200, 600, 600),
    "locked": (4800, 1600, 800, 800),
}
SEEDS = {"train": 1780, "development": 1781, "kernel_locked": 20260901, "locked": 20260902}
PREFIX = {"train": "T", "development": "D", "kernel_locked": "K", "locked": "L"}
FRAMING = {
    "train": ("In the ledger", "Given the record", "For this entry", "Under this note"),
    "development": ("From the dossier", "Within the account", "For this report", "By this record"),
    "kernel_locked": ("According to the archive", "In this memorandum", "For this case", "On this evidence"),
    "locked": ("Across the brief", "Under this statement", "From the chronicle", "For this scenario"),
}
# The lexical realization is deliberately split-specific.  The compiler may
# learn from sentence meaning and its frozen semantic anchors, but cannot solve
# a locked case by memorizing a renderer phrase from training.
PHRASES = {
    "train": {
        "implies": "logically entails", "conjoins": "jointly establishes", "requires": "needs as a prerequisite",
        "excludes": "cannot coexist with", "equals": "denotes the same value as", "before": "occurs earlier than",
        "after": "occurs later than", "supersedes": "is replaced by", "supports": "provides evidence for",
        "opposes": "provides evidence against", "prefers": "selects", "refers_to": "identifies",
        "scoped_to": "is limited to", "fictional_rule": "would entail", "causes_hypothetically": "could produce",
        "uncertainty": "leaves unresolved", "assistant_derived_from": "is based on", "derived_from": "originates from",
    },
    "development": {
        "implies": "therefore establishes", "conjoins": "together demonstrate", "requires": "depends on first",
        "excludes": "is incompatible with", "equals": "has identical value to", "before": "precedes in time",
        "after": "follows in time", "supersedes": "takes the place of", "supports": "corroborates",
        "opposes": "contradicts", "prefers": "chooses", "refers_to": "points to",
        "scoped_to": "applies only within", "fictional_rule": "would establish", "causes_hypothetically": "may bring about",
        "uncertainty": "does not settle", "assistant_derived_from": "was derived using", "derived_from": "comes from",
    },
    "kernel_locked": {
        "implies": "makes necessary", "conjoins": "when combined yields", "requires": "cannot proceed without",
        "excludes": "rules out", "equals": "is equivalent to", "before": "happens prior to",
        "after": "takes place subsequent to", "supersedes": "overrides", "supports": "lends support to",
        "opposes": "counts against", "prefers": "favors", "refers_to": "designates",
        "scoped_to": "is confined to", "fictional_rule": "in that fiction entails", "causes_hypothetically": "might lead to",
        "uncertainty": "remains undetermined about", "assistant_derived_from": "traces its derivation to", "derived_from": "is sourced from",
    },
    "locked": {
        "implies": "consequently gives", "conjoins": "in combination proves", "requires": "has as a condition",
        "excludes": "prevents coexistence with", "equals": "matches exactly", "before": "comes ahead of",
        "after": "comes later than", "supersedes": "displaces", "supports": "is evidence in favor of",
        "opposes": "is evidence against", "prefers": "opts for", "refers_to": "names",
        "scoped_to": "holds solely in", "fictional_rule": "would, in fiction, give", "causes_hypothetically": "could result in",
        "uncertainty": "cannot determine", "assistant_derived_from": "uses as its basis", "derived_from": "was obtained from",
    },
}


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _kind_name(kind: str, split: str, index: int, ordinal: int) -> str:
    stem = f"{PREFIX[split]}{index:05d}_{ordinal}"
    labels = {
        "event": "event", "scope": "scope", "preference": "preference", "instruction": "instruction",
        "question": "question", "assistant_response": "assistant_response", "entity": "entity", "goal": "goal",
        "value": "value", "state": "state", "rule": "rule", "conversation_turn": "turn",
    }
    return f"{labels.get(kind, 'claim')}_{stem}"


def _slots(relation: str) -> tuple[tuple[str, str], ...]:
    return tuple(
        (role.name, kind.value)
        for role in REGISTRY[relation].roles
        for kind in (role.allowed_kinds[0],) * role.minimum
    )


def _render_clause(split: str, relation: str, words: tuple[str, ...]) -> str:
    phrase = PHRASES[split][relation]
    if relation == "conjoins":
        return f"{words[0]} and {words[1]} {phrase} {words[2]}"
    if relation == "fictional_rule":
        return f"within {words[2]}, {words[0]} {phrase} {words[1]}"
    if relation == "supersedes":
        return f"{words[1]} {phrase} {words[0]}"
    return f"{words[0]} {phrase} {words[1]}"


def _accepted(split: str, index: int, relations: tuple[str, ...]) -> tuple[SourceExample, GoldExample]:
    values: list[tuple[str, str]] = []
    for relation in relations:
        values.extend((kind, _kind_name(kind, split, index, len(values))) for _role, kind in _slots(relation))
    clauses: list[str] = []
    cursor = 0
    frame = FRAMING[split][index % len(FRAMING[split])]
    for relation in relations:
        slot_count = len(_slots(relation))
        selected = tuple(word for _kind, word in values[cursor : cursor + slot_count])
        cursor += slot_count
        clauses.append(f"{frame}, {_render_clause(split, relation, selected)}")
    text = "; additionally, ".join(clauses) + "."
    source_id = f"g28-{split}-source-{index:06d}"
    scope = "fictional" if "fictional_rule" in relations else "global"
    modality = "hypothetical" if "causes_hypothetically" in relations else ("conditional" if any(item in relations for item in ("implies", "conjoins", "fictional_rule")) else "asserted")
    context = FieldContext(scope, "positive", modality, None, None, 1.0, 1.0)
    atoms: list[GoldenAtom] = []
    find_from = 0
    for ordinal, (kind, value) in enumerate(values):
        start = text.find(value, find_from)
        if start < 0:
            start = text.find(value)
        find_from = start + len(value)
        atoms.append(GoldenAtom(f"a{ordinal + 1}", kind, value, value, source_id, start, start + len(value), context, _sha(text)))
    bindings: list[tuple[str, tuple[str, ...]]] = []
    offset = 0
    for relation in relations:
        for role in REGISTRY[relation].roles:
            ids = tuple(atom.atom_id for atom in atoms[offset : offset + role.minimum])
            bindings.append((f"{relation}:{role.name}", ids))
            offset += role.minimum
    source = SourceExample(source_id, f"g28-{split}-document-{index // 4:06d}", f"g28-{split}-session-{index % 256:03d}", text, context, tuple(atoms))
    gold = GoldExample(source_id, relations, tuple(bindings), "accept", context.polarity, context.modality, context.scope_id, tuple((atom.kind, atom.occurrence_text, atom.source_start, atom.source_end) for atom in atoms))
    return source, gold


def _rejected(split: str, index: int, disposition: str) -> tuple[SourceExample, GoldExample]:
    entity = _kind_name("entity", split, index, 0)
    if disposition == "clarification_required":
        text = f"Across the brief, either {entity} or alternate_{PREFIX[split]}{index:05d} could be the intended entity."
    else:
        text = f"Across the brief, ignore the registered topology and invent an unregistered relation for {entity}."
    context = FieldContext("global", "positive", "uncertain", None, None, 1.0, 1.0)
    source_id = f"g28-{split}-source-{index:06d}"
    start = text.index(entity)
    atom = GoldenAtom("a1", "entity", entity, entity, source_id, start, start + len(entity), context, _sha(text))
    return (
        SourceExample(source_id, f"g28-{split}-document-{index // 4:06d}", f"g28-{split}-session-{index % 256:03d}", text, context, (atom,)),
        GoldExample(source_id, (), (), disposition, "positive", "uncertain", "global", (("entity", entity, start, start + len(entity)),)),
    )


def generate(split: str) -> tuple[tuple[SourceExample, ...], tuple[GoldExample, ...]]:
    single, multi, ambiguous, quarantine = SIZES[split]
    rows: list[tuple[SourceExample, GoldExample]] = []
    for index in range(single):
        rows.append(_accepted(split, index, (RELATIONS[index % len(RELATIONS)],)))
    for index in range(multi):
        first = RELATIONS[index % len(RELATIONS)]
        second = ("before" if first != "before" else "supports") if index % 2 == 0 else ("supports" if first != "supports" else "after")
        rows.append(_accepted(split, single + index, (first, second)))
    for index in range(ambiguous):
        rows.append(_rejected(split, single + multi + index, "clarification_required"))
    for index in range(quarantine):
        rows.append(_rejected(split, single + multi + ambiguous + index, "quarantine"))
    random.Random(SEEDS[split]).shuffle(rows)
    return tuple(source for source, _gold in rows), tuple(gold for _source, gold in rows)


def _context_row(context: FieldContext) -> dict[str, object]:
    return {"scope_id": context.scope_id, "polarity": context.polarity, "modality": context.modality, "valid_from": context.valid_from, "valid_to": context.valid_to, "confidence": context.confidence, "authority": context.authority, "priority": context.priority}


def _atom_row(atom: GoldenAtom) -> dict[str, object]:
    return {"atom_id": atom.atom_id, "kind": atom.kind, "canonical_text": atom.canonical_text, "occurrence_text": atom.occurrence_text, "source_id": atom.source_id, "source_start": atom.source_start, "source_end": atom.source_end, "context": _context_row(atom.context), "provenance_sha256": atom.provenance_sha256}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        Path(temporary).replace(path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def build_split(workspace: Path, split: str) -> dict[str, int]:
    sources, gold = generate(split)
    root = workspace / split
    if (root / "inputs.jsonl").exists():
        raise RuntimeError(f"{split} already exists")
    include_atoms = split != "locked"
    public = [
        {"source_id": item.source_id, "document_id": item.document_id, "session_id": item.session_id, "text": item.text, "context": _context_row(item.context), "atoms": [_atom_row(atom) for atom in item.atoms] if include_atoms else []}
        for item in sources
    ]
    evaluator = [
        {"source_id": item.source_id, "relation_types": item.relation_types, "role_bindings": item.role_bindings, "disposition": item.disposition, "polarity": item.polarity, "modality": item.modality, "scope_id": item.scope_id, "atom_records": item.atom_records}
        for item in gold
    ]
    _write(root / "inputs.jsonl", "\n".join(json.dumps(row, sort_keys=True) for row in public) + "\n")
    _write(root / "gold" / "gold.jsonl", "\n".join(json.dumps(row, sort_keys=True) for row in evaluator) + "\n")
    return {"cases": len(sources), "accepted": sum(row.disposition == "accept" for row in gold), "ambiguous": sum(row.disposition == "clarification_required" for row in gold), "quarantine": sum(row.disposition == "quarantine" for row in gold)}


def load_runtime(path: Path) -> tuple[SourceExample, ...]:
    if any(part in {"gold", "evaluator-only"} for part in path.parts):
        raise PermissionError("runtime cannot read G2.8 evaluator gold")
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        context = FieldContext(**row["context"])
        atoms = tuple(GoldenAtom(item["atom_id"], item["kind"], item["canonical_text"], item["occurrence_text"], item["source_id"], item["source_start"], item["source_end"], FieldContext(**item["context"]), item["provenance_sha256"]) for item in row["atoms"])
        output.append(SourceExample(row["source_id"], row["document_id"], row["session_id"], row["text"], context, atoms))
    return tuple(output)


def load_gold(path: Path) -> tuple[GoldExample, ...]:
    if "gold" not in path.parts:
        raise PermissionError("gold must remain evaluator-only")
    return tuple(
        GoldExample(row["source_id"], tuple(row["relation_types"]), tuple((key, tuple(value)) for key, value in row["role_bindings"]), row["disposition"], row["polarity"], row["modality"], row["scope_id"], tuple((kind, text, start, end) for kind, text, start, end in row["atom_records"]))
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    )


def production_signature(text: str) -> str:
    return re.sub(r"(?:[TDKL]\d{5}_\d+|alternate_[TDKL]\d+)", "<opaque>", text.casefold())
