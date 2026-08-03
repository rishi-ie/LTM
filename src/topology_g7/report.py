from __future__ import annotations

import json
from pathlib import Path


def report(workspace: Path) -> dict:
    data = json.loads((workspace / "locked-results.json").read_text()); metrics = data["metrics"]
    table = "\n".join(f"| {name.replace('_', ' ')} | {value:.6g} |" for name, value in metrics.items() if not isinstance(value, dict))
    controls = "\n".join(f"| {name.replace('_', ' ')} | {value:.6g} |" for name, value in metrics["controls"].items())
    text = f"""# G7 — Structured Latent Optimizer and Soft Reconciliation Report

## Classification

**{data['classification']}**

## What was tested

G7 held the G6 exact result fixed, enumerated at most two admissible soft
branches in this compact suite, then optimized confidence, preference,
reference and uncertainty variables with deterministic projected gradient
descent. An independently constructed quadratic oracle checked the selected
branch, state and energy. The 240 locked cases covered authority conflicts,
ambiguous references, observations, preferences, uncertainty and mixed G6
proofs.

| Metric | Result |
| --- | ---: |
{table}

## Controls

| Control | Decision accuracy |
| --- | ---: |
{controls}

Runtime: `{data['runtime_seconds']:.4f} s`; peak RSS: `{data['peak_rss_mb']:.2f} MB`; repeated-result agreement: `{data['repeated_result_agreement']}`.

## Bounded conclusion

This is a controlled mechanics result. It demonstrates that the registered
structured optimizer can reconcile the generated soft signals without changing
the G6 hard conclusion, and agrees with an independent quadratic oracle. It
does **not** demonstrate natural-language ingestion, a learned latent geometry,
decoder quality, or that soft optimization itself derives G6 logical truths.
"""
    path = Path(__file__).resolve().parents[2] / "docs" / "g7-optimizer-report.md"; path.write_text(text); return {"classification": data["classification"], "report": str(path)}
