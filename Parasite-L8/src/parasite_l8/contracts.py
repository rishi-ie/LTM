from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PolicyInstruction:
    opcode: str
    value: Any
    scope: str = "global"
    priority: int = 0
    source_id: str = "policy"


@dataclass(frozen=True, slots=True)
class CompiledPolicy:
    policy_id: str
    revision: str
    instructions: tuple[PolicyInstruction, ...]
    hash: str


@dataclass(frozen=True, slots=True)
class L8Candidate:
    atom_id: str
    expression: str
    polarity: int
    activation: float
    opposing_activation: float
    margin: float
    supporting_body_ids: tuple[str, ...]
    opposing_body_ids: tuple[str, ...]
    independent_sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class L8Trace:
    sweep: int
    objective: float
    residual: float
    state_hash: str


@dataclass(frozen=True, slots=True)
class L8Result:
    disposition: str
    candidates: tuple[L8Candidate, ...]
    selected_candidate_id: str | None
    positive: tuple[tuple[str, float], ...]
    negative: tuple[tuple[str, float], ...]
    tension: tuple[tuple[str, float], ...]
    factor_activations: tuple[tuple[str, float], ...]
    trajectory: tuple[L8Trace, ...]
    objective: float
    residual: float
    policy_hash: str
    factual_operations: tuple[()] = ()
