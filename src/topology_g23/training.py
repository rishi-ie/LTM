"""Deterministic four-phase, resumable G2.3 training."""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .candidates import candidate_tensors
from .compiler import SentenceTopologyCompiler
from .dataset import LinkExample, SentenceExample
from .linker import NONE_INDEX, candidate_text
from .registry import RELATION_LABELS
from .runstate import atomic_json

PHASES: tuple[tuple[str, int], ...] = (
    ("span_grounding", 6),
    ("gold_grounded_topology", 6),
    ("self_conditioned", 10),
    ("joint_linking", 8),
)
CHECKPOINT_STEPS = 25


@dataclass(frozen=True, slots=True)
class TrainingInfo:
    recurrent: bool
    epochs: int
    best_loss: float
    device: str
    completed_phases: tuple[str, ...]
    optimizer_steps: int


def set_seed(seed: int = 1744) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def _token_range(offsets: torch.Tensor, start: int, end: int) -> tuple[int, int] | None:
    rows = offsets[0].tolist()
    valid = [index for index, (left, right) in enumerate(rows) if right > left]
    begin = next((index for index in valid if rows[index][0] <= start < rows[index][1]), None)
    finish = next((index for index in reversed(valid) if rows[index][0] < end <= rows[index][1]), None)
    return (begin, finish + 1) if begin is not None and finish is not None and finish >= begin else None


def _kind_index(kind: str) -> int:
    from .registry import NODE_KINDS

    return NODE_KINDS.index(kind) + 1


def _span_loss(logits: torch.Tensor, offsets: torch.Tensor, example: SentenceExample) -> tuple[torch.Tensor, list]:
    positives: list[tuple[int, int, int]] = []
    spans = []
    for span in example.gold.spans:
        token_range = _token_range(offsets, span.start, span.end)
        if token_range is None:
            continue
        positives.append((token_range[0], token_range[1] - 1, _kind_index(span.node_kind)))
        spans.append(span)
    if not positives:
        return logits.sum() * 0, spans
    values = torch.stack([logits[0, left, right] for left, right, _kind in positives])
    targets = torch.tensor([kind for _left, _right, kind in positives], dtype=torch.long)
    # Focal scaling makes the rare typed span signal survive the none majority.
    ce = nn.functional.cross_entropy(values, targets, reduction="none")
    probability = torch.softmax(values, -1).gather(1, targets.unsqueeze(1)).squeeze(1)
    return ((1 - probability).pow(2) * ce).mean(), spans


def _relation_loss(
    model: SentenceTopologyCompiler,
    projected: torch.Tensor,
    mask: torch.Tensor,
    offsets: torch.Tensor,
    example: SentenceExample,
) -> torch.Tensor:
    if not example.gold.relations:
        return projected.sum() * 0
    spans = example.gold.spans
    packed, legal = candidate_tensors(spans)
    if not legal:
        return projected.sum() * 0
    relation_ids, role_ids, bound_ids, _ = packed
    span_states = []
    for span in spans:
        token_range = _token_range(offsets, span.start, span.end)
        if token_range is None:
            return projected.sum() * 0
        span_states.append(projected[0, token_range[0] : token_range[1]].mean(0))
    hub = (projected * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)
    scores, _ = model.hierarchy.reconcile(torch.stack(span_states).unsqueeze(0), hub, relation_ids, role_ids, bound_ids)
    targets = {
        (relation.relation_type, relation.role_candidate_ids)
        for relation in example.gold.relations
    }
    labels = torch.tensor(
        [1.0 if (relation, bindings) in targets else 0.0 for relation, bindings, _score in legal],
        dtype=scores.dtype,
    )
    return nn.functional.binary_cross_entropy_with_logits(scores, labels)


