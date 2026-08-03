import torch

from topology_g21.dataset import ROLE_LABELS
from topology_g21.models import MultiHead


def test_model_output_shapes():
    model = MultiHead(1539, len(ROLE_LABELS), True)
    output = model(torch.zeros((4, 1539)))
    assert output["relation"].shape == (4, 20)
    assert output["roles"].shape == (4, 3, len(ROLE_LABELS))
    assert output["embedding"].shape == (4, 128)
