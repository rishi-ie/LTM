from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    kind: str
    premises: tuple[str, ...]
    conclusion: str | None = None
    scope: str = "global"
    confidence: float = 1.0
    authority: float = 1.0


@dataclass(frozen=True, slots=True)
class ReasoningProblem:
    problem_id: str
    family: str
    facts: tuple[str, ...]
    rules: tuple[Rule, ...]
    target: str
    scope: str = "global"
    depth: int = 1


@dataclass(frozen=True, slots=True)
class ProofStep:
    conclusion: str
    rule_id: str
    premises: tuple[str, ...]
    depth: int


@dataclass(frozen=True, slots=True)
class ProgramResult:
    problem_id: str
    conclusion: str
    active: tuple[str, ...]
    inactive: tuple[str, ...]
    proofs: tuple[ProofStep, ...]
    conflicts: tuple[str, ...]
    obligations: tuple[str, ...]
    messages: tuple[str, ...]
    constraints: tuple[str, ...]
    bindings: tuple[str, ...]
    residuals: tuple[tuple[str, float], ...]
    rounds: int


def row(value: object) -> dict:
    return asdict(value)
