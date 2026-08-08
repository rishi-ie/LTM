"""Small fixed curriculum for the atomic-coordinate kernel."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from torch import nn

from .basis import build_basis
from .dataset import AtomicExample
from .encoder import OnePassMiniLM
from .measure import AtomicMeasurementHead


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    steps: int
    loss: float
    trainable_parameters: int
    encoder_forward_calls: int


def _span_masks(tokenizer, texts: list[str], examples: list[AtomicExample], max_spans: int = 3) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
    tokens = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=128,
        return_offsets_mapping=True,
        return_tensors="pt",
    )
    offsets = tokens.pop("offset_mapping")
    sequence_length = tokens["input_ids"].shape[1]
    masks = torch.zeros((len(examples), max_spans, sequence_length), dtype=torch.float32)
    for batch_index, example in enumerate(examples):
        for span_index, span in enumerate(example.spans[:max_spans]):
            for token_index, (start, end) in enumerate(offsets[batch_index].tolist()):
                if end > start and end > span.start and start < span.end:
                    masks[batch_index, span_index, token_index] = 1.0
    return tokens, masks


def _targets(examples: list[AtomicExample], feature_index: dict[str, int], max_spans: int = 3) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    width = len(feature_index)
    unary = torch.zeros((len(examples), max_spans, width), dtype=torch.float32)
    pair = torch.zeros((len(examples), max_spans, max_spans, width), dtype=torch.float32)
    context = torch.zeros((len(examples), width), dtype=torch.float32)
    for batch_index, example in enumerate(examples):
        if example.disposition != "accept":
            continue
        indexes = [feature_index[item] for item in example.feature_ids if item in feature_index]
        unary[batch_index, : len(example.spans[:max_spans]), indexes] = 1.0
        context[batch_index, indexes] = 1.0
        if len(example.spans) >= 2:
            pair[batch_index, 0, 1, indexes] = 1.0
            pair[batch_index, 1, 0, indexes] = 1.0
    return unary, pair, context


def train_kernel(workspace: Path, examples: tuple[AtomicExample, ...], *, steps: int = 1_200) -> TrainingSummary:
    torch.set_num_threads(4)
    random.seed(1821)
    torch.manual_seed(1821)
    basis = build_basis()
    feature_index = {f"feature:{item.description}": index for index, item in enumerate(basis.features)}
    encoder = OnePassMiniLM()
    head = AtomicMeasurementHead(len(basis.features))
    parameters = [parameter for parameter in encoder.parameters() if parameter.requires_grad] + list(head.parameters())
    optimizer = torch.optim.AdamW(parameters, lr=3e-4, weight_decay=.01)
    bce = nn.BCEWithLogitsLoss()
    batch_size = 8
    total_loss = 0.0
    iterator = 0
    for step in range(steps):
        batch = [examples[(step * batch_size + index) % len(examples)] for index in range(batch_size)]
        tokens, span_masks = _span_masks(encoder.tokenizer, [item.text for item in batch], batch)
        input_ids = tokens["input_ids"]
        attention_mask = tokens["attention_mask"]
        extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
        hidden = encoder(input_ids, attention_mask, **extra)
        output = head(hidden, span_masks)
        targets = _targets(batch, feature_index)
        loss = (
            bce(output["unary"], targets[0])
            + bce(output["pair"], targets[1])
            + bce(output["context"], targets[2])
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0)
        optimizer.step()
        total_loss += float(loss.detach())
        iterator += 1
    workspace.mkdir(parents=True, exist_ok=True)
    torch.save({"encoder": encoder.state_dict(), "head": head.state_dict(), "steps": steps}, workspace / "kernel-checkpoint.pt")
    trainable = sum(parameter.numel() for parameter in parameters)
    return TrainingSummary(steps, total_loss / max(1, iterator), trainable, encoder.forward_calls)


def save_summary(workspace: Path, summary: TrainingSummary) -> None:
    (workspace / "kernel-training-summary.json").write_text(
        json.dumps(asdict(summary), sort_keys=True) + "\n", encoding="utf-8"
    )
