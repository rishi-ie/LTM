from __future__ import annotations

import hashlib
import json
import re

from ltm_limit_l5.compiler import DeterministicCoordinateEncoder
from ltm_limit_l5.end_to_end import (
    build_raw_chain_case,
    build_raw_end_to_end_panel,
    compile_raw_chain,
    raw_chain_gold_payload,
    raw_chain_public_payload,
    score_raw_chains,
)


class _InputAlignedEncoder:
    """Deterministic semantic stand-in: shared inputs share coordinates."""

    def __init__(self) -> None:
        self.forward_calls = 0

    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        del source_id
        self.forward_calls += 1
        match = re.search(
            r"^(?:when|given)\s+([A-Za-z][A-Za-z0-9_.:-]*)",
            text,
            re.IGNORECASE,
        )
        assert match is not None
        raw = hashlib.shake_256(match.group(1).encode()).digest(256)
        return tuple(
            (int.from_bytes(raw[index : index + 2], "big") / 32767.5) - 1
            for index in range(0, len(raw), 2)
        )


def test_raw_chain_keeps_runtime_input_separate_from_evaluator_gold() -> None:
    case = build_raw_chain_case(4, 20270610, split="test")

    public = raw_chain_public_payload(case)
    gold = raw_chain_gold_payload(case)

    assert "expected_semantic_key" not in public
    assert "depth" not in public
    assert {
        "case_id",
        "expected_semantic_key",
        "expected_disposition",
        "expected_candidates",
        "depth",
    } <= set(gold)
    assert all("expected" not in source for source in public["sources"])


def test_raw_chain_runs_the_complete_authority_bounded_path() -> None:
    case = build_raw_chain_case(4, 20270610, split="test")
    public = raw_chain_public_payload(case)
    encoder = DeterministicCoordinateEncoder()

    prediction = compile_raw_chain(public, encoder)
    metrics = score_raw_chains(
        (public,),
        (raw_chain_gold_payload(case),),
        (prediction,),
    )

    assert prediction["disposition"] == "candidate"
    assert prediction["selected_semantic_key"] == case.expected_semantic_key
    assert prediction["certificate_body_count"] == case.depth
    assert prediction["decoder_authorized"] is True
    assert prediction["encoder_calls"] == case.depth + 1
    assert encoder.forward_calls == case.depth + 1
    assert prediction["factual_operations"] == ()
    assert metrics["accepted_precision"] == 1.0
    assert metrics["all_case_exactness"] == 1.0
    assert metrics["one_pass_per_item"] == 1.0


def test_raw_chain_evaluator_detects_an_incorrect_accepted_result() -> None:
    case = build_raw_chain_case(0, 20270610, split="test")
    public = raw_chain_public_payload(case)
    prediction = compile_raw_chain(public, DeterministicCoordinateEncoder())
    prediction["selected_semantic_key"] = "atom:incorrect"

    metrics = score_raw_chains(
        (public,),
        (raw_chain_gold_payload(case),),
        (prediction,),
    )

    assert metrics["accepted_precision"] == 0.0
    assert metrics["all_case_exactness"] == 0.0
    assert metrics["incorrect_accepted_predictions"] == 1


def test_raw_chain_uses_supplied_acceptance_thresholds() -> None:
    case = build_raw_chain_case(0, 20270610, split="test")
    prediction = compile_raw_chain(
        raw_chain_public_payload(case),
        DeterministicCoordinateEncoder(),
        margin_threshold=1.1,
    )

    assert prediction["disposition"] == "ambiguous"


def test_raw_panel_covers_depths_and_safe_null_dispositions() -> None:
    panel = build_raw_end_to_end_panel(32, 20270610, split="test-panel")
    public = tuple(raw_chain_public_payload(item) for item in panel)
    gold = tuple(raw_chain_gold_payload(item) for item in panel)
    encoder = _InputAlignedEncoder()
    predictions = tuple(compile_raw_chain(item, encoder) for item in public)

    metrics = score_raw_chains(public, gold, predictions)

    assert {item.depth for item in panel if item.expected_disposition == "candidate"} == set(
        range(1, 17)
    )
    assert {item.expected_disposition for item in panel} == {
        "candidate",
        "unknown",
        "ambiguous",
        "alternatives",
    }
    assert metrics["accepted_precision"] == 1.0
    assert metrics["unknown_or_alternative_agreement"] == 1.0
    assert metrics["incorrect_accepted_predictions"] == 0
    assert all(value == 1.0 for value in metrics["family"].values())


def test_raw_panel_public_values_do_not_reveal_evaluator_family() -> None:
    panel = build_raw_end_to_end_panel(32, 20270610, split="test-panel")
    repeated = build_raw_end_to_end_panel(32, 20270610, split="test-panel")
    public = tuple(raw_chain_public_payload(item) for item in panel)

    assert public == tuple(raw_chain_public_payload(item) for item in repeated)
    assert all(re.fullmatch(r"test-panel:item:[0-9a-f]{20}", item["case_id"]) for item in public)
    serialized = json.dumps(public, sort_keys=True).lower()
    for hidden_label in (
        "answerable",
        "balanced_conflict",
        "alternatives",
        "ambiguous",
        "unknown",
        "candidate",
    ):
        assert hidden_label not in serialized
