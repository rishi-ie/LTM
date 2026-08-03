from __future__ import annotations

from collections import defaultdict

from .summaries import SummaryCatalog


class SummaryIndexes:
    def __init__(self, catalog: SummaryCatalog):
        self.catalog = catalog
        self.by_key: dict[str, tuple[str, ...]] = {}
        self.by_literal: dict[str, tuple[str, ...]] = {}
        self.by_premise: dict[str, tuple[str, ...]] = {}
        self.hard: dict[str, tuple[str, ...]] = {}
        self.exception: dict[str, tuple[str, ...]] = {}
        self.correction: dict[str, tuple[str, ...]] = {}
        self.conflict: dict[str, tuple[str, ...]] = {}
        self.bridge: dict[str, tuple[str, ...]] = {}
        maps = [defaultdict(list) for _ in range(8)]
        for region_id, summary in catalog.summaries.items():
            for key in summary.influence_keys: maps[0][key].append(region_id)
            for literal in summary.possible_positive_literals + summary.possible_negative_literals: maps[1][literal].append(region_id)
            for premise in summary.boundary_premises: maps[2][premise].append(region_id)
            if summary.contains_hard_constraint:
                for literal in summary.possible_positive_literals + summary.possible_negative_literals: maps[3][literal].append(region_id)
            if summary.contains_exact_exception:
                for literal in summary.possible_positive_literals + summary.possible_negative_literals: maps[4][literal].append(region_id)
            if summary.contains_correction:
                for literal in summary.possible_positive_literals + summary.possible_negative_literals: maps[5][literal].append(region_id)
            if summary.contains_conflict:
                for literal in summary.possible_positive_literals + summary.possible_negative_literals: maps[6][literal].append(region_id)
            if summary.contains_bridge:
                for literal in summary.possible_positive_literals + summary.possible_negative_literals + summary.boundary_premises: maps[7][literal].append(region_id)
        names = ("by_key", "by_literal", "by_premise", "hard", "exception", "correction", "conflict", "bridge")
        for name, mapping in zip(names, maps): setattr(self, name, {key: tuple(sorted(value)) for key, value in mapping.items()})

    def candidates(self, target: str, key: str, obligations: tuple[str, ...]) -> tuple[tuple[str, ...], int]:
        ids = set(self.by_key.get(key, ())) | set(self.by_literal.get(target, ())) | set(self.by_literal.get(f"not:{target}", ()))
        for obligation in obligations: ids.update(self.by_premise.get(obligation, ()))
        return tuple(sorted(ids)), len(ids)
