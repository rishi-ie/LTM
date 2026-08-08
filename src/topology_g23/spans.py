from __future__ import annotations

import torch
from torch import Tensor, nn

from .registry import NODE_KINDS
from .schemas import SentenceSource, TypedSpanCandidate


class BiaffineSpanParser(nn.Module):
    """Bounded typed span lattice; preserves competing kinds for one boundary."""

    def __init__(self, hidden_size: int = 384, state_dim: int = 128, max_width: int = 48) -> None:
        super().__init__()
        self.state_dim = state_dim; self.max_width = max_width
        self.left = nn.Linear(hidden_size, state_dim)
        self.right = nn.Linear(hidden_size, state_dim)
        self.width = nn.Embedding(max_width + 1, 32)
        self.kind_embeddings = nn.Parameter(torch.randn(len(NODE_KINDS) + 1, state_dim) * 0.02)
        self.biaffine = nn.Parameter(torch.randn(len(NODE_KINDS) + 1, state_dim + 1, state_dim + 1) * 0.02)

    def logits(self, states: Tensor, mask: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        left = self.left(states); right = self.right(states)
        batch, tokens, _ = states.shape
        left_aug = torch.cat((left, torch.ones((batch, tokens, 1), device=states.device, dtype=states.dtype)), -1)
        right_aug = torch.cat((right, torch.ones((batch, tokens, 1), device=states.device, dtype=states.dtype)), -1)
        logits = torch.einsum("bti,kij,buj->btuk", left_aug, self.biaffine, right_aug)
        positions = torch.arange(tokens, device=states.device)
        valid_width = (positions.unsqueeze(0) >= positions.unsqueeze(1)) & ((positions.unsqueeze(0) - positions.unsqueeze(1)) < self.max_width)
        logits = logits.masked_fill(~valid_width.unsqueeze(0).unsqueeze(-1), -1e9)
        valid = mask.bool().unsqueeze(1) & mask.bool().unsqueeze(2)
        logits = logits.masked_fill(~valid.unsqueeze(-1), -1e9)
        return logits, left, right

    def candidate_lattice(self, source: SentenceSource, offsets: Tensor, states: Tensor, mask: Tensor, maximum: int = 32) -> tuple[TypedSpanCandidate, ...]:
        logits, _left, _right = self.logits(states, mask)
        probabilities = torch.softmax(logits[0], -1)
        rows = offsets[0].tolist(); candidates: list[TypedSpanCandidate] = []
        per_kind = {kind: [] for kind in NODE_KINDS}
        for start in range(probabilities.shape[0]):
            for end in range(start, min(probabilities.shape[1], start + self.max_width)):
                if rows[start][1] <= rows[start][0] or rows[end][1] <= rows[end][0] or rows[end][1] <= rows[start][0]:
                    continue
                values, indices = torch.topk(probabilities[start, end], min(4, probabilities.shape[-1]))
                for value, index in zip(values.tolist(), indices.tolist()):
                    if index == 0 or value <= 0.001:
                        continue
                    kind = NODE_KINDS[index - 1]
                    begin, finish = rows[start][0], rows[end][1]
                    item = TypedSpanCandidate(f"s-{start}-{end}-{kind}", source.text[begin:finish], begin, finish, kind, float(value), float(value))
                    per_kind[kind].append(item)
        for kind in NODE_KINDS:
            candidates.extend(sorted(per_kind[kind], key=lambda item: (-item.span_probability, item.start, item.end))[:6])
        candidates.sort(key=lambda item: (-item.span_probability, item.start, item.end, item.node_kind))
        return tuple(candidates[:maximum])


def span_loss(logits: Tensor, positives: list[tuple[int, int, int]]) -> Tensor:
    """Class-balanced sampled loss; avoids the all-none start/end failure in G2.2."""
    if not positives:
        return logits.new_zeros(())
    selected = []
    targets = []
    for start, end, kind in positives:
        selected.append(logits[0, start, end]); targets.append(kind + 1)
    values = torch.stack(selected); target = torch.tensor(targets, device=logits.device)
    return nn.functional.cross_entropy(values, target)