def _disposition_loss(model: SentenceTopologyCompiler, projected: torch.Tensor, mask: torch.Tensor, example: SentenceExample) -> torch.Tensor:
    hub = (projected * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp_min(1)
    logits = model.hierarchy.disposition_head(hub)
    target = {"accept": 0, "clarification_required": 1, "quarantine": 2}[example.gold.disposition]
    return nn.functional.cross_entropy(logits, torch.tensor([target]))


def _batch_sentence_loss(model: SentenceTopologyCompiler, examples: list[SentenceExample], phase: str) -> torch.Tensor:
    encoded = model.encoder.tokenize([example.source.text for example in examples])
    offsets = encoded.pop("offset_mapping")
    extra = {key: value for key, value in encoded.items() if key not in {"input_ids", "attention_mask"}}
    raw = model.encoder(encoded["input_ids"], encoded["attention_mask"], **extra)
    projected = model.projection(raw)
    logits, _left, _right = model.parser.logits(raw, encoded["attention_mask"])
    losses = []
    for index, example in enumerate(examples):
        span, _gold_spans = _span_loss(logits[index : index + 1], offsets[index : index + 1], example)
        if phase == "span_grounding":
            losses.append(2.0 * span)
            continue
        relation = _relation_loss(
            model,
            projected[index : index + 1],
            encoded["attention_mask"][index : index + 1],
            offsets[index : index + 1],
            example,
        )
        disposition = _disposition_loss(
            model,
            projected[index : index + 1],
            encoded["attention_mask"][index : index + 1],
            example,
        )
        # Phase C has the same supervised target but is executed through the
        # model lattice at inference; missed lattice spans remain penalized by
        # the span loss rather than fabricating a graph target.
        losses.append(2.0 * span + relation + 0.5 * disposition)
    return torch.stack(losses).mean()


def _link_loss(model: SentenceTopologyCompiler, examples: list[LinkExample]) -> torch.Tensor:
    left: list[str] = []
    right: list[str] = []
    targets: list[int] = []
    for example in examples:
        expected = {(link.target_object_id, link.relation_type) for link in example.gold.links}
        span = example.fragment_spans[0]
        for candidate in example.public_candidates:
            left.append(example.source.text)
            right.append(candidate_text(example.source, span, candidate))
            relation = next((value for object_id, value in expected if object_id == candidate.object_id), None)
            targets.append(RELATION_LABELS.index(relation) if relation is not None else NONE_INDEX)
    if not left:
        return next(model.parameters()).sum() * 0
    return nn.functional.cross_entropy(model.link_logits(left, right), torch.tensor(targets))


def _checkpoint_path(workspace: Path, variant: str) -> Path:
    return workspace / "training" / f"{variant}-progress.pt"


def _save_progress(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def _load_progress(path: Path) -> dict[str, object] | None:
    return torch.load(path, weights_only=False, map_location="cpu") if path.exists() else None


def _epoch_order(length: int, epoch: int) -> list[int]:
    order = list(range(length))
    random.Random(1744 + epoch).shuffle(order)
    return order


def train_variant(
    train: tuple[SentenceExample, ...],
    development: tuple[SentenceExample, ...],
    *,
    recurrent: bool,
    workspace: Path | None = None,
    variant: str | None = None,
    link_train: tuple[LinkExample, ...] = (),
    max_epochs: int = 30,
    patience: int = 3,
) -> tuple[SentenceTopologyCompiler, TrainingInfo]:
    """Run or resume the fixed 6/6/10/8 curriculum.

    The only model-selection decision is the best validation checkpoint.  An
    interrupted run resumes from its saved epoch/batch cursor with identical
    deterministic ordering; a completed checkpoint is simply reloaded.
    """
    set_seed()
    name = variant or ("hierarchical" if recurrent else "nonrecurrent")
    progress_path = _checkpoint_path(workspace, name) if workspace is not None else None
    payload = _load_progress(progress_path) if progress_path is not None else None
    model = SentenceTopologyCompiler(recurrent=recurrent)
    encoder_parameters = [parameter for parameter in model.encoder.parameters() if parameter.requires_grad]
    head_parameters = [parameter for parameter_name, parameter in model.named_parameters() if not parameter_name.startswith("encoder.")]
    optimizer = torch.optim.AdamW(
        ({"params": encoder_parameters, "lr": 2e-5}, {"params": head_parameters, "lr": 1e-3}),
        weight_decay=0.01,
    )
    phase_index = 0
    local_epoch = 0
    epoch_counter = 0
    start_batch = 0
    phase_best_loss = float("inf")
    phase_best_state = None
    phase_stale = 0
    optimizer_steps = 0
    completed_phases: list[str] = []
    if payload is not None:
        if bool(payload["recurrent"]) != recurrent:
            raise RuntimeError(f"resume checkpoint mismatch: {name}")
        model.load_state_dict(payload["model"])
        optimizer.load_state_dict(payload["optimizer"])
        phase_index = int(payload["phase_index"])
        local_epoch = int(payload["local_epoch"])
        epoch_counter = int(payload["epoch_counter"])
        start_batch = int(payload.get("batch", 0))
        phase_best_loss = float(payload["phase_best_loss"])
        phase_best_state = payload["phase_best_state"]
        phase_stale = int(payload["phase_stale"])
        optimizer_steps = int(payload["optimizer_steps"])
        completed_phases = list(payload["completed_phases"])
        torch.set_rng_state(payload["torch_rng"])
        random.setstate(payload["python_rng"])
        np.random.set_state(payload["numpy_rng"])
        if bool(payload.get("completed", False)):
            model.eval()
            return model, TrainingInfo(recurrent, epoch_counter, phase_best_loss, "cpu", tuple(completed_phases), optimizer_steps)
    model.train()
    configured_epochs = sum(value for _phase, value in PHASES)
    epoch_limit = min(max_epochs, configured_epochs)
    while phase_index < len(PHASES) and epoch_counter < epoch_limit:
        phase, configured_phase_epochs = PHASES[phase_index]
        phase_epochs = min(configured_phase_epochs, epoch_limit - epoch_counter + local_epoch)
        while local_epoch < phase_epochs and epoch_counter < epoch_limit:
            order = _epoch_order(len(train), epoch_counter)
            first_batch = start_batch
            for start in range(first_batch, len(order), 16):
                examples = [train[index] for index in order[start : start + 16]]
                optimizer.zero_grad(set_to_none=True)
                loss = _batch_sentence_loss(model, examples, phase)
                if phase == "joint_linking" and link_train and (start // 16) % 4 == 3:
                    link_order = _epoch_order(len(link_train), epoch_counter + 1000)
                    link_examples = [link_train[index] for index in link_order[(start % len(link_train)) : (start % len(link_train)) + 8]]
                    if link_examples:
                        loss = loss + _link_loss(model, link_examples)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer_steps += 1
                if progress_path is not None and optimizer_steps % CHECKPOINT_STEPS == 0:
                    _save_progress(progress_path, {
                        "recurrent": recurrent, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                        "phase_index": phase_index, "local_epoch": local_epoch, "epoch_counter": epoch_counter,
                        "batch": start + 16, "phase_best_loss": phase_best_loss,
                        "phase_best_state": phase_best_state, "phase_stale": phase_stale,
                        "optimizer_steps": optimizer_steps, "completed_phases": completed_phases,
                        "torch_rng": torch.get_rng_state(), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                        "completed": False,
                    })
            model.eval()
            validation = []
            with torch.no_grad():
                for start in range(0, len(development), 16):
                    validation.append(float(_batch_sentence_loss(model, list(development[start : start + 16]), phase)))
            value = float(np.mean(validation))
            print(f"G2.3 {name} {phase} epoch={local_epoch + 1}/{phase_epochs} validation_loss={value:.5f}", flush=True)
            if value < phase_best_loss - 1e-6:
                phase_best_loss = value
                phase_best_state = copy.deepcopy(model.state_dict())
                phase_stale = 0
            else:
                phase_stale += 1
            local_epoch += 1
            epoch_counter += 1
            start_batch = 0
            if progress_path is not None:
                _save_progress(progress_path, {
                    "recurrent": recurrent, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "phase_index": phase_index, "local_epoch": local_epoch, "epoch_counter": epoch_counter,
                    "batch": 0, "phase_best_loss": phase_best_loss,
                    "phase_best_state": phase_best_state, "phase_stale": phase_stale,
                    "optimizer_steps": optimizer_steps, "completed_phases": completed_phases,
                    "torch_rng": torch.get_rng_state(), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                    "completed": False,
                })
            model.train()
            if phase_stale >= patience:
                break
        if phase_best_state is None:
            phase_best_state = copy.deepcopy(model.state_dict())
        model.load_state_dict(phase_best_state)
        if phase not in completed_phases:
            completed_phases.append(phase)
        phase_index += 1
        local_epoch = 0
        start_batch = 0
        phase_stale = 0
        # Losses are phase-specific and cannot be compared across curriculum
        # stages.  The next phase starts from this phase's best model but owns
        # a fresh validation selector.
        if phase_index < len(PHASES) and epoch_counter < epoch_limit:
            phase_best_loss = float("inf")
            phase_best_state = None
    if phase_best_state is None:
        phase_best_state = copy.deepcopy(model.state_dict())
    model.load_state_dict(phase_best_state)
    model.eval()
    if progress_path is not None:
        _save_progress(progress_path, {
            "recurrent": recurrent, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
            "phase_index": phase_index, "local_epoch": local_epoch, "epoch_counter": epoch_counter,
            "batch": 0, "phase_best_loss": phase_best_loss,
            "phase_best_state": phase_best_state, "phase_stale": phase_stale,
            "optimizer_steps": optimizer_steps, "completed_phases": completed_phases,
            "torch_rng": torch.get_rng_state(), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
            "completed": True,
        })
        atomic_json(workspace / "training" / f"{name}-info.json", asdict(TrainingInfo(recurrent, epoch_counter, phase_best_loss, "cpu", tuple(completed_phases), optimizer_steps)))
    return model, TrainingInfo(recurrent, epoch_counter, phase_best_loss, "cpu", tuple(completed_phases), optimizer_steps)
