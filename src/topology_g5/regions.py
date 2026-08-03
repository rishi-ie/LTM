from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from topology_g4.schemas import TopologyFactor

from .schemas import RegionRecord, canonical_hash


class RegionStore:
    """Immutable exact blocks; ordinary execution retrieves blocks only by region ID."""

    def __init__(self, factors: tuple[TopologyFactor, ...], factor_regions: dict[str, str]):
        self.factors = {factor.factor_id: factor for factor in factors}
        self.factor_regions = dict(factor_regions)
        grouped: dict[str, list[str]] = defaultdict(list)
        for factor in factors:
            grouped[self.factor_regions[factor.factor_id]].append(factor.factor_id)
        self.regions: dict[str, RegionRecord] = {}
        for region_id, ids in grouped.items():
            ordered = tuple(sorted(ids))
            members = [self.factors[fid] for fid in ordered]
            scopes = tuple(sorted({factor.scope_id for factor in members}))
            starts = [factor.valid_from for factor in members if factor.valid_from is not None]
            ends = [factor.valid_to for factor in members if factor.valid_to is not None]
            self.regions[region_id] = RegionRecord(region_id, ordered, (f"block:{region_id}",), scopes, min(starts) if starts else None, max(ends) if ends else None, canonical_hash([asdict(factor) for factor in members]))
        if any(len(region.factor_ids) > 256 for region in self.regions.values()):
            raise ValueError("region exceeds 256 factors")
        self.partition_hash = canonical_hash({key: value.factor_ids for key, value in sorted(self.regions.items())})

    def open_region(self, region_id: str) -> tuple[TopologyFactor, ...]:
        return tuple(self.factors[fid] for fid in self.regions[region_id].factor_ids)

    def region_for(self, factor_id: str) -> str:
        return self.factor_regions[factor_id]

    def manifest(self) -> dict:
        return {"regions": len(self.regions), "partition_hash": self.partition_hash, "max_region_factors": max(len(item.factor_ids) for item in self.regions.values())}
