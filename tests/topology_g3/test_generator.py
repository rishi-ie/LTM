from topology_g3.generator import build_topology, topology_manifest


def test_topology_size_and_determinism():
    first = build_topology(1731); second = build_topology(1731)
    assert len(first) == 10000
    assert topology_manifest(first) == topology_manifest(second)
