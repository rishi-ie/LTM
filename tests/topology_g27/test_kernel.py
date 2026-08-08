from __future__ import annotations

from topology_g27.atom_bank import ATOM_BANK, BANK_HASH, RELATIONS
from topology_g27.dataset import generate


def test_atom_bank_matches_g1_registry() -> None:
    assert len(ATOM_BANK) == 18
    assert len(set(RELATIONS)) == 18
    assert len(BANK_HASH) == 64


def test_split_has_multi_relations_and_rejections() -> None:
    runtime, gold = generate("development")
    assert len(runtime) == len(gold) == 3600
    assert sum(item.family == "multi" for item in gold) == 720
    assert sum(item.disposition == "clarification_required" for item in gold) == 360
    assert sum(item.disposition == "quarantine" for item in gold) == 360


def test_split_names_do_not_overlap() -> None:
    train, _ = generate("train")
    dev, _ = generate("development")
    assert not ({item.text for item in train} & {item.text for item in dev})
