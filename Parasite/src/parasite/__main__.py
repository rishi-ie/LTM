"""Stable JSON command line interface for Parasite."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from parasite.contracts import IngestRequest, QueryRequest
from parasite.integrity import plain
from parasite.runtime import ParasiteRuntime


def _defaults() -> tuple[Path, Path]:
    root = Path.cwd()
    parasite = root / "Parasite" if (root / "Parasite/config/runtime-v1.json").exists() else Path(__file__).resolve().parents[2]
    return parasite / "var", parasite / "config/runtime-v1.json"


def _runtime(args):
    return ParasiteRuntime.open(args.state, args.config)


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit(value) -> None:
    print(json.dumps(plain(value), indent=2, sort_keys=True))


def _demo(args) -> dict:
    demo_root = Path(args.state) / "demo-runs"
    demo_root.mkdir(parents=True, exist_ok=True)
    state = Path(tempfile.mkdtemp(prefix="parasite-v01-", dir=demo_root))
    runtime = ParasiteRuntime.open(state, args.config)
    try:
        atoms = [{"id": "s0", "expression": "1 ⊕ 1 = 3", "sort": "custom"}] + [{"id": f"s{i}", "expression": f"custom-state-{i}", "sort": "custom"} for i in range(1, 21)]
        factors = [{"id": f"step-{i}", "inputs": [f"s{i}"], "outcome": f"s{i+1}", "source_key": f"source-{i}", "authority": 1.0, "confidence": 1.0} for i in range(20)]
        # A losing contradictory source remains visible at the terminal.
        factors.append({"id": "terminal-opposition", "inputs": ["s19"], "outcome": "s20", "polarity": -1, "source_key": "opposition", "authority": 0.4, "confidence": 1.0})
        math_payload = {"source_text": "custom reality: 1 plus 1 is 3; followed by twenty registered transitions", "atoms": atoms, "factors": factors}
        math_request = IngestRequest("demo", "custom-alpha", "demo-math", hashlib.sha256(math_payload["source_text"].encode()).hexdigest(), "mathematical_reality", math_payload)
        math_compile = runtime.ingest(math_request)
        answer = runtime.ask(QueryRequest("demo", "custom-alpha", "demo-query", "fixed_equilibrium", "formal", {"assumptions": ["1 ⊕ 1 = 3"], "query_expression": "custom-state-20", "query_sort": "custom"}, requested_style="detailed"))
        standard_payload = {
            "source_text": "registered standard arithmetic identity",
            "atoms": [
                {"id": "premise", "expression": "standard arithmetic", "sort": "arithmetic"},
                {"id": "answer", "expression": "1 + 1 = 2", "sort": "arithmetic"},
            ],
            "factors": [{"id": "standard-addition", "inputs": ["premise"], "outcome": "answer", "source_key": "standard-arithmetic-manifest"}],
        }
        standard_compile = runtime.ingest(IngestRequest("demo", "standard-math", "standard-source", hashlib.sha256(standard_payload["source_text"].encode()).hexdigest(), "mathematical_reality", standard_payload))
        standard_answer = runtime.ask(QueryRequest("demo", "standard-math", "standard-query", "fixed_equilibrium", "formal", {"assumptions": ["standard arithmetic"], "query_expression": "1 + 1 = 2", "query_sort": "arithmetic"}))
        text = "For this session, I prefer style_7 to be value_00007."
        key, value = "style_7", "value_00007"
        spans = [
            {"id": "preference-key", "text": key, "start": text.index(key), "end": text.index(key) + len(key), "slot_type": "preference_key"},
            {"id": "preference-value", "text": value, "start": text.index(value), "end": text.index(value) + len(value), "slot_type": "preference_value"},
        ]
        conversation = runtime.ingest(IngestRequest("demo", "conversation", "demo-conversation", hashlib.sha256(text.encode()).hexdigest(), "conversation_turn", {"source_text": text, "semantic_spans": spans}, session_id="demo-session"))
        memory = runtime.ask(QueryRequest("demo", "conversation", "memory-query", "conversation_memory", "context", {}, session_id="demo-session"))
        return {
            "state_path": str(state), "math_compile": math_compile, "math_result": answer,
            "standard_compile": standard_compile, "standard_result": standard_answer,
            "conversation_compile": conversation, "conversation_context": memory,
            "inspection": runtime.inspect("demo", "custom-alpha"),
        }
    finally:
        runtime.close()


def main(argv: list[str] | None = None) -> int:
    default_state, default_config = _defaults()
    parser = argparse.ArgumentParser(prog="python -m parasite")
    parser.add_argument("--state", default=str(default_state))
    parser.add_argument("--config", default=str(default_config))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    for command in ("ingest", "ask"):
        item = sub.add_parser(command); item.add_argument("--input", required=True)
    delete = sub.add_parser("delete"); delete.add_argument("--tenant", required=True); delete.add_argument("--reality", required=True); delete.add_argument("--object", required=True)
    clear = sub.add_parser("clear-session"); clear.add_argument("--tenant", required=True); clear.add_argument("--session", required=True)
    for command in ("inspect", "verify"):
        item = sub.add_parser(command); item.add_argument("--tenant", required=True); item.add_argument("--reality", required=True)
    sub.add_parser("demo")
    args = parser.parse_args(argv)
    if args.command == "demo":
        _emit(_demo(args)); return 0
    with _runtime(args) as runtime:
        if args.command == "init":
            _emit({"initialized": True, "state_path": str(runtime.state_path), "runtime_revision": runtime.config["runtime_revision"]})
        elif args.command == "ingest":
            _emit(runtime.ingest(IngestRequest(**_load(args.input))))
        elif args.command == "ask":
            _emit(runtime.ask(QueryRequest(**_load(args.input))))
        elif args.command == "delete":
            _emit({"deleted": runtime.delete(args.tenant, args.reality, args.object)})
        elif args.command == "clear-session":
            _emit({"cleared": runtime.clear_session(args.tenant, args.session)})
        elif args.command == "inspect":
            _emit(runtime.inspect(args.tenant, args.reality))
        elif args.command == "verify":
            _emit(runtime.verify(args.tenant, args.reality))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
