from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .contracts import CompiledPolicy, PolicyInstruction, canonical, digest

ALLOWED = {
    "source_multiplier", "require_source_class", "path_decay", "conjunction_mode",
    "conflict_margin", "candidate_threshold", "minimum_independent_sources",
    "response_style", "disclose_tension", "include_certificate",
}


def _bounded(opcode: str, value: Any) -> Any:
    if opcode == "source_multiplier":
        if not isinstance(value, dict) or not value or any(not isinstance(k, str) for k in value):
            raise ValueError("POLICY_SOURCE_MULTIPLIER_INVALID")
        if any(not isinstance(v, (int, float)) or not 0 <= float(v) <= 2 for v in value.values()):
            raise ValueError("POLICY_SOURCE_MULTIPLIER_BOUNDS")
        return {k: float(value[k]) for k in sorted(value)}
    if opcode == "require_source_class":
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", value):
            raise ValueError("POLICY_SOURCE_CLASS_INVALID")
    elif opcode == "path_decay":
        if not isinstance(value, (int, float)) or not 0.8 <= float(value) <= 1:
            raise ValueError("POLICY_PATH_DECAY_BOUNDS")
        return float(value)
    elif opcode == "conjunction_mode":
        if value == "all":
            return value
        if not isinstance(value, dict) or value.get("mode") != "quorum" or not isinstance(value.get("k"), int) or value["k"] < 1:
            raise ValueError("POLICY_CONJUNCTION_INVALID")
        return {"mode": "quorum", "k": value["k"]}
    elif opcode in {"conflict_margin", "candidate_threshold"}:
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise ValueError("POLICY_NUMERIC_BOUNDS")
        return float(value)
    elif opcode == "minimum_independent_sources":
        if not isinstance(value, int) or value < 1 or value > 16:
            raise ValueError("POLICY_SOURCE_COUNT_BOUNDS")
    elif opcode in {"response_style"}:
        if value not in {"brief", "detailed", "winner_plus_tension"}:
            raise ValueError("POLICY_STYLE_INVALID")
    elif opcode in {"disclose_tension", "include_certificate"} and not isinstance(value, bool):
        raise ValueError("POLICY_BOOLEAN_INVALID")
    return value


def compile_policy(policy_id: str, rows: list[dict[str, Any]], revision: str = "l8-policy-v1") -> CompiledPolicy:
    if not policy_id or not isinstance(rows, list):
        raise ValueError("POLICY_INPUT_INVALID")
    instructions: list[PolicyInstruction] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("opcode") not in ALLOWED:
            raise ValueError("POLICY_OPCODE_FORBIDDEN")
        opcode = str(row["opcode"])
        scope = str(row.get("scope", "global"))
        priority = int(row.get("priority", 0))
        source_id = str(row.get("source_id", "policy"))
        if scope not in {"global", "query", "reality"} and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", scope):
            raise ValueError("POLICY_SCOPE_INVALID")
        instructions.append(PolicyInstruction(opcode, _bounded(opcode, row.get("value")), scope, priority, source_id))
    grouped: dict[tuple[str, str, int], list[PolicyInstruction]] = defaultdict(list)
    for item in instructions:
        grouped[(item.scope, item.opcode, item.priority)].append(item)
    for values in grouped.values():
        if len({canonical(item.value) for item in values}) > 1:
            raise ValueError("POLICY_CONFLICT")
    instructions.sort(key=lambda item: (item.scope, item.opcode, item.priority, item.source_id, canonical(item.value)))
    payload = {"policy_id": policy_id, "revision": revision, "instructions": [item.__dict__ if hasattr(item, "__dict__") else {"opcode": item.opcode, "value": item.value, "scope": item.scope, "priority": item.priority, "source_id": item.source_id} for item in instructions]}
    return CompiledPolicy(policy_id, revision, tuple(instructions), digest(payload))


def parse_controlled_policy(text: str) -> list[dict[str, Any]]:
    """Tiny diagnostic grammar; it is deliberately not the authoritative input."""
    normalized = " ".join(text.lower().split())
    if normalized == "prefer support sources":
        return [{"opcode": "source_multiplier", "value": {"support": 1.5, "opposition": 0.5}}]
    if normalized == "prefer opposition sources":
        return [{"opcode": "source_multiplier", "value": {"support": 0.5, "opposition": 1.5}}]
    if normalized == "require support sources":
        return [{"opcode": "require_source_class", "value": "support"}]
    if normalized == "use all inputs":
        return [{"opcode": "conjunction_mode", "value": "all"}]
    if normalized == "use one input quorum":
        return [{"opcode": "conjunction_mode", "value": {"mode": "quorum", "k": 1}}]
    raise ValueError("CONTROLLED_POLICY_TEXT_UNSUPPORTED")


def policy_values(policy: CompiledPolicy, scope: str, source_classes: dict[str, str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    ranked = sorted(policy.instructions, key=lambda item: (item.priority, item.scope == "global"))
    for item in ranked:
        if item.scope not in {"global", "query", "reality", scope}:
            continue
        if item.opcode == "source_multiplier":
            values.setdefault(item.opcode, {}).update(item.value)
        else:
            values[item.opcode] = item.value
    values.setdefault("source_multiplier", {})
    values["source_classes"] = source_classes
    values.setdefault("path_decay", 1.0)
    values.setdefault("conjunction_mode", "all")
    values.setdefault("conflict_margin", 0.05)
    values.setdefault("candidate_threshold", 0.5)
    values.setdefault("minimum_independent_sources", 1)
    return values
