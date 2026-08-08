from topology_g1.registry import REGISTRY
from topology_g211.basis import (
    build_basis,
    coordinates_for_relation,
    relation_from_coordinates,
    verify_basis,
)
from topology_g211.composer import compose_relation
from topology_g211.measure import AtomicMeasurementHead


def test_basis_covers_every_g1_relation_and_role() -> None:
    manifest = build_basis()
    result = verify_basis(manifest)
    assert result["relation_count"] == len(REGISTRY)
    assert result["unique_signatures"]
    assert result["reconstruction_exact"]
    assert result["signature_collisions"] == 0


def test_atomic_coordinates_reconstruct_every_relation() -> None:
    for relation in REGISTRY:
        coordinates = coordinates_for_relation(relation)
        assert relation_from_coordinates(coordinates) == relation
        assert compose_relation("basis-test", relation).relation_types == (relation,)


def test_measurement_head_shapes_and_pair_direction() -> None:
    import torch

    head = AtomicMeasurementHead(len(build_basis().features))
    outputs = head(torch.randn(2, 7, 384), torch.ones(2, 3, 7))
    width = len(build_basis().features)
    assert outputs["unary"].shape == (2, 3, width)
    assert outputs["pair"].shape == (2, 3, 3, width)
    assert outputs["context"].shape == (2, width)
