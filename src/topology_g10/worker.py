from __future__ import annotations

import argparse
import os
from dataclasses import asdict
from pathlib import Path

from .decode import decode
from .generator import load, write_json
from .model import Qwen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="G10 public-only decoder worker")
    parser.add_argument("--bundles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    args = parser.parse_args(argv)
    bundle_path, output_path = Path(args.bundles).resolve(), Path(args.output).resolve()
    if "gold" in bundle_path.parts or "gold" in output_path.parts:
        raise RuntimeError("GOLD_PATH_DENIED")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    bundles = load(bundle_path.parent)
    model = Qwen(Path(args.model_path))
    settings = {"max_tokens": args.max_tokens}
    full = [asdict(decode(bundle, model, settings)) for bundle in bundles]
    panel = [bundle for number, bundle in enumerate(bundles) if number % 2 == 0]
    controls = {
        "no_state": [asdict(decode(bundle, model, settings, method="no_state")) for bundle in panel],
        "state_only": [asdict(decode(bundle, model, settings, method="state_only")) for bundle in panel],
    }
    write_json(output_path, {"full": full, "control_panel_ids": [bundle.bundle_id for bundle in panel], "controls": controls})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
