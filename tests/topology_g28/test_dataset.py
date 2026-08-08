from topology_g28.dataset import generate, production_signature


def test_split_vocabulary_and_production_signatures_are_disjoint() -> None:
    train, _ = generate("train")
    locked, _ = generate("locked")
    train_signatures = {production_signature(item.text) for item in train[:200]}
    locked_signatures = {production_signature(item.text) for item in locked[:200]}
    assert train_signatures.isdisjoint(locked_signatures)
