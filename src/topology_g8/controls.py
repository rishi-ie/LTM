from __future__ import annotations

from dataclasses import replace

import numpy as np

from .engine import _block_contribution, ordered_blocks, prepare
from .store import BlockStore


def vector(state, request) -> np.ndarray:
    values = dict(state.confidence_values)
    values.update(dict(state.preference_values))
    values.update(dict(state.reference_values))
    values["u:unknown"] = state.uncertainty
    return np.array([values[item.variable_id] for item in request.soft_variables], dtype=np.float64)


def scores(request, field_root, settings: dict, reference, seed: int) -> dict[str, bool]:
    """Controls intentionally violate G8's global-reduce-before-update rule."""
    from .engine import evaluate_reference

    ordered = ordered_blocks(request, "ascending", seed)
    last = evaluate_reference(replace(request, selected_block_ids=(ordered[-1],)), field_root, settings)
    local_states = [
        evaluate_reference(replace(request, selected_block_ids=(block_id,)), field_root, settings)
        for block_id in ordered
    ]
    averaged = np.mean([vector(item.final_state, request) for item in local_states], axis=0)
    store = BlockStore(field_root, 1)
    prepared = prepare(request, store, ordered)
    values = np.array([item.initial for item in request.soft_variables], dtype=np.float64)
    positions = {item.variable_id: index for index, item in enumerate(request.soft_variables)}
    for block in prepared:
        contribution = _block_contribution(values, block, positions, None)
        values = np.clip(values - settings["learning_rate"] * np.array(contribution.gradient), 0, 1)
    reference_vector = vector(reference.final_state, request)
    return {
        "last_block_wins": last.hard_result.conclusion == reference.hard_result.conclusion
        and last.disposition == reference.disposition,
        "average_local_states": float(np.linalg.norm(averaged - reference_vector)) <= 1e-8,
        "sequential_update": float(np.linalg.norm(values - reference_vector)) <= 1e-8,
    }
