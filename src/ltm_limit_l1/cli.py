from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import (
    boundary_evaluate,
    controls,
    evaluate,
    model_check,
    report,
    scale_evaluate,
    suite_build,
    verify,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("model-check", "suite-build", "freeze", "evaluate", "boundary-evaluate", "controls", "scale-evaluate", "verify", "report", "run-all"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(); workspace = Path(args.workspace); checkpoint = Path("workspaces/ltm-inference-i3-1-r13/selected-kernel.pt")
    if args.command == "model-check": result = model_check(workspace, checkpoint)
    elif args.command == "suite-build": result = suite_build(workspace)
    elif args.command == "freeze": result = {"status": "frozen", "checkpoint": str(checkpoint)}; (workspace / "frozen-manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    elif args.command == "evaluate": result = evaluate(workspace, checkpoint)
    elif args.command == "boundary-evaluate": result = boundary_evaluate(workspace, checkpoint)
    elif args.command == "controls": result = controls(workspace, checkpoint)
    elif args.command == "scale-evaluate": result = scale_evaluate(workspace, checkpoint)
    elif args.command == "verify": result = verify(workspace, checkpoint)
    elif args.command == "report": result = report(workspace)
    else:
        model_check(workspace, checkpoint); suite_build(workspace); result = evaluate(workspace, checkpoint); controls(workspace, checkpoint); verify(workspace, checkpoint); result = report(workspace)
    print(json.dumps(result, indent=2, sort_keys=True)); return 0
