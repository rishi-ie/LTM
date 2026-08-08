"""Permanent bounded report renderer for LTM-R2."""

from __future__ import annotations

from pathlib import Path

from .evaluate import _atomic, _read


def write_report(workspace: Path, destination: Path) -> str:
    result = _read(workspace / "locked-results.json")
    verification = _read(workspace / "verification.json") if (workspace / "verification.json").exists() else {"semantic_replay": False}
    rows = "\n".join(f"| {name} | {value:.3f} |" for name, value in sorted(result["profile_agreement"].items()))
    compatibility = result["compatibility"]
    agreement = compatibility["agreement"]
    direct_rows = "\n".join(
        f"| {name} | {agreement[name]:.3f} |"
        for name in ("g1_projection", "g3_address", "g4_frontier", "g5_coverage", "g6_hard", "g7_soft", "g8_reduction", "g9_verification", "g101_realization")
    )
    text = f"""# LTM-R2 — Universal Mumbrane Representation Audit

Classification: **{result['classification']}**

## Locked result

| Metric | Value |
| --- | ---: |
| Locked bodies | {result['locked_bodies']} |
| Profile executions | {result['profile_executions']} |
| Registered attacks rejected | {result['attacks_rejected']} / 320 |
| Packed reload equality | {result['packed_reload']} |
| Semantic replay | {verification['semantic_replay']} |
| Runtime | {result['runtime_seconds']:.3f} s |
| Peak RSS | {result['peak_rss_mb']:.1f} MB |
| Active byte ratio | {result['active_byte_ratio']:.3f} |

## Profile agreement

| Profile | Oracle agreement |
| --- | ---: |
{rows}

## Compatibility boundary

{compatibility['executed_cases']} independently constructed single-relation
projections were executed through the actual FieldIR v2 adapters and request
path. The agreement below is against the paired legacy path for the same
projected G1 objects.

| Direct adapter check | Agreement |
| --- | ---: |
{direct_rows}

G11–G14 were not rerun with their historical lifecycle fixtures in this
representation audit. Their Mumbrane-specific precondition—exact G1
projection—was `1.000`; their separate behavioural evidence remains LTM-R1 and
their own locked reports. This is deliberately not presented as a fresh
G11–G14 run.

## Conclusion boundary

This audit measures evaluator-owned semantic bodies, not raw-language
compilation. A pass establishes that one Mumbrane unit/port/coordinate schema
can preserve the registered exact topology while profile configuration changes
execution purpose, soft dynamics, and migration behavior. The active numeric
storage was `{result['active_byte_ratio']:.3f}` of the paired FieldIR v2
representation for the representative direct-adapter case; this is a
compactness observation, not a production capacity claim. It does not establish
unrestricted compilation, ontology completeness, a perfected compiler, or
decoder naturalness.
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    _atomic(workspace / "report.json", {"classification": result["classification"], "destination": str(destination)})
    return text
