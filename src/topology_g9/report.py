from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    data = json.loads((workspace / "locked-results.json").read_text()); metrics = data["metrics"]
    rows = "\n".join(f"| {name.replace('_', ' ')} | {value:.8g} |" for name, value in metrics.items() if not isinstance(value, dict))
    controls = "\n".join(f"| {name.replace('_', ' ')} | {value:.8g} |" for name, value in metrics["control_false_accept_rates"].items())
    text = f"""# G9 — Independent Result Verifier Report

## Classification

**{data['classification']}**

## Locked experiment

G9 evaluated 48 valid reasoning-result bundles and 48 plausible corrupted
twins. The verifier independently replayed hard proof steps, source hashes,
scope, supersession, conflicts, hard factors, coverage, provenance and the
registered separable soft objective. It imported no G5–G8 engine or optimizer.

| Measurement | Result |
| --- | ---: |
{rows}

## Weak authorization controls

Values are corrupted-bundle false-accept rates.

| Control | False accepts |
| --- | ---: |
{controls}

Runtime: `{data['runtime_seconds']:.4f} s`; peak RSS: `{data['peak_rss_mb']:.2f} MB`.

## Bounded conclusion

This result tests a small self-contained verifier contract. It {'demonstrates that the independently implemented verifier rejected every registered plausible corruption before authorizing a result.' if data['classification'].startswith('G9-A') else 'does not establish reliable independent authorization under the registered gates.'} It does not demonstrate cross-workspace integration, unrestricted-language correctness, decoder faithfulness, production security, or 100M-context reliability.
"""
    path = ROOT / "docs" / "experiments" / "gaps" / "g09" / "report.md"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
    return {"classification": data["classification"], "report": str(path)}
