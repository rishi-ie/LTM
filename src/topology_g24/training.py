"""Deterministic staged training for the G2.4 compiler."""

from __future__ import annotations

import random
from dataclasses import dataclass

import torch
from torch import Tensor

from .compiler import DISPOSITIONS, AtomTopologyCompiler
from .dataset import generate_examples
from .registry import NODE_KINDS, RELATION_LABELS
from .schemas import ProgramExample


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    epochs: int
    examples: int
    final_loss: float
    encoder_trainable: bool


def _token_targets(example: ProgramExample, offsets: Tensor, slots: int) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor, Tensor]:
    active = torch.zeros(slots, dtype=torch.float32)
    kinds = torch.zeros(slots, dtype=torch.long)
    start = torch.zeros(slots, dtype=torch.long)
    end = torch.zeros(slots, dtype=torch.long)
    for slot, atom in enumerate(example.gold.atoms[:slots]):
        active[slot] = 1.0
        kinds[slot] = NODE_KINDS.index(atom.node_kind)
        covered = ((offsets[:, 0] <= atom.source_start) & (offsets[:, 1] >= atom.source_end)).nonzero().flatten()
        overlap = ((offsets[:, 1] > atom.source_start) & (offsets[:, 0] < atom.source_end)).nonzero().flatten()
        tokens = covered if len(covered) else overlap
        if len(tokens):
            start[slot], end[slot] = tokens[0], tokens[-1]
    relation = torch.tensor(RELATION_LABELS.index(example.family) if example.gold.disposition == "accept" else 0)
    disposition = torch.tensor(DISPOSITIONS.index(example.gold.disposition))
    return active, kinds, start, end, relation, disposition


def _loss(model: AtomTopologyCompiler, batch: list[ProgramExample]) -> Tensor:
    tokens = model.encoder.tokenize([item.source.text for item in batch])
    offsets = tokens["offset_mapping"]
    output = model(tokens)
    pieces: list[Tensor] = []
    for row, example in enumerate(batch):
        active, kinds, start, end, relation, disposition = _token_targets(example, offsets[row], model.grounder.slots)
        active = active.to(output["active_logits"].device)
        kinds, start, end, relation, disposition = (value.to(active.device) for value in (kinds, start, end, relation, disposition))
        pieces.append(torch.nn.functional.binary_cross_entropy_with_logits(output["active_logits"][row], active))
        selected = active.bool()
        if selected.any():
            pieces.append(torch.nn.functional.cross_entropy(output["type_logits"][row][selected], kinds[selected]))
            pieces.append(torch.nn.functional.cross_entropy(output["start_logits"][row][selected], start[selected]))
            pieces.append(torch.nn.functional.cross_entropy(output["end_logits"][row][selected], end[selected]))
        if example.gold.disposition == "accept":
            pieces.append(torch.nn.functional.cross_entropy(output["relation_logits"][row : row + 1], relation.view(1)))
        pieces.append(torch.nn.functional.cross_entropy(output["disposition_logits"][row : row + 1], disposition.view(1)))
    return torch.stack(pieces).mean()


def train_compiler(
    *,
    encoder_trainable: bool,
    head_epochs: int = 1,
    fine_tune_epochs: int = 1,
    limit: int | None = None,
) -> tuple[AtomTopologyCompiler, TrainingSummary]:
    """Two-stage run: train heads, then optionally unfreeze encoder once."""
    torch.manual_seed(1746)
    torch.set_num_threads(4)
    examples = list(generate_examples("train"))
    if limit is not None:
        examples = examples[:limit]
    model = AtomTopologyCompiler(encoder_trainable=False)
    phases = [(False, head_epochs)] + ([(True, fine_tune_epochs)] if encoder_trainable else [])
    final_loss = 0.0
    for unfreeze, epochs in phases:
        for parameter in model.encoder.model.parameters():
            parameter.requires_grad = unfreeze
        params = [parameter for parameter in model.parameters() if parameter.requires_grad]
        optimizer = torch.optim.AdamW(params, lr=1e-5 if unfreeze else 5e-4, weight_decay=0.01)
        for epoch in range(epochs):
            random.Random(1746 + epoch + (100 if unfreeze else 0)).shuffle(examples)
            model.train()
            for start in range(0, len(examples), 8):
                optimizer.zero_grad(set_to_none=True)
                loss = _loss(model, examples[start : start + 8])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                optimizer.step()
                final_loss = float(loss.detach())
    model.eval()
    return model, TrainingSummary(head_epochs + (fine_tune_epochs if encoder_trainable else 0), len(examples), final_loss, encoder_trainable)
