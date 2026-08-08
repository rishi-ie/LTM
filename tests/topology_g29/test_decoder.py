from topology_g29.decoder import minimum_matching_cost


def test_bounded_bipartite_matching_is_deterministic() -> None:
    assert minimum_matching_cost(((.2, .8, .4), (.7, .1, .5))) == (0, 1)
