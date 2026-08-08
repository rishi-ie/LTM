from __future__ import annotations

import hashlib

from ltm_limit_l5.compiler_eval import (
    build_compiler_panel,
    compile_public_payloads,
    compiler_gold_payload,
    compiler_public_payload,
    evaluate_compiler_panel,
    score_compiler_predictions,
)


class _SharedAtomEncoder:
    def __init__(self) -> None:
        self.forward_calls = 0

    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        del source_id
        self.forward_calls += 1
        words = text.replace(",", "").replace("?", "").split()
        atom = words[1]
        raw = hashlib.shake_256(atom.encode()).digest(128)
        return tuple((item - 127.5) / 127.5 for item in raw)


def test_raw_compiler_panel_is_split_disjoint_and_contains_negative_cases() -> None:
    development = build_compiler_panel(100, 31, split="development")
    locked = build_compiler_panel(100, 32, split="locked")
    assert {item.source.text for item in development}.isdisjoint(
        item.source.text for item in locked if item.should_accept
    )
    assert sum(item.should_accept for item in development) == 80
    assert all(item.alignment_group is None for item in development if not item.should_accept)


def test_raw_compiler_metrics_use_real_compiler_outputs_and_one_passes() -> None:
    cases = build_compiler_panel(100, 41, split="development")
    metrics = evaluate_compiler_panel(cases, _SharedAtomEncoder())
    assert metrics["accepted_semantic_precision"] == 1.0
    assert metrics["safe_coverage"] == 1.0
    assert metrics["exact_content_agreement"] == 1.0
    assert metrics["coordinate_recall_at_8"] == 1.0
    assert metrics["incorrect_accepted_compilations"] == 0
    assert metrics["encoder_calls"] == metrics["expected_encoder_calls"] == 100


def test_locked_compiler_public_runtime_is_separate_from_gold_scoring() -> None:
    cases = build_compiler_panel(100, 43, split="locked")
    public = tuple(compiler_public_payload(item) for item in cases)
    gold = tuple(compiler_gold_payload(item) for item in cases)
    predictions = compile_public_payloads(public, _SharedAtomEncoder())
    metrics = score_compiler_predictions(public, gold, predictions)

    assert all("should_accept" not in row for row in public)
    assert all("expected_input_keys" not in row for row in public)
    assert metrics["accepted_semantic_precision"] == 1.0
    assert metrics["coordinate_recall_at_8"] == 1.0
