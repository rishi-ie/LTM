"""Restart-safe joint graph training for G2.8."""

from __future__ import annotations

import os
import random
import resource
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch

from .atom_bank import AtomBankManifest
from .decoder import GraphCandidate, enumerate_graphs, gold_graph
from .encoder import AdaptedMiniLM
from .model import GoldenGraphKernel
from .runtime import _feature_states_batch


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    stage: str
    steps: int
    examples: int
    final_loss: float
    checkpoint_path: str
    trainable_parameters: int


def _rss_gb() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value / (1024 * 1024 * 1024) if os.sys.platform == "darwin" else value / (1024 * 1024)


def _save(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        torch.save(payload, temporary_path)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _anchor_encoder(encoder: AdaptedMiniLM):
    def encode(texts: list[str]) -> torch.Tensor:
        tokens = encoder.tokenize(texts)
        tokens.pop("offset_mapping")
        with torch.no_grad():
            states = encoder(tokens["input_ids"], tokens["attention_mask"])
            mask = tokens["attention_mask"].float().unsqueeze(-1)
            return torch.nn.functional.normalize((states * mask).sum(1) / mask.sum(1).clamp_min(1), dim=-1)
    return encode


def _candidate_index(candidates: tuple[GraphCandidate, ...], gold: GraphCandidate) -> int:
    for index, candidate in enumerate(candidates):
        if candidate == gold:
            return index
    raise ValueError("gold candidate absent from G1 lattice")


def _loss_for_features(kernel, source, gold, sentence, atom_states) -> torch.Tensor:
    atoms = tuple(source.atoms)
    candidates = list(enumerate_graphs(tuple((atom.atom_id, atom.kind) for atom in atoms)))
    target_graph = gold_graph(gold.relation_types, gold.role_bindings, gold.disposition)
    if target_graph not in candidates:
        candidates[-1] = target_graph
    candidate_tuple = tuple(candidates)
    scores, signals = kernel.score_graphs(sentence, atom_states, tuple(atom.atom_id for atom in atoms), candidate_tuple)
    target = _candidate_index(candidate_tuple, target_graph)
    graph_loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0), torch.tensor([target]))
    relation_target = torch.zeros(len(kernel.relation_index), dtype=torch.float32)
    for relation in gold.relation_types:
        relation_target[kernel.relation_index[relation]] = 1.0
    operator_loss = torch.nn.functional.binary_cross_entropy_with_logits(signals["operator_logits"], relation_target)
    disposition_target = torch.tensor([{"accept": 0, "clarification_required": 1, "quarantine": 2}[gold.disposition]])
    disposition_loss = torch.nn.functional.cross_entropy(signals["disposition_logits"].unsqueeze(0), disposition_target)
    reversed_indices = [
        index for index, candidate in enumerate(candidate_tuple)
        if candidate.disposition == "accept" and candidate.relation_types == target_graph.relation_types and candidate.role_bindings != target_graph.role_bindings
    ]
    if reversed_indices:
        reverse = scores[torch.tensor(reversed_indices)]
        margin_loss = torch.relu(.35 - scores[target] + reverse).mean()
    else:
        margin_loss = scores.sum() * 0
    return 2.0 * graph_loss + .75 * operator_loss + .75 * disposition_loss + 1.5 * margin_loss


def train_kernel(
    workspace: Path,
    bank: AtomBankManifest,
    sources,
    gold,
    *,
    stage: str = "kernel",
    # The complete-candidate objective is deliberately evaluated for every
    # sentence in a batch.  On the four-thread CPU envelope, 700 steps is the
    # largest fixed budget that keeps the kernel decision below 90 active
    # minutes; the old 1,800-step aspirational value was not executable inside
    # the published cap.
    max_steps: int = 700,
) -> tuple[GoldenGraphKernel, AdaptedMiniLM, TrainingSummary]:
    torch.set_num_threads(4)
    torch.manual_seed(1780)
    random.seed(1780)
    encoder = AdaptedMiniLM()
    kernel = GoldenGraphKernel(bank)
    kernel.initialize_anchors(_anchor_encoder(encoder))
    checkpoint = workspace / f"{stage}-checkpoint.pt"
    start_step = 0
    optimizer_state = None
    if checkpoint.exists():
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        kernel.load_state_dict(state["kernel"])
        encoder.load_state_dict(state["encoder"])
        start_step = int(state["step"])
        optimizer_state = state.get("optimizer")
        random.setstate(state["python_rng"])
        torch.set_rng_state(state["torch_rng"])
    encoder_params = [parameter for parameter in encoder.parameters() if parameter.requires_grad]
    kernel_params = list(kernel.parameters())
    optimizer = torch.optim.AdamW(
        [{"params": encoder_params, "lr": 1e-5}, {"params": kernel_params, "lr": 3e-4}],
        weight_decay=.01,
    )
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)
    by_id = {item.source_id: item for item in gold}
    order = list(range(len(sources)))
    final_loss = 0.0
    encoder.train(); kernel.train()
    for step in range(start_step, max_steps):
        random.Random(1780 + step).shuffle(order)
        batch_indices = [order[(step * 16 + index) % len(order)] for index in range(16)]
        optimizer.zero_grad(set_to_none=True)
        batch_sources = [sources[index] for index in batch_indices]
        features = _feature_states_batch(encoder, tuple((source, tuple(source.atoms)) for source in batch_sources))
        losses = [
            _loss_for_features(kernel, source, by_id[source.source_id], sentence, atom_states)
            for source, (sentence, atom_states, _contents) in zip(batch_sources, features, strict=True)
        ]
        loss = torch.stack(losses).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(encoder_params + kernel_params, 1.0)
        optimizer.step()
        final_loss = float(loss.detach())
        if (step + 1) % 50 == 0 or step + 1 == max_steps:
            _save(checkpoint, {"kernel": kernel.state_dict(), "encoder": encoder.state_dict(), "optimizer": optimizer.state_dict(), "step": step + 1, "python_rng": random.getstate(), "torch_rng": torch.get_rng_state(), "final_loss": final_loss})
        if _rss_gb() >= 18:
            raise RuntimeError("G2.8 development RSS limit reached")
    trainable = sum(parameter.numel() for parameter in encoder_params + kernel_params)
    return kernel.eval(), encoder.eval(), TrainingSummary(stage, max_steps, len(sources), final_loss, str(checkpoint), trainable)
