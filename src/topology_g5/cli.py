from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g5")
    parser.add_argument("command", choices=("develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g5")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve()
    if args.command == "develop": value = develop(workspace)
    elif args.command == "freeze": value = freeze(workspace)
    elif args.command == "locked-suite-build": value = locked_suite_build(workspace)
    elif args.command == "evaluate": value = evaluate_locked(workspace)
    elif args.command == "report": value = report(workspace)
    elif args.command == "verify": value = verify(workspace)
    else:
        if not (workspace / "development-results.json").exists(): develop(workspace)
        if not (workspace / "frozen-manifest.json").exists(): freeze(workspace)
        if not (workspace / "locked" / "cases.json").exists(): locked_suite_build(workspace)
        if not (workspace / "locked-results.json").exists(): evaluate_locked(workspace)
        value = report(workspace)
    print(json.dumps(value, indent=2, sort_keys=True)); return 0
