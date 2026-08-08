"""Restart-safe G2.9 kernel training with dynamic same-encoder queries."""

from __future__ import annotations

import os
import random
import resource
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch

from .decoder import GraphCandidate, enumerate_graphs, gold_graph, minimum_matching_cost
from .runtime import _batch_features, encode_query_bank


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    stage: str
    steps: int
    examples: int
    final_loss: float
    checkpoint_path: str
    trainable_parameters: int


def _rss_gb() -> float:
    amount = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return amount / (1024 * 1024 * 1024) if os.sys.platform == "darwin" else amount / (1024 * 1024)


def _save(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        torch.save(payload, temporary_path)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _acquire_single_writer_lock(workspace: Path) -> Path:
    """Refuse two writers before any checkpoint can be touched."""
    lock = workspace / "kernel-training.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError("another G2.9 kernel writer owns this workspace") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{os.getpid()}\n")
    return lock


def _target_index(candidates: tuple[GraphCandidate, ...], target: GraphCandidate) -> int:
    for index, candidate in enumerate(candidates):
        if candidate == target:
            return index
    raise ValueError("gold graph is absent from the legal G1 lattice")


def _loss(kernel, source, gold, token_states, attention_mask, span_masks, contents, offsets, anchors) -> torch.Tensor:
    atoms = tuple(source.atoms)
    state = kernel.contextualize(token_states, attention_mask, anchors)
    spans = kernel.span_states(token_states, span_masks)
    candidates = enumerate_graphs(tuple((atom.atom_id, atom.kind) for atom in atoms))
    target = gold_graph(gold.relation_types, gold.role_bindings, gold.disposition)
    # Global beam truncation must never remove a legal gold graph during
    # supervised training; inference receives no such injection.
    if target not in candidates:
        candidates = candidates[:-1] + (target,)
    scores, signals = kernel.score_graphs(state, spans, span_masks.any(-1), tuple(atom.atom_id for atom in atoms), candidates)
    graph_index = _target_index(candidates, target)
    graph_loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0), torch.tensor([graph_index]))
    activation_target = torch.zeros((1, len(kernel.relation_index)), dtype=torch.float32)
    for relation in gold.relation_types:
        activation_target[0, kernel.relation_index[relation]] = 1.0
    activation_loss = torch.nn.functional.binary_cross_entropy_with_logits(signals["operator_logits"], activation_target)
    disposition = {"accept": 0, "clarification_required": 1, "quarantine": 2}[gold.disposition]
    disposition_loss = torch.nn.functional.cross_entropy(signals["disposition_logits"], torch.tensor([disposition]))
    # Exact bounded matching of up to three operator instances.  The matching
    # selects slots but never supplies a gold slot at inference.
    groups = []
    for relation in gold.relation_types[:3]:
        group = kernel.relation_index[relation]
        groups.append(tuple(float(-value.detach()) for value in signals["slot_logits"][0, group]))
    matching = minimum_matching_cost(tuple(groups)) if groups else ()
    slot_loss = scores.sum() * 0
    for relation, slot in zip(gold.relation_types, matching, strict=True):
        slot_loss = slot_loss + torch.nn.functional.cross_entropy(
            signals["slot_logits"][0, kernel.relation_index[relation]].unsqueeze(0),
            torch.tensor([slot]),
        )
    reverse = [index for index, candidate in enumerate(candidates) if candidate.disposition == "accept" and candidate.relation_types == target.relation_types and candidate.role_bindings != target.role_bindings]
    margin_loss = torch.relu(.35 - scores[graph_index] + scores[torch.tensor(reverse)]).mean() if reverse else scores.sum() * 0
    return 2.0 * graph_loss + activation_loss + .75 * disposition_loss + .5 * slot_loss + 1.5 * margin_loss


def train_kernel(workspace: Path, bank, sources, gold, *, stage: str = "kernel", max_steps: int = 1_200) -> tuple[object, object, TrainingSummary]:
    """Train Stage A; atom boundary input is public only in this stage."""
    lock = _acquire_single_writer_lock(workspace)
    try:
        return _train_kernel_locked(workspace, bank, sources, gold, stage=stage, max_steps=max_steps)
    finally:
        lock.unlink(missing_ok=True)


def _train_kernel_locked(workspace: Path, bank, sources, gold, *, stage: str, max_steps: int) -> tuple[object, object, TrainingSummary]:
    torch.set_num_threads(4)
    torch.manual_seed(1790)
    random.seed(1790)
    from .encoder import AdaptedMiniLM
    from .model import GoldenQueryKernel

    encoder = AdaptedMiniLM()
    kernel = GoldenQueryKernel(bank)
    checkpoint = workspace / f"{stage}-checkpoint.pt"
    start = 0
    optimizer_state = None
    if checkpoint.exists():
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        encoder.load_state_dict(state["encoder"]); kernel.load_state_dict(state["kernel"])
        start = int(state["step"]); optimizer_state = state.get("optimizer")
        random.setstate(state["python_rng"]); torch.set_rng_state(state["torch_rng"])
    encoder_parameters = [item for item in encoder.parameters() if item.requires_grad]
    kernel_parameters = list(kernel.parameters())
    optimizer = torch.optim.AdamW(({"params": encoder_parameters, "lr": 1e-5}, {"params": kernel_parameters, "lr": 3e-4}), weight_decay=.01)
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)
    by_id = {item.source_id: item for item in gold}
    order = list(range(len(sources)))
    final_loss = 0.0
    encoder.train(); kernel.train()
    for step in range(start, max_steps):
        random.Random(1790 + step).shuffle(order)
        indices = [order[(step * 32 + position) % len(order)] for position in range(32)]
        batch = [sources[index] for index in indices]
        optimizer.zero_grad(set_to_none=True)
        # Query anchors are encoded after every parameter update in the same
        # coordinate system as the sentence; this is G2.9's central change.
        anchors = encode_query_bank(encoder, kernel)
        features = _batch_features(encoder, tuple((source, tuple(source.atoms)) for source in batch))
        losses = [_loss(kernel, source, by_id[source.source_id], *feature, anchors) for source, feature in zip(batch, features, strict=True)]
        loss = torch.stack(losses).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(encoder_parameters + kernel_parameters, 1.0)
        optimizer.step()
        final_loss = float(loss.detach())
        if (step + 1) % 50 == 0 or step + 1 == max_steps:
            _save(checkpoint, {"encoder": encoder.state_dict(), "kernel": kernel.state_dict(), "optimizer": optimizer.state_dict(), "step": step + 1, "python_rng": random.getstate(), "torch_rng": torch.get_rng_state(), "final_loss": final_loss})
        if _rss_gb() >= 18:
            raise RuntimeError("G2.9 development RSS limit reached; checkpoint retained")
    count = sum(item.numel() for item in encoder_parameters + kernel_parameters)
    if count > 10_000_000:  # lower layers are frozen; kernel stays compact.
        raise RuntimeError("G2.9 trainable parameter budget exceeded")
    return kernel.eval(), encoder.eval(), TrainingSummary(stage, max_steps, len(sources), final_loss, str(checkpoint), count)
