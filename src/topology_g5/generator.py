from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from topology_g4.execute import execute
from topology_g4.schemas import TopologyFactor, TraversalRequest

from .latent import force_for
from .regions import RegionStore
from .schemas import FactorInfluence, canonical_hash

FAMILIES = ("premise", "correction", "hard_constraint", "exception", "conflict", "bridge")


def _factor(fid: str, kind: str, sources: tuple[str, ...], targets: tuple[str, ...], **kwargs) -> TopologyFactor:
    return TopologyFactor(fid, kind, sources, targets, provenance_ids=(f"prov:{fid}",), **kwargs)


def _request(case_id: str, scope: str) -> TraversalRequest:
    return TraversalRequest(case_id, (f"entity:{case_id}",), (f"predicate:{case_id}",), f"{case_id}:target", scope, 60, None, "positive")


def _remote_factors(case_id: str, family: str, variant: str, scope: str) -> list[TopologyFactor]:
    target = f"{case_id}:target"; neg = f"not:{target}"; seed = f"{case_id}:remote-seed"
    if variant in ("latent", "harmless", "unbounded"):
        return [_factor(f"{case_id}:remote-force", "supports", (), (f"{case_id}:remote-note",), scope_id=scope)]
    if family == "premise": return [_factor(f"{case_id}:remote-negative", "negative_fact", (), (neg,), scope_id=scope)]
    if family == "correction":
        return [_factor(f"{case_id}:newer", "negative_fact", (), (neg,), scope_id=scope), _factor(f"{case_id}:supersede", "supersedes", (target, neg), (target,), scope_id=scope)]
    if family == "hard_constraint": return [_factor(f"{case_id}:hard", "hard_constraint", (), (neg,), scope_id=scope, hard=True)]
    if family == "exception": return [_factor(f"{case_id}:exception", "exact_exception", (), (neg,), scope_id=scope, hard=True, exact_exception=True)]
    if family == "conflict":
        return [_factor(f"{case_id}:opposing", "negative_fact", (), (neg,), scope_id=scope), _factor(f"{case_id}:exclude", "excludes", (target, neg), (target,), scope_id=scope)]
    return [_factor(f"{case_id}:remote-seed", "fact", (), (seed,), scope_id=scope), _factor(f"{case_id}:bridge", "bridge", (seed,), (neg,), scope_id=scope, bridge_region_id=f"bridge:{case_id}")]


