"""Controlled split-disjoint reasoning bodies and hidden query programs."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .schemas import AtomicMumbrane, ReasoningBody, body_hash
from .vectors import semantic_vector


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _unit_id(split: str, index: int, phase: int, state: int, entity: int, ordinal: int = 0) -> str:
    return f"{split}:u:{index}:{phase}:{state}:{entity}:{ordinal}"


def generate_bodies(split: str, count: int, seed: int) -> tuple[ReasoningBody, tuple[AtomicMumbrane, ...], np.ndarray]:
    bodies: list[ReasoningBody] = []
    units: list[AtomicMumbrane] = []
    vectors: list[np.ndarray] = []
    namespace = seed * 1000
    for index in range(count):
        entity = namespace + index // 64
        source_state = index % 64
        target_state = (source_state + 1) % 64
        body_id = f"{split}:body:{index:07d}"
        conjunction = index % 31 == 0
        source_states = (source_state, (source_state + 7) % 64) if conjunction else (source_state,)
        local: list[AtomicMumbrane] = []
        for ordinal, state in enumerate(source_states):
            local.append(AtomicMumbrane(
                _unit_id(split, index, 0, state, entity, ordinal), body_id, 0, ordinal, 0,
                "positive", "observed", "global", None, None,
                f"entity:{entity}|state:{state}", f"source:{body_id}",
            ))
        local.append(AtomicMumbrane(
            _unit_id(split, index, 1, target_state, entity), body_id, 0, len(local), 1,
            "positive", "observed", "global", None, None,
            f"entity:{entity}|state:{target_state}", f"source:{body_id}",
        ))
        start = len(units)
        for item in local:
            ref = len(vectors)
            vectors.append(semantic_vector(str(entity), int(item.identity_key.split("state:")[-1])))
            units.append(AtomicMumbrane(
                item.unit_id, item.body_id, ref, item.local_index, item.phase_index,
                item.polarity, item.modality, item.scope_key, item.valid_from, item.valid_to,
                item.identity_key, item.provenance_id,
            ))
        ids = tuple(unit.unit_id for unit in units[start:])
        region = f"region:{index % 256}"
        bodies.append(ReasoningBody(body_id, ids, 2, region, f"source:{split}:{index}", body_hash(ids, 2, region)))
    return tuple(bodies), tuple(units), np.asarray(vectors, dtype=np.float32)


def generate_queries(split: str, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], count: int, seed: int) -> tuple[dict[str, object], ...]:
    rng = random.Random(seed)
    by_body = {body.body_id: body for body in bodies}
    by_id = {unit.unit_id: unit for unit in units}
    source_by_key: dict[str, list[AtomicMumbrane]] = {}
    for unit in units:
        if unit.phase_index == 0:
            source_by_key.setdefault(unit.identity_key, []).append(unit)
    source_units = tuple(unit for unit in units if unit.phase_index == 0 and unit.local_index == 0)
    queries: list[dict[str, object]] = []
    for index in range(count):
        first = source_units[(index * 37 + rng.randrange(len(source_units))) % len(source_units)]
        depth = 1 + (index % 64)
        entity, state_text = first.identity_key.split("|")
        entity_id = entity.split(":")[-1]
        state = int(state_text.split(":")[-1])
        required: list[str] = []
        target: AtomicMumbrane | None = first
        current = state
        for _ in range(depth):
            choices = source_by_key.get(f"entity:{entity_id}|state:{current}", ())
            if not choices:
                target = None
                break
            source = choices[0]
            required.append(source.body_id)
            body = by_body[source.body_id]
            outputs = [by_id[item] for item in body.unit_ids if by_id[item].phase_index == 1]
            if not outputs:
                target = None
                break
            target = outputs[0]
            current = int(target.identity_key.split("state:")[-1])
        unsupported = index % 13 == 0
        ambiguous = not unsupported and index % 17 == 0
        answerable = not unsupported and not ambiguous and len(required) == depth
        queries.append({
            "prompt_id": f"{split}:query:{index:07d}",
            "clamped_unit_ids": (first.unit_id,),
            "scope_key": "global",
            "valid_at": None,
            "maximum_steps": 32,
            "maximum_bodies": 64,
            "depth": depth,
            "query_type": "ambiguous" if ambiguous else ("unknown" if unsupported else "answerable"),
            "gold_candidate_id": target.unit_id if answerable else None,
            "required_body_ids": tuple(required),
        })
    return tuple(queries)


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_split(root: Path, split: str, body_count: int, query_count: int, seed: int) -> dict[str, object]:
    bodies, units, vectors = generate_bodies(split, body_count, seed)
    queries = generate_queries(split, bodies, units, query_count, seed + 1) if query_count else ()
    split_root = root / "datasets" / split
    split_root.mkdir(parents=True, exist_ok=True)
    np.save(split_root / "vectors.npy", vectors)
    _write_jsonl(split_root / "bodies.jsonl", tuple(asdict(body) for body in bodies))
    _write_jsonl(split_root / "units.jsonl", tuple(asdict(unit) for unit in units))
    public = tuple({key: value for key, value in query.items() if key not in {"gold_candidate_id", "required_body_ids"}} for query in queries)
    gold = tuple({key: value for key, value in query.items() if key in {"prompt_id", "gold_candidate_id", "required_body_ids", "depth", "query_type"}} for query in queries)
    _write_jsonl(split_root / "public.jsonl", public)
    _write_jsonl(split_root / "gold.jsonl", gold)
    return {"split": split, "bodies": body_count, "units": len(units), "queries": query_count, "vector_rows": len(vectors), "sha256": hashlib.sha256((split_root / "bodies.jsonl").read_bytes()).hexdigest()}
