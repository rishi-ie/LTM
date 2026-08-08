"""Restartable factorized kernel training."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from torch import Tensor

from .dataset import AtomicCase
from .model import FactorizedCompiler
from .registry import DISPOSITIONS, MODALITIES, POLARITIES, RELATIONS, ROLE_INDEX, SCOPES


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    steps: int
    loss: float
    trainable_parameters: int
    encoder_forward_calls: int


def make_batch(model: FactorizedCompiler, examples: list[AtomicCase], maximum_spans: int = 8) -> tuple[dict[str, Tensor], Tensor]:
    tokens = model.encoder.tokenize([example.text for example in examples])
    offsets = tokens["offset_mapping"]
    masks = torch.zeros((len(examples), maximum_spans, offsets.shape[1]), dtype=torch.bool)
    for row, example in enumerate(examples):
        for column, span in enumerate(example.spans[:maximum_spans]):
            start = offsets[row, :, 0]
            end = offsets[row, :, 1]
            masks[row, column] = (end > span.start) & (start < span.end) & (end > start)
    return tokens, masks


def _targets(examples: list[AtomicCase], device: torch.device) -> tuple[Tensor, Tensor, Tensor, Tensor, Tensor, Tensor]:
    batch = len(examples)
    operators = torch.zeros((batch, len(RELATIONS)), device=device)
    polarity = torch.tensor([POLARITIES.index(example.polarity) for example in examples], device=device)
    modality = torch.tensor([MODALITIES.index(example.modality) for example in examples], device=device)
    scope = torch.tensor([SCOPES.index(example.scope_id) for example in examples], device=device)
    disposition = torch.tensor([DISPOSITIONS.index(example.disposition) for example in examples], device=device)
    role_rows: list[tuple[int, int, int, int]] = []
    pair_rows: list[tuple[int, int, int, int, int]] = []
    for row, example in enumerate(examples):
        for relation in example.relations:
            relation_index = RELATIONS.index(relation)
            operators[row, relation_index] = 1.0
            bindings = [item for item in example.role_bindings if item[0] == relation]
            positions = {span.span_id: index for index, span in enumerate(example.spans)}
            for _relation, role, span_ids in bindings:
                for span_id in span_ids:
                    role_rows.append((row, relation_index, ROLE_INDEX[role], positions[span_id]))
            if len(bindings) >= 2:
                first = positions[bindings[0][2][0]]
                second = positions[bindings[1][2][0]]
                pair_rows.append((row, relation_index, first, second, 1))
                pair_rows.append((row, relation_index, second, first, 0))
    role_targets = torch.tensor(role_rows, dtype=torch.long, device=device) if role_rows else torch.empty((0, 4), dtype=torch.long, device=device)
    pair_targets = torch.tensor(pair_rows, dtype=torch.long, device=device) if pair_rows else torch.empty((0, 5), dtype=torch.long, device=device)
    return operators, role_targets, pair_targets, polarity, modality, torch.stack((scope, disposition))


def _loss(model: FactorizedCompiler, output: dict[str, Tensor], examples: list[AtomicCase]) -> Tensor:
    operators, role_rows, pair_rows, polarity, modality, context = _targets(examples, output["sentence"].device)
    single_rows = [row for row, example in enumerate(examples) if len(example.relations) == 1]
    multi_rows = [row for row, example in enumerate(examples) if len(example.relations) != 1]
    loss = output["sentence"].sum() * 0.0
    if single_rows:
        labels = torch.tensor([RELATIONS.index(examples[row].relations[0]) for row in single_rows], device=loss.device)
        loss = loss + torch.nn.functional.cross_entropy(output["operator_logits"][single_rows], labels)
    if multi_rows:
        loss = loss + torch.nn.functional.binary_cross_entropy_with_logits(output["operator_logits"][multi_rows], operators[multi_rows])
    if len(role_rows):
        role_logits = output["role_scores"][role_rows[:, 0], role_rows[:, 1], role_rows[:, 2]]
        loss = loss + 1.5 * torch.nn.functional.cross_entropy(role_logits, role_rows[:, 3])
    if len(pair_rows):
        pair_logits = output["pair_scores"][pair_rows[:, 0], pair_rows[:, 1], pair_rows[:, 2], pair_rows[:, 3]]
        positive = pair_logits[pair_rows[:, 4] == 1]
        negative = pair_logits[pair_rows[:, 4] == 0]
        count = min(len(positive), len(negative))
        if count:
            loss = loss + 1.5 * torch.nn.functional.margin_ranking_loss(
                positive[:count], negative[:count], torch.ones(count, device=loss.device), margin=0.35
            )
    loss = loss + 0.75 * torch.nn.functional.cross_entropy(output["polarity_logits"], polarity)
    loss = loss + 0.75 * torch.nn.functional.cross_entropy(output["modality_logits"], modality)
    loss = loss + 0.75 * torch.nn.functional.cross_entropy(output["scope_logits"], context[0])
    loss = loss + 0.75 * torch.nn.functional.cross_entropy(output["disposition_logits"], context[1])
    return loss


def _set_encoder_trainable(model: FactorizedCompiler, value: bool) -> None:
    for layer in model.encoder.model.encoder.layer:
        for parameter in layer.parameters():
            parameter.requires_grad = value and layer in list(model.encoder.model.encoder.layer)[-2:]


def train_kernel(workspace: Path, examples: tuple[AtomicCase, ...], *, steps: int = 1500, warmup: int = 250) -> TrainingSummary:
    torch.set_num_threads(4)
    random.seed(1830)
    torch.manual_seed(1830)
    model = FactorizedCompiler()
    _set_encoder_trainable(model, False)
    head_parameters = [parameter for name, parameter in model.named_parameters() if not name.startswith("encoder.")]
    optimizer = torch.optim.AdamW(head_parameters, lr=3e-4, weight_decay=0.01)
    total = 0.0
    for step in range(steps):
        if step == warmup:
            _set_encoder_trainable(model, True)
            optimizer = torch.optim.AdamW(
                [parameter for parameter in model.parameters() if parameter.requires_grad],
                lr=1e-5,
                weight_decay=0.01,
            )
        batch = [examples[(step * 16 + index) % len(examples)] for index in range(16)]
        tokens, masks = make_batch(model, batch)
        output = model(tokens, masks)
        loss = _loss(model, output, batch)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_([parameter for parameter in model.parameters() if parameter.requires_grad], 1.0)
        optimizer.step()
        total += float(loss.detach())
    workspace.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "steps": steps}, workspace / "kernel-checkpoint.pt")
    trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    return TrainingSummary(steps, total / max(1, steps), trainable, model.encoder.forward_calls)


def save_summary(workspace: Path, summary: TrainingSummary) -> None:
    (workspace / "kernel-training-summary.json").write_text(json.dumps(asdict(summary), sort_keys=True) + "\n", encoding="utf-8")
