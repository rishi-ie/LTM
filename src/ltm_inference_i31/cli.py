from __future__ import annotations

import argparse
from pathlib import Path

from . import lifecycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("dataset-build", "develop", "controls", "stress-develop", "freeze", "prompt-audit"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--checkpoint", default="workspaces/ltm-inference-i3-1-r13/selected-kernel.pt")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(); workspace = Path(args.workspace)
    if args.command == "prompt-audit":
        from .prompt_audit import main as audit_main
        return audit_main(workspace, Path(args.checkpoint))
    {"dataset-build": lifecycle.dataset_build, "develop": lifecycle.develop, "controls": lifecycle.controls, "stress-develop": lifecycle.stress_develop, "freeze": lifecycle.freeze}[args.command](workspace)
    return 0
