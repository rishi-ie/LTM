"""Restart-safe staged training for the G2.6 joint scorer."""

from __future__ import annotations

import os
import random
import resource
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch

from .decoder import GoldenAtomInput, enumerate_candidates
from .encoder import OnePassMiniLM
from .inference import _features
from .model import JointCandidateScorer, directional_margin_loss
from .schemas import SemanticExample


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    stage: str
    examples: int
    steps: int
    final_loss: float
    checkpoint_path: str


def _rss_mb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024) if os.sys.platform == "darwin" else value / 1024


def _save(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".pt", dir=path.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        torch.save(state, temporary)
        temporary.replace(path)
    finally:
        if temporary.exists(): temporary.unlink()


def _gold_index(candidates: tuple[object, ...], example: SemanticExample) -> int:
    target = example.candidate
    for index, candidate in enumerate(candidates):
        if candidate == target:
            return index
    raise ValueError(f"gold candidate absent from legal lattice: {example.source_id}")


def _loss_for_batch(model: JointCandidateScorer, encoder: OnePassMiniLM, batch: list[SemanticExample]) -> torch.Tensor:
    hubs, atoms = _features(encoder, [item.text for item in batch], [item.atoms for item in batch])
    losses: list[torch.Tensor] = []
    for row, example in enumerate(batch):
        candidates = enumerate_candidates(tuple(GoldenAtomInput(atom.atom_id, atom.kind) for atom in example.atoms))
        scores = model.score_candidates(hubs[row], atoms[row, : len(example.atoms)], tuple(atom.atom_id for atom in example.atoms), candidates)
        target = _gold_index(candidates, example)
        losses.append(torch.nn.functional.cross_entropy(scores.unsqueeze(0), torch.tensor([target])))
        if example.candidate.relation_type is not None:
            reversed_indices = tuple(index for index, candidate in enumerate(candidates) if candidate.relation_type == example.candidate.relation_type and candidate.role_bindings != example.candidate.role_bindings)
            losses.append(directional_margin_loss(scores, target, reversed_indices))
    return torch.stack(losses).mean()


def train_kernel(workspace: Path, examples: tuple[SemanticExample, ...], *, max_steps: int = 1200, stage: str = "kernel") -> tuple[JointCandidateScorer, OnePassMiniLM, TrainingSummary]:
    torch.manual_seed(1760)
    random.seed(1760)
    torch.set_num_threads(4)
    encoder = OnePassMiniLM(trainable=False)
    model = JointCandidateScorer()
    from .cards import RELATION_DESCRIPTIONS
    description_tokens = encoder.tokenize([RELATION_DESCRIPTIONS[name] for name in RELATION_DESCRIPTIONS])
    description_tokens.pop("offset_mapping")
    description_states = encoder(description_tokens["input_ids"], description_tokens["attention_mask"])
    description_mask = description_tokens["attention_mask"].float().unsqueeze(-1)
    description_hubs = (description_states * description_mask).sum(1) / description_mask.sum(1).clamp_min(1)
    model.relation_text_features.copy_(description_hubs.detach())
    checkpoint = workspace / "kernel-checkpoint.pt"
    start_step = 0
    if checkpoint.exists():
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model"])
        encoder.load_state_dict(state["encoder"])
        start_step = int(state.get("step", 0))
        random.setstate(state["python_rng"])
        torch.set_rng_state(state["torch_rng"])
    params = list(model.parameters()) + list(encoder.parameters())
    optimizer = torch.optim.AdamW(params, lr=5e-4, weight_decay=0.01)
    if checkpoint.exists() and state.get("optimizer"):
        optimizer.load_state_dict(state["optimizer"])
    model.train(); encoder.train()
    final_loss = 0.0
    order = list(range(len(examples)))
    for step in range(start_step, max_steps):
        if step == 200:
            for parameter in encoder.model.parameters(): parameter.requires_grad = True
            optimizer = torch.optim.AdamW(list(model.parameters()) + list(encoder.parameters()), lr=2e-5, weight_decay=0.01)
        random.Random(1760 + step).shuffle(order)
        batch = [examples[index] for index in order[(step * 16) % len(order) : (step * 16) % len(order) + 16]]
        if len(batch) < 4:
            batch = list(examples[:16])
        optimizer.zero_grad(set_to_none=True)
        loss = _loss_for_batch(model, encoder, batch)
        (loss / 4).backward()
        torch.nn.utils.clip_grad_norm_(list(model.parameters()) + list(encoder.parameters()), 1.0)
        optimizer.step()
        final_loss = float(loss.detach())
        if (step + 1) % 50 == 0 or step + 1 == max_steps:
            _save(checkpoint, {"model": model.state_dict(), "encoder": encoder.state_dict(), "optimizer": optimizer.state_dict(), "step": step + 1, "python_rng": random.getstate(), "torch_rng": torch.get_rng_state(), "loss": final_loss})
        if _rss_mb() >= 18 * 1024:
            raise RuntimeError("G2.6 development RSS ceiling reached")
    model.eval(); encoder.eval()
    return model, encoder, TrainingSummary(stage, len(examples), max_steps, final_loss, str(checkpoint))
