from __future__ import annotations

from topology_g26.cards import CARDS, RELATIONS
from topology_g26.dataset import generate_examples, load_runtime
from topology_g26.decoder import GoldenAtomInput, choose_candidate, enumerate_candidates
from topology_g26.metrics import evaluate, passes
from topology_g26.schemas import KernelGold, KernelPrediction


def test_candidates_never_create_an_illegal_g1_role_assignment() -> None:
    atoms = (GoldenAtomInput("a", "claim"), GoldenAtomInput("b", "claim"))
    candidates = enumerate_candidates(atoms)
    implication = next(item for item in candidates if item.relation_type == "implies")
    assert implication.role_bindings == (("premise", ("a",)), ("conclusion", ("b",)))


def test_low_margin_candidate_abstains() -> None:
    atoms = (GoldenAtomInput("a", "claim"), GoldenAtomInput("b", "claim"))
    candidates = enumerate_candidates(atoms)
    chosen = choose_candidate(candidates, tuple(0.0 for _ in candidates), probability_floor=.9, margin_floor=.5)
    assert chosen.disposition == "clarification_required"


def test_reversed_implication_is_a_distinct_candidate() -> None:
    atoms = (GoldenAtomInput("a", "claim"), GoldenAtomInput("b", "claim"))
    candidates = [item for item in enumerate_candidates(atoms) if item.relation_type == "implies"]
    assert {item.role_bindings for item in candidates} >= {
        (("premise", ("a",)), ("conclusion", ("b",))),
        (("premise", ("b",)), ("conclusion", ("a",))),
    }


def test_metrics_reject_a_reversed_accepted_direction() -> None:
    forward = next(item for item in enumerate_candidates((GoldenAtomInput("a", "claim"), GoldenAtomInput("b", "claim"))) if item.relation_type == "implies")
    reverse = next(item for item in enumerate_candidates((GoldenAtomInput("a", "claim"), GoldenAtomInput("b", "claim"))) if item.relation_type == "implies" and item.role_bindings != forward.role_bindings)
    gold = (KernelGold("s", forward, "positive", "asserted", "global"),)
    prediction = (KernelPrediction("s", reverse, "positive", "asserted", "global", True, True),)
    metrics = evaluate(gold, prediction)
    assert metrics["reversal_false_accepts"] == 1
    assert not passes(metrics)


def test_relation_cards_cover_g1_without_duplicates() -> None:
    assert tuple(card.relation_type for card in CARDS) == RELATIONS
    assert len({card.relation_type for card in CARDS}) == len(RELATIONS)
    assert all(len(card.structural_vector) == 64 for card in CARDS)


def test_clean_development_data_is_balanced_by_relation() -> None:
    examples = [item for item in generate_examples("development") if item.disposition == "accept"]
    counts = {relation: sum(item.candidate.relation_type == relation for item in examples) for relation in RELATIONS}
    assert set(counts.values()) == {140}


def test_unsupported_and_ambiguous_cases_have_no_relation_candidate() -> None:
    examples = generate_examples("development")
    assert all(item.candidate.relation_type is not None for item in examples if item.disposition == "accept")
    assert all(item.candidate.relation_type is None for item in examples if item.disposition != "accept")


def test_runtime_loader_contains_no_gold_candidate(tmp_path) -> None:
    from topology_g26.dataset import build_split

    build_split("development", tmp_path)
    runtime = load_runtime(tmp_path / "development" / "inputs.jsonl")
    assert runtime and all(item.candidate.relation_type is None for item in runtime)


def test_safe_coverage_is_a_kernel_gate() -> None:
    metrics = {
        "operator_macro_f1": 1.0,
        "named_role_exact": 1.0,
        "complete_exact": 1.0,
        "safe_coverage": 0.89,
        "accepted_exact_precision": 1.0,
        "polarity_accuracy": 1.0,
        "modality_accuracy": 1.0,
        "scope_accuracy": 1.0,
        "disposition_accuracy": 1.0,
        "fieldir_valid_rate": 1.0,
        "g1_valid_rate": 1.0,
        "reversal_false_accepts": 0,
        "invalid_insertions": 0,
    }
    assert not passes(metrics)
