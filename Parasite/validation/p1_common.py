"""Fresh, opaque P1 acceptance-suite generation (no Parasite runtime imports)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SEED = 20260809


def _h(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(map(str, parts)).encode()).hexdigest()[:16]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class AcceptanceCase:
    case_id: str
    track: str
    tenant: str
    reality: str
    source: str
    request: dict[str, Any]
    expected: dict[str, Any]

    def public(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "track": self.track,
            "tenant": self.tenant,
            "reality": self.reality,
            "source": self.source,
            "request": self.request,
        }

    def gold(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "track": self.track, **self.expected}


def _math_case(index: int, depth: int, *, family: str = "unique", opposition: float | None = None,
               alternative: bool = False, missing: bool = False, custom: bool = False) -> AcceptanceCase:
    case = f"p1-{_h(SEED, index, depth, family)}"
    tenant, reality = f"tenant-{_h(case, 'tenant')}", f"reality-{_h(case, 'reality')}"
    source = f"source-{_h(case, 'source')}"
    atoms = []
    expressions: list[str] = []
    for position in range(depth + 1):
        expression = f"atom-{_h(SEED, case, 'expression', position)}"
        expressions.append(expression)
        atoms.append({"id": f"atom-{_h(SEED, case, position)}", "expression": expression, "sort": "custom" if custom else "formal"})
    factors = []
    for position in range(depth):
        if missing and position == depth - 1:
            continue
        factors.append({
            "id": f"factor-{_h(SEED, case, 'factor', position)}",
            "inputs": [atoms[position]["id"]], "outcome": atoms[position + 1]["id"],
            "source_key": f"independent-{_h(case, position)}", "authority": 1.0, "confidence": 1.0,
        })
    if opposition is not None:
        factors.append({
            "id": f"factor-{_h(case, 'opposition')}", "inputs": [atoms[-2]["id"]], "outcome": atoms[-1]["id"],
            "polarity": -1, "authority": opposition, "confidence": 1.0, "source_key": f"opposition-{_h(case)}",
        })
    if alternative:
        factors.append({
            "id": f"factor-{_h(case, 'alternative')}", "inputs": [atoms[-2]["id"]], "outcome": atoms[-1]["id"],
            "polarity": -1, "authority": 1.0, "confidence": 1.0, "source_key": f"alternative-{_h(case)}",
        })
    # Query-independent legal distractors make the benchmark non-trivial while
    # keeping the locked field at the v0.1 limit.
    while len(factors) < 512:
        n = len(factors)
        left = f"d-{_h(case, 'left', n)}"
        right = f"d-{_h(case, 'right', n)}"
        atoms.extend((
            {"id": left, "expression": f"noise-{_h(case, n, 'l')}", "sort": "formal"},
            {"id": right, "expression": f"noise-{_h(case, n, 'r')}", "sort": "formal"},
        ))
        factors.append({"id": f"factor-{_h(case, 'noise', n)}", "inputs": [left], "outcome": right,
                        "source_key": f"noise-source-{_h(case, n)}"})
    text = f"signed reality {reality} opaque mathematical field"
    payload = {"source_text": text, "atoms": atoms, "factors": factors}
    request = {"tenant_id": tenant, "reality_id": reality, "source_id": source,
               "source_hash": _sha(text), "input_kind": "mathematical_reality", "payload": payload,
               "query": {"assumptions": [expressions[0]], "query_expression": expressions[-1], "query_sort": "custom" if custom else "formal"}}
    expected = {"disposition": "alternatives" if alternative else "unknown" if missing else "candidate",
                "claim": None if alternative or missing else expressions[-1],
                "polarity": None if alternative or missing else 1,
                "depth": depth, "family": family, "certificate_length": depth if not missing else 0,
                "expected_sources": depth if not missing else 0}
    return AcceptanceCase(case, "equilibrium", tenant, reality, source, request, expected)


def _topology_case(index: int, invalid: bool = False, track: str = "compiler") -> AcceptanceCase:
    case = f"p1-topology-{_h(SEED, index)}"
    tenant, reality, source = f"tenant-{_h(case)}", f"reality-{_h(case, 'r')}", f"source-{_h(case, 's')}"
    text = "opaque topology acceptance case"
    nodes = [{"id": "n-a", "kind": "claim", "attributes": {"label": "opaque-a"}},
             {"id": "n-b", "kind": "claim", "attributes": {"label": "opaque-b"}}]
    relations = [{"id": "rel", "relation_type": "implies",
                  "arguments": [{"role": "premise", "node_id": "n-a"},
                                 {"role": "conclusion", "node_id": "n-b"}]}]
    if invalid:
        relations[0]["arguments"][1]["node_id"] = "missing"
    payload = {"source_text": text, "nodes": nodes, "relations": relations}
    request = {"tenant_id": tenant, "reality_id": reality, "source_id": source,
               "source_hash": _sha(text), "input_kind": "topology_document", "payload": payload}
    expected_disposition = "quarantine" if invalid else ("candidate" if track == "exact" else "accept")
    return AcceptanceCase(case, track, tenant, reality, source, request,
                          {"disposition": expected_disposition, "claim": "n-b" if track == "exact" and not invalid else None, "polarity": None})


def _conversation_case(index: int, ambiguous: bool = False) -> AcceptanceCase:
    case = f"p1-conversation-{_h(SEED, index)}"
    tenant, reality, session = f"tenant-{_h(case)}", "conversation", f"session-{_h(case, 'session')}"
    if ambiguous:
        text = "Use mention_opaque to refer to either entity_alpha or entity_beta."
        spans = [{"id": "s0", "text": "mention_opaque", "start": 4, "end": 17, "slot_type": "reference"},
                 {"id": "s1", "text": "entity_alpha", "start": 32, "end": 44, "slot_type": "content"},
                 {"id": "s2", "text": "entity_beta", "start": 48, "end": 59, "slot_type": "content"}]
        candidates = [{"object_id": "opaque-a", "object_kind": "entity", "alias": "mention_opaque", "session_id": session, "episode_id": session, "scope_id": "session", "recency": 2},
                      {"object_id": "opaque-b", "object_kind": "entity", "alias": "mention_opaque", "session_id": session, "episode_id": session, "scope_id": "session", "recency": 1}]
        expected = {"disposition": "clarification_required", "claim": None, "polarity": None}
    else:
        text = "For this session, I prefer style_opaque to be value_opaque."
        key, value = "style_opaque", "value_opaque"
        spans = [{"id": "s0", "text": key, "start": text.index(key), "end": text.index(key) + len(key), "slot_type": "preference_key"},
                 {"id": "s1", "text": value, "start": text.index(value), "end": text.index(value) + len(value), "slot_type": "preference_value"}]
        candidates = []
        expected = {"disposition": "candidate", "claim": None, "polarity": None}
    payload = {"source_text": text, "semantic_spans": spans, "candidates": candidates, "event_id": f"event-{_h(case)}"}
    request = {"tenant_id": tenant, "reality_id": reality, "source_id": f"source-{_h(case)}", "source_hash": _sha(text),
               "input_kind": "conversation_turn", "payload": payload, "session_id": session}
    return AcceptanceCase(case, "conversation", tenant, reality, request["source_id"], request, expected)


def build_suite() -> tuple[AcceptanceCase, ...]:
    cases: list[AcceptanceCase] = []
    cases.extend(_topology_case(index) for index in range(3))
    cases.extend(_topology_case(index, invalid=True) for index in range(3, 6))
    cases.extend(_math_case(100 + index, 1 + index % 3, family="compiler-math") for index in range(3))
    cases.extend(_conversation_case(index, ambiguous=index == 1) for index in range(3))
    cases.extend(_topology_case(50 + index, track="exact") for index in range(8))
    cases.extend(_math_case(200 + index, depth, custom=index % 2 == 1) for index, depth in enumerate((1, 5, 10, 20) * 4))
    cases.extend(_math_case(300 + index, 10, family="weighted-contradiction", opposition=0.55) for index in range(4))
    cases.extend(_math_case(320 + index, 10, family="balanced-alternative", alternative=True) for index in range(4))
    cases.extend(_math_case(340 + index, 10, family="missing-decisive", missing=True) for index in range(4))
    cases.extend(_math_case(360 + index, 10, family="scope-time", custom=index % 2 == 0) for index in range(4))
    cases.extend(_conversation_case(400 + index, ambiguous=index % 2 == 1) for index in range(8))
    # Integrity cases reuse freshly generated fields but are scored separately.
    cases.extend(_math_case(500 + index, 20, family="integrity", custom=index % 2 == 0) for index in range(12))
    return tuple(cases)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def serial_case(case: AcceptanceCase) -> dict[str, Any]:
    return asdict(case)
