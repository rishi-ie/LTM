from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkTurn:
    turn_id: str
    conversation_id: str
    turn_index: int
    speaker: str
    text: str
    source_hash: str


@dataclass(frozen=True, slots=True)
class BenchmarkQuery:
    query_id: str
    conversation_id: str
    family: str
    prompt: str
    proof_depth: int
    session_required: bool
    coverage_required: bool
    facts: tuple[str, ...]
    rules: tuple[tuple[str, tuple[str, ...], str], ...]


@dataclass(frozen=True, slots=True)
class BenchmarkGold:
    query_id: str
    gold: str
    required_factor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MethodSpec:
    method_id: str
    input_contract: str
    retrieval_contract: str
    reasoning_contract: str
    memory_contract: str
    verifier_contract: str


@dataclass(frozen=True, slots=True)
class ComponentTrace:
    query_id: str
    method_id: str
    address_ids: tuple[str, ...]
    frontier_factor_ids: tuple[str, ...]
    coverage_disposition: str
    hard_conclusion: str
    verifier_status: str
    session_ok: bool
    full_scan: bool
    runtime_us: int


@dataclass(frozen=True, slots=True)
class MethodResult:
    query_id: str
    method_id: str
    conclusion: str
    disposition: str
    provenance_ids: tuple[str, ...]
    trace: ComponentTrace


def row(value: object) -> dict:
    return asdict(value)
