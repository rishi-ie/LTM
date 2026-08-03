from __future__ import annotations

from pathlib import Path

import pytest

from topology_g1.codec import decode_node, encode_node
from topology_g1.engine import execute, verify_derivation
from topology_g1.evaluate import run_suite
from topology_g1.fixtures import fixtures, legacy_node_v1
from topology_g1.migrate import node_v1_to_v2
from topology_g1.registry import validate_relation
from topology_g1.schemas import SchemaError
from topology_g1.store import TopologyStore


def test_fixture_program_is_exactly_stratified():
    development = fixtures("development")
    locked = fixtures("locked")
    assert len(development) == len(locked) == 80
    assert len(development + locked) == 160
    assert {item.family for item in development} == {item.family for item in locked}


def test_canonical_round_trip_and_migration():
    fixture = fixtures("locked")[4]
    node = fixture.nodes[0]
    assert decode_node(encode_node(node)) == node
    assert node_v1_to_v2(legacy_node_v1(node)) == node


def test_invalid_fixture_is_rejected_by_registry():
    fixture = next(item for item in fixtures("locked") if item.invalid_code == "MISSING_ROLE")
    with pytest.raises(SchemaError, match="wrong arity"):
        validate_relation(fixture.relation, {node.node_id: node for node in fixture.nodes})


def test_implication_is_directional_and_verifier_rejects_fabrication():
    fixture = next(item for item in fixtures("development") if item.family == "implies" and item.variant == 0)
    nodes = {node.node_id: node for node in fixture.nodes}
    derivations, _, _ = execute(fixture.relation, nodes, fixture.state)
    assert len(derivations) == 1
    assert verify_derivation(derivations[0], fixture.relation, nodes, fixture.state).valid
    fabricated = derivations[0].__class__(
        derivations[0].premise_ids[0], derivations[0].relation_id, (), derivations[0].scope_id, derivations[0].provenance
    )
    assert not verify_derivation(fabricated, fixture.relation, nodes, fixture.state).valid


def test_store_replay_is_order_independent(tmp_path: Path):
    result = run_suite(fixtures("development"), tmp_path)
    assert result["passed"]
    assert result["snapshot_hash"] == result["replay_hash"] == result["reverse_hash"]


def test_conflicting_identity_is_rejected(tmp_path: Path):
    fixture = fixtures("development")[0]
    store = TopologyStore(tmp_path / "topology.sqlite")
    try:
        node = fixture.nodes[0]
        store.insert_node(node)
        changed = node.__class__(
            node.node_id, node.schema_version, node.kind, (("label", "changed"),), node.scope_id, node.validity, node.provenance
        )
        with pytest.raises(SchemaError, match=node.node_id):
            store.insert_node(changed)
    finally:
        store.close()
