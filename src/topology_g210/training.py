"""Restart-safe G2.10 training; gold drives loss only, never runtime projection."""

from __future__ import annotations

import os
import random
import resource
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from .runtime import DISPOSITIONS, MODALITY_NAMES, SCOPE_NAMES, _span_masks
from .topology import CELL_BY_ID, CELLS, signature

_SIGNATURES = torch.from_numpy(np.stack(tuple(signature(cell) for cell in CELLS)).astype(np.float32))
_VARIANCE = _SIGNATURES.var(dim=0, unbiased=False)
# Ponytail: static discriminative-coordinate weights replace a second large model.
_WEIGHTS = torch.where(_VARIANCE > 1e-10, _VARIANCE / _VARIANCE[_VARIANCE > 1e-10].mean(), torch.zeros_like(_VARIANCE))


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    stage: str
    steps: int
    examples: int
    final_loss: float
    checkpoint: str
    trainable_parameters: int


def _save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        torch.save(value, temporary); temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _rss_gb() -> float:
    amount = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return amount / (1024 * 1024 * 1024) if os.sys.platform == "darwin" else amount / (1024 * 1024)


def _targets(gold, device) -> tuple[torch.Tensor, int, int, int, int, int]:
    if gold.cell_id is None:
        return torch.zeros(1704, device=device), -1, DISPOSITIONS.index(gold.disposition), 0, 0, -1
    port = 0 if gold.atom_ids == ("a1", "a2") else 1
    return (
        torch.tensor(signature(CELL_BY_ID[gold.cell_id]), dtype=torch.float32, device=device),
        port,
        DISPOSITIONS.index(gold.disposition),
        SCOPE_NAMES.index(gold.scope_id),
        MODALITY_NAMES.index(gold.modality),
        1,
    )


def _behavior_loss(prediction: torch.Tensor, target: torch.Tensor, cell_id: str) -> torch.Tensor:
    weights = _WEIGHTS.to(prediction.device)
    coordinate = (torch.nn.functional.smooth_l1_loss(prediction, target, reduction="none") * weights).sum() / weights.sum().clamp_min(1)
    signatures = _SIGNATURES.to(prediction.device)
    distance = (((prediction.unsqueeze(0) - signatures) ** 2 * weights).sum(-1) / weights.sum().clamp_min(1)).sqrt()
    cycle = torch.nn.functional.cross_entropy((-20.0 * distance).unsqueeze(0), torch.tensor([next(index for index, cell in enumerate(CELLS) if cell.cell_id == cell_id)], device=prediction.device))
    return coordinate + cycle


def train(workspace: Path, sources, gold, *, stage: str, steps: int, extraction: bool) -> tuple[object, object, TrainingSummary]:
    from .encoder import AdaptedMiniLM
    from .model import BehavioralCompiler

    torch.set_num_threads(4); torch.manual_seed(1800); random.seed(1800)
    encoder = AdaptedMiniLM(); model = BehavioralCompiler()
    checkpoint = workspace / f"{stage}-checkpoint.pt"; start = 0; optimizer_state = None
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
        encoder.load_state_dict(saved["encoder"]); model.load_state_dict(saved["model"])
        start = int(saved["step"]); optimizer_state = saved.get("optimizer")
        random.setstate(saved["python_rng"]); torch.set_rng_state(saved["torch_rng"])
    parameters = [value for value in encoder.parameters() if value.requires_grad] + list(model.parameters())
    optimizer = torch.optim.AdamW(({"params": [value for value in encoder.parameters() if value.requires_grad], "lr": 1e-5}, {"params": model.parameters(), "lr": 3e-4}), weight_decay=.01)
    if optimizer_state is not None: optimizer.load_state_dict(optimizer_state)
    by_id = {item.source_id: item for item in gold}; order = list(range(len(sources))); final_loss = 0.0
    encoder.train(); model.train()
    for step in range(start, steps):
        random.Random(1800 + step).shuffle(order)
        batch = [sources[order[(step * 32 + number) % len(order)]] for number in range(32)]
        tokens = encoder.tokenize([item.text for item in batch]); offsets = tokens.pop("offset_mapping")
        extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
        states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
        masks = torch.cat(tuple(_span_masks(offsets[index], source.atoms) for index, source in enumerate(batch)), dim=0)
        output = model(states, tokens["attention_mask"], masks)
        losses = []
        for index, source in enumerate(batch):
            target, port, disposition, scope, modality, active = _targets(by_id[source.source_id], states.device)
            loss = .75 * torch.nn.functional.cross_entropy(output["disposition"][index:index + 1], torch.tensor([disposition]))
            loss = loss + .5 * torch.nn.functional.cross_entropy(output["scope"][index:index + 1], torch.tensor([scope]))
            loss = loss + .5 * torch.nn.functional.cross_entropy(output["modality"][index:index + 1], torch.tensor([modality]))
            if active == 1:
                loss = loss + 2.0 * _behavior_loss(output["signature"][index], target, by_id[source.source_id].cell_id)
                loss = loss + torch.nn.functional.cross_entropy(output["ports"][index:index + 1], torch.tensor([port]))
                loss = loss + torch.relu(.35 - output["ports"][index, port] + output["ports"][index, 1 - port])
                if extraction:
                    for atom_index in range(2):
                        mask = masks[index, atom_index]
                        start = int(torch.where(mask)[0][0]); end = int(torch.where(mask)[0][-1])
                        loss = loss + torch.nn.functional.cross_entropy(output["start"][index:index + 1], torch.tensor([start]))
                        loss = loss + torch.nn.functional.cross_entropy(output["end"][index:index + 1], torch.tensor([end]))
                        kind = {"claim": 0, "value": 1, "event": 2}[source.atoms[atom_index].kind]
                        loss = loss + torch.nn.functional.cross_entropy(output["kind"][index, start:end + 1].mean(0).unsqueeze(0), torch.tensor([kind]))
            losses.append(loss)
        optimizer.zero_grad(set_to_none=True); value = torch.stack(losses).mean(); value.backward()
        torch.nn.utils.clip_grad_norm_(parameters, 1.0); optimizer.step(); final_loss = float(value.detach())
        if (step + 1) % 50 == 0 or step + 1 == steps:
            _save(checkpoint, {"encoder": encoder.state_dict(), "model": model.state_dict(), "optimizer": optimizer.state_dict(), "step": step + 1, "python_rng": random.getstate(), "torch_rng": torch.get_rng_state(), "final_loss": final_loss})
        if _rss_gb() >= 18:
            raise RuntimeError("G2.10 development RSS limit reached; checkpoint retained")
    count = sum(value.numel() for value in parameters)
    if count >= 10_000_000: raise RuntimeError("G2.10 trainable parameter budget exceeded")
    return model.eval(), encoder.eval(), TrainingSummary(stage, steps, len(sources), final_loss, str(checkpoint), count)
