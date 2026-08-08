from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from .schemas import (
    AddressRecord,
    CandidateBundle,
    CoverageRecord,
    FactRecord,
    ProofRecord,
    RuleRecord,
    SoftFactorRecord,
    SoftRecord,
    SourceRecord,
    SupersessionRecord,
    row,
    text_hash,
)

ATTACKS = (
    "REVERSED_RELATION", "MISSING_PREMISE", "FABRICATED_CONCLUSION", "SCOPE_VIOLATION",
    "SUPERSEDED_EVIDENCE", "UNDISCLOSED_CONFLICT", "MISSING_HARD_FACTOR",
    "INSUFFICIENT_COVERAGE", "SOURCE_HASH_MISMATCH", "ASSISTANT_SELF_EVIDENCE",
    "SOFT_STATE_MISMATCH", "VERSION_MISMATCH",
)


def _soft(case: str) -> SoftRecord:
    factors = (
        SoftFactorRecord(f"{case}:soft:c0", "confidence", .5, 4.0, None, "src:user"),
        SoftFactorRecord(f"{case}:soft:c-left", "confidence", .8, 2.0, "left", "src:rule"),
        SoftFactorRecord(f"{case}:soft:c-right", "confidence", .1, 1.0, "right", "src:rule"),
        SoftFactorRecord(f"{case}:soft:p", "preference", .75, 2.0, None, "src:user"),
        SoftFactorRecord(f"{case}:soft:u", "uncertainty", .2, 3.0, None, "src:user"),
    )
    values = (("confidence", .6), ("preference", .75), ("uncertainty", .2))
    residuals = tuple((factor.factor_id, factor.weight * (dict(values)[factor.variable_id] - factor.target) ** 2) for factor in factors if factor.alternative_id in (None, "left"))
    return SoftRecord(("confidence", "preference", "uncertainty"), factors, ("left", "right"), values, "left", ("left", "right"), sum(item[1] for item in residuals), residuals)


