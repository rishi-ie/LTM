import pytest

from ltm_inference_i3.schemas import FormalExpression
from ltm_limit_l4.schemas import L4Problem


def test_runtime_contract_rejects_wrong_reality_and_budgets() -> None:
    atom = FormalExpression("symbol", value="x")
    with pytest.raises(ValueError):
        L4Problem("p", atom, atom, "other-reality")
    with pytest.raises(ValueError):
        L4Problem("p", atom, atom, "standard-l4-v1", maximum_steps=65)
