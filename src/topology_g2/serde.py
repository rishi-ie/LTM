from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .schemas import (
    CandidateAmbiguity,
    CandidateIR,
    CandidateObject,
    CandidateReference,
    CandidateRelation,
    ContextEntity,
    ContextSnapshot,
    GoldCase,
    SourceRecord,
)


def plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: plain(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    return value


def dumps(value: Any) -> str:
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def source_from_dict(raw: dict[str, Any]) -> SourceRecord:
    return SourceRecord(**raw)


def context_from_dict(raw: dict[str, Any]) -> ContextSnapshot:
    # G2 does not serialize G1 context topology into runtime fixtures yet.
    return ContextSnapshot(
        tuple(ContextEntity(**item) for item in raw["entities"]), (), (),
        tuple(source_from_dict(item) for item in raw["recent_turns"]), tuple(raw["reference_candidates"]),
    )


def candidate_from_dict(raw: dict[str, Any]) -> CandidateIR:
    expected = {"disposition", "speech_acts", "objects", "relations", "references", "ambiguities"}
    if set(raw) != expected:
        raise ValueError("UNKNOWN_JSON_FIELD")
    return CandidateIR(
        raw["disposition"],
        tuple(raw["speech_acts"]),
        tuple(CandidateObject(**item) for item in raw["objects"]),
        tuple(CandidateRelation(item["relation_type"], tuple((role, tuple(ids)) for role, ids in item["arguments"]), item["scope_name"], item["valid_from"], item["valid_to"], item["confidence"]) for item in raw["relations"]),
        tuple(CandidateReference(**item) for item in raw["references"]),
        tuple(CandidateAmbiguity(**item) for item in raw["ambiguities"]),
    )


def gold_to_dict(case: GoldCase) -> dict[str, Any]:
    return {
        "source": plain(case.source),
        "context": plain(case.context),
        "gold_ir": plain(case.gold_ir),
        "topology_hash": case.topology_hash,
        "relation_types": list(case.relation_types),
        "complexity": case.complexity,
    }


def gold_from_dict(raw: dict[str, Any]) -> GoldCase:
    return GoldCase(
        source_from_dict(raw["source"]), context_from_dict(raw["context"]), candidate_from_dict(raw["gold_ir"]),
        raw["topology_hash"], tuple(raw["relation_types"]), raw["complexity"],
    )
