from topology_g29.dataset import SIZES, generate, production_signature


def test_split_sizes_and_disjoint_production_signatures() -> None:
    train, _ = generate("train")
    development, _ = generate("development")
    assert len(train) == sum(SIZES["train"])
    assert len(development) == sum(SIZES["development"])
    assert not {production_signature(item.text) for item in train} & {production_signature(item.text) for item in development}
