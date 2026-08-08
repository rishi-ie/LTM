"""Restart-safe Phase-A training for the typed representation kernel."""

from __future__ import annotations

import os
import random
import resource
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import Tensor

from topology_g1.registry import REGISTRY

from .dataset import generate_kernel_examples
from .encoder import OnePassMiniLM
from .model import TypedAtomKernel
from .registry import DISPOSITIONS, MODALITIES, NODE_KINDS, POLARITIES, RELATIONS, ROLES, SCOPES
from .schemas import KernelExample, KernelRuntimeCase


@dataclass(frozen=True, slots=True)
class KernelTrainingSummary:
    examples: int
    epochs_completed: int
    optimizer_steps: int
    final_loss: float
    checkpoint_path: str


def _span_mask(offsets: Tensor, example: KernelExample, maximum_atoms: int) -> Tensor:
    mask = torch.zeros((maximum_atoms, offsets.shape[0]), dtype=torch.bool)
    for index, atom in enumerate(example.atoms[:maximum_atoms]):
        overlap = (offsets[:, 1] > atom.source_start) & (offsets[:, 0] < atom.source_end)
        mask[index] = overlap
    return mask


def make_batch(
    model: TypedAtomKernel,
    examples: list[KernelExample] | list[KernelRuntimeCase],
    maximum_atoms: int = 8,
) -> tuple[dict[str, Tensor], Tensor, Tensor, Tensor]:
    tokens = model.encoder.tokenize([example.source.text for example in examples])
    offsets = tokens["offset_mapping"]
    masks = torch.stack(
        [
            _span_mask(offsets[index], example, maximum_atoms)
            for index, example in enumerate(examples)
        ]
    )
    kinds = torch.full((len(examples), maximum_atoms), len(NODE_KINDS), dtype=torch.long)
    present = torch.zeros((len(examples), maximum_atoms), dtype=torch.bool)
    for row, example in enumerate(examples):
        for column, atom in enumerate(example.atoms[:maximum_atoms]):
            kinds[row, column] = NODE_KINDS.index(atom.node_kind)
            present[row, column] = True
    return tokens, masks, kinds, present


def _role_loss(
    model: TypedAtomKernel,
    output: dict[str, Tensor],
    examples: list[KernelExample],
    atom_mask: Tensor,
) -> Tensor:
    losses: list[Tensor] = []
    for row, example in enumerate(examples):
        if example.relation_type is None:
            continue
        spec = REGISTRY[example.relation_type]
        relation_id = torch.tensor(
            [RELATIONS.index(example.relation_type)], device=output["sentence"].device
        )
        role_ids = torch.tensor(
            [[ROLES.index(role.name) for role in spec.roles]], device=output["sentence"].device
        )
        scores = model.role_logits(
            output["sentence"][row : row + 1],
            output["content"][row : row + 1],
            relation_id,
            role_ids,
            atom_mask[row : row + 1],
            output["operator_state"][row : row + 1],
        )
        target = torch.zeros_like(scores)
        atom_positions = {atom.atom_id: index for index, atom in enumerate(example.atoms)}
        for role_index, (_role, atom_ids) in enumerate(example.role_bindings):
            for atom_id in atom_ids:
                target[0, role_index, atom_positions[atom_id]] = 1.0
        valid = atom_mask[row : row + 1].unsqueeze(1).expand_as(scores)
        losses.append(
            torch.nn.functional.binary_cross_entropy_with_logits(scores[valid], target[valid])
        )
    return torch.stack(losses).mean() if losses else output["sentence"].sum() * 0


def kernel_loss(
    model: TypedAtomKernel, examples: list[KernelExample]
) -> tuple[Tensor, dict[str, float]]:
    tokens, masks, kinds, atom_mask = make_batch(model, examples)
    output = model(tokens, masks, kinds)
    device = output["sentence"].device
    accepted_rows = [
        index for index, example in enumerate(examples) if example.relation_type is not None
    ]
    components: dict[str, Tensor] = {}
    if accepted_rows:
        relations = torch.tensor(
            [
                RELATIONS.index(examples[index].relation_type or RELATIONS[0])
                for index in accepted_rows
            ],
            device=device,
        )
        components["operator"] = torch.nn.functional.cross_entropy(
            output["operator_logits"][accepted_rows], relations
        )
    else:
        components["operator"] = output["sentence"].sum() * 0
    components["roles"] = _role_loss(model, output, examples, atom_mask.to(device))
    components["polarity"] = torch.nn.functional.cross_entropy(
        output["polarity_logits"],
        torch.tensor([POLARITIES.index(example.polarity) for example in examples], device=device),
    )
    components["modality"] = torch.nn.functional.cross_entropy(
        output["modality_logits"],
        torch.tensor([MODALITIES.index(example.modality) for example in examples], device=device),
    )
    components["scope"] = torch.nn.functional.cross_entropy(
        output["scope_logits"],
        torch.tensor([SCOPES.index(example.scope_id) for example in examples], device=device),
    )
    components["disposition"] = torch.nn.functional.cross_entropy(
        output["disposition_logits"],
        torch.tensor(
            [DISPOSITIONS.index(example.disposition) for example in examples], device=device
        ),
    )
    total = (
        components["operator"]
        + 1.5 * components["roles"]
        + 0.75 * components["polarity"]
        + 0.75 * components["modality"]
        + 0.75 * components["scope"]
        + 0.75 * components["disposition"]
    )
    return total, {key: float(value.detach()) for key, value in components.items()}


