from __future__ import annotations

from dataclasses import replace

import pytest

from ltm_limit_l5.dataset import build_case
from ltm_limit_l5.scale import (
    MAX_MATERIALIZED_DISTRACTORS,
    LazyDistractorCorpus,
    attach_distractors,
    build_shared_field,
    incremental_rebuild,
    run_shared_query,
    verify_cache,
)


def _signature(observation) -> tuple[object, ...]:
    result = observation.result
    return (
        result.disposition,
        tuple((item.semantic_key, item.polarity) for item in result.candidates),
        result.coverage_disposition,
    )


def test_shared_field_preserves_isolated_query_and_is_storage_order_invariant() -> None:
    first = build_case(2, 1941, family="dependency_2_4", domain="math").public
    second = build_case(12, 1941, family="dependency_5_8", domain="math").public
    isolated = build_shared_field((first,))
    forward = build_shared_field((first, second))
    reversed_field = build_shared_field((second, first))
    assert _signature(run_shared_query(isolated, first.case_id)) == _signature(run_shared_query(forward, first.case_id))
    assert forward.manifest == reversed_field.manifest
    assert verify_cache(forward)


def test_realities_are_separate_and_runtime_reads_remain_bounded() -> None:
    math_case = build_case(3, 1941, family="dependency_5_8", domain="math").public
    abstract_case = build_case(4, 1941, family="dependency_5_8", domain="abstract").public
    field = build_shared_field((math_case, abstract_case))
    math_partition = field.partition_for(math_case.case_id)
    abstract_partition = field.partition_for(abstract_case.case_id)
    assert math_partition is not abstract_partition
    assert all(item.reality_key == "standard-math" for item in math_partition.bodies)
    observation = run_shared_query(field, math_case.case_id)
    assert observation.maximum_active_bodies <= 128
    assert observation.cumulative_distinct_body_reads <= 2048
    assert observation.full_field_scans == 0
    assert observation.minimap_cells_scored > 0
    assert observation.body_records_read > 0
    assert observation.consumer_index_lookups > 0


def test_aggregation_preserves_source_normalized_duplicate_suppression() -> None:
    original = build_case(0, 1941, family="one_body", domain="math").public
    duplicate = replace(original, case_id="duplicate-case", prompt=replace(original.prompt, prompt_id="duplicate-case"))
    field = build_shared_field((original, duplicate))
    index = field.index_for(original.case_id)
    weights = index.normalized_body_weights({body_id: 1.0 for body_id in index.bodies})
    assert sum(value > 0 for value in weights.values()) == 1


def test_incremental_rebuild_changes_only_affected_reality_and_matches_clean_build() -> None:
    math_case = build_case(0, 1941, family="one_body", domain="math").public
    abstract_case = build_case(1, 1941, family="one_body", domain="abstract").public
    addition = build_case(10, 1941, family="dependency_2_4", domain="math").public
    field = build_shared_field((math_case, abstract_case))
    old_abstract = field.partition_for(abstract_case.case_id)
    rebuilt = incremental_rebuild(field, (addition,))
    assert rebuilt.affected_realities == ("standard-math",)
    assert rebuilt.unaffected_partition_hash_equality
    assert rebuilt.clean_rebuild_equality
    assert rebuilt.field.partition_for(abstract_case.case_id) is old_abstract
    assert verify_cache(rebuilt.field)


def test_mutated_vector_or_summary_fails_stale_cache_verification() -> None:
    case = build_case(0, 1941, family="one_body", domain="math").public
    field = build_shared_field((case,))
    partition = field.partition_for(case.case_id)
    partition.summaries[0, 0] += 0.25
    with pytest.raises(ValueError, match="STALE_MINIMAP_CACHE"):
        verify_cache(field)

    clean = build_shared_field((case,))
    clean_partition = clean.partition_for(case.case_id)
    clean_partition.vectors[0, 0] += 0.25
    with pytest.raises(ValueError, match="STALE_MINIMAP_CACHE"):
        verify_cache(clean)


@pytest.mark.parametrize("requested,materialized", ((100_000, 0), (100_000, 16)))
def test_large_lazy_distractor_commitment_is_honest_and_bounded(requested: int, materialized: int) -> None:
    case = build_case(2, 1941, family="dependency_2_4", domain="math").public
    base = build_shared_field((case,))
    baseline = run_shared_query(base, case.case_id)
    corpus = LazyDistractorCorpus(requested, 20270612, reality_key="standard-math")
    overlay = attach_distractors(base, corpus, materialize_limit=materialized)
    measured = run_shared_query(overlay, case.case_id)
    assert _signature(measured) == _signature(baseline)
    assert overlay.metrics.requested_distractor_bodies == requested
    assert overlay.metrics.materialized_distractor_bodies == materialized
    assert overlay.metrics.lazy_committed_distractor_bodies == requested - materialized
    assert overlay.metrics.full_field_scans == 0
    assert measured.maximum_active_bodies <= 128
    assert measured.cumulative_distinct_body_reads <= 2048
    assert overlay.overlay_sha256 == attach_distractors(base, corpus, materialize_limit=materialized).overlay_sha256
    with pytest.raises(ValueError, match="bounded-memory"):
        attach_distractors(base, corpus, materialize_limit=MAX_MATERIALIZED_DISTRACTORS + 1)


def test_cache_manifest_argument_rejects_an_old_generation() -> None:
    first = build_case(0, 1941, family="one_body", domain="math").public
    second = build_case(10, 1941, family="one_body", domain="math").public
    field = build_shared_field((first,))
    changed = incremental_rebuild(field, (second,), verify_clean=False).field
    with pytest.raises(ValueError, match="STALE_MINIMAP_CACHE"):
        verify_cache(changed, field.manifest)
    assert verify_cache(changed)
