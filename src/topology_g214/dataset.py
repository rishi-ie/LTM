from __future__ import annotations

import json
import random
from dataclasses import asdict, replace
from pathlib import Path

from topology_g213.dataset import generate as generate_g213
from topology_g213.schemas import ConversationCase, ConversationSpan, ConversationTurnSource

from .schemas import GateCandidate, GateCase

SIZES = {"calibration": (800, 400, 400, 400, 200, 200), "locked": (1600, 800, 800, 800, 400, 400)}


def _fresh_case(case: ConversationCase, split: str, index: int) -> ConversationCase:
    source_id = f"g214-{split}-{index:05d}"
    source = ConversationTurnSource(source_id, f"g214-session:{index % 97}", f"g214-episode:{index % 31}", index % 12, "user", case.source.text, case.source.source_hash)
    spans = tuple(replace(span, span_id=span.span_id.replace(case.source.source_id, source_id)) for span in case.spans)
    return replace(case, source=source, spans=spans)


def _candidates(case: ConversationCase, index: int) -> tuple[GateCandidate, ...]:
    link_span = next((span for span in case.spans if span.slot_type in {"reference", "correction"}), None)
    alias = link_span.text if link_span else f"unused_{index}"
    target = case.target_id or f"object:{alias}"
    values: list[GateCandidate] = []
    if case.reference_state == "ambiguous":
        values.extend((GateCandidate(f"ambiguous:{index}:a", "entity", alias, case.source.session_id, case.source.episode_id, "session", True, False, False, False, 1), GateCandidate(f"ambiguous:{index}:b", "entity", alias, case.source.session_id, case.source.episode_id, "session", True, False, False, False, 2)))
    elif case.reference_state == "unique" or case.action in {"correct", "retract"}:
        kind = "claim" if case.action in {"correct", "retract"} else "entity"
        values.append(GateCandidate(target, kind, alias, case.source.session_id, case.source.episode_id, "session", True, False, False, False, 1))
    for offset in range(1, 16 - len(values)):
        values.append(GateCandidate(f"decoy:{index}:{offset}", "entity", f"decoy_{index}_{offset}", case.source.session_id if offset % 3 else f"other:{offset}", case.source.episode_id, "session" if offset % 4 else "fictional", offset < 12, offset == 12, offset == 13, offset == 14, offset))
    return tuple(values[:16])


def generate(split: str) -> tuple[GateCase, ...]:
    counts = SIZES[split]
    cases = generate_g213("development") if split == "calibration" else generate_g213("locked") + generate_g213("development")[:1200]
    total = sum(counts)
    selected = [_fresh_case(case, split, index) for index, case in enumerate(cases[:total])]
    random.Random(1850 if split == "calibration" else 20261220).shuffle(selected)
    return tuple(GateCase(case, _candidates(case, index)) for index, case in enumerate(selected))


def _public(item: GateCase) -> dict[str, object]:
    return {"source": asdict(item.case.source), "text": item.case.source.text, "spans": [asdict(span) for span in item.case.spans], "candidates": [asdict(candidate) for candidate in item.candidates]}


def _gold(item: GateCase) -> dict[str, object]:
    case = item.case
    return {"source_id": case.source.source_id, "act": case.act, "action": case.action, "reference_state": case.reference_state, "polarity": case.polarity, "modality": case.modality, "scope_id": case.scope_id, "disposition": case.disposition, "target_id": case.target_id}


def build_split(workspace: Path, split: str) -> dict[str, int]:
    root = workspace / "datasets" / split
    root.mkdir(parents=True, exist_ok=True)
    cases = generate(split)
    (root / "public.jsonl").write_text("\n".join(json.dumps(_public(item), sort_keys=True) for item in cases) + "\n", encoding="utf-8")
    (root / "gold.jsonl").write_text("\n".join(json.dumps(_gold(item), sort_keys=True) for item in cases) + "\n", encoding="utf-8")
    return {"cases": len(cases), "maximum_candidates": max(len(item.candidates) for item in cases)}


def load_split(path: Path) -> tuple[GateCase, ...]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    cases = []
    for row in rows:
        source = ConversationTurnSource(**row["source"])
        spans = tuple(ConversationSpan(**span) for span in row["spans"])
        case = ConversationCase(source, spans, "statement", "none", "none", "positive", "asserted", "session", "accept")
        candidates = tuple(GateCandidate(**candidate) for candidate in row["candidates"])
        cases.append(GateCase(case, candidates))
    return tuple(cases)


def load_gold(path: Path) -> dict[str, dict[str, object]]:
    return {row["source_id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)}