def build_dataset(seed: int, factor_count: int, pairs: int) -> dict:
    factors: list[TopologyFactor] = []; influences: list[FactorInfluence] = []; factor_regions: dict[str, str] = {}; cases: list[dict] = []; summary_modes: dict[str, str] = {}
    local_per_region = 40
    remote_factors: list[TopologyFactor] = []
    for index in range(pairs):
        family = FAMILIES[index % len(FAMILIES)]
        within = index % 40
        variant = "answer" if within < 20 else "latent" if within < 30 else "harmless" if within < 38 else "unbounded"
        case_id = f"g5-{seed:x}-{index:04d}"; base_scope = f"base:{case_id}"; twin_scope = f"twin:{case_id}"; target = f"{case_id}:target"; local = f"{case_id}:local"
        local_region = f"seed-{index // local_per_region:03d}"
        local_factors = [_factor(f"{case_id}:local-fact", "fact", (), (local,)), _factor(f"{case_id}:local-rule", "implies", (local,), (target,))]
        for factor in local_factors:
            factors.append(factor); factor_regions[factor.factor_id] = local_region
            influences.append(FactorInfluence(factor.factor_id, (target,), force_for(factor.factor_id, 0.01), 0.01))
        remote_region = f"remote-{index:04d}"
        remote = _remote_factors(case_id, family, variant, twin_scope)
        remote_factors.extend(remote)
        for factor in remote:
            factor_regions[factor.factor_id] = remote_region
            weight = 0.20 if variant in ("latent", "unbounded") else 0.08 if variant == "answer" else 0.005
            influences.append(FactorInfluence(factor.factor_id, (target,), force_for(factor.factor_id, weight), weight))
        if variant == "latent" and index % 2 == 0: summary_modes[remote_region] = "coarse"
        elif variant == "unbounded": summary_modes[remote_region] = "unbounded"
        else: summary_modes[remote_region] = "quantized"
        for label, request, remote_enabled in (("base", _request(case_id, base_scope), False), ("twin", _request(case_id, twin_scope), True)):
            cases.append({"request_id": f"{case_id}:{label}", "pair_id": case_id, "variant": label, "request": asdict(TraversalRequest(f"{case_id}:{label}", request.starting_entity_ids, request.starting_predicate_ids, request.target_literal, request.scope_id, request.valid_at, request.episode_id, request.polarity)), "seed_regions": [local_region], "remote_region": remote_region, "influence_key": target, "remote_enabled": remote_enabled})
    factors.extend(remote_factors)
    filler = 0
    while len(factors) < factor_count:
        region = f"filler-{filler // 256:04d}"; fid = f"distractor:{seed}:{filler:06d}"; factor = _factor(fid, "implies", (f"d:{filler}",), (f"d:{filler+1}",), scope_id=f"scope:{filler % 20}")
        factors.append(factor); factor_regions[fid] = region; filler += 1
    factors = factors[:factor_count]
    kept = {factor.factor_id for factor in factors}; influences = [item for item in influences if item.factor_id in kept]
    store = RegionStore(tuple(factors), factor_regions)
    return {"factors": tuple(factors), "influences": tuple(influences), "factor_regions": factor_regions, "cases": cases, "summary_modes": summary_modes, "store": store}


def validate_dataset(dataset: dict) -> None:
    factors: tuple[TopologyFactor, ...] = dataset["factors"]
    by_id = {factor.factor_id: factor for factor in factors}
    for row in dataset["cases"]:
        request_row = row["request"]; request = TraversalRequest(**{**request_row, "starting_entity_ids": tuple(request_row["starting_entity_ids"]), "starting_predicate_ids": tuple(request_row["starting_predicate_ids"])})
        result = execute(request, factors)
        if row["variant"] == "base" and result.conclusion != "entailed": raise RuntimeError("base must be entailed")
        if row["variant"] == "twin" and row["remote_enabled"] and not row["remote_region"]: raise RuntimeError("missing remote region")
    if len(by_id) != len(factors): raise RuntimeError("duplicate factor identity")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temp = path.with_suffix(path.suffix + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"); temp.replace(path)


def materialize(path: Path, dataset: dict) -> dict:
    write_json(path / "factors.json", [asdict(item) for item in dataset["factors"]]); write_json(path / "influences.json", [asdict(item) for item in dataset["influences"]]); write_json(path / "factor-regions.json", dataset["factor_regions"]); write_json(path / "cases.json", dataset["cases"]); write_json(path / "summary-modes.json", dataset["summary_modes"])
    return {"factor_count": len(dataset["factors"]), "case_count": len(dataset["cases"]), **dataset["store"].manifest(), "dataset_hash": canonical_hash([asdict(item) for item in dataset["factors"]])}


def load(path: Path) -> dict:
    factor_rows = json.loads((path / "factors.json").read_text()); factors = tuple(TopologyFactor(**{**row, "source_ids": tuple(row["source_ids"]), "target_ids": tuple(row["target_ids"]), "provenance_ids": tuple(row["provenance_ids"])}) for row in factor_rows)
    influence_rows = json.loads((path / "influences.json").read_text()); influences = tuple(FactorInfluence(**{**row, "influence_keys": tuple(row["influence_keys"]), "force_vector": tuple(row["force_vector"])}) for row in influence_rows)
    regions = json.loads((path / "factor-regions.json").read_text()); store = RegionStore(factors, regions)
    return {"factors": factors, "influences": influences, "factor_regions": regions, "cases": json.loads((path / "cases.json").read_text()), "summary_modes": json.loads((path / "summary-modes.json").read_text()), "store": store}
