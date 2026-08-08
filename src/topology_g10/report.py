from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def _table(values: dict) -> str:
    return "\n".join(f"| {name.replace('_', ' ')} | {value:.8g} |" for name, value in values.items())


def _ledger_section(data: dict) -> str:
    classification, metrics = data["classification"], data["metrics"]
    if classification == "BLOCKED-RUNTIME":
        return """## 14. G10 — Compact verified conversational decoder

### Mechanical classification

**`BLOCKED-RUNTIME`**

The pinned Qwen run could not access Metal. No substitute decoder was used and
no technical decoder metrics were recorded. A fresh normal-Mac Metal execution
remains required.
"""
    return f"""## 14. G10 — Compact verified conversational decoder

### Locked result

- Experiment: [G10 specification](../experiments/gaps/g10/specification.md)
- Authoritative report: [G10 locked report](../experiments/gaps/g10/report.md)
- Locked suite: `64` verified opaque fictional bundles; controls: `32` no-state
  and `32` state-only generations; validator attacks: `64`.

| Measurement | Result |
| --- | ---: |
{_table(metrics)}

### Mechanical classification

**`{classification}`**

This is a bounded technical decoder result with deterministic authorization,
one repair attempt and verified fallback. Human naturalness, raw-language
compilation, native latent prefixes and production conversation memory remain
unmeasured.
"""


def _update_ledger(data: dict) -> None:
    ledger = ROOT / "docs" / "roadmap" / "results-ledger.md"
    text = ledger.read_text()
    classification = data["classification"]
    status = "**BLOCKED**" if classification == "BLOCKED-RUNTIME" else ("**PASS (technical)**" if classification in ("G10-T-A — TECHNICAL PASS", "G10-T-E — STATE CHANNEL NOT USEFUL") else "**FAILED**")
    consequence = "Requires a normal Mac Metal session" if classification == "BLOCKED-RUNTIME" else "G11 is authorized only for a technical pass"
    text = re.sub(r"\| G10 \| Conversational decoder \| .*", f"| G10 | Conversational decoder | {status} | `{classification}` | {consequence} |", text)
    section = _ledger_section(data)
    text, replaced = re.subn(r"## 14\. G10 — Compact verified conversational decoder.*?(?=## 15\. Next experiment decision)", section + "\n", text, flags=re.DOTALL)
    if replaced != 1:
        raise RuntimeError("G10_LEDGER_SECTION_NOT_FOUND")
    _atomic(ledger, text)


def report(workspace: Path) -> dict:
    data = json.loads((workspace / "locked-results.json").read_text())
    verification = json.loads((workspace / "verification.json").read_text()) if (workspace / "verification.json").exists() else {}
    if data["classification"] == "BLOCKED-RUNTIME":
        text = f"""# G10 — Compact Verified Conversational Decoder Report

## Classification

**BLOCKED-RUNTIME**

The local Qwen hashes, datasets, worker, validator, repair limit and fallback
are ready, but the pinned runtime could not access Metal:

```text
{data['reason']}
```

No alternate backend or model was used. No decoder generation was scored, so
this is not evidence about Qwen's conversational faithfulness.
"""
    else:
        attacks = json.loads((workspace / "validator-attacks.json").read_text())["attacks"]
        counterexamples = json.loads((workspace / "counterexamples.json").read_text())["counterexamples"]
        text = f"""# G10 — Compact Verified Conversational Decoder Report

## Classification

**{data['classification']}**

## Locked technical-faithfulness result

The pinned Qwen 0.5B received 64 bounded G9-authorized bundles. A separate
runtime worker saw only public bundles; the evaluator read hidden expected
claims afterwards. Every final response passed authorization, was repaired
once, or used a deterministic verified fallback. Human naturalness was not
scored.

| Metric | Result |
| --- | ---: |
{_table(data['metrics'])}

## Structured-state diagnostic

| Diagnostic | Result |
| --- | ---: |
{_table(data['state_channel'])}

Deterministic semantic replay: `{verification.get('identical_results')}`;
metric replay: `{verification.get('identical_metrics')}`. Runtime:
`{data['runtime_seconds']:.3f} s`; peak RSS: `{data['peak_rss_mb']:.2f} MB`.

The validator rejected `{sum(not item['accepted'] for item in attacks)}/{len(attacks)}`
registered adversarial responses. Retained model failures requiring repair or
fallback: `{len(counterexamples)}`.

## Bounded conclusion

This classification describes only controlled verified-bundle rendering. It
does not establish unrestricted language compilation, latent-prefix decoding,
human-rated naturalness, integrated conversation memory or 100M-context
serving.
"""
    path = ROOT / "docs" / "experiments" / "gaps" / "g10" / "report.md"
    _atomic(path, text)
    _update_ledger(data)
    return {"classification": data["classification"], "report": str(path)}
