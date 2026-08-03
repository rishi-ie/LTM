from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArgumentSpan:
    argument_id: str
    text: str
    node_kind: str
    source_start: int
    source_end: int


@dataclass(frozen=True, slots=True)
class ReasoningCase:
    case_id: str
    statement: str
    arguments: tuple[ArgumentSpan, ...]
    gold_relation: str
    gold_roles: tuple[str, ...]
    gold_direction: str
    gold_scope: str
    gold_disposition: str
    paraphrase_group: str
    source_hash: str
    template_id: str

    @classmethod
    def make(
        cls,
        case_id: str,
        statement: str,
        arguments: tuple[ArgumentSpan, ...],
        relation: str,
        roles: tuple[str, ...],
        direction: str,
        scope: str,
        disposition: str,
        group: str,
        template_id: str,
    ) -> ReasoningCase:
        return cls(case_id, statement, arguments, relation, roles, direction, scope, disposition, group, hashlib.sha256(statement.encode()).hexdigest(), template_id)


@dataclass(frozen=True, slots=True)
class ReasoningPrediction:
    case_id: str
    relation: str
    direction: str
    roles: tuple[str, ...]
    scope: str
    disposition: str
    confidence: float
    embedding: tuple[float, ...] | None = None
