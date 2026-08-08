import torch

from ltm_inference_i31.kernel import SearchKernel
from ltm_limit_l1.generator import formal_case, traversal_case
from ltm_limit_l1.runner import _observation


def test_grounded_depth_is_exact_and_over_budget_is_not_claimed():
    model = SearchKernel()
    model.load_state_dict(torch.load("workspaces/ltm-inference-i3-1-r13/selected-kernel.pt", map_location="cpu", weights_only=True))
    model.eval()
    short = _observation(formal_case(4, 1), model)
    assert short.proof_valid and short.discovered_depth == 4
    assert not _observation(traversal_case(65, 2, 4), model).proof_valid
