from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze
from .report import report


def _workspace(value: str) -> Path:
    return Path(value).resolve()


def verify(workspace: Path) -> dict[str, object]:
    manifest = json.loads((workspace / "frozen-manifest.json").read_text())
    checks = {}
    for key, filename in (("selected_sha256", "selected.json"), ("train_sha256", "train.jsonl"), ("dev_sha256", "dev.jsonl")):
        digest = hashlib.sha256((workspace / filename).read_bytes()).hexdigest()
        checks[key] = digest == manifest[key]
    if (workspace / "locked-results.json").exists():
        checks["locked_results"] = True
    if not all(checks.values()):
        raise RuntimeError(f"artifact verification failed: {checks}")
    return {"ok": True, "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="micro_ltm")
    parser.add_argument("command", choices=("develop", "freeze", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/micro-ltm")
    args = parser.parse_args(argv)
    workspace = _workspace(args.workspace)
    if args.command == "develop":
        print(json.dumps(develop(workspace), indent=2))
    elif args.command == "freeze":
        print(json.dumps(freeze(workspace), indent=2))
    elif args.command == "evaluate":
        result = evaluate_locked(workspace)
        print(json.dumps(result["metrics"], indent=2, sort_keys=True))
    elif args.command == "report":
        print(json.dumps(report(workspace), indent=2))
    elif args.command == "verify":
        print(json.dumps(verify(workspace), indent=2))
    else:
        if not (workspace / "selected.json").exists():
            develop(workspace)
        if not (workspace / "frozen-manifest.json").exists():
            freeze(workspace)
        if not (workspace / "locked-results.json").exists():
            evaluate_locked(workspace)
        print(json.dumps(report(workspace), indent=2))
    return 0
