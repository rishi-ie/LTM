"""Semantic-program-first, split-disjoint G2.10 data."""

from __future__ import annotations

import hashlib
import json
import random
import tempfile
from dataclasses import asdict
from pathlib import Path

from .schemas import GoldExample, PublicAtom, SourceExample
from .topology import CELLS

SIZES = {
    "train": (18_000, 2_250, 2_250),
    "development": (3_600, 450, 450),
    "kernel_locked": (3_600, 450, 450),
    "locked": (3_600, 450, 450),
}
SEEDS = {"train": 1800, "development": 1801, "kernel_locked": 20260920, "locked": 20260921}
PREFIX = {"train": "T", "development": "D", "kernel_locked": "K", "locked": "L"}

# A split owns its language; opaque atoms ensure that word identity cannot leak.
PHRASES = {
    "train": (("entails", "requires", "backs", "rebuts", "leaves uncertain", "matches", "rules out", "precedes", "supersedes"), ("forces", "needs", "corroborates", "counts against", "keeps open", "equals", "excludes", "comes before", "replaces")),
    "development": (("therefore establishes", "depends on", "corroborates", "contradicts", "does not settle", "is equivalent to", "cannot coexist with", "happens before", "takes precedence over"), ("makes necessary", "has a prerequisite", "adds support for", "weighs against", "remains unresolved about", "has identical value to", "bars", "is earlier than", "displaces")),
    "kernel_locked": (("licenses", "cannot proceed without", "lends support to", "is opposition to", "is indeterminate regarding", "has an equal interpretation to", "forbids", "is first relative to", "becomes current instead of"), ("consequently gives", "relies on", "is corroboration for", "provides counterevidence to", "keeps the status unknown for", "coincides with", "prevents coexistence with", "appears earlier than", "overrides")),
    "locked": (("necessitates", "relies on", "provides corroboration of", "provides counterevidence to", "leaves unresolved", "has identical meaning to", "is mutually exclusive with", "appears prior to", "is the newer replacement for"), ("compels", "needs completion of", "offers evidence for", "offers evidence against", "does not determine", "is equal in value to", "rules out", "comes ahead of", "takes the place of")),
}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _cell_index(cell_id: str) -> int:
    return next(index for index, cell in enumerate(CELLS) if cell.cell_id == cell_id)


def _kinds(cell_id: str) -> tuple[str, str]:
    if cell_id == "precedes":
        return "event", "event"
    if cell_id == "constraint.equal":
        return "value", "value"
    return "claim", "claim"


def _context(split: str, index: int, body: str) -> tuple[str, str, str]:
    fictional = index % 4 in {1, 3}
    conditional = index % 4 in {2, 3}
    prefix = "Within the fictional scenario, " if fictional else "Globally, "
    if conditional:
        prefix += "if stated, "
    return prefix + body, "fictional" if fictional else "global", "conditional" if conditional else "asserted"


def _accepted(split: str, index: int, cell_id: str) -> tuple[SourceExample, GoldExample]:
    cell = next(item for item in CELLS if item.cell_id == cell_id)
    first_kind, second_kind = _kinds(cell_id)
    first = f"{first_kind}_{PREFIX[split]}{index:05d}_a"
    second = f"{second_kind}_{PREFIX[split]}{index:05d}_b"
    surface_after = cell_id == "precedes" and index % 2 == 1
    rendered_left, rendered_right = (second, first) if surface_after else (first, second)
    relation_word = "after" if surface_after else PHRASES[split][index % len(PHRASES[split])][_cell_index(cell_id)]
    text, scope, modality = _context(split, index, f"{rendered_left} {relation_word} {rendered_right}.")
    source_id = f"g210-{split}-{index:06d}"
    source_hash = _hash(text)
    atoms = (
        PublicAtom("a1", first_kind, first, text.index(first), text.index(first) + len(first), source_hash),
        PublicAtom("a2", second_kind, second, text.index(second), text.index(second) + len(second), source_hash),
    )
    # "second after first" normalizes to before(first, second): the original
    # atom identities, not source order, define the canonical ports.
    ids = ("a1", "a2")
    if cell.symmetric:
        ids = tuple(sorted(ids))
    return (
        SourceExample(source_id, text, atoms, source_hash),
        GoldExample(source_id, cell_id, ids, scope, modality, "accept", "after" if surface_after else cell.relation_type, tuple((atom.kind, atom.text, atom.start, atom.end) for atom in atoms)),
    )


