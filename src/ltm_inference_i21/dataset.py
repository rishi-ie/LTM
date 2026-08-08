"""Split-disjoint observed transition bodies for I2.1."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ltm_inference_i2.vectors import semantic_vector

from .schemas import AtomicMumbrane, ReasoningBody

# There are 64 observed transitions (0->1 through 63->64) per entity.
CHAIN_LENGTH = 65


def _hash(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _identity(entity: int, state: int) -> str:
    return f"entity:{entity}|state:{state}"


def generate_bodies(split: str, count: int, seed: int) -> tuple[tuple[ReasoningBody, ...], tuple[AtomicMumbrane, ...], np.ndarray]:
    """Each body is an observed phase-0 to phase-1 state change, never a rule."""
    bodies: list[ReasoningBody] = []
    units: list[AtomicMumbrane] = []
    vectors: list[np.ndarray] = []
    namespace = seed * 1000
    for index in range(count):
        entity = namespace + index // (CHAIN_LENGTH - 1)
        outcome_entity = entity + 1
        state = index % (CHAIN_LENGTH - 1)
        # A path must retain one applicability context while it crosses leaves.
        scope = "global"
        body_id = f"{split}:body:{index:07d}"
        unit_ids: list[str] = []
        for phase, item_entity, state_value in ((0, entity, state), (1, outcome_entity, state + 1)):
            unit_id = f"{split}:unit:{index:07d}:{phase}"
            unit_ids.append(unit_id)
            vectors.append(semantic_vector(str(item_entity), state_value, scope=scope))
            units.append(AtomicMumbrane(
                unit_id=unit_id,
                body_id=body_id,
                semantic_vector_ref=len(vectors) - 1,
                local_index=phase,
                phase_index=phase,
                polarity="positive",
                modality="observed",
                scope_key=scope,
                identity_key=_identity(item_entity, state_value),
                provenance_id=f"source:{body_id}",
            ))
        bodies.append(ReasoningBody(body_id, tuple(unit_ids), scope, f"source:{split}:{index}", _hash((body_id, tuple(unit_ids), scope))))
    return tuple(bodies), tuple(units), np.asarray(vectors, dtype=np.float32)


def _entity(identity: str) -> str:
    return identity.split("|", 1)[0]


def generate_queries(split: str, bodies: tuple[ReasoningBody, ...], units: tuple[AtomicMumbrane, ...], count: int, seed: int) -> tuple[dict[str, object], ...]:
    """Public rows contain no answer/candidate/path identifiers; gold rows do."""
    rng = random.Random(seed)
    by_unit = {unit.unit_id: unit for unit in units}
    source_by_identity = {unit.identity_key: unit for unit in units if unit.phase_index == 0}
    output_by_body = {body.body_id: next(by_unit[item] for item in body.unit_ids if by_unit[item].phase_index == 1) for body in bodies}
    terminal_units = tuple(unit for unit in units if unit.phase_index == 1 and unit.identity_key.endswith("state:64"))
    maximum_entity = max(int(_entity(unit.identity_key).split(":", 1)[1]) for unit in source_by_identity.values())
    rows: list[dict[str, object]] = []
    for index in range(count):
        unknown = index % 13 == 0
        depth = 1 + (index % 64)
        if unknown:
            initial = terminal_units[(index * 53 + rng.randrange(len(terminal_units))) % len(terminal_units)]
        else:
            start_state = CHAIN_LENGTH - 1 - depth
            # Reserve enough successive entity leaves for the entire terminal path.
            eligible = tuple(
                unit for unit in source_by_identity.values()
                if unit.identity_key.endswith(f"state:{start_state}")
                and int(_entity(unit.identity_key).split(":", 1)[1]) + depth <= maximum_entity
            )
            initial = eligible[(index * 53 + rng.randrange(len(eligible))) % len(eligible)]
        current = initial
        required: list[str] = []
        target: AtomicMumbrane | None = None
        for _ in range(depth):
            source = source_by_identity.get(current.identity_key)
            if source is None:
                target = None
                break
            required.append(source.body_id)
            target = output_by_body[source.body_id]
            current = target
        answerable = not unknown and target is not None and len(required) == depth and target.identity_key.endswith("state:64")
        rows.append({
            "prompt_id": f"{split}:query:{index:07d}",
            "clamped_unit_ids": (initial.unit_id,),
            "scope_key": initial.scope_key,
            "maximum_bodies": 64,
            "maximum_steps": 64,
            "gold_candidate_id": target.unit_id if answerable and target else None,
            "required_body_ids": tuple(required),
            "depth": depth,
            "query_type": "answerable" if answerable else "unknown",
            "initial_entity": _entity(initial.identity_key),
        })
    return tuple(rows)


def build_split(workspace: Path, split: str, body_count: int, query_count: int, seed: int) -> dict[str, object]:
    bodies, units, vectors = generate_bodies(split, body_count, seed)
    queries = generate_queries(split, bodies, units, query_count, seed + 1) if query_count else ()
    root = workspace / "datasets" / split
    root.mkdir(parents=True, exist_ok=True)
    np.save(root / "vectors.npy", vectors)
    _write_jsonl(root / "bodies.jsonl", tuple(asdict(body) for body in bodies))
    _write_jsonl(root / "units.jsonl", tuple(asdict(unit) for unit in units))
    public = tuple({key: value for key, value in row.items() if key not in {"gold_candidate_id", "required_body_ids", "depth", "query_type", "initial_entity"}} for row in queries)
    gold = tuple({key: value for key, value in row.items() if key in {"prompt_id", "gold_candidate_id", "required_body_ids", "depth", "query_type"}} for row in queries)
    _write_jsonl(root / "public.jsonl", public)
    _write_jsonl(root / "gold.jsonl", gold)
    return {"split": split, "bodies": len(bodies), "units": len(units), "queries": len(queries), "sha256": hashlib.sha256((root / "bodies.jsonl").read_bytes()).hexdigest()}


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
