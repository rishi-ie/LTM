from topology_g28.decoder import enumerate_graphs, gold_graph


def test_g1_graph_lattice_keeps_reversed_direction_candidates() -> None:
    graphs = enumerate_graphs((("a1", "claim"), ("a2", "claim")))
    options = [item for item in graphs if item.disposition == "accept" and item.relation_types == ("implies",)]
    assert any(dict(item.relations[0].role_bindings)["premise"] == ("a1",) for item in options)
    assert any(dict(item.relations[0].role_bindings)["premise"] == ("a2",) for item in options)


def test_gold_graph_has_exact_named_roles() -> None:
    graph = gold_graph(("requires",), (("requires:dependent", ("a1",)), ("requires:prerequisite", ("a2",))), "accept")
    assert graph.relation_types == ("requires",)
    assert dict(graph.relations[0].role_bindings)["prerequisite"] == ("a2",)
