from __future__ import annotations

from pathlib import Path

from ltm_limit_l3.generator import grounded_case
from ltm_limit_l3.runtime import run_case


def test_forty_five_hop_proof_replays_independently():
    checkpoint = Path("workspaces/ltm-inference-i3-1-r13/selected-kernel.pt")
    case = grounded_case(45, 3)
    result = run_case(case, case.bodies, checkpoint)
    assert result.disposition == "proved"
    assert result.proof_steps == 45
    assert result.proof_valid
    assert result.failure_code == "NONE"
