from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Scale:
    name: str
    tokens: int
    chunks: int
    factors: int
    blocks: int
    regions: int


@dataclass(frozen=True, slots=True)
class QueryCase:
    query_id: str
    family: str
    gold: str
    depth: int
    target: str
    scope: str
    episode_id: str | None
    required_blocks: tuple[int, ...]
    remote_block: int | None
    has_constraint: bool
    has_exception: bool
    session_overlay: bool


@dataclass(frozen=True, slots=True)
class PipelineResult:
    query_id: str
    conclusion: str
    disposition: str
    required_blocks: tuple[int, ...]
    opened_blocks: tuple[int, ...]
    factors_opened: int
    factors_required: int
    candidate_count: int
    coverage_disposition: str
    widened: bool
    verifier_ok: bool
    batch_invariant: bool
    session_ok: bool
    bytes_read: int
    full_scan: bool
    runtime_us: int


def row(value: object) -> dict:
    return asdict(value)
