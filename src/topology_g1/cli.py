from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g1")
    parser.add_argument("command", choices=("develop", "freeze", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g1")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "develop":
        result = develop(workspace)
    elif args.command == "freeze":
        result = freeze(workspace)
    elif args.command == "evaluate":
        result = evaluate_locked(workspace)
    elif args.command == "report":
        result = report(workspace)
    elif args.command == "verify":
        result = verify(workspace)
    else:
        if not (workspace / "development-results.json").exists():
            develop(workspace)
        if not (workspace / "frozen-manifest.json").exists():
            freeze(workspace)
        if not (workspace / "locked-results.json").exists():
            evaluate_locked(workspace)
        result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0
