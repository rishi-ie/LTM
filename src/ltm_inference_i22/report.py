"""I2.2 measured report."""

from __future__ import annotations

import json
from pathlib import Path


def write_report(workspace: Path, destination: Path) -> None:
    dev = json.loads((workspace / "development-results.json").read_text())
    locked = json.loads((workspace / "locked-results.json").read_text())
    verify = json.loads((workspace / "verification.json").read_text())
    if not verify["frozen_source_matches"] or locked["routing"]["identity_route_present"]:
        classification = "I2.2-G — INTEGRITY FAILURE"
    elif locked["routing"]["next_body_recall_at_64"] < .99:
        classification = "I2.2-B — GLOBAL ROUTING FAILURE"
    elif locked["metrics"]["answerable_exactness"] < .9:
        classification = "I2.2-C — GLOBAL COMPOSITION FAILURE"
    else:
        classification = "I2.2-A — GLOBAL CONTENT-ADDRESSED NAVIGATION PASS"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"""# I2.2 — Global Content-Addressed Minimap Navigation

**{classification}**

| Metric | Development | Locked |
| --- | ---: | ---: |
| Next-body recall@64 | {dev['routing']['next_body_recall_at_64']:.4f} | {locked['routing']['next_body_recall_at_64']:.4f} |
| Cross-leaf change rate | {dev['routing']['cross_leaf_change_rate']:.4f} | {locked['routing']['cross_leaf_change_rate']:.4f} |
| Terminal exactness | {dev['metrics']['answerable_exactness']:.4f} | {locked['metrics']['answerable_exactness']:.4f} |
| Accepted precision | {dev['metrics']['accepted_precision']:.4f} | {locked['metrics']['accepted_precision']:.4f} |
| Safe coverage | {dev['metrics']['safe_coverage']:.4f} | {locked['metrics']['safe_coverage']:.4f} |

I2.2 routes only from the current learned vector through a complete vector tree;
the runtime has no identity-to-leaf map, relation labels, closure, candidate
list, or factual write. This is a controlled terminal-completion result only.
""", encoding="utf-8")
