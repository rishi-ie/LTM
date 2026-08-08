from __future__ import annotations

import pytest

from ltm_limit_l5.compiler import (
    CompilerIntegrityError,
    DeterministicCoordinateEncoder,
    SharedCoordinateCompiler,
    compile_prompt,
    controlled_source,
)


def test_source_and_prompt_share_one_pass_coordinate_boundary() -> None:
    encoder = DeterministicCoordinateEncoder()
    compiler = SharedCoordinateCompiler(encoder)
    item = controlled_source("For every x, x + 0 = x")

    stored = compiler.compile_source(item)
    prompt = compiler.compile_prompt(item)

    assert stored.disposition == prompt.disposition == "accept"
    assert stored.semantic_position == prompt.anchor_position
    assert stored.content is not None
    assert stored.content.input_keys == (prompt.influences[0].semantic_key,)
    assert stored.encoder_calls == prompt.encoder_calls == 1
    assert encoder.forward_calls == 2


def test_context_and_weights_are_explicit_and_exact() -> None:
    item = controlled_source(
        "5 + 0 = 5",
        scope_key="session:7",
        reality_key="custom:blue",
        valid_at=42,
        polarity=-1,
        modality="hypothetical",
        compiler_confidence=0.98,
        provenance_id="source:paper:9",
    )
    result = compile_prompt(item, DeterministicCoordinateEncoder())
    influence = result.influences[0]

    assert influence.clamp_strength == 1.0
    assert influence.query_relevance_weight == 0.98
    assert influence.polarity_sign == -1
    assert influence.modality_weight == 0.5
    assert (influence.scope_key, influence.reality_key, influence.valid_at) == (
        "session:7",
        "custom:blue",
        42,
    )
    assert influence.provenance_id == "source:paper:9"


def test_low_confidence_or_open_ended_input_clarifies_without_influence() -> None:
    low = compile_prompt(
        controlled_source("5 + 0 = 5", compiler_confidence=0.94),
        DeterministicCoordinateEncoder(),
    )
    open_ended = compile_prompt(
        controlled_source("What is 5 + 0?"),
        DeterministicCoordinateEncoder(),
    )

    assert low.disposition == open_ended.disposition == "clarification_required"
    assert low.influences == open_ended.influences == ()
    assert low.failure_codes == ("LOW_COMPILER_CONFIDENCE",)
    assert open_ended.failure_codes == ("GOAL_DISCOVERY_REQUIRED",)


def test_compiler_never_returns_factual_operations() -> None:
    result = SharedCoordinateCompiler(DeterministicCoordinateEncoder()).compile_source(
        controlled_source("5 + 0 = 5")
    )
    assert result.factual_operations == ()
    assert result.provenance_id == "source:local"


def test_abstract_body_compiles_exact_inputs_and_outcomes() -> None:
    result = SharedCoordinateCompiler(DeterministicCoordinateEncoder()).compile_source(
        controlled_source("when metal_hot and pressure_high then valve_open and alarm_on")
    )

    assert result.disposition == "accept"
    assert result.content is not None
    assert result.content.content_kind == "abstract_body"
    assert len(result.content.input_keys) == len(result.content.outcome_keys) == 2
    assert set(result.content.input_keys).isdisjoint(result.content.outcome_keys)


def test_abstract_prompt_emits_one_influence_per_input_in_one_pass() -> None:
    encoder = DeterministicCoordinateEncoder()
    result = compile_prompt(
        controlled_source("given metal_hot and pressure_high, what follows?"),
        encoder,
    )

    assert result.disposition == "accept"
    assert len(result.influences) == 2
    assert len({item.semantic_key for item in result.influences}) == 2
    assert all(item.semantic_position == result.anchor_position for item in result.influences)
    assert encoder.forward_calls == result.encoder_calls == 1


@pytest.mark.parametrize(
    ("text", "failure"),
    [
        ("when metal_hot and then valve_open", "ABSTRACT_ATOM_MALFORMED"),
        ("given , what follows?", "ABSTRACT_PROMPT_MALFORMED"),
        ("given metal_hot, what follows? expected_depth=4", "FORBIDDEN_RUNTIME_METADATA"),
        ("when route_identifier then valve_open", "FORBIDDEN_RUNTIME_METADATA"),
        ("given metal_hot, what follows? answer=valve_open", "FORBIDDEN_RUNTIME_METADATA"),
    ],
)
def test_abstract_grammar_rejects_malformed_atoms_and_runtime_metadata(
    text: str, failure: str
) -> None:
    result = compile_prompt(controlled_source(text), DeterministicCoordinateEncoder())
    assert result.disposition == "clarification_required"
    assert result.influences == ()
    assert result.failure_codes == (failure,)


def test_source_and_prompt_forms_cannot_be_interchanged() -> None:
    compiler = SharedCoordinateCompiler(DeterministicCoordinateEncoder())
    prompt_as_source = compiler.compile_source(
        controlled_source("given metal_hot, what follows?")
    )
    body_as_prompt = compiler.compile_prompt(
        controlled_source("when metal_hot then valve_open")
    )

    assert prompt_as_source.failure_codes == ("SOURCE_BODY_REQUIRED",)
    assert body_as_prompt.failure_codes == ("PROMPT_FORM_REQUIRED",)


class _BadCallEncoder(DeterministicCoordinateEncoder):
    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        result = super().encode(source_id, text)
        self.forward_calls += 1
        return result


class _BadDimensionEncoder(DeterministicCoordinateEncoder):
    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        super().encode(source_id, text)
        return (1.0,)


@pytest.mark.parametrize("encoder", [_BadCallEncoder(), _BadDimensionEncoder()])
def test_encoder_contract_fails_closed(encoder: DeterministicCoordinateEncoder) -> None:
    with pytest.raises(CompilerIntegrityError):
        compile_prompt(controlled_source("5 + 0 = 5"), encoder)
