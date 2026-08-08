from __future__ import annotations

import argparse
from pathlib import Path

from .experiment import dataset_build, model_check, run


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m ltm_limit_l6")
    parser.add_argument("command", choices=("model-check", "dataset-build", "kernel-develop", "controls-develop", "calibrate", "freeze", "locked-suite-build", "evaluate", "controls", "intervene", "text-evaluate", "verify", "report", "resume", "run-all"))
    parser.add_argument("--workspace", type=Path, default=Path("workspaces/ltm-limit-l6-r1"))
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.command == "model-check":
        model_check(args.workspace)
    elif args.command == "dataset-build":
        dataset_build(args.workspace, args.limit)
    elif args.command in {"evaluate", "controls", "run-all"}:
        run(args.workspace, limit=args.limit)
    else:
        raise SystemExit(
            f"L6 stage {args.command!r} is not implemented; no artifact was written. "
            "Use model-check, dataset-build or the bounded smoke evaluate path."
        )


if __name__ == "__main__":
    main()
