from __future__ import annotations

import pytest

from topology_g10.decode import decode
from topology_g10.generator import build
from topology_g10.prompting import render
from topology_g10.validator import adversarial, fallback, validate
from topology_g10.worker import main as worker_main


def test_fallback_is_authorized_for_every_category() -> None:
    bundles, _ = build(1738, 24)
    assert all(validate(fallback(bundle), bundle).accepted for bundle in bundles)


def test_adversarial_claims_are_rejected() -> None:
    bundles, _ = build(1738, 8)
    assert all(not validate(text, bundle).accepted for bundle in bundles for text in adversarial(bundle))
    assert sum(len(adversarial(bundle)) for bundle in bundles) == 64


def test_unknown_bundle_requires_abstention() -> None:
    bundles, _ = build(1738, 8)
    unknown = next(bundle for bundle in bundles if bundle.category == "unknown")
    assert not validate("I can verify it.", unknown).accepted


def test_controls_separate_state_and_claim_table() -> None:
    bundle, *_ = build(1738, 1)[0]
    state_only = render(bundle, "state_only")
    no_state = render(bundle, "no_state")
    assert "Allowed claims:\n- withheld" in state_only
    assert "Proof: withheld" in state_only
    assert "Verifier status: withheld" in state_only
    assert bundle.proof_summary not in state_only
    assert "State: withheld" in no_state
    assert bundle.proof_summary in no_state


def test_generator_balances_styles_and_polarities() -> None:
    bundles, _ = build(20260811, 64)
    assert {bundle.state.style for bundle in bundles} == {"brief", "explanatory", "formal", "conversational"}
    factual = [bundle for bundle in bundles if bundle.authorized_claims]
    assert {bundle.authorized_claims[0].polarity for bundle in factual} == {"positive", "negative"}


def test_negative_claim_and_opposite_polarity_are_distinguished() -> None:
    bundles, _ = build(1738, 8)
    negative = next(bundle for bundle in bundles if bundle.authorized_claims and bundle.authorized_claims[0].polarity == "negative")
    assert validate(fallback(negative), negative).accepted
    positive = f"{negative.authorized_claims[0].entity} {negative.authorized_claims[0].predicate} {negative.authorized_claims[0].object}."
    assert not validate(positive, negative).accepted


def test_worker_denies_a_gold_path_before_model_loading() -> None:
    with pytest.raises(RuntimeError, match="GOLD_PATH_DENIED"):
        worker_main(["--bundles", "/tmp/gold/bundles.json", "--output", "/tmp/output.json", "--model-path", "/tmp/model", "--max-tokens", "64"])


def test_failed_repair_uses_verified_fallback_once() -> None:
    class InvalidModel:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, prompt: str, max_tokens: int) -> tuple[str, int, float]:
            self.calls += 1
            return "Velin-999 owns prism-999.", 4, 1.0

    bundle, *_ = build(1738, 1)[0]
    model = InvalidModel()
    result = decode(bundle, model, {"max_tokens": 64})
    assert model.calls == 2
    assert result.fallback_used
    assert result.validation.accepted
