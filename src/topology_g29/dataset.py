"""Semantic-program-first data for G2.9 with strict public/gold separation."""

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
    "train": (14_400, 4_800, 2_400, 2_400),
    "development": (2_160, 720, 360, 360),
    "kernel_locked": (2_160, 720, 360, 360),
    "locked": (3_600, 1_200, 600, 600),
}
SEEDS = {"train": 1790, "development": 1791, "kernel_locked": 20260910, "locked": 20260911}
PREFIX = {"train": "T", "development": "D", "kernel_locked": "K", "locked": "L"}

# Each split uses separate constructions.  Challenge forms are a second,
# independently worded bank selected for 20% of each accepted split.
PHRASES = {
    "train": ("entails", "together establish", "requires", "excludes", "equals", "precedes", "follows", "supersedes", "supports", "opposes", "prefers", "refers to", "is scoped to", "would imply", "could cause", "leaves uncertain", "assistant-derived from", "derived from"),
    "development": ("therefore establishes", "jointly demonstrate", "depends on", "is incompatible with", "matches", "happens before", "comes after", "replaces", "corroborates", "contradicts", "chooses", "identifies", "applies within", "would establish", "might produce", "does not settle", "traces to assistant evidence", "originates from"),
    "kernel_locked": ("makes necessary", "when combined yields", "cannot proceed without", "rules out", "is equivalent to", "occurs prior to", "occurs subsequent to", "overrides", "lends support to", "counts against", "favours", "designates", "is confined to", "in fiction entails", "might lead to", "remains unresolved about", "has assistant provenance from", "is sourced from"),
    "locked": ("consequently gives", "in combination proves", "has as a condition", "prevents coexistence with", "has the same value as", "comes ahead of", "comes later than", "displaces", "is evidence in favour of", "is evidence against", "opts for", "names", "holds only in", "fictionally gives", "may result in", "cannot determine", "uses assistant material from", "was obtained from"),
}
CHALLENGE = {
    "train": ("forces", "both warrant", "needs first", "bars", "coincides with", "is earlier than", "is later than", "takes priority over", "backs", "rebuts", "selects", "points toward", "belongs only to", "would follow from", "can bring about", "keeps open", "cites an assistant derivation from", "has provenance in"),
    "development": ("compels", "collectively justify", "has a prerequisite", "cannot share a state with", "is identical to", "is temporally earlier than", "is temporally later than", "takes the place of", "adds support for", "weighs against", "marks as preferred", "resolves to", "is bounded by", "would follow", "can hypothetically yield", "does not resolve", "records assistant derivation from", "was derived from"),
    "kernel_locked": ("licenses", "as a set establish", "needs completion of", "forbids", "has an equal interpretation to", "is first relative to", "is second relative to", "becomes current instead of", "is corroboration for", "is opposition to", "ranks above", "has reference to", "has applicability limited by", "in a story would follow", "is a possible cause of", "is indeterminate regarding", "has assistant lineage from", "has derivation lineage from"),
    "locked": ("necessitates", "taken together prove", "relies on", "is mutually exclusive with", "has identical meaning to", "appears earlier than", "appears later than", "is the newer replacement for", "provides corroboration of", "provides counterevidence to", "ranks", "has the referent", "is valid solely under", "would follow in a fiction", "is a hypothetical producer of", "is unresolved with respect to", "was assistant-derived using", "has its source in"),
}
RELATION_INDEX = {relation: index for index, relation in enumerate(RELATIONS)}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slots(relation: str) -> tuple[tuple[str, str], ...]:
    return tuple((role.name, kind.value) for role in REGISTRY[relation].roles for kind in (role.allowed_kinds[0],) * role.minimum)


def _atom_text(kind: str, split: str, index: int, ordinal: int) -> str:
    # Prefixing the ontology kind makes generated source spans grounded without
    # turning the relation itself into a phrase-table decision.
    return f"{kind}_{PREFIX[split]}{index:05d}_{ordinal}"


