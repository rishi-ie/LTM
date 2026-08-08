from __future__ import annotations

from ltm_inference_i21.dataset import generate_bodies
from ltm_inference_i21.kernel import AlignedTransitionKernel, infer
from ltm_inference_i21.schemas import DynamicPrompt
from ltm_inference_i22.field import GlobalTreeField


def test_global_tree_has_no_identity_route_and_accounts_for_every_body() -> None:
    bodies, units, vectors = generate_bodies("test", 512, 31)
    field = GlobalTreeField(bodies, units, vectors)
    model = AlignedTransitionKernel()
    field.refresh(model)
    assert not hasattr(field, "by_source_identity")
    assert field.tree_membership_ok()


def test_global_tree_routes_terminal_path_without_identity_lookup() -> None:
    bodies, units, vectors = generate_bodies("test", 512, 37)
    field = GlobalTreeField(bodies, units, vectors)
    model = AlignedTransitionKernel()
    field.refresh(model)
    source = next(unit for unit in units if unit.phase_index == 0 and unit.identity_key.endswith("state:60"))
    result = infer(model, field, DynamicPrompt("p", (source.unit_id,), source.scope_key, 64, 64), confidence=.99999)
    assert result.disposition == "candidate"
    assert len(result.visited_body_ids) == 4
    assert field.units[result.selected_candidate_id].identity_key.endswith("state:64")
