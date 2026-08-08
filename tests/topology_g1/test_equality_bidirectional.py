from topology_g1.engine import execute, verify_derivation
from topology_g1.fixtures import fixtures


def test_equality_derivations_are_bidirectional() -> None:
    fixture = next(item for item in fixtures("development") if item.family == "equals" and item.variant == 0)
    nodes = {node.node_id: node for node in fixture.nodes}
    derivations, _, _ = execute(fixture.relation, nodes, fixture.state)
    assert len(derivations) == 2
    assert all(verify_derivation(item, fixture.relation, nodes, fixture.state).valid for item in derivations)
