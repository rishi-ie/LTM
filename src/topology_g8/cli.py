from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, verify_run
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G8 memory-bounded field experiment")
    parser.add_argument(
        "command",
        choices=("develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"),
    )
    parser.add_argument("--workspace", default="workspaces/topology-g8")
    parser.add_argument("--offline", action="store_true", help="required by the frozen experiment contract")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()

    if args.command == "develop":
        output = develop(workspace)
    elif args.command == "freeze":
        output = freeze(workspace)
    elif args.command == "locked-suite-build":
        output = locked_suite_build(workspace)
    elif args.command == "evaluate":
        output = evaluate_locked(workspace)
    elif args.command == "report":
        output = report(workspace)
    elif args.command == "verify":
        output = verify_run(workspace)
    else:
        if not (workspace / "development-results.json").exists():
            develop(workspace)
        if not (workspace / "frozen-manifest.json").exists():
            freeze(workspace)
        if not (workspace / "locked" / "requests.json").exists():
            locked_suite_build(workspace)
        if not (workspace / "locked-results.json").exists():
            evaluate_locked(workspace)
        output = report(workspace)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0
