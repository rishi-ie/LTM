from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from torch import Tensor

from .dataset import ConversationCase
from .model import ConversationCompiler
from .registry import (
    ACTIONS,
    ACTS,
    DISPOSITIONS,
    MODALITIES,
    POLARITIES,
    REFERENCE_STATES,
    SCOPES,
    SLOT_TYPES,
)


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    steps: int
    loss: float
    trainable_parameters: int
    encoder_forward_calls: int


def make_batch(model: ConversationCompiler, examples: list[ConversationCase], maximum_spans: int = 8) -> tuple[dict[str, Tensor], Tensor]:
    tokens = model.encoder.tokenize([example.source.text for example in examples])
    offsets = tokens["offset_mapping"]
    masks = torch.zeros((len(examples), maximum_spans, offsets.shape[1]), dtype=torch.bool)
    for row, example in enumerate(examples):
        for column, span in enumerate(example.spans[:maximum_spans]):
            start, end = offsets[row, :, 0], offsets[row, :, 1]
            masks[row, column] = (end > span.start) & (start < span.end) & (end > start)
    return tokens, masks


def _targets(examples: list[ConversationCase], device: torch.device) -> dict[str, Tensor]:
    values = {
        "act": torch.tensor([ACTS.index(item.act) for item in examples], device=device),
        "action": torch.tensor([ACTIONS.index(item.action) for item in examples], device=device),
        "reference": torch.tensor([REFERENCE_STATES.index(item.reference_state) for item in examples], device=device),
        "polarity": torch.tensor([POLARITIES.index(item.polarity) for item in examples], device=device),
        "modality": torch.tensor([MODALITIES.index(item.modality) for item in examples], device=device),
        "scope": torch.tensor([SCOPES.index(item.scope_id) for item in examples], device=device),
        "disposition": torch.tensor([DISPOSITIONS.index(item.disposition) for item in examples], device=device),
    }
    slot_rows: list[tuple[int, int, int]] = []
    for row, example in enumerate(examples):
        for span_index, span in enumerate(example.spans):
            if span_index >= 8:
                continue
            slot_rows.append((row, span_index, SLOT_TYPES.index(span.slot_type)))
    values["slot_rows"] = torch.tensor(slot_rows, dtype=torch.long, device=device) if slot_rows else torch.empty((0, 3), dtype=torch.long, device=device)
    return values


def loss_for(model: ConversationCompiler, output: dict[str, Tensor], examples: list[ConversationCase]) -> Tensor:
    target = _targets(examples, output["sentence"].device)
    loss = output["sentence"].sum() * 0.0
    for name in ("act", "action", "reference", "polarity", "modality", "scope", "disposition"):
        loss = loss + torch.nn.functional.cross_entropy(output[f"{name}_logits"], target[name])
    rows = target["slot_rows"]
    if len(rows):
        slot_logits = output["slot_logits"][rows[:, 0], rows[:, 1]]
        loss = loss + 1.25 * torch.nn.functional.cross_entropy(slot_logits, rows[:, 2])
    return loss


def _set_upper_trainable(model: ConversationCompiler, enabled: bool) -> None:
    layers = list(model.encoder.model.encoder.layer)
    for index, layer in enumerate(layers):
        for parameter in layer.parameters():
            parameter.requires_grad = enabled and index >= len(layers) - 2


def train_kernel(workspace: Path, examples: tuple[ConversationCase, ...], *, steps: int = 1000, warmup: int = 200) -> TrainingSummary:
    torch.set_num_threads(4)
    random.seed(1840)
    torch.manual_seed(1840)
    model = ConversationCompiler()
    _set_upper_trainable(model, False)
    heads = [parameter for name, parameter in model.named_parameters() if not name.startswith("encoder.")]
    optimizer = torch.optim.AdamW(heads, lr=3e-4, weight_decay=0.01)
    total = 0.0
    for step in range(steps):
        if step == warmup:
            _set_upper_trainable(model, True)
            optimizer = torch.optim.AdamW([parameter for parameter in model.parameters() if parameter.requires_grad], lr=1e-5, weight_decay=0.01)
        batch = [examples[(step * 32 + offset) % len(examples)] for offset in range(32)]
        tokens, masks = make_batch(model, batch)
        output = model(tokens, masks)
        loss = loss_for(model, output, batch)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_([parameter for parameter in model.parameters() if parameter.requires_grad], 1.0)
        optimizer.step()
        total += float(loss.detach())
    workspace.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "steps": steps}, workspace / "kernel-checkpoint.pt")
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    return TrainingSummary(steps, total / max(steps, 1), trainable, model.encoder.forward_calls)


def save_summary(workspace: Path, summary: TrainingSummary) -> None:
    (workspace / "kernel-training-summary.json").write_text(json.dumps(asdict(summary), sort_keys=True) + "\n", encoding="utf-8")

