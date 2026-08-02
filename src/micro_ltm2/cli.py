from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="micro_ltm2")
    parser.add_argument("command", choices=("develop", "freeze", "evaluate", "report", "run-all"))
    parser.add_argument("--workspace", default="workspaces/micro-ltm-2")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "develop":
        output = develop(workspace)
    elif args.command == "freeze":
        output = freeze(workspace)
    elif args.command == "evaluate":
        output = evaluate_locked(workspace)
        output = output["metrics"]
    elif args.command == "report":
        output = report(workspace)
    else:
        if not (workspace / "selected.json").exists():
            develop(workspace)
        if not (workspace / "frozen-manifest.json").exists():
            freeze(workspace)
        if not (workspace / "locked-results.json").exists():
            evaluate_locked(workspace)
        output = report(workspace)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0
