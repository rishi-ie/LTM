from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def render(workspace: Path) -> str:
    result = json.loads((workspace / "locked-results.json").read_text())
    checks = result["checks"]
    return f"""# G1 — Executable Conversational Topology Report

## Result

**Classification: {result['classification']}**

This deterministic schema experiment tested a fresh 80-fixture locked suite after an
independent 80-fixture development run. It used only Python's standard library
and SQLite. It did not use a language model, embeddings, latent optimization or
a decoder.

## Locked measurements

| Check | Result |
| --- | ---: |
| Valid fixture acceptance | {checks['valid_acceptance']}/{checks['valid_total']} |
| Invalid fixture rejection | {checks['invalid_rejection']}/{checks['invalid_total']} |
| Canonical round trips | {checks['round_trip']}/{checks['valid_total']} |
| Exact operator checks | {checks['operator']}/{checks['valid_total']} |
| Valid verifier checks | {checks['verifier']}/{checks['valid_total']} |
| Adversarial verifier rejections | {checks['adversarial_rejection']}/{checks['valid_total']} |
| Version-1 migration checks | {checks['migration']}/16 |
| Field contracts | {'PASS' if result['field_contract_ok'] else 'FAIL'} |
| Replay hash equals stored hash | {result['snapshot_hash'] == result['replay_hash']} |
| Reverse-order hash equals stored hash | {result['snapshot_hash'] == result['reverse_hash']} |
| Runtime | {result['runtime_seconds']:.4f} s |
| Peak RSS | {result['peak_rss_mb']:.2f} MB |

## Conclusion boundary

{'The registered initial conversational topology is a stable executable internal language under this controlled schema test. G2, natural-language topology compilation, is authorized.' if result['classification'] == 'G1-A' else 'The registered topology did not satisfy every mechanical G1 gate. G2 is not authorized until the failed condition is fixed and the locked experiment is rerun in a fresh workspace.'}

This result does not establish unrestricted-language compilation, prompt
addressing, active-frontier coverage, latent optimization, decoder quality or
100M-context scaling.
"""


def report(workspace: Path) -> dict[str, object]:
    text = render(workspace)
    (workspace / "g1-topology-report.md").write_text(text)
    (ROOT / "docs" / "g1-topology-report.md").write_text(text)
    return {"report": str(ROOT / "docs" / "g1-topology-report.md")}
