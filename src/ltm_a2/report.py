"""Permanent human-readable report for the fresh architecture audit."""

from __future__ import annotations

import json
from pathlib import Path


def _metric(result: dict[str, object], key: str) -> str:
    return str(result.get(key, "not recorded"))


def write_report(workspace: Path, destination: Path) -> None:
    result = json.loads((workspace / "audit-results.json").read_text(encoding="utf-8"))
    evidence_rows = []
    for item in result["historical_evidence"]:
        artifact = item["artifact"]
        detail = "replayed artifact available" if artifact.get("exists") else "report/ledger evidence"
        evidence_rows.append(f"| {item['id']} | {item['ledger_status']} | {item['boundary']} | {detail} |")
    scenario_rows = []
    for scenario in result["representation_scenarios"]:
        passes = all(value["oracle_agreement"] for value in scenario["profiles"].values())
        scenario_rows.append(f"| {scenario['scenario']} | {', '.join(scenario['relation_types'])} | {scenario['units']} | {passes} |")
    finding_rows = []
    for finding in result["critical_findings"]:
        finding_rows.append(f"- **{finding.get('id', 'G2.14_HANDOFF')} — {finding['verdict']}:** {finding['interpretation']}")
    research_rows = []
    for paper in result["research_basis"]:
        research_rows.append(f"- [{paper['citation']}]({paper['url']}) — {paper['support']}.")
    text = f"""# Fresh LTM Architecture Viability Audit

Date: `2026-08-06`  
Audit revision: `{result['audit_revision']}`  
Method: fresh source/report inspection plus new evaluator-owned semantic-body
replays. No model was trained and no historical locked result was overwritten.

## Bottom line

**Controlled LTM v1: {result['verdicts']['controlled_ltm_v1']}.** The exact
topology, Mumbrane/FieldIR representation, profile execution, addressing,
hard/soft execution, verification, constrained realization, lifecycle and
storage components have credible controlled evidence.

**Unrestricted/full vision: {result['verdicts']['unrestricted_full_vision']}.**
The decisive unsolved boundary is safe raw reasoning-language compilation, not
the packed field representation. Product serving/isolation (G15) is also not
yet measured.

## Forecasts

These are engineering forecasts after the fresh audit, not pass metrics:

| Outcome | Forecast |
| --- | ---: |
| Exact representation and profile execution | {result['engineering_forecasts']['exact_representation_and_profile_execution']:.0%} |
| Structured topology to verified answer | {result['engineering_forecasts']['structured_topology_to_verified_answer']:.0%} |
| Controlled user-facing v1 with current compilers | {result['engineering_forecasts']['controlled_user_facing_v1_with_current_compilers']:.0%} |
| Bounded-domain product after the writer and G15 | {result['engineering_forecasts']['bounded_domain_product_after_writer_and_g15']:.0%} |
| Robust general raw reasoning compiler with the current small encoder | {result['engineering_forecasts']['robust_general_raw_reasoning_compiler_with_current_small_encoder']:.0%} |
| Full general LTM vision with the current known architecture | {result['engineering_forecasts']['full_general_ltm_vision_with_current_known_architecture']:.0%} |

## Evidence inventory

| Area | Ledger state | Proven boundary | Evidence source |
| --- | --- | --- | --- |
{chr(10).join(evidence_rows)}

The G2 result must be read as two distinct routes: G2.14 passed its narrow
supplied-span conversational acceptance boundary, while G2.5 is a deliberately
adopted provisional reasoning baseline despite its failed reliability gate.
Neither result establishes unrestricted raw-language reasoning compilation.

## Fresh representation replay

Nine fresh semantic bodies were compiled into Mumbrane programs and executed
under reasoning, planning, evidence, and conversation profiles. Each result was
compared against the independent semantic-body oracle. This validates the
representation/configuration path, not natural-language extraction.

| Scenario | Active relations in generated body | Mumbrane units | All profile/oracle agreements |
| --- | --- | ---: | --- |
{chr(10).join(scenario_rows)}

Overall replay agreement: `{result['representation_scenario_agreement']}`.

## What a prompt flow means in the present system

1. **“Prefer concise answers.”** A supplied semantic span is classified as a
   session preference, candidate-resolved, then safely committed only if every
   threshold and margin passes. The conversation profile may alter answer form;
   it cannot make a factual claim true.
2. **“Actually, Project A replaces Project B.”** The compiler must identify one
   active target. If it cannot, it asks for clarification; if it can, the exact
   `supersedes` port is stored, and a later request sees the revised item.
3. **“Does A imply B?”** A reasoning compiler would have to ground `A`, `B`,
   operator `implies`, named roles and scope before G6 can derive anything.
   This is the presently weak boundary: G2.5 has not demonstrated it safely
   from arbitrary raw text.
4. **“Evidence E supports C, but F opposes C.”** Exact ports preserve the two
   evidence factors. G6 never turns the soft geometry into a hard fact; G7
   reconciles the confidence and G9 must disclose tension before G10.1 realizes
   only authorized claims.
5. **Changing a profile from reasoning to planning.** The same Mumbrane units
   remain stored. A new compiled profile changes active operators and soft
   objectives; it changes the execution hash, not the semantic substrate hash.
   If the new purpose needs missing information, the contract requires source
   recompilation rather than inventing a default.

## Critical findings

{chr(10).join(finding_rows)}

The first finding is especially consequential for implementation planning: G2.14
can be used as a conservative conversational routing/authorization module, but
not yet cited as an end-to-end compiler-to-Mumbrane handoff. That adapter must
be implemented and independently tested before it becomes an active runtime
writer.

## Research grounding

{chr(10).join(research_rows)}

These papers support individual design choices, not a proof of the architecture
as a whole. In particular, none establishes that a small encoder can reliably
compile unrestricted natural language into this ontology.

## Next engineering decision

Proceed with the controlled v1 integration only behind the existing exact,
atomic, verifier-gated boundary. Prioritize (1) a real supplied-span G2.14 to
G1/FieldIR/Mumbrane writer and integration test, (2) raw semantic span
segmentation as a separately measured module, (3) replacement of provisional
G2.5 reasoning compilation, and (4) G15 serving/isolation evaluation. Do not
claim a general raw-language reasoning compiler until that compiler passes a
fresh locked test at its intended boundary.
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
