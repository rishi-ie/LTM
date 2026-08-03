from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, verify
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="topology_g3"); parser.add_argument("command", choices=("develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all")); parser.add_argument("--workspace", default="workspaces/topology-g3"); parser.add_argument("--offline", action="store_true"); args = parser.parse_args(argv); work = Path(args.workspace).resolve()
    if args.command == "develop": value = develop(work)
    elif args.command == "freeze": value = freeze(work)
    elif args.command == "locked-suite-build": value = locked_suite_build(work)
    elif args.command == "evaluate": value = evaluate_locked(work)
    elif args.command == "report": value = report(work)
    elif args.command == "verify": value = verify(work)
    else:
        if not (work / "development-results.json").exists(): develop(work)
        if not (work / "frozen-manifest.json").exists(): freeze(work)
        if not (work / "locked" / "inputs.jsonl").exists(): locked_suite_build(work)
        if not (work / "locked-results.json").exists(): evaluate_locked(work)
        value = report(work)
    print(json.dumps(value, indent=2, sort_keys=True, default=str)); return 0
