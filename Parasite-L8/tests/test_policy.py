from __future__ import annotations

import pytest

from parasite_l8.policy import compile_policy


def test_policy_is_canonical_and_bounded() -> None:
    first = compile_policy("p", [{"opcode": "path_decay", "value": 0.9}, {"opcode": "candidate_threshold", "value": 0.6}])
    second = compile_policy("p", [{"opcode": "candidate_threshold", "value": 0.6}, {"opcode": "path_decay", "value": 0.9}])
    assert first.hash == second.hash
    assert first.instructions[0].opcode == "candidate_threshold" or first.instructions[0].opcode == "path_decay"


@pytest.mark.parametrize("row", [
    {"opcode": "unknown", "value": 1},
    {"opcode": "path_decay", "value": 0.1},
    {"opcode": "candidate_threshold", "value": 2},
])
def test_invalid_policy_fails_closed(row: dict) -> None:
    with pytest.raises(ValueError):
        compile_policy("bad", [row])


def test_conflicting_same_tier_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="POLICY_CONFLICT"):
        compile_policy("bad", [
            {"opcode": "response_style", "value": "brief", "source_id": "a"},
            {"opcode": "response_style", "value": "detailed", "source_id": "b"},
        ])
