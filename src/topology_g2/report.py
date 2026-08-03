from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict[str, str]:
    result = json.loads((workspace / "locked-results.json").read_text())
    metrics = result["metrics"]
    text = f"""# G2 — Natural-Language Topology Compiler Report

## Result

**Classification: {result['classification']}**

G2 tested the frozen local Qwen 2.5 0.5B 4-bit MLX model on a fresh locked
300-case controlled natural-language suite. The model proposed JSON IR; strict
deterministic validation was allowed to normalize and validate it but not to
invent missing meaning.

## Locked measurements

| Measurement | Result |
| --- | ---: |
| Claim tuple F1 | {metrics['claim_f1']:.3f} |
| Relation direction accuracy | {metrics['relation_direction_accuracy']:.3f} |
| Named-role exact match | {metrics['named_role_exact_match']:.3f} |
| Entity-link accuracy | {metrics['entity_link_accuracy']:.3f} |
| Coreference accuracy | {metrics['coreference_accuracy']:.3f} |
| Scope accuracy | {metrics['scope_accuracy']:.3f} |
| Temporal accuracy | {metrics['temporal_accuracy']:.3f} |
| Source-span F1 | {metrics['source_span_f1']:.3f} |
| Provenance integrity | {metrics['provenance_integrity']:.3f} |
| Correct disposition | {metrics['disposition_accuracy']:.3f} |
| Exact topology agreement | {metrics['topology_agreement']:.3f} |
| Direct valid IR | {metrics['direct_valid_ir']:.3f} |
| Final valid IR | {metrics['final_valid_ir']:.3f} |
| Repair rate | {metrics['repair_rate']:.3f} |
| Runtime | {result['runtime_seconds']:.2f} s |
| Peak RSS | {result['peak_rss_mb']:.2f} MB |

## Conclusion boundary

{'The selected 0.5B compiler boundary passed every registered G2 gate and G3 is authorized.' if result['classification'] == 'G2-A' else 'The selected 0.5B compiler boundary did not pass every registered G2 gate. This does not invalidate G1; it means this extraction mechanism is not yet sufficient for G3.'}
"""
    (workspace / "g2-compiler-report.md").write_text(text)
    (ROOT / "docs" / "g2-compiler-report.md").write_text(text)
    return {"report": str(ROOT / "docs" / "g2-compiler-report.md")}
