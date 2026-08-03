from __future__ import annotations

from collections import Counter

import pytest

from topology_g1.schemas import SchemaError
from topology_g2.dataset import RELATIONS, generate_cases
from topology_g2.serde import plain
from topology_g2.validate import parse_candidate, validate_candidate


def test_dataset_is_stratified_and_relation_complete():
    development = generate_cases("development")
    locked = generate_cases("locked")
    assert len(development) == len(locked) == 300
    assert sum(case.gold_ir.disposition == "accept" for case in development) == 240
    assert sum(case.gold_ir.disposition == "clarification_required" for case in development) == 30
    assert sum(case.gold_ir.disposition == "quarantine" for case in development) == 30
    counts = Counter(relation for case in locked for relation in case.relation_types)
    assert set(counts) == set(RELATIONS)
    assert min(counts.values()) >= 16
    assert {case.source.text for case in development}.isdisjoint({case.source.text for case in locked})


def test_gold_accept_cases_validate_to_g1_topology():
    for case in generate_cases("development")[:30]:
        validated = validate_candidate(case.gold_ir, case.source, case.context)
        assert validated.disposition == "accept"
        assert validated.nodes


def test_non_accepting_cases_cannot_write_topology():
    case = next(case for case in generate_cases("development") if case.gold_ir.disposition == "quarantine")
    validated = validate_candidate(case.gold_ir, case.source, case.context)
    assert not validated.nodes and not validated.relations


def test_unknown_json_fields_are_rejected():
    case = generate_cases("development")[0]
    raw = plain(case.gold_ir)
    raw["unexpected"] = True
    with pytest.raises(SchemaError) as error:
        parse_candidate(__import__("json").dumps(raw))
    assert error.value.code == "INVALID_JSON"


def test_invalid_quote_is_rejected_without_recovery():
    case = generate_cases("development")[0]
    raw = plain(case.gold_ir)
    raw["objects"][0]["source_quote"] = "not in source"
    candidate = parse_candidate(__import__("json").dumps(raw))
    with pytest.raises(SchemaError) as error:
        validate_candidate(candidate, case.source, case.context)
    assert error.value.code == "INVALID_SOURCE_SPAN"


def test_relation_role_is_checked_by_g1_registry():
    case = next(case for case in generate_cases("development") if case.relation_types == ("implies",))
    raw = plain(case.gold_ir)
    raw["relations"][0]["arguments"][0][0] = "wrong_role"
    candidate = parse_candidate(__import__("json").dumps(raw))
    with pytest.raises(SchemaError) as error:
        validate_candidate(candidate, case.source, case.context)
    assert error.value.code == "MISSING_ROLE"
