from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict

import numpy as np

from .regions import RegionStore
from .schemas import FactorInfluence, RegionSummary, canonical_hash


def _quantize(vector: np.ndarray) -> tuple[np.ndarray, float, float]:
    if not np.any(vector): return np.zeros_like(vector), 1.0, 0.0
    scale = float(np.max(np.abs(vector)) / 127.0)
    values = np.clip(np.rint(vector / scale), -127, 127).astype(np.int8)
    restored = values.astype(np.float64) * scale
    return restored, scale, float(np.linalg.norm(vector - restored))


class SummaryCatalog:
    def __init__(self, store: RegionStore, influences: tuple[FactorInfluence, ...], summary_modes: dict[str, str]):
        self.store = store; self.influences = {item.factor_id: item for item in influences}; self.terms: dict[tuple[str, str], tuple[tuple[float, ...], float]] = {}; self.summaries: dict[str, RegionSummary] = {}
        for region_id, region in store.regions.items():
            members = [store.factors[fid] for fid in region.factor_ids]
            keys: dict[str, list[np.ndarray]] = defaultdict(list)
            for factor in members:
                influence = self.influences.get(factor.factor_id)
                if influence:
                    for key in influence.influence_keys: keys[key].append(np.array(influence.force_vector, dtype=np.float64))
            mode = summary_modes.get(region_id, "quantized")
            all_force = np.zeros(32, dtype=np.float64); total_error = 0.0
            for key, vectors in keys.items():
                exact = np.sum(vectors, axis=0)
                if mode in ("coarse", "unbounded"):
                    approximate = np.zeros(32, dtype=np.float64); error = float(np.linalg.norm(exact))
                else:
                    approximate, _, residual = _quantize(exact); error = math.nextafter(residual, math.inf)
                self.terms[(region_id, key)] = (tuple(approximate), error)
                all_force += approximate; total_error += error
            positive = sorted({target for factor in members for target in factor.target_ids if not target.startswith("not:")})
            negative = sorted({target for factor in members for target in factor.target_ids if target.startswith("not:")})
            premises = sorted({source for factor in members for source in factor.source_ids})
            payload = {"region_id": region_id, "influence_keys": sorted(keys), "positive": positive, "negative": negative, "premises": premises, "types": sorted({factor.factor_type for factor in members}), "mode": mode}
            self.summaries[region_id] = RegionSummary(region_id, tuple(sorted(keys)), tuple(positive), tuple(negative), tuple(premises), tuple(sorted({factor.factor_type for factor in members})), region.scope_ids, region.time_min, region.time_max, tuple(sorted({factor.episode_id for factor in members if factor.episode_id})), any(factor.hard for factor in members), any(factor.exact_exception for factor in members), any(factor.factor_type == "supersedes" for factor in members), any(factor.factor_type in ("excludes", "opposes") for factor in members), any(factor.factor_type == "bridge" for factor in members), tuple(all_force), total_error, mode != "unbounded", canonical_hash(payload))
        self.validate()

    def term(self, region_id: str, key: str) -> tuple[np.ndarray, float]:
        vector, error = self.terms.get((region_id, key), (tuple([0.0] * 32), 0.0))
        return np.array(vector, dtype=np.float64), error

    def validate(self) -> None:
        for region_id, region in self.store.regions.items():
            summary = self.summaries[region_id]
            members = [self.store.factors[fid] for fid in region.factor_ids]
            if not {target for factor in members for target in factor.target_ids if not target.startswith("not:")}.issubset(summary.possible_positive_literals): raise RuntimeError("positive summary omission")
            if not {target for factor in members for target in factor.target_ids if target.startswith("not:")}.issubset(summary.possible_negative_literals): raise RuntimeError("negative summary omission")
            if not {source for factor in members for source in factor.source_ids}.issubset(summary.boundary_premises): raise RuntimeError("premise summary omission")
            by_key: dict[str, list[np.ndarray]] = defaultdict(list)
            for factor in members:
                influence = self.influences.get(factor.factor_id)
                if influence:
                    for key in influence.influence_keys: by_key[key].append(np.array(influence.force_vector, dtype=np.float64))
            for key, vectors in by_key.items():
                exact = np.sum(vectors, axis=0); approximate, bound = self.term(region_id, key)
                if float(np.linalg.norm(exact - approximate)) > bound + 1e-12: raise RuntimeError("unsound force bound")

    def serializable(self) -> dict:
        return {"summaries": [asdict(item) for item in self.summaries.values()], "terms": {f"{region}|{key}": {"force": list(vector), "bound": error} for (region, key), (vector, error) in self.terms.items()}}
