import torch

from topology_g24.model import AtomSlotGrounder, RoleAwareHRM
from topology_g24.registry import RELATION_LABELS, ROLE_LABELS


def test_atom_slot_grounder_returns_multiple_normalized_atom_vectors_from_one_pass():
    torch.manual_seed(7)
    model = AtomSlotGrounder()
    states = torch.randn(2, 11, 384)
    mask = torch.ones(2, 11, dtype=torch.long)

    output = model(states, mask)

    assert output["slot_states"].shape == (2, 12, 128)
    assert output["type_logits"].shape == (2, 12, 19)
    assert output["start_logits"].shape == (2, 12, 11)
    assert torch.allclose(output["semantic_vectors"].norm(dim=-1), torch.ones(2, 12), atol=1e-6)


def test_hrm_keeps_directional_role_bindings_distinct():
    torch.manual_seed(11)
    hrm = RoleAwareHRM()
    atoms = torch.randn(2, 128)
    hub = torch.randn(1, 128)
    relation = torch.tensor([RELATION_LABELS.index("implies"), RELATION_LABELS.index("implies")])
    premise = ROLE_LABELS.index("premise")
    conclusion = ROLE_LABELS.index("conclusion")
    roles = torch.tensor([[premise, conclusion], [premise, conclusion]])

    forward, _, _ = hrm(atoms, hub, relation, roles, torch.tensor([[0, 1], [1, 0]]))

    assert forward.shape == (2,)
    assert not torch.equal(forward[0], forward[1])
