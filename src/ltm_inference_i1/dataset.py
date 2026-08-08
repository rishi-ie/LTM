"""Split-disjoint body and query generation with hidden evaluator gold."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .schemas import AtomicMumbrane, ReasoningBody, body_hash
from .vectors import semantic_vector


def _stable(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _unit_id(split: str, index: int, phase: int, predicate: int, entity: int) -> str:
    return f"{split}:u:{index}:{phase}:{predicate}:{entity}"


def _make_body(split: str, index: int, entity: int, source_predicate: int, target_predicate: int, *, conjunction: bool = False) -> tuple[AtomicMumbrane, ...]:
    body_id = f"{split}:body:{index:06d}"
    source_predicates = (source_predicate, (source_predicate + 3) % 16) if conjunction else (source_predicate,)
    units: list[AtomicMumbrane] = []
    for local_index, predicate in enumerate(source_predicates):
        unit_id = _unit_id(split, index, 0, predicate, entity)
        units.append(AtomicMumbrane(
            unit_id, body_id, 0, local_index, 0, "positive", "observed", "global", None, None,
            f"entity:{entity}|predicate:{predicate}", f"source:{body_id}",
        ))
    target_id = _unit_id(split, index, 1, target_predicate, entity)
    units.append(AtomicMumbrane(
        target_id, body_id, 0, len(units), 1, "positive", "observed", "global", None, None,
        f"entity:{entity}|predicate:{target_predicate}", f"source:{body_id}",
    ))
    return tuple(units)


def generate_bodies(split: str, count: int, seed: int) -> tuple[ReasoningBody, tuple[AtomicMumbrane, ...], np.ndarray]:
    bodies: list[ReasoningBody] = []
    units: list[AtomicMumbrane] = []
    vectors: list[np.ndarray] = []
    for index in range(count):
        # Each entity receives a complete local transition vocabulary. This
        # makes multi-hop composition possible while keeping the chain itself
        # absent from any single body.
        # Keep the sixteen predicates for a given entity together.  This is
        # what makes an unseen multi-hop chain composable across separate
        # bodies; the split seed still gives each split a disjoint entity
        # namespace.
        entity = (index // 16 + seed * 17) % 100000
        source = index % 16
        target = (source + 1) % 16
        atom_units = _make_body(split, index, entity, source, target, conjunction=index % 11 == 0)
        start = len(units)
        for atom in atom_units:
            vector = semantic_vector(str(entity), str(atom.identity_key.split("|")[-1]), str(atom.phase_index))
            vectors.append(vector)
            units.append(atom.__class__(
                atom.unit_id, atom.body_id, len(vectors) - 1, atom.local_index, atom.phase_index,
                atom.polarity, atom.modality, atom.scope_key, atom.valid_from, atom.valid_to,
                atom.identity_key, atom.provenance_id,
            ))
        ids = tuple(item.unit_id for item in units[start:])
        bodies.append(ReasoningBody(body_id=atom_units[0].body_id, unit_ids=ids, phase_count=2, region_id=f"region:{index % 256}", source_id=f"source:{split}:{index}", body_hash=body_hash(ids, 2, f"region:{index % 256}")))
    return tuple(bodies), tuple(units), np.asarray(vectors, dtype=np.float32)


def generate_queries(split: str, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], count: int, seed: int) -> tuple[dict[str, object], ...]:
    rng = random.Random(seed)
    by_body = {body.body_id: body for body in bodies}
    by_id = {unit.unit_id: unit for unit in units}
    source_units = [unit for unit in units if unit.phase_index == 0]
    source_by_identity: dict[str, list[AtomicMumbrane]] = {}
    target_by_entity: dict[str, list[AtomicMumbrane]] = {}
    for unit in units:
        if unit.phase_index == 0:
            source_by_identity.setdefault(unit.identity_key, []).append(unit)
        else:
            entity_key = unit.identity_key.split("|")[0]
            target_by_entity.setdefault(entity_key, []).append(unit)
    queries: list[dict[str, object]] = []
    for index in range(count):
        first = source_units[(index * 13 + rng.randrange(len(source_units))) % len(source_units)]
        chain_depth = 1 + (index % 6)
        entity = first.identity_key.split("|")[0].split(":")[-1]
        predicate = int(first.identity_key.split(":")[-1])
        current = predicate
        target = first
        required: list[str] = []
        for depth in range(chain_depth):
            candidates = source_by_identity.get(f"entity:{entity}|predicate:{current}", [])
            if not candidates:
                break
            source = candidates[0]
            body = by_body[source.body_id]
            required.append(body.body_id)
            destinations = [by_id[item] for item in body.unit_ids if by_id[item].phase_index == 1]
            if not destinations:
                break
            target = destinations[0]
            current = int(target.identity_key.split(":")[-1])
        # Ten percent of prompts are intentionally unsupported and must be
        # rejected rather than converted into a false candidate.
        answerable = index % 10 != 0 and len(required) >= chain_depth
        candidate_ids = [unit.unit_id for unit in target_by_entity.get(f"entity:{entity}", [])]
        if target.unit_id not in candidate_ids:
            candidate_ids.append(target.unit_id)
        # Preserve candidate recall even when an entity has more than the
        # bounded public candidate budget.  The target is never silently
        # truncated out of the evaluator-visible frontier.
        candidate_list = list(dict.fromkeys(candidate_ids))
        if target.unit_id not in candidate_list[:64]:
            candidate_list = candidate_list[:63] + [target.unit_id]
        candidate_ids = tuple(candidate_list[:64])
        queries.append({
            "prompt_id": f"{split}:query:{index:06d}",
            "clamped_unit_ids": (first.unit_id,),
            "candidate_atom_ids": candidate_ids,
            "scope_key": "global",
            "valid_at": None,
            "maximum_bodies": 32,
            "gold_candidate_id": target.unit_id if answerable else None,
            "required_body_ids": tuple(required),
            "depth": chain_depth,
            "answerable": answerable,
        })
    return tuple(queries)


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def build_split(root: Path, split: str, body_count: int, query_count: int, seed: int) -> dict[str, object]:
    bodies, units, vectors = generate_bodies(split, body_count, seed)
    queries = generate_queries(split, bodies, units, query_count, seed + 1)
    split_root = root / "datasets" / split
    split_root.mkdir(parents=True, exist_ok=True)
    np.save(split_root / "vectors.npy", vectors)
    _write_jsonl(split_root / "bodies.jsonl", tuple(asdict(item) for item in bodies))
    public_queries = tuple({key: value for key, value in query.items() if not key.startswith("gold_") and key != "required_body_ids"} for query in queries)
    gold_queries = tuple({"prompt_id": item["prompt_id"], "gold_candidate_id": item["gold_candidate_id"], "required_body_ids": item["required_body_ids"], "depth": item["depth"], "answerable": item["answerable"]} for item in queries)
    _write_jsonl(split_root / "units.jsonl", tuple(asdict(item) for item in units))
    _write_jsonl(split_root / "public.jsonl", public_queries)
    _write_jsonl(split_root / "gold.jsonl", gold_queries)
    return {"split": split, "bodies": body_count, "units": len(units), "queries": query_count, "vector_rows": len(vectors)}


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
