from topology_g4.generator import build_dataset


def test_locked_shape_is_deterministic():
    first, requests, gold = build_dataset(99, 10_000, 12)
    second, _, _ = build_dataset(99, 10_000, 12)
    assert len(first) == 10_000
    assert len(requests) == len(gold) == 12
    assert first == second
