from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import (
    develop,
    evaluate_locked,
    freeze,
    locked_suite_build,
    preflight_run,
    verify_run,
)
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G13 disk-backed 1M-to-100M scale experiment")
    parser.add_argument("command", choices=("preflight", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g13")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve()
    if args.command == "preflight": output = preflight_run(workspace)
    elif args.command == "develop": output = develop(workspace)
    elif args.command == "freeze": output = freeze(workspace)
    elif args.command == "locked-suite-build": output = locked_suite_build(workspace)
    elif args.command == "evaluate": output = evaluate_locked(workspace)
    elif args.command == "report": output = report(workspace)
    elif args.command == "verify": output = verify_run(workspace)
    else:
        preflight_run(workspace)
        if not (workspace / "development-results.json").exists(): develop(workspace)
        if not (workspace / "frozen-manifest.json").exists(): freeze(workspace)
        if not (workspace / "locked" / "build.json").exists(): locked_suite_build(workspace)
        if not (workspace / "locked-results.json").exists(): evaluate_locked(workspace)
        output = report(workspace)
    print(json.dumps(output, indent=2, sort_keys=True)); return 0
