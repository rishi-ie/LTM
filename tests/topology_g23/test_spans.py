import torch

from topology_g23.dataset import generate_sentence_examples
from topology_g23.spans import BiaffineSpanParser


def test_span_parser_has_bounded_candidates():
    example = generate_sentence_examples("development")[0]
    parser = BiaffineSpanParser()
    states = torch.randn(1, 16, 384)
    offsets = torch.tensor([[[0, 1]] * 16])
    candidates = parser.candidate_lattice(example.source, offsets, states, torch.ones(1, 16, dtype=torch.long))
    assert len(candidates) <= 32
