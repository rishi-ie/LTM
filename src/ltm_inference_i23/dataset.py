"""Opaque, non-ordinal observed-body generator with separated public and gold archives."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .schemas import AtomicMumbrane, ReasoningBody

DIMENSION = 384
_LENGTHS = (2, 3, 5, 8, 13, 21, 34, 55, 64)


def _sha(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _opaque(seed: int, chain: int, point: int) -> str:
    return hashlib.sha256(f"{seed}|{chain}|{point}".encode()).hexdigest()[:20]


def semantic_vector(identity: str, scope: str) -> np.ndarray:
    """Deterministic opaque semantic coordinate with no ordinal state feature."""
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], "little"))
    value = rng.normal(size=DIMENSION).astype(np.float32)
    scope_rng = np.random.default_rng(int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], "little"))
    value += .12 * scope_rng.normal(size=DIMENSION).astype(np.float32)
    value /= max(float(np.linalg.norm(value)), 1e-8)
    return value.astype(np.float32)


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _build_graph(split: str, count: int, seed: int) -> tuple[tuple[ReasoningBody, ...], tuple[AtomicMumbrane, ...], np.ndarray, tuple[dict[str, object], ...]]:
    """Create shuffled opaque chains with scope-isolated confounder branches.

    The logical state labels never contain their traversal position. Body order is
    shuffled after construction, so row order cannot encode an answer path.
    """
    rng = random.Random(seed)
    bodies: list[ReasoningBody] = []
    units: list[AtomicMumbrane] = []
    vectors: list[np.ndarray] = []
    chains: list[dict[str, object]] = []
    body_number = 0
    chain_number = 0
    prior_terminal: str | None = None
    while body_number < count:
        length = min(_LENGTHS[chain_number % len(_LENGTHS)], count - body_number)
        scope = "global" if chain_number % 5 else "fictional"
        state_rows = [_opaque(seed, chain_number, point) for point in range(length + 1)]
        # Every second path merges at a shared terminal without creating an
        # ambiguous source transition. The opaque terminal carries no rank cue.
        if chain_number % 2 and prior_terminal is not None:
            state_rows[-1] = prior_terminal
        states = tuple(state_rows)
        body_ids: list[str] = []
        for point in range(length):
            body_id = f"{split}:body:{body_number:07d}"
            body_ids.append(body_id)
            input_unit = f"{body_id}:input"
            outcome_unit = f"{body_id}:outcome"
            for local_index, unit_id, identity in ((0, input_unit, states[point]), (1, outcome_unit, states[point + 1])):
                vectors.append(semantic_vector(identity, scope))
                units.append(AtomicMumbrane(
                    unit_id=unit_id,
                    body_id=body_id,
                    semantic_vector_ref=len(vectors) - 1,
                    local_index=local_index,
                    phase_index=local_index,
                    polarity="positive",
                    modality="observed",
                    scope_key=scope,
                    identity_key=f"opaque:{identity}",
                    provenance_id=f"source:{body_id}",
                ))
            bodies.append(ReasoningBody(body_id, (input_unit, outcome_unit), scope, f"source:{split}:{body_number}", _sha((body_id, states[point], states[point + 1], scope))))
            body_number += 1
        chains.append({"scope": scope, "states": states, "body_ids": tuple(body_ids)})
        if chain_number % 2 == 0:
            prior_terminal = states[-1]
        # Add a scope-isolated branch from an interior observed state. This is a
        # genuine alternative body in the public field, but it is incompatible
        # with the main path's scope and therefore must not contaminate it.
        if len(states) >= 3 and body_number < count:
            branch_scope = "fictional" if scope == "global" else "global"
            branch_source = states[len(states) // 2]
            branch_outcome = _opaque(seed, chain_number, 1000000)
            branch_id = f"{split}:body:{body_number:07d}"
            input_unit, outcome_unit = f"{branch_id}:input", f"{branch_id}:outcome"
            for local_index, unit_id, identity in ((0, input_unit, branch_source), (1, outcome_unit, branch_outcome)):
                vectors.append(semantic_vector(identity, branch_scope))
                units.append(AtomicMumbrane(unit_id, branch_id, len(vectors) - 1, local_index, local_index, "positive", "observed", branch_scope, f"opaque:{identity}", f"source:{branch_id}"))
            bodies.append(ReasoningBody(branch_id, (input_unit, outcome_unit), branch_scope, f"source:{split}:{body_number}", _sha((branch_id, branch_source, branch_outcome, branch_scope))))
            chains.append({"scope": branch_scope, "states": (branch_source, branch_outcome), "body_ids": (branch_id,)})
            body_number += 1
        chain_number += 1
    rng.shuffle(bodies)
    return tuple(bodies), tuple(units), np.asarray(vectors, dtype=np.float32), tuple(chains)


def _queries(split: str, chains: tuple[dict[str, object], ...], units: tuple[AtomicMumbrane, ...], count: int, seed: int) -> tuple[dict[str, object], ...]:
    rng = random.Random(seed)
    unit_by_identity = {(unit.identity_key.removeprefix("opaque:"), unit.scope_key): unit for unit in units if unit.phase_index == 0}
    outcome_by_identity = {(unit.identity_key.removeprefix("opaque:"), unit.scope_key): unit for unit in units if unit.phase_index == 1}
    outcome_by_body = {unit.body_id: unit for unit in units if unit.phase_index == 1}
    rows: list[dict[str, object]] = []
    eligible = [chain for chain in chains if chain["body_ids"]]
    for index in range(count):
        unknown = index % 13 == 0
        chain = eligible[(index * 29 + rng.randrange(len(eligible))) % len(eligible)]
        states = tuple(chain["states"])
        body_ids = tuple(chain["body_ids"])
        if unknown:
            initial_state = states[-1]
            target = None
            required: tuple[str, ...] = ()
        else:
            remaining = 1 + (index % len(body_ids))
            start = len(body_ids) - remaining
            initial_state = states[start]
            target = outcome_by_body[body_ids[-1]].unit_id
            required = body_ids[start:]
        initial = unit_by_identity.get((initial_state, str(chain["scope"])))
        if initial is None:
            # A terminal state has no input occurrence, so expose its existing outcome
            # occurrence as immutable evidence; it still has no compatible source body.
            initial = outcome_by_identity[(initial_state, str(chain["scope"]))]
        rows.append({
            "prompt_id": f"{split}:prompt:{index:07d}",
            "clamped_unit_ids": (initial.unit_id,),
            "scope_key": str(chain["scope"]),
            "maximum_bodies": 64,
            "maximum_steps": 32,
            "gold_candidate_id": target,
            "required_body_ids": required,
            "query_type": "unknown" if unknown else "answerable",
        })
    return tuple(rows)


def build_split(workspace: Path, split: str, body_count: int, prompt_count: int, seed: int) -> dict[str, object]:
    bodies, units, vectors, chains = _build_graph(split, body_count, seed)
    prompts = _queries(split, chains, units, prompt_count, seed + 1) if prompt_count else ()
    public_root = workspace / "public" / split
    gold_root = workspace / "evaluator-gold" / split
    public_root.mkdir(parents=True, exist_ok=True)
    np.save(public_root / "vectors.npy", vectors)
    _write_jsonl(public_root / "bodies.jsonl", tuple(asdict(item) for item in bodies))
    _write_jsonl(public_root / "units.jsonl", tuple(asdict(item) for item in units))
    public = tuple({key: value for key, value in row.items() if key not in {"gold_candidate_id", "required_body_ids", "query_type"}} for row in prompts)
    gold = tuple({key: value for key, value in row.items() if key in {"prompt_id", "gold_candidate_id", "required_body_ids", "query_type"}} for row in prompts)
    _write_jsonl(public_root / "prompts.jsonl", public)
    _write_jsonl(gold_root / "gold.jsonl", gold)
    return {
        "split": split,
        "bodies": len(bodies),
        "units": len(units),
        "prompts": len(prompts),
        "public_sha256": hashlib.sha256((public_root / "bodies.jsonl").read_bytes()).hexdigest(),
        "gold_sha256": hashlib.sha256((gold_root / "gold.jsonl").read_bytes()).hexdigest(),
    }


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    return tuple(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