def _base(seed: int, number: int, settings: dict) -> CandidateBundle:
    case = f"g9-{seed:x}-{number:03d}"
    attack_index = number % len(ATTACKS)
    # Keep the locked valid bases exactly balanced while ensuring the
    # undisclosed-conflict attack has a real conflict to hide.
    status_kind = 3 if attack_index == 5 else 1 if attack_index == 3 else number % 4
    target = f"{case}:goal"; negative = f"not:{target}"
    source_user = SourceRecord("src:user", "user", f"User evidence for {case}", "", 1.0)
    source_rule = SourceRecord("src:rule", "document", f"Registered rules for {case}", "", 1.0)
    source_assistant = SourceRecord("src:assistant", "assistant", f"Assistant wording for {case}", "", .25)
    sources = tuple(replace(item, content_hash=text_hash(item.text)) for item in (source_user, source_rule, source_assistant))
    scope = "fictional" if number % 3 == 1 else "conversation" if number % 3 == 2 else "global"
    addresses = (
        AddressRecord(f"{case}:address:a", "claim", scope, case, 0, None),
        AddressRecord(f"{case}:address:b", "claim", scope, case, 0, None),
        AddressRecord(f"{case}:address:goal", "claim", scope, case, 0, None),
    )
    facts = [
        FactRecord(f"{case}:fact:a", f"{case}:a", addresses[0].address_id, ("src:user",), scope, 0, None),
        FactRecord(f"{case}:fact:b", f"{case}:b", addresses[1].address_id, ("src:user",), scope, 0, None),
        FactRecord(f"{case}:fact:permit", f"{case}:permit", addresses[2].address_id, ("src:rule",), scope, 0, None),
        FactRecord(f"{case}:fact:old", f"{case}:old-a", addresses[0].address_id, ("src:user",), scope, 0, None),
        FactRecord(f"{case}:fact:new", f"{case}:a", addresses[0].address_id, ("src:user",), scope, 0, None),
    ]
    side = f"{case}:side"
    rules = [
        RuleRecord(f"{case}:rule:join", "conjoins", (f"{case}:a", f"{case}:b"), f"{case}:mid", scope, ("src:rule",)),
        RuleRecord(f"{case}:rule:end", "implies", (f"{case}:mid",), target if status_kind == 0 else side, scope, ("src:rule",)),
        RuleRecord(f"{case}:rule:old", "implies", (f"{case}:old-a",), f"{case}:mid", scope, ("src:rule",)),
        RuleRecord(f"{case}:rule:need", "requires", (target, f"{case}:permit"), None, scope, ("src:rule",)),
        RuleRecord(f"{case}:rule:conflict", "excludes", (target, negative), None, scope, ("src:rule",)),
    ]
    proof = (ProofRecord(f"{case}:mid", rules[0].rule_id, rules[0].premises, 1), ProofRecord(rules[1].conclusion or side, rules[1].rule_id, rules[1].premises, 2))
    if status_kind == 1:
        facts.append(FactRecord(f"{case}:fact:negative", negative, addresses[2].address_id, ("src:user",), scope, 0, None))
        conclusion = "contradicted"; conflicts = ()
    elif status_kind == 2:
        facts = [item for item in facts if item.fact_id != f"{case}:fact:b"]; proof = ()
        conclusion = "unknown"; conflicts = ()
    elif status_kind == 3:
        facts.append(FactRecord(f"{case}:fact:positive", target, addresses[2].address_id, ("src:user",), scope, 0, None))
        facts.append(FactRecord(f"{case}:fact:negative", negative, addresses[2].address_id, ("src:user",), scope, 0, None))
        conclusion = "conflict"; conflicts = (rules[4].rule_id,)
    else:
        conclusion = "entailed"; conflicts = ()
    regions = tuple(f"{case}:region:{item}" for item in range(8))
    coverage = CoverageRecord(regions, (regions[0], regions[1]), regions[2:], (), (), (), ("hard",), ("exception",), .001, .01, "certified")
    provenance = tuple(sorted({source for fact in facts if fact.literal in {f"{case}:a", f"{case}:b"} for source in fact.source_ids} | {"src:rule"}))
    return CandidateBundle(case, settings["topology_version"], settings["field_version"], addresses[2].address_id, target, scope, case, 10, sources, tuple(addresses), tuple(facts), tuple(rules), (SupersessionRecord(f"{case}:fact:old", f"{case}:fact:new"),), (f"{case}:hard",), (f"{case}:hard",), conclusion, proof, conflicts, coverage, _soft(case), provenance, .95, True)


def mutate(bundle: CandidateBundle, attack: str) -> CandidateBundle:
    raw = json.loads(json.dumps(row(bundle))); case = bundle.bundle_id
    if attack == "REVERSED_RELATION": raw["rules"][1]["premises"] = [bundle.target_literal]; raw["rules"][1]["conclusion"] = f"{case}:mid"
    elif attack == "MISSING_PREMISE": raw["proof"][0]["premises"] = [f"{case}:a"]
    elif attack == "FABRICATED_CONCLUSION": raw["proof"] = [{"conclusion": bundle.target_literal, "rule_id": f"{case}:rule:invented", "premises": [f"{case}:a"], "depth": 1}]
    elif attack == "SCOPE_VIOLATION": raw["rules"][1]["scope_id"] = "outside"
    elif attack == "SUPERSEDED_EVIDENCE": raw["proof"][0] = {"conclusion": f"{case}:mid", "rule_id": f"{case}:rule:old", "premises": [f"{case}:old-a"], "depth": 1}
    elif attack == "UNDISCLOSED_CONFLICT": raw["claimed_conflicts"] = []
    elif attack == "MISSING_HARD_FACTOR": raw["applied_hard_ids"] = []
    elif attack == "INSUFFICIENT_COVERAGE": raw["coverage"]["summarized_region_ids"] = raw["coverage"]["summarized_region_ids"][:-1]
    elif attack == "SOURCE_HASH_MISMATCH": raw["sources"][0]["content_hash"] = "0" * 64
    elif attack == "ASSISTANT_SELF_EVIDENCE":
        for fact in raw["facts"]:
            if fact["literal"] == f"{case}:a": fact["source_ids"] = ["src:assistant"]
    elif attack == "SOFT_STATE_MISMATCH": raw["soft"]["final_values"][0][1] = .1; raw["soft"]["final_energy"] = 0.0
    elif attack == "VERSION_MISMATCH": raw["topology_version"] = "topology-v0"
    return bundle_from_row(raw)


