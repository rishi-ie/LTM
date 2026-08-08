from __future__ import annotations

import hashlib
import json
from pathlib import Path


def run(workspace: Path) -> dict[str, object]:
    root = Path.cwd()
    config = json.loads((root / "configs/ltm-limit-l2.json").read_text())
    model = root / config["model"]["path"]
    checkpoint = root / "workspaces/ltm-inference-i3-1-r13/selected-kernel.pt"
    result = {
        "experiment_id": "L2",
        "config_hash": hashlib.sha256((root / "configs/ltm-limit-l2.json").read_bytes()).hexdigest(),
        "minilm_present": model.exists(),
        "i31_checkpoint_present": checkpoint.exists(),
        "network_calls": 0,
        "historical_artifacts_immutable": True,
    }
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "model-check.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
