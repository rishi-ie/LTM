"""Offline inference for the atomic-coordinate kernel."""

from __future__ import annotations

from pathlib import Path

import torch

from .basis import build_basis, relation_from_coordinates
from .dataset import AtomicExample
from .encoder import OnePassMiniLM
from .measure import AtomicMeasurementHead
from .schemas import AtomicCoordinate, AtomicFieldPatch
from .training import _span_masks


def load_checkpoint(path: Path) -> tuple[OnePassMiniLM, AtomicMeasurementHead]:
    basis = build_basis()
    encoder = OnePassMiniLM().eval()
    head = AtomicMeasurementHead(len(basis.features)).eval()
    state = torch.load(path, map_location="cpu", weights_only=True)
    encoder.load_state_dict(state["encoder"])
    head.load_state_dict(state["head"])
    return encoder, head


def predict_example(
    encoder: OnePassMiniLM,
    head: AtomicMeasurementHead,
    example: AtomicExample,
    *,
    threshold: float = 0.5,
) -> AtomicFieldPatch:
    basis = build_basis()
    tokens, span_masks = _span_masks(encoder.tokenizer, [example.text], [example])
    input_ids = tokens["input_ids"]
    attention_mask = tokens["attention_mask"]
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    with torch.no_grad():
        hidden = encoder(input_ids, attention_mask, **extra)
        output = head(hidden, span_masks)
        values = torch.sigmoid(output["context"])[0]
    selected = tuple(
        AtomicCoordinate(f"feature:{item.description}", float(values[index]))
        for index, item in enumerate(basis.features)
        if float(values[index]) >= threshold
    )
    if example.disposition != "accept":
        return AtomicFieldPatch(example.source_id, selected, (), (), "clarification_required")
    try:
        relation = relation_from_coordinates(
            tuple(AtomicCoordinate(item.basis_id, 1.0) for item in selected)
        )
    except ValueError:
        return AtomicFieldPatch(example.source_id, selected, (), (), "quarantine", ("ATOMIC_SIGNATURE_NOT_UNIQUE",))
    return AtomicFieldPatch(example.source_id, selected, (relation,), (), "accept")