def bundle_from_row(item: dict) -> CandidateBundle:
    return CandidateBundle(
        item["bundle_id"], item["topology_version"], item["field_version"], item["request_address_id"], item["target_literal"], item["scope_id"], item["session_id"], item["valid_at"],
        tuple(SourceRecord(**row) for row in item["sources"]), tuple(AddressRecord(**row) for row in item["addresses"]),
        tuple(FactRecord(**{**row, "source_ids": tuple(row["source_ids"])} ) for row in item["facts"]),
        tuple(RuleRecord(**{**row, "premises": tuple(row["premises"]), "provenance_ids": tuple(row["provenance_ids"])} ) for row in item["rules"]),
        tuple(SupersessionRecord(**row) for row in item["supersessions"]), tuple(item["hard_constraint_ids"]), tuple(item["applied_hard_ids"]), item["claimed_conclusion"],
        tuple(ProofRecord(**{**row, "premises": tuple(row["premises"])} ) for row in item["proof"]), tuple(item["claimed_conflicts"]),
        CoverageRecord(**{**item["coverage"], **{name: tuple(item["coverage"][name]) for name in ("manifest_region_ids", "opened_region_ids", "summarized_region_ids", "uncertifiable_region_ids", "threats", "open_obligations", "checked_hard_indexes", "checked_exception_indexes")}}),
        SoftRecord(tuple(item["soft"]["variable_ids"]), tuple(SoftFactorRecord(**row) for row in item["soft"]["factors"]), tuple(item["soft"]["alternatives"]), tuple((name, float(value)) for name, value in item["soft"]["final_values"]), item["soft"]["selected_branch"], tuple(item["soft"]["retained_branches"]), item["soft"]["final_energy"], tuple((name, float(value)) for name, value in item["soft"]["residuals"])),
        tuple(item["decisive_provenance_ids"]), item["confidence"], item["self_claimed_valid"],
    )


def build(seed: int, pairs: int, settings: dict) -> tuple[list[CandidateBundle], dict[str, dict]]:
    bundles: list[CandidateBundle] = []; gold: dict[str, dict] = {}
    for number in range(pairs):
        base = _base(seed, number, settings); attack = ATTACKS[number % len(ATTACKS)]; twin = mutate(base, attack)
        twin = replace(twin, bundle_id=f"{base.bundle_id}:attack:{attack}")
        bundles.extend((base, twin)); gold[base.bundle_id] = {"status": "unknown" if base.claimed_conclusion == "unknown" else "verified_with_tension" if base.claimed_conclusion == "conflict" else "verified", "failure": None}; gold[twin.bundle_id] = {"status": "rejected", "failure": attack}
    return bundles, gold


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, default=str, sort_keys=True, indent=2)); temporary.replace(path)


def materialize(root: Path, bundles: list[CandidateBundle], gold: dict[str, dict]) -> None:
    write_json(root / "bundles.json", [row(bundle) for bundle in bundles]); write_json(root / "gold" / "expected.json", gold)


def load(path: Path) -> list[CandidateBundle]:
    return [bundle_from_row(item) for item in json.loads((path / "bundles.json").read_text())]
