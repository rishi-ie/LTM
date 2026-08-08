from topology_g13.generator import cases, scales
from topology_g13.pipeline import _independent_conclusion, _problem
from topology_g13.storage import physical_block


def test_scales_have_actual_requested_capacity():
    config = {"scale_tokens": [1_000_000, 10_000_000, 30_000_000, 100_000_000], "tokens_per_chunk": 32,
              "factors_per_chunk": 8, "factor_block_size": 256, "region_block_count": 16}
    values = scales(config)
    assert values[-1].tokens == 100_000_000
    assert values[-1].factors == 25_000_000


def test_layout_mapping_is_a_permutation():
    for layout in ("identity", "reverse", "affine"):
        values = {physical_block(item, 97_657, layout) for item in range(97_657)}
        assert len(values) == 97_657


def test_query_programs_and_independent_replay_agree():
    for case in cases(20260813, 64, development=False):
        assert _independent_conclusion(_problem(case)) == case.gold