def _rejected(split: str, index: int, disposition: str) -> tuple[SourceExample, GoldExample]:
    left = f"claim_{PREFIX[split]}{index:05d}_a"; right = f"claim_{PREFIX[split]}{index:05d}_b"
    body = f"{left} may support or oppose {right}." if disposition == "clarification_required" else f"{left} invents an unregistered topology relation for {right}."
    text, _scope, _modality = _context(split, index, body)
    source_id = f"g210-{split}-{index:06d}"; digest = _hash(text)
    atoms = (
        PublicAtom("a1", "claim", left, text.index(left), text.index(left) + len(left), digest),
        PublicAtom("a2", "claim", right, text.index(right), text.index(right) + len(right), digest),
    )
    return SourceExample(source_id, text, atoms, digest), GoldExample(source_id, None, (), "global", "asserted", disposition, None, tuple((atom.kind, atom.text, atom.start, atom.end) for atom in atoms))


def generate(split: str) -> tuple[tuple[SourceExample, ...], tuple[GoldExample, ...]]:
    accepted, ambiguous, quarantine = SIZES[split]
    rows = [_accepted(split, index, CELLS[index % len(CELLS)].cell_id) for index in range(accepted)]
    rows.extend(_rejected(split, accepted + index, "clarification_required") for index in range(ambiguous))
    rows.extend(_rejected(split, accepted + ambiguous + index, "quarantine") for index in range(quarantine))
    random.Random(SEEDS[split]).shuffle(rows)
    return tuple(item[0] for item in rows), tuple(item[1] for item in rows)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name); handle.write(text)
    temporary.replace(path)


def build_split(workspace: Path, split: str) -> dict[str, int]:
    root = workspace / split
    if (root / "inputs.jsonl").exists():
        raise RuntimeError(f"{split} already exists")
    sources, gold = generate(split)
    include_atoms = split != "locked"
    public = (
        {"source_id": item.source_id, "text": item.text, "source_hash": item.source_hash, "atoms": [asdict(atom) for atom in item.atoms] if include_atoms else []}
        for item in sources
    )
    _write(root / "inputs.jsonl", "\n".join(json.dumps(item, sort_keys=True) for item in public) + "\n")
    _write(root / "gold" / "gold.jsonl", "\n".join(json.dumps(asdict(item), sort_keys=True) for item in gold) + "\n")
    return {"cases": len(sources), "accepted": accepted_count(gold), "ambiguous": sum(item.disposition == "clarification_required" for item in gold), "quarantine": sum(item.disposition == "quarantine" for item in gold)}


def accepted_count(gold: tuple[GoldExample, ...]) -> int:
    return sum(item.disposition == "accept" for item in gold)


def load_runtime(path: Path) -> tuple[SourceExample, ...]:
    if "gold" in path.parts:
        raise PermissionError("runtime cannot read evaluator gold")
    rows = []
    for line in path.read_text().splitlines():
        item = json.loads(line)
        rows.append(SourceExample(item["source_id"], item["text"], tuple(PublicAtom(**atom) for atom in item["atoms"]), item["source_hash"]))
    return tuple(rows)


def load_gold(path: Path) -> tuple[GoldExample, ...]:
    if "gold" not in path.parts:
        raise PermissionError("gold must stay evaluator-only")
    rows = []
    for line in path.read_text().splitlines():
        item = json.loads(line)
        rows.append(
            GoldExample(
                item["source_id"],
                item["cell_id"],
                tuple(item["atom_ids"]),
                item["scope_id"],
                item["modality"],
                item["disposition"],
                item["surface_relation"],
                tuple((kind, text, start, end) for kind, text, start, end in item["atom_records"]),
            )
        )
    return tuple(rows)


def production_signature(text: str) -> str:
    import re

    return re.sub(r"(?:[TDKL]\d{5}_[ab])", "<opaque>", text.casefold())
