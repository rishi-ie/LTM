"""Small deterministic topology-kernel training with frozen encoder."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import torch

from .atom_bank import RELATIONS
from .encoder import FrozenMiniLM
from .kernel import CoordinateKernel
from .schemas import GoldRecord, RuntimeExample


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    steps: int
    examples: int
    final_loss: float
    trainable_parameters: int
    checkpoint_path: str


def train_kernel(
    workspace: Path,
    examples: tuple[RuntimeExample, ...],
    gold: tuple[GoldRecord, ...],
    max_steps: int = 120,
) -> tuple[CoordinateKernel, FrozenMiniLM, TrainingSummary]:
    torch.manual_seed(1770)
    random.seed(1770)
    torch.set_num_threads(4)
    encoder = FrozenMiniLM()
    kernel = CoordinateKernel(encoder)
    kernel.initialize_anchors()
    trainable = [parameter for parameter in kernel.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=3e-4, weight_decay=.01)
    labels = {item.source_id: item for item in gold}
    disposition_index = {"accept": 0, "clarification_required": 1, "quarantine": 2}
    # Training labels come from the training-only semantic programs.  No
    # surface-cue detector, evaluator gold, or held-out template identifier is
    # available to the runtime kernel.
    losses = []
    usable = [item for item in examples if item.text]
    for step in range(max_steps):
        batch = [usable[(step * 16 + offset) % len(usable)] for offset in range(16)]
        optimizer.zero_grad(set_to_none=True)
        batch_loss = []
        for item in batch:
            sentence, _atoms, _meta = kernel.encode(item.text, item.atoms)
            relation_logits = kernel.relation_logits(sentence)
            record = labels[item.source_id]
            relation_target = torch.zeros(len(RELATIONS), dtype=torch.float32)
            for relation in record.relation_types:
                relation_target[RELATIONS.index(relation)] = 1.0
            relation_loss = torch.nn.functional.binary_cross_entropy_with_logits(relation_logits, relation_target)
            decision_target = torch.tensor([disposition_index[record.disposition]])
            decision_loss = torch.nn.functional.cross_entropy(kernel.disposition_logits(sentence).unsqueeze(0), decision_target)
            batch_loss.append(relation_loss + decision_loss)
        loss = torch.stack(batch_loss).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(trainable, 1.0)
        optimizer.step()
        losses.append(float(loss.detach()))
    checkpoint = workspace / "kernel-checkpoint.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"kernel": kernel.state_dict(), "steps": max_steps, "encoder_hashes": "frozen"}, checkpoint)
    return kernel.eval(), encoder.eval(), TrainingSummary(max_steps, len(examples), losses[-1] if losses else 0.0, sum(parameter.numel() for parameter in trainable), str(checkpoint))
