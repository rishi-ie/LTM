"""Bounded typed span lattice used after a passing kernel."""

from __future__ import annotations

import torch

from .schemas import AtomCandidate


def build_span_lattice(
    text: str,
    offsets: torch.Tensor,
    token_states: torch.Tensor,
    *,
    maximum_spans: int = 48,
    maximum_width: int = 48,
) -> tuple[AtomCandidate, ...]:
    """Return deterministic non-empty spans; no span is committed here."""
    candidates: list[AtomCandidate] = []
    token_count = int(offsets.shape[0])
    for start in range(token_count):
        for end in range(start, min(token_count, start + maximum_width)):
            left, right = int(offsets[start, 0]), int(offsets[end, 1])
            if right <= left or not text[left:right].strip():
                continue
            state = token_states[start : end + 1].mean(0)
            vector = torch.nn.functional.normalize(state, dim=0).detach().cpu().float()
            candidates.append(AtomCandidate(f"span:{left}:{right}", text[left:right], left, right, "claim", 0.5, tuple(float(v) for v in vector)))
    candidates.sort(key=lambda item: (-(item.end - item.start), item.start, item.end, item.candidate_id if hasattr(item, "candidate_id") else item.atom_id))
    return tuple(candidates[:maximum_spans])

