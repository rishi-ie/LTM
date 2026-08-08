from __future__ import annotations

import numpy as np

from ltm_limit_l5.kernel import parameter_count
from ltm_limit_l5.training import (
    alignment_arrays_from_rows,
    build_alignment_examples,
    train_alignment_kernel,
)


def test_alignment_curriculum_contains_no_answer_or_route_metadata() -> None:
    examples = build_alignment_examples(16, 19)
    assert len(examples) == 16
    assert len(set(examples)) == 16
    assert all("answer" not in repr(item).lower() for item in examples)
    assert all("route" not in repr(item).lower() for item in examples)
    assert all(item.prompt_text.startswith("given ") for item in examples)


def test_alignment_arrays_and_kernel_fit_replacement_budget() -> None:
    examples = build_alignment_examples(8, 23)
    rng = np.random.default_rng(23)
    rows = rng.normal(size=(len(examples) * 3, 384)).astype(np.float32)
    rows /= np.linalg.norm(rows, axis=1, keepdims=True)
    arrays = alignment_arrays_from_rows(examples, rows)
    kernel, losses = train_alignment_kernel(
        arrays, steps=3, batch_size=8, seed=23
    )

    assert arrays.positive_pairs.shape == arrays.negative_pairs.shape == (8, 2)
    assert arrays.body_triples.shape == (8, 3)
    assert parameter_count(kernel) <= 2_000_000
    assert len(losses) == 3
    assert all(np.isfinite(item) for item in losses)
