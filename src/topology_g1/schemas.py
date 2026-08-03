from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

ScalarValue = str | int | float | bool | None


class SchemaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class NodeKind(str, Enum):
    ENTITY = "entity"
    VALUE = "value"
    STATE = "state"
    FACT = "fact"
    OBSERVATION = "observation"
    CLAIM = "claim"
    HYPOTHESIS = "hypothesis"
    GOAL = "goal"
    QUESTION = "question"
    INSTRUCTION = "instruction"
    PREFERENCE = "preference"
    EVENT = "event"
    RULE = "rule"
    CORRECTION = "correction"
    CONFLICT = "conflict"
    SCOPE = "scope"
    CONVERSATION_TURN = "conversation_turn"
    ASSISTANT_RESPONSE = "assistant_response"
    PROVENANCE_ARTIFACT = "provenance_artifact"


def _check_scalar(value: ScalarValue) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise SchemaError("NONFINITE_SCALAR", "scalar floats must be finite")
    if not isinstance(value, (str, int, float, bool, type(None))):
        raise SchemaError("INVALID_SCALAR", "attributes must be scalar values")


@dataclass(frozen=True, slots=True)
class Provenance:
    source_id: str
    source_span_start: int
    source_span_end: int
    source_hash: str

    def __post_init__(self) -> None:
        if not self.source_id or self.source_span_start < 0 or self.source_span_end < self.source_span_start:
            raise SchemaError("MISSING_PROVENANCE", "invalid source provenance")
        if len(self.source_hash) != 64 or any(c not in "0123456789abcdef" for c in self.source_hash):
            raise SchemaError("SOURCE_HASH_MISMATCH", "source hash must be lower-case sha256")


@dataclass(frozen=True, slots=True)
class ValidityInterval:
    valid_from: int | None = None
    valid_to: int | None = None

    def __post_init__(self) -> None:
        if self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to:
            raise SchemaError("TEMPORAL_VIOLATION", "valid_from must not exceed valid_to")


@dataclass(frozen=True, slots=True)
class TopologyNode:
    node_id: str
    schema_version: int
    kind: NodeKind
    attributes: tuple[tuple[str, ScalarValue], ...]
    scope_id: str
    validity: ValidityInterval
    provenance: tuple[Provenance, ...]

    def __post_init__(self) -> None:
        if not self.node_id or self.schema_version != 2 or not self.scope_id:
            raise SchemaError("INVALID_NODE", "invalid node identity, version, or scope")
        keys = [key for key, _ in self.attributes]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise SchemaError("INVALID_ATTRIBUTES", "attributes must have unique sorted keys")
        for _, value in self.attributes:
            _check_scalar(value)
        if not self.provenance:
            raise SchemaError("MISSING_PROVENANCE", "nodes require provenance")

    def attr(self, name: str, default: ScalarValue = None) -> ScalarValue:
        return dict(self.attributes).get(name, default)


@dataclass(frozen=True, slots=True)
class RoleBinding:
    role: str
    node_id: str

    def __post_init__(self) -> None:
        if not self.role or not self.node_id:
            raise SchemaError("MISSING_ROLE", "role and node id are required")


@dataclass(frozen=True, slots=True)
class RoleSpec:
    name: str
    allowed_kinds: tuple[NodeKind, ...]
    minimum: int = 1
    maximum: int = 1


@dataclass(frozen=True, slots=True)
class RelationSpec:
    relation_type: str
    roles: tuple[RoleSpec, ...]
    hard_or_soft: str
    exact_operator: str
    field_operator: str
    verifier_rule: str
    explanation_template: str


@dataclass(frozen=True, slots=True)
class RelationInstance:
    relation_id: str
    schema_version: int
    relation_type: str
    arguments: tuple[RoleBinding, ...]
    scope_id: str
    validity: ValidityInterval
    confidence: float
    authority: float
    provenance: tuple[Provenance, ...]

    def __post_init__(self) -> None:
        if not self.relation_id or self.schema_version != 2 or not self.scope_id:
            raise SchemaError("INVALID_RELATION", "invalid relation identity, version, or scope")
        if not math.isfinite(self.confidence) or not math.isfinite(self.authority):
            raise SchemaError("NONFINITE_SCALAR", "relation weights must be finite")
        if not 0 <= self.confidence <= 1 or not 0 <= self.authority <= 1:
            raise SchemaError("INVALID_WEIGHT", "confidence and authority must be in [0, 1]")
        if not self.provenance:
            raise SchemaError("MISSING_PROVENANCE", "relations require provenance")

    def role_ids(self, role: str) -> tuple[str, ...]:
        return tuple(x.node_id for x in self.arguments if x.role == role)


@dataclass(frozen=True, slots=True)
class SupersessionRecord:
    old_claim_id: str
    new_claim_id: str


@dataclass(frozen=True, slots=True)
class TopologyOperation:
    operation_id: str
    operation_type: str
    payload: TopologyNode | RelationInstance | SupersessionRecord
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    relation_id: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TypedMessage:
    relation_id: str
    message_type: str
    source_ids: tuple[str, ...]
    value: float


@dataclass(frozen=True, slots=True)
class HardObligation:
    relation_id: str
    code: str
    node_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FieldContribution:
    relation_id: str
    residual: float
    messages: tuple[TypedMessage, ...]
    hard_obligations: tuple[HardObligation, ...]


@dataclass(frozen=True, slots=True)
class Derivation:
    conclusion_id: str
    relation_id: str
    premise_ids: tuple[str, ...]
    scope_id: str
    provenance: tuple[Provenance, ...]


@dataclass(frozen=True, slots=True)
class VerificationRecord:
    valid: bool
    checked_roles: tuple[str, ...]
    checked_sources: tuple[str, ...]
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionState:
    active_claims: frozenset[str]
    inactive_claims: frozenset[str] = frozenset()
    numeric_values: tuple[tuple[str, float], ...] = ()
    reference_bindings: tuple[tuple[str, str], ...] = ()
    response_constraints: tuple[str, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    scope_id: str = "global"

    def value(self, node_id: str) -> float:
        values = dict(self.numeric_values)
        if node_id in values:
            return values[node_id]
        return 1.0 if node_id in self.active_claims else 0.0
