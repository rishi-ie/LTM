from __future__ import annotations

import numpy as np

from ltm_limit_l5.kernel import EquilibriumKernel, NumpyCompatibility, parameter_count, train_kernel


def test_kernel_fits_the_replacement_budget() -> None:
    model = EquilibriumKernel()
    assert parameter_count(model) <= 2_000_000
    assert sum(item.numel() * item.element_size() for item in model.parameters()) <= 8_000_000


def test_shared_projection_and_gate_train_without_routes() -> None:
    rng = np.random.default_rng(5)
    rows = rng.normal(size=(12, 384)).astype(np.float32)
    rows[1] = rows[0] + 0.01
    rows[3] = rows[2] + 0.01
    positives = np.asarray(((0, 1), (2, 3)), dtype=np.int64)
    negatives = np.asarray(((0, 4), (2, 5)), dtype=np.int64)
    triples = np.asarray(((0, 1, 7), (2, 3, 8)), dtype=np.int64)
    model, losses = train_kernel(
        rows, positives, negatives, triples, steps=20, batch_size=2, seed=7
    )
    assert len(losses) == 20
    assert np.isfinite(losses).all()
    compatibility = NumpyCompatibility(model)
    position = model.project(__import__("torch").from_numpy(rows)).detach().numpy()
    relevant = compatibility(position[0], position[1], position[1], object())
    unrelated = compatibility(position[0], position[7], position[7], object())
    assert 0.75 <= unrelated < relevant <= 1
