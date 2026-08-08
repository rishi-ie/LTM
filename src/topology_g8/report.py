from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _number(value: float) -> str:
    return f"{value:.8g}"


def report(workspace: Path) -> dict:
    data = json.loads((workspace / "locked-results.json").read_text())
    metrics = data["metrics"]
    controls = metrics["control_failure_rates"]
    metric_rows = "\n".join(
        f"| {name.replace('_', ' ')} | {_number(value)} |"
        for name, value in metrics.items()
        if not isinstance(value, dict)
    )
    control_rows = "\n".join(
        f"| {name.replace('_', ' ')} | {_number(value)} |"
        for name, value in controls.items()
    )
    status = "PASS" if data["classification"].startswith("G8-A") else "FAILED"
    text = f"""# G8 — Memory-Bounded Batch Execution Report

## Classification

**{data['classification']}**

## Question

Can the same selected G6 hard program and G7 soft reconciliation problem be
loaded in physical blocks, reduced in any batch width or order, and solved once
globally without changing the result or materializing the whole field?

## Locked method

The locked run used 96 generated requests. Each request selected 16 physical
blocks of 256 factors from a 65,536-factor field. It compared nine candidate
executions: batch widths 1, 4 and 16 crossed with ascending, descending and
seeded-random block orders. The reference loaded all 16 selected blocks. The
candidate never averaged independently optimized block states: it unioned G6
hard objects, canonically reduced G7 soft contributions, then ran one global
soft optimization.

| Measurement | Result |
| --- | ---: |
{metric_rows}

## Incorrect-composition controls

The values below are failure rates against the reference. They test why a
global canonical reduction is necessary.

| Control | Failure rate |
| --- | ---: |
{control_rows}

Runtime: `{data['runtime_seconds']:.4f} s`; peak RSS: `{data['peak_rss_mb']:.2f} MB`.

## Bounded conclusion

This {status.lower()} result concerns the generated G6/G7-compatible field
only. {'It demonstrates that physical batching and delivery order do not change the registered hard result, soft state, branch/disposition, or decisive provenance while the configured residency cap is honored.' if status == 'PASS' else 'It does not establish an order-independent memory-bounded execution mechanism under the registered gates.'} It does **not** demonstrate arbitrary asynchronous message passing, full-field coverage, language ingestion, decoder quality, or 100-million-token serving.
"""
    path = ROOT / "docs" / "experiments" / "gaps" / "g08" / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return {"classification": data["classification"], "report": str(path)}
