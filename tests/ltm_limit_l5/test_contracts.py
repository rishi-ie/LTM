from __future__ import annotations

from dataclasses import fields

import pytest

from ltm_limit_l5.schemas import (
    FORBIDDEN_PUBLIC_FIELDS,
    CompiledPromptField,
    FieldEquilibriumResult,
    LatentModeState,
    PromptInfluenceRecord,
)


def _position(value: float = 0.0) -> tuple[float, ...]:
    return (value,) * 128


def test_public_prompt_contract_cannot_carry_answers_or_routes() -> None:
    names = {item.name for item in fields(CompiledPromptField)}
    assert names.isdisjoint(FORBIDDEN_PUBLIC_FIELDS)


def test_compiled_prompt_requires_exactly_one_encoder_call() -> None:
    influence = PromptInfluenceRecord(
        "prompt:u0", "alpha", _position(), 1.0, 1.0, 1, 1.0,
        "global", "reality:test", None, 1.0, "source:test",
    )
    compiled = CompiledPromptField(
        "prompt", (influence,), _position(), "accept", (), 1, "0" * 64,
    )
    assert compiled.encoder_calls == 1
    with pytest.raises(ValueError, match="compilation boundary"):
        CompiledPromptField("prompt", (influence,), _position(), "accept", (), 2, "0" * 64)


def test_result_cannot_commit_factual_operations() -> None:
    mode = LatentModeState("mode:0", _position(), (), 1.0, 1, (), "0" * 64)
    with pytest.raises(ValueError, match="cannot mutate"):
        FieldEquilibriumResult(
            "prompt", "unknown", (mode,), (mode,), (), None, (), (), (), "certified", (), ((),),
        )
