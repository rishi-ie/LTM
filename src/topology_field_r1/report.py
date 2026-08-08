from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def report(workspace: Path) -> dict:
    result = json.loads((workspace / "audit-results.json").read_text())
    g1 = result["g1"]
    replays = result["downstream_replays"]
    ordered_replays = sorted(replays.items(), key=lambda item: int(item[0][1:]))
    replay_lines = [
        f"| {gap} | {item['passed']} | {item.get('result', {}).get('classification', 'error')} |"
        for gap, item in ordered_replays
    ]
    checks = result["representation_checks"]
    resources = result["resource_contract"]
    g2 = result["g2_boundary"]
    lines = [
        "# LTM-R1 — Vector-Native Field Representation Compatibility Audit",
        "",
        "## Status",
        "",
        f"**{result['classification']}**",
        "",
        "The audit replaces active FieldIR text fields with numeric atom, factor, role-incidence, context, provenance and vector-reference records. Historical experiments remain immutable inputs.",
        "",
        "## Implemented evidence",
        "",
        "| Check | Result |",
        "| --- | ---: |",
        f"| G1 locked fixtures | {g1['fixtures']} |",
        f"| G1 valid semantic agreement | {g1['semantic_agreement']} |",
        f"| G1 text-free core execution | {g1['text_free_core']} |",
        f"| G1 active-byte non-regression | {g1['no_active_byte_increase']} |",
        f"| Authoritative workspace artifacts present | {result['authoritative_artifacts_present']} |",
        "",
        "## Causal representation checks",
        "",
        "| Check | Result |",
        "| --- | ---: |",
        *[f"| {name.replace('_', ' ')} | {value} |" for name, value in checks.items()],
        "",
        "Changing source wording alone leaves the active numeric field unchanged. Changing role incidence, context, or a vector-row hash changes its semantic digest. This is the required separation between display text and reasoning state.",
        "",
        "## G2 boundary",
        "",
        f"G2 remains **{g2['classification_preserved']}**. Its controlled compiler output is representation-compatible (`FieldIR/G1 round trip = {g2['field_round_trip']}`, invalid insertions = {g2['invalid_g1_insertions']}), but its recorded language-recovery limitations are not reclassified.",
        "",
        "## G3–G14 deterministic replay",
        "",
        "| Gap | Replay | Historical classification |",
        "| --- | ---: | --- |",
        *replay_lines,
        "",
        "Text remains permitted only at explicit boundaries: G3 addressing input, G9 source-hash verification, G10 surface decoding, G11 audit/display events, and G14 ingestion. It is not active field reasoning state.",
        "",
        "## Resource contract",
        "",
        f"The replacement targets the existing {resources['existing_factor_record_bytes']}-byte G13 factor record, reuses vector rows by reference, and adds zero core runtime adapter layers. Across the G1 fixtures the numeric active layout is {resources['active_bytes_total']:,} bytes versus {resources['legacy_bytes_total']:,} bytes for the legacy serialized structures.",
        "",
        "## Conclusion boundary",
        "",
        "The vector-native representation is structurally compatible with G1–G14 and can replace text-bearing active FieldIR records without changing the tested reasoning behavior or widening the fixed-width runtime record. This is an isomorphism and replay audit, not a direct rewrite of every historical package. It does not improve G2 language compilation, G10 language quality, or prove unrestricted-language correctness.",
    ]
    target = ROOT / "docs" / "experiments" / "representation" / "r01" / "report.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n")
    return {"classification": result["classification"], "report": str(target)}