def _render(relation: str, words: tuple[str, ...], phrase: str) -> str:
    if relation == "conjoins":
        return f"{words[0]} and {words[1]} {phrase} {words[2]}"
    if relation == "fictional_rule":
        return f"within {words[2]}, {words[0]} {phrase} {words[1]}"
    if relation == "supersedes":
        return f"{words[1]} {phrase} {words[0]}"
    return f"{words[0]} {phrase} {words[1]}"


def _accepted(split: str, index: int, relations: tuple[str, ...], challenge: bool) -> tuple[SourceExample, GoldExample]:
    values: list[tuple[str, str]] = []
    for relation in relations:
        values.extend((kind, _atom_text(kind, split, index, len(values))) for _role, kind in _slots(relation))
    phrases = CHALLENGE[split] if challenge else PHRASES[split]
    clauses: list[str] = []
    cursor = 0
    for relation in relations:
        count = len(_slots(relation))
        phrase = phrases[RELATION_INDEX[relation]]
        clauses.append(_render(relation, tuple(value for _kind, value in values[cursor:cursor + count]), phrase))
        cursor += count
    text = "; moreover, ".join(clauses) + "."
    source_id = f"g29-{split}-source-{index:06d}"
    scope = "fictional" if "fictional_rule" in relations else "global"
    modality = "hypothetical" if "causes_hypothetically" in relations else ("conditional" if any(item in relations for item in ("implies", "conjoins", "fictional_rule")) else "asserted")
    context = FieldContext(scope, "positive", modality, None, None, 1.0, 1.0)
    atoms: list[GoldenAtom] = []
    start_at = 0
    for ordinal, (kind, value) in enumerate(values):
        start = text.find(value, start_at)
        if start < 0:
            start = text.find(value)
        start_at = start + len(value)
        atoms.append(GoldenAtom(f"a{ordinal + 1}", kind, value, value, source_id, start, start + len(value), context, _digest(text)))
    bindings: list[tuple[str, tuple[str, ...]]] = []
    atom_offset = 0
    for relation in relations:
        for role in REGISTRY[relation].roles:
            bindings.append((f"{relation}:{role.name}", tuple(item.atom_id for item in atoms[atom_offset:atom_offset + role.minimum])))
            atom_offset += role.minimum
    source = SourceExample(source_id, f"g29-{split}-doc-{index // 4:06d}", f"g29-{split}-session-{index % 256:03d}", text, context, tuple(atoms))
    gold = GoldExample(source_id, relations, tuple(bindings), "accept", context.polarity, context.modality, context.scope_id, tuple((atom.kind, atom.occurrence_text, atom.source_start, atom.source_end) for atom in atoms))
    return source, gold


def _rejected(split: str, index: int, disposition: str) -> tuple[SourceExample, GoldExample]:
    entity = _atom_text("entity", split, index, 0)
    text = (f"Either {entity} or alternative_{PREFIX[split]}{index:05d} may be the intended entity."
            if disposition == "clarification_required" else f"Ignore the topology and manufacture an unregistered relation for {entity}.")
    source_id = f"g29-{split}-source-{index:06d}"
    context = FieldContext("global", "positive", "uncertain", None, None, 1.0, 1.0)
    start = text.index(entity)
    atom = GoldenAtom("a1", "entity", entity, entity, source_id, start, start + len(entity), context, _digest(text))
    return SourceExample(source_id, f"g29-{split}-doc-{index // 4:06d}", f"g29-{split}-session-{index % 256:03d}", text, context, (atom,)), GoldExample(source_id, (), (), disposition, "positive", "uncertain", "global", (("entity", entity, start, start + len(entity)),))


