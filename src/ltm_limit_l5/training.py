"""Fixed, answer-free alignment curriculum for the shared L5 coordinate kernel."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .compiler_eval import controlled_atom
from .kernel import EquilibriumKernel, train_kernel


@dataclass(frozen=True, slots=True)
class AlignmentExample:
    prompt_text: str
    relevant_body_text: str
    unrelated_body_text: str


@dataclass(frozen=True, slots=True)
class AlignmentArrays:
    texts: tuple[str, ...]
    semantic_rows: np.ndarray
    positive_pairs: np.ndarray
    negative_pairs: np.ndarray
    body_triples: np.ndarray


def build_alignment_examples(count: int, seed: int) -> tuple[AlignmentExample, ...]:
    """Generate reusable body/prompt pairs with no answer or route metadata."""

    if count < 2:
        raise ValueError("alignment corpus requires at least two examples")
    rows = []
    for index in range(count):
        source = controlled_atom(seed, index, "condition")
        outcome = controlled_atom(seed, index, "outcome")
        wrong_source = controlled_atom(
            seed, (index + count // 2 + 1) % count, "condition"
        )
        wrong_outcome = controlled_atom(
            seed, (index + count // 2 + 1) % count, "outcome"
        )
        rows.append(
            AlignmentExample(
                f"given {source}, what follows?",
                f"when {source} then {outcome}",
                f"when {wrong_source} then {wrong_outcome}",
            )
        )
    return tuple(rows)


def alignment_arrays_from_rows(
    examples: tuple[AlignmentExample, ...],
    semantic_rows: np.ndarray,
) -> AlignmentArrays:
    texts = tuple(
        text
        for item in examples
        for text in (item.prompt_text, item.relevant_body_text, item.unrelated_body_text)
    )
    values = np.asarray(semantic_rows, dtype=np.float32)
    if values.shape != (len(texts), 384) or not np.isfinite(values).all():
        raise ValueError("alignment semantic rows must be finite [items,384]")
    positive = []
    negative = []
    triples = []
    for index in range(len(examples)):
        prompt, relevant, unrelated = 3 * index, 3 * index + 1, 3 * index + 2
        positive.append((prompt, relevant))
        negative.append((prompt, unrelated))
        triples.append((prompt, relevant, unrelated))
    return AlignmentArrays(
        texts,
        values,
        np.asarray(positive, dtype=np.int64),
        np.asarray(negative, dtype=np.int64),
        np.asarray(triples, dtype=np.int64),
    )


def encode_alignment_examples(
    examples: tuple[AlignmentExample, ...],
    model_path: Path,
    *,
    batch_size: int = 64,
) -> AlignmentArrays:
    """Encode training items locally; runtime still uses one pass per item."""

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    texts = tuple(
        text
        for item in examples
        for text in (item.prompt_text, item.relevant_body_text, item.unrelated_body_text)
    )
    model = SentenceTransformer(str(model_path), local_files_only=True, device="cpu")
    rows = model.encode(
        list(texts),
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)
    return alignment_arrays_from_rows(examples, rows)


def train_alignment_kernel(
    arrays: AlignmentArrays,
    *,
    steps: int,
    batch_size: int,
    seed: int,
) -> tuple[EquilibriumKernel, tuple[float, ...]]:
    return train_kernel(
        arrays.semantic_rows,
        arrays.positive_pairs,
        arrays.negative_pairs,
        arrays.body_triples,
        steps=steps,
        batch_size=batch_size,
        seed=seed,
    )


__all__ = [
    "AlignmentArrays",
    "AlignmentExample",
    "alignment_arrays_from_rows",
    "build_alignment_examples",
    "encode_alignment_examples",
    "train_alignment_kernel",
]
