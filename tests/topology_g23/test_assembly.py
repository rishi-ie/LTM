from topology_g23.assemble import assemble
from topology_g23.dataset import generate_sentence_examples


def test_gold_sentence_assembles_through_g1():
    example = next(item for item in generate_sentence_examples("development") if item.gold.relations)
    from topology_g23.schemas import TopologyHypothesis
    hypothesis = TopologyHypothesis("gold", example.gold.spans, example.gold.relations, "accept", 1.0, 1.0)
    result = assemble(example.source, hypothesis)
    assert result is not None
    assert result.ir.operations
    assert result.handoff.field_operators


def test_ambiguous_fragment_does_not_assemble():
    example = next(item for item in generate_sentence_examples("development") if item.gold.disposition != "accept")
    from topology_g23.schemas import TopologyHypothesis
    hypothesis = TopologyHypothesis("amb", example.gold.spans, (), example.gold.disposition, 1.0, 1.0)
    assert assemble(example.source, hypothesis) is None
