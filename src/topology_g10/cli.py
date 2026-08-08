from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import develop, evaluate_locked, freeze, locked_suite_build, model_check, verify_run
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G10 compact verified decoder")
    parser.add_argument("command", choices=("model-check", "develop", "freeze", "locked-suite-build", "evaluate", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g10"); parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve()
    if args.command == "model-check": output = model_check(workspace)
    elif args.command == "develop": output = develop(workspace)
    elif args.command == "freeze": output = freeze(workspace)
    elif args.command == "locked-suite-build": output = locked_suite_build(workspace)
    elif args.command == "evaluate": output = evaluate_locked(workspace)
    elif args.command == "report": output = report(workspace)
    elif args.command == "verify": output = verify_run(workspace)
    else:
        checked = model_check(workspace)
        if checked["status"] != "ready": output = {"classification": "BLOCKED-RUNTIME", "reason": checked.get("reason")}
        else:
            if not (workspace / "development-results.json").exists(): develop(workspace)
            if not (workspace / "frozen-manifest.json").exists(): freeze(workspace)
            if not (workspace / "locked" / "bundles.json").exists(): locked_suite_build(workspace)
            if not (workspace / "locked-results.json").exists(): evaluate_locked(workspace)
            if not (workspace / "verification.json").exists(): verify_run(workspace)
            output = report(workspace)
    print(json.dumps(output, indent=2, sort_keys=True)); return 0
