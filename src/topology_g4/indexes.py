from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from .schemas import TopologyFactor, canonical_hash


class FactorIndexes:
    def __init__(self, factors: tuple[TopologyFactor, ...], block_size: int = 256):
        self.factors = {factor.factor_id: factor for factor in factors}
        self.by_target: dict[str, list[str]] = defaultdict(list)
        self.by_source: dict[str, list[str]] = defaultdict(list)
        self.hard: dict[str, list[str]] = defaultdict(list)
        self.exceptions: dict[str, list[str]] = defaultdict(list)
        self.sessions: dict[str, list[str]] = defaultdict(list)
        self.conflicts: dict[str, list[str]] = defaultdict(list)
        self.block_size = block_size
        self.position = {factor.factor_id: index for index, factor in enumerate(factors)}
        for factor in factors:
            for target in factor.target_ids:
                self.by_target[target].append(factor.factor_id)
                if factor.hard: self.hard[target].append(factor.factor_id)
                if factor.exact_exception: self.exceptions[target].append(factor.factor_id)
                if factor.factor_type in ("excludes", "opposes"): self.conflicts[target].append(factor.factor_id)
            for source in factor.source_ids: self.by_source[source].append(factor.factor_id)
            if factor.session_factor and factor.episode_id: self.sessions[factor.episode_id].append(factor.factor_id)
        for mapping in (self.by_target, self.by_source, self.hard, self.exceptions, self.sessions, self.conflicts):
            for ids in mapping.values(): ids.sort()

    def block(self, factor_id: str) -> str:
        return f"block-{self.position[factor_id] // self.block_size:05d}"

    def manifest(self) -> dict:
        payload = {"targets": dict(self.by_target), "sources": dict(self.by_source), "hard": dict(self.hard), "exceptions": dict(self.exceptions), "sessions": dict(self.sessions)}
        return {"index_hash": canonical_hash(payload), "factor_hash": canonical_hash([asdict(x) for x in self.factors.values()]), "postings": sum(len(ids) for group in payload.values() for ids in group.values()), "indexes": 6}
