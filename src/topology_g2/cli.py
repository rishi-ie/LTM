from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, model_check, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g2")
    parser.add_argument("command", choices=("model-check", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g2")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "model-check":
        result = model_check(workspace)
    elif args.command == "develop":
        result = develop(workspace)
    elif args.command == "freeze":
        result = freeze(workspace)
    elif args.command == "locked-suite-build":
        result = locked_suite_build(workspace)
    elif args.command == "evaluate":
        result = evaluate_locked(workspace)
    elif args.command == "report":
        result = report(workspace)
    elif args.command == "verify":
        result = verify(workspace)
    else:
        check = model_check(workspace)
        if check["status"] != "ok":
            result = {"classification": "BLOCKED-RUNTIME", "model_check": check}
        else:
            if not (workspace / "development-results.json").exists():
                develop(workspace)
            if not (workspace / "frozen-manifest.json").exists():
                freeze(workspace)
            if not (workspace / "locked" / "inputs.jsonl").exists():
                locked_suite_build(workspace)
            if not (workspace / "locked-results.json").exists():
                evaluate_locked(workspace)
            result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