def generate(split: str) -> tuple[tuple[SourceExample, ...], tuple[GoldExample, ...]]:
    single, multi, ambiguous, quarantine = SIZES[split]
    rows: list[tuple[SourceExample, GoldExample]] = []
    for index in range(single):
        rows.append(_accepted(split, index, (RELATIONS[index % len(RELATIONS)],), index % 5 == 0))
    for index in range(multi):
        first = RELATIONS[index % len(RELATIONS)]
        second = ("before" if first != "before" else "supports") if index % 2 == 0 else ("supports" if first != "supports" else "after")
        rows.append(_accepted(split, single + index, (first, second), (single + index) % 5 == 0))
    rows.extend(_rejected(split, single + multi + index, "clarification_required") for index in range(ambiguous))
    rows.extend(_rejected(split, single + multi + ambiguous + index, "quarantine") for index in range(quarantine))
    random.Random(SEEDS[split]).shuffle(rows)
    return tuple(item[0] for item in rows), tuple(item[1] for item in rows)


def _context_row(context: FieldContext) -> dict[str, object]:
    return {"scope_id": context.scope_id, "polarity": context.polarity, "modality": context.modality, "valid_from": context.valid_from, "valid_to": context.valid_to, "confidence": context.confidence, "authority": context.authority, "priority": context.priority}


def _atom_row(atom: GoldenAtom) -> dict[str, object]:
    return {"atom_id": atom.atom_id, "kind": atom.kind, "canonical_text": atom.canonical_text, "occurrence_text": atom.occurrence_text, "source_id": atom.source_id, "source_start": atom.source_start, "source_end": atom.source_end, "context": _context_row(atom.context), "provenance_sha256": atom.provenance_sha256}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        Path(temporary).replace(path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def build_split(workspace: Path, split: str) -> dict[str, int]:
    root = workspace / split
    if (root / "inputs.jsonl").exists():
        raise RuntimeError(f"{split} already exists")
    sources, gold = generate(split)
    # Kernel development and the kernel locked suite provide gold spans.  Raw
    # full locked inputs intentionally do not.
    include_atoms = split != "locked"
    public = ({"source_id": source.source_id, "document_id": source.document_id, "session_id": source.session_id, "text": source.text, "context": _context_row(source.context), "atoms": [_atom_row(atom) for atom in source.atoms] if include_atoms else []} for source in sources)
    evaluator = ({"source_id": item.source_id, "relation_types": item.relation_types, "role_bindings": item.role_bindings, "disposition": item.disposition, "polarity": item.polarity, "modality": item.modality, "scope_id": item.scope_id, "atom_records": item.atom_records} for item in gold)
    _atomic_write(root / "inputs.jsonl", "\n".join(json.dumps(item, sort_keys=True) for item in public) + "\n")
    _atomic_write(root / "gold" / "gold.jsonl", "\n".join(json.dumps(item, sort_keys=True) for item in evaluator) + "\n")
    return {"cases": len(sources), "accepted": sum(item.disposition == "accept" for item in gold), "ambiguous": sum(item.disposition == "clarification_required" for item in gold), "quarantine": sum(item.disposition == "quarantine" for item in gold)}


def load_runtime(path: Path) -> tuple[SourceExample, ...]:
    if any(part in {"gold", "evaluator-only"} for part in path.parts):
        raise PermissionError("runtime cannot read evaluator gold")
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        atoms = tuple(GoldenAtom(item["atom_id"], item["kind"], item["canonical_text"], item["occurrence_text"], item["source_id"], item["source_start"], item["source_end"], FieldContext(**item["context"]), item["provenance_sha256"]) for item in row["atoms"])
        output.append(SourceExample(row["source_id"], row["document_id"], row["session_id"], row["text"], FieldContext(**row["context"]), atoms))
    return tuple(output)


def load_gold(path: Path) -> tuple[GoldExample, ...]:
    if "gold" not in path.parts:
        raise PermissionError("gold must stay evaluator-only")
    return tuple(GoldExample(row["source_id"], tuple(row["relation_types"]), tuple((key, tuple(value)) for key, value in row["role_bindings"]), row["disposition"], row["polarity"], row["modality"], row["scope_id"], tuple((kind, text, start, end) for kind, text, start, end in row["atom_records"])) for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()))


def production_signature(text: str) -> str:
    return re.sub(r"(?:[TDKL]\\d{5}_\\d+|alternative_[TDKL]\\d+)", "<opaque>", text.casefold())
