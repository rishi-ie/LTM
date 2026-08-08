import torch

from topology_g29.atom_bank import ATOM_BANK_V1
from topology_g29.model import GoldenQueryKernel


def test_dynamic_query_shapes_and_three_slots() -> None:
    model = GoldenQueryKernel(ATOM_BANK_V1)
    anchors = torch.randn(18 + len(model.layout.role_keys), 384)
    operators, _roles, queries = model.dynamic_queries(anchors)
    assert operators.shape == (18, 192)
    assert queries.shape == (54, 192)