def _atomic_checkpoint(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".pt", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(value, temporary)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _set_encoder_trainable(model: TypedAtomKernel, trainable: bool) -> None:
    for parameter in model.encoder.model.parameters():
        parameter.requires_grad = trainable


def _peak_rss_mb() -> float:
    """Return the process high-water mark on both Linux and macOS."""
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # macOS reports bytes; Linux reports KiB.
    return value / (1024 * 1024) if os.sys.platform == "darwin" else value / 1024


def train_kernel(
    workspace: Path, *, limit: int | None = None
) -> tuple[TypedAtomKernel, KernelTrainingSummary]:
    """Run six fixed epochs; resume exactly from an atomic checkpoint."""
    torch.manual_seed(1748)
    random.seed(1748)
    torch.set_num_threads(4)
    examples = list(generate_kernel_examples("train"))
    if limit is not None:
        examples = examples[:limit]
    model = TypedAtomKernel(OnePassMiniLM(trainable=False))
    checkpoint = workspace / "kernel-checkpoint.pt"
    start_epoch = 0
    start_batch = 0
    steps = 0
    final_loss = 0.0
    optimizer: torch.optim.Optimizer | None = None
    saved_trainable: bool | None = None
    if checkpoint.exists():
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        model.load_state_dict(state["model"])
        start_epoch, start_batch, steps, final_loss = (
            state["epoch"],
            state["batch"],
            state["steps"],
            state["loss"],
        )
        saved_trainable = state.get("encoder_trainable")
        random.setstate(state["python_rng"])
        torch.set_rng_state(state["torch_rng"])
    for epoch in range(start_epoch, 6):
        trainable = epoch >= 2
        _set_encoder_trainable(model, trainable)
        parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
        optimizer = torch.optim.AdamW(parameters, lr=2e-5 if trainable else 5e-4, weight_decay=0.01)
        if checkpoint.exists() and epoch == start_epoch and saved_trainable == trainable:
            state = torch.load(checkpoint, map_location="cpu", weights_only=False)
            if state.get("optimizer") is not None:
                optimizer.load_state_dict(state["optimizer"])
        order = list(range(len(examples)))
        random.Random(1748 + epoch).shuffle(order)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        for batch_number, begin in enumerate(range(0, len(order), 16)):
            if epoch == start_epoch and batch_number < start_batch:
                continue
            batch = [examples[index] for index in order[begin : begin + 16]]
            loss, _components = kernel_loss(model, batch)
            # Four 16-case micro-batches are accumulated exactly as frozen in
            # the experiment configuration.  A final incomplete group is
            # deliberately stepped rather than discarded.
            (loss / 4).backward()
            final_loss = float(loss.detach())
            should_step = (batch_number + 1) % 4 == 0 or begin + 16 >= len(order)
            if not should_step:
                continue
            torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            steps += 1
            if _peak_rss_mb() >= 18 * 1024:
                _atomic_checkpoint(
                    checkpoint,
                    {
                        "model": model.state_dict(),
                        "optimizer": optimizer.state_dict(),
                        "epoch": epoch,
                        "batch": batch_number + 1,
                        "steps": steps,
                        "loss": final_loss,
                        "encoder_trainable": trainable,
                        "python_rng": random.getstate(),
                        "torch_rng": torch.get_rng_state(),
                    },
                )
                raise RuntimeError(
                    "G2.5 development RSS ceiling (18 GB) reached; checkpoint retained"
                )
            if steps % 100 == 0:
                _atomic_checkpoint(
                    checkpoint,
                    {
                        "model": model.state_dict(),
                        "optimizer": optimizer.state_dict(),
                        "epoch": epoch,
                        "batch": batch_number + 1,
                        "steps": steps,
                        "loss": final_loss,
                        "encoder_trainable": trainable,
                        "python_rng": random.getstate(),
                        "torch_rng": torch.get_rng_state(),
                    },
                )
        start_batch = 0
        _atomic_checkpoint(
            checkpoint,
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "epoch": epoch + 1,
                "batch": 0,
                "steps": steps,
                "loss": final_loss,
                "encoder_trainable": trainable,
                "python_rng": random.getstate(),
                "torch_rng": torch.get_rng_state(),
            },
        )
    model.eval()
    return model, KernelTrainingSummary(len(examples), 6, steps, final_loss, str(checkpoint))
