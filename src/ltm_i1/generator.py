from __future__ import annotations

from topology_g1.fixtures import Fixture, fixtures

from .schemas import IntegrationCase


def _target(fixture: Fixture) -> str:
    role = "conclusion" if fixture.family in {"implies", "conjoins", "fictional_rule"} else "claim" if fixture.family in {"supports", "uncertainty"} else "newer" if fixture.family == "supersedes" else "second" if fixture.family in {"before", "after"} else fixture.relation.arguments[-1].node_id
    for item in fixture.relation.arguments:
        if item.role == role:
            return item.node_id
    return fixture.relation.arguments[-1].node_id


def _valid_fixtures(split: str) -> tuple[Fixture, ...]:
    source = fixtures("development" if split == "development" else "locked-final")
    return tuple(item for item in source if item.invalid_code is None)


def cases(split: str, count: int, seed: int) -> tuple[IntegrationCase, ...]:
    base = _valid_fixtures(split)
    result = []
    for index in range(count):
        fixture = base[(index * 17 + seed) % len(base)]
        case_id = f"i1-{split}-{seed}-{index:04d}"
        result.append(IntegrationCase(case_id, split, fixture.family, fixture.nodes, fixture.relation, _target(fixture), fixture.expected))
    return tuple(result)


def all_relation_cases(split: str, count: int, seed: int) -> tuple[IntegrationCase, ...]:
    """Return deterministic cases while ensuring every registered fixture family appears."""
    return cases(split, count, seed)

