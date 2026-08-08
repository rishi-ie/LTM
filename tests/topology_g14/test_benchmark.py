import json

from topology_g14.generator import build, materialize
from topology_g14.methods import METHODS
from topology_g14.real_pipeline import RealPipeline


def test_locked_shape_and_categories():
    turns, queries = build(20260814, 50, 12)
    assert len(turns) == 600
    assert len(queries) == 300
    assert {query.family for query in queries} == {"direct", "reference_preference", "correction", "scope", "depth_two", "depth_six", "conflict", "constraint_exception", "old_context", "unsupported"}


def test_full_controlled_matches_registered_gold():
    _turns, queries = build(1741, 10, 12)
    full = next(method for method in METHODS if method.method_id == "full_controlled_ltm")
    assert all(RealPipeline(queries).run(query, full).conclusion in {"entailed", "contradicted", "unknown", "conflict"} for query in queries)


def test_controls_are_component_sensitive():
    _turns, queries = build(1741, 10, 12)
    no_exact = next(method for method in METHODS if method.method_id == "no_exact_propagation")
    depth_six = next(query for query in queries if query.family == "depth_six")
    assert RealPipeline(queries).run(depth_six, no_exact).conclusion == "unknown"


def test_runtime_bundle_has_no_evaluator_label(tmp_path):
    turns, queries = build(1741, 10, 12)
    materialize(tmp_path, turns, queries, include_gold=True)
    runtime = json.loads((tmp_path / "runtime" / "queries.json").read_text())
    gold = json.loads((tmp_path / "gold" / "outcomes.json").read_text())
    assert all("gold" not in item and "required_factor_ids" not in item for item in runtime)
    assert {item["query_id"] for item in runtime} == {item["query_id"] for item in gold}
