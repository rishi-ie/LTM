from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    core = json.loads((workspace / "core-results.json").read_text()); public = json.loads((workspace / "public-results.json").read_text())
    full, rag = core["metrics"]["full_controlled_ltm"], core["metrics"]["hybrid_rag"]
    text = f"""# G14 — Unified Benchmark Report

## Two verdicts

| Verdict | Result |
| --- | --- |
| Structured controlled architecture | `{core['controlled_architecture']}` |
| Raw-language product path | `{public['product_readiness']}` |

The verdicts intentionally answer different questions. The controlled result
uses public, evaluator-separated typed facts and rules; the runtime cannot read
the gold conclusion. It exercises G3 addressing, G4 traversal, G5 widening,
G6 exact execution, G7 reconciliation, and G9 independent verification. It
does not establish raw-language compilation, fluent model decoding, or broad
benchmark quality.

## Controlled locked result

| Method | Accuracy | Required-factor recall |
| --- | ---: | ---: |
| Full controlled LTM | {full['accuracy']:.3f} | {full['required_factor_recall']:.3f} |
| Bounded retrieval control | {rag['accuracy']:.3f} | {rag['required_factor_recall']:.3f} |
| No exact propagation | {core['metrics']['no_exact_propagation']['accuracy']:.3f} | {core['metrics']['no_exact_propagation']['required_factor_recall']:.3f} |
| No session overlay | {core['metrics']['no_session_overlay']['accuracy']:.3f} | {core['metrics']['no_session_overlay']['required_factor_recall']:.3f} |
| No coverage widening | {core['metrics']['no_coverage']['accuracy']:.3f} | {core['metrics']['no_coverage']['required_factor_recall']:.3f} |

The paired bootstrap interval for full minus bounded retrieval is
`[{core['bootstrap_full_minus_rag']['lower']:.3f}, {core['bootstrap_full_minus_rag']['upper']:.3f}]`.
The independent G9 verifier rejected `{core['verifier_attack_rejection']:.3f}`
of deliberately fabricated hard-state bundles. Semantic replay matched exactly;
the measured peak RSS was `{core['peak_rss_mb']:.1f} MB`, below the 20-GB ceiling.

G7 soft reconciliation was executed but did not change the symbolic labels in
this hard-reasoning suite; this run therefore does not demonstrate a separate
end-to-end answer-quality contribution from soft optimization. G8 batching,
G11 lifecycle, G12 persistence, and G13 scaling remain upstream component
evidence rather than newly composed per-request claims in this small benchmark.

## Public benchmark status

LongMemEval items discovered: `{public['public_counts'].get('longmemeval', 0)}`.
LoCoMo QA items discovered: `{public['public_counts'].get('locomo', 0)}`.

The current raw-language product path is **not ready** because the frozen G2,
G2.1 and G10 results already fail their required input and decoder gates. Public
data was catalogued without injecting its answers or evidence into runtime.
Published online scores are contextual references only and do not affect this
classification.
"""
    path = ROOT / "docs" / "experiments" / "gaps" / "g14" / "report.md"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    return {"report": str(path), "controlled": core["controlled_architecture"], "product": public["product_readiness"]}
