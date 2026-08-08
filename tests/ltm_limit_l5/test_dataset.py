from __future__ import annotations

import json
import math

import numpy as np

from ltm_limit_l5.dataset import (
    FAMILIES,
    build_case,
    build_dependency_case,
    iter_cases,
    public_payload,
)
from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.schemas import FORBIDDEN_PUBLIC_FIELDS


def test_cases_are_deterministic_lazy_and_cover_all_families() -> None:
    iterator = iter_cases(len(FAMILIES), 1941)
    assert iter(iterator) is iterator
    rows = tuple(iterator)
    assert {item.expected.family for item in rows} == set(FAMILIES)
    assert build_case(3, 1941) == build_case(3, 1941)
    assert {item.expected.dependency_count for item in tuple(iter_cases(80, 1941))} >= set(range(1, 17))


def test_public_payload_has_no_gold_fields_and_vectors_are_valid() -> None:
    case = build_case(5, 1941, family="weighted_contradiction").public
    payload = public_payload(case)
    encoded = json.dumps(payload, sort_keys=True)
    assert not any(f'"{field}"' in encoded for field in FORBIDDEN_PUBLIC_FIELDS)
    assert all(len(row) == 128 for row in case.vector_table)
    assert all(math.isclose(sum(value * value for value in row), 1.0, abs_tol=1e-12) for row in case.vector_table)
    assert all(unit.semantic_vector_ref < len(case.vector_table) for unit in case.units)
    assert case.prompt.encoder_calls == 1


def test_math_and_abstract_cases_use_same_public_contract() -> None:
    math_case = build_case(0, 7, family="dependency_2_4", domain="math")
    abstract_case = build_case(1, 7, family="dependency_2_4", domain="abstract")
    assert type(math_case.public) is type(abstract_case.public)
    assert math_case.public.prompt.influences[0].reality_key == "standard-math"
    assert abstract_case.public.prompt.influences[0].reality_key.startswith("user-reality:")


def test_generated_case_loads_into_the_real_field_index() -> None:
    case = build_case(23, 1941, family="dependency_5_8").public
    vectors = np.asarray(case.vector_table, dtype=np.float32)
    cells, summaries = build_minimap(case.bodies, case.units, vectors)
    field = EquilibriumFieldIndex(case.bodies, case.units, vectors, cells, summaries)
    assert len(field.bodies) == len(case.bodies)


def test_explicit_depth_stress_case_hides_depth_and_has_one_body_per_dependency() -> None:
    generated = build_dependency_case(4, 17, depth=23)
    public = generated.public
    assert generated.expected.dependency_count == 23
    assert len(public.bodies) == 23
    assert "23" not in public.case_id
    units = {item.unit_id: item for item in public.units}
    source = public.prompt.influences[0].semantic_key
    terminal = generated.expected.selected[0]
    assert all(len(item.outcome_unit_ids) == 1 for item in public.bodies)
    assert not any(
        {units[value].semantic_key for value in item.input_unit_ids} == {source}
        and {units[value].semantic_key for value in item.outcome_unit_ids} == {terminal}
        for item in public.bodies
    )
