import torch
from torch import nn

from topology_g1.registry import REGISTRY
from topology_g212.dataset import generate
from topology_g212.model import FactorizedCompiler
from topology_g212.registry import RELATIONS, ROLES


class DummyEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.forward_calls = 0

    def forward(self, input_ids, attention_mask, **_extra):
        self.forward_calls += 1
        return torch.ones((*input_ids.shape, 384), dtype=torch.float32)


def test_factorized_shapes_and_single_forward() -> None:
    model = FactorizedCompiler(DummyEncoder()).eval()
    tokens = {
        "input_ids": torch.ones((1, 5), dtype=torch.long),
        "attention_mask": torch.ones((1, 5), dtype=torch.long),
    }
    masks = torch.zeros((1, 8, 5), dtype=torch.bool)
    masks[0, 0, 1] = True
    masks[0, 1, 2] = True
    output = model(tokens, masks)
    assert output["operator_logits"].shape == (1, len(RELATIONS))
    assert output["role_scores"].shape == (1, len(RELATIONS), len(ROLES), 8)
    assert output["pair_scores"].shape == (1, len(RELATIONS), 8, 8)
    assert model.encoder.forward_calls == 1


def test_every_g1_relation_has_registered_roles() -> None:
    assert set(RELATIONS) == set(REGISTRY)
    assert all(spec.roles for spec in REGISTRY.values())


def test_dataset_keeps_two_relation_cases_and_rejections() -> None:
    rows = generate("development")
    assert any(len(row.relations) == 2 for row in rows)
    assert any(row.disposition == "clarification_required" for row in rows)
    assert any(row.disposition == "quarantine" for row in rows)
    assert all(row.source_hash for row in rows)
