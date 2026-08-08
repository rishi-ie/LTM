from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluate import (
    benchmark_fetch,
    develop,
    evaluate_core,
    evaluate_public,
    freeze,
    locked_suite_build,
    preflight,
    verify_run,
)
from .report import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G14 unified benchmark")
    parser.add_argument("command", choices=("benchmark-fetch", "preflight", "develop", "freeze", "locked-suite-build", "evaluate-core", "evaluate-public", "report", "verify", "run-all"))
    parser.add_argument("--workspace", default="workspaces/topology-g14")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv); workspace = Path(args.workspace).resolve(); workspace.mkdir(parents=True, exist_ok=True)
    if args.command == "benchmark-fetch": output = benchmark_fetch(workspace)
    elif args.command == "preflight": output = preflight(workspace)
    elif args.command == "develop": output = develop(workspace)
    elif args.command == "freeze": output = freeze(workspace)
    elif args.command == "locked-suite-build": output = locked_suite_build(workspace)
    elif args.command == "evaluate-core": output = evaluate_core(workspace)
    elif args.command == "evaluate-public": output = evaluate_public(workspace)
    elif args.command == "report": output = report(workspace)
    elif args.command == "verify": output = verify_run(workspace)
    else:
        if not (workspace / "benchmark-sources" / "manifest.json").exists(): raise RuntimeError("BENCHMARK_FETCH_REQUIRED")
        preflight(workspace)
        if not (workspace / "development-results.json").exists(): develop(workspace)
        if not (workspace / "frozen-manifest.json").exists(): freeze(workspace)
        if not (workspace / "locked" / "build.json").exists(): locked_suite_build(workspace)
        if not (workspace / "core-results.json").exists(): evaluate_core(workspace)
        if not (workspace / "public-results.json").exists(): evaluate_public(workspace)
        output = report(workspace)
    print(json.dumps(output, indent=2, sort_keys=True)); return 0
