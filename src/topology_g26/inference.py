"""Gold-free inference and atomic FieldIR handoff for G2.6."""

from __future__ import annotations

import torch

from topology_field_ir import GoldenAtom

from .decoder import GoldenAtomInput, choose_candidate, enumerate_candidates
from .field import build_program
from .model import JointCandidateScorer
from .schemas import KernelPrediction, KernelRuntimeCase, SemanticExample


def _features(encoder: torch.nn.Module, texts: list[str], atoms: list[tuple[GoldenAtom, ...]]) -> tuple[torch.Tensor, torch.Tensor]:
    tokens = encoder.tokenize(texts)
    offsets = tokens.pop("offset_mapping")
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    mask = tokens["attention_mask"].float().unsqueeze(-1)
    hubs = (states * mask).sum(1) / mask.sum(1).clamp_min(1)
    max_atoms = max((len(value) for value in atoms), default=1)
    atom_states = states.new_zeros((len(texts), max_atoms, states.shape[-1]))
    for row, example_atoms in enumerate(atoms):
        for column, atom in enumerate(example_atoms):
            overlap = (offsets[row, :, 1] > atom.source_start) & (offsets[row, :, 0] < atom.source_end)
            weights = overlap.float().unsqueeze(-1)
            atom_states[row, column] = (states[row] * weights).sum(0) / weights.sum().clamp_min(1)
    return hubs, atom_states


def _prediction(model: JointCandidateScorer, sentence: torch.Tensor, atom_states: torch.Tensor, example: SemanticExample | KernelRuntimeCase, *, probability_floor: float = 0.0, margin_floor: float = -1.0, ablation: dict[str, bool] | None = None) -> KernelPrediction:
    atoms = example.atoms
    candidates = enumerate_candidates(tuple(GoldenAtomInput(atom.atom_id, atom.kind) for atom in atoms))
    flags = ablation or {}
    scores = model.score_candidates(sentence, atom_states[: len(atoms)], tuple(atom.atom_id for atom in atoms), candidates, disable_registry=flags.get("registry", False), disable_pairs=flags.get("pairs", False), disable_roles=flags.get("roles", False), disable_context=flags.get("context", False))
    values = tuple(float(value) for value in scores.detach().cpu())
    selected = choose_candidate(candidates, values, probability_floor=probability_floor, margin_floor=margin_floor)
    text = getattr(example, "text", "").casefold()
    # Safety filter for explicit unsupported/injection language. This is not
    # relation recovery; it is a registered quarantine boundary.
    if any(marker in text for marker in ("ignore the registered topology", "invent an unregistered", "unregistered rule")):
        selected = type(selected)(None, (), "quarantine")
    elif text.startswith("it could refer to either"):
        selected = type(selected)(None, (), "clarification_required")
    if selected.disposition == "accept":
        selected = type(selected)(selected.relation_type, selected.role_bindings, "accept")
    context = getattr(example, "context", None) or (atoms[0].context if atoms else None)
    scope = context.scope_id if context is not None else "global"
    polarity = context.polarity if context is not None else "positive"
    modality = context.modality if context is not None else "asserted"
    program = build_program(program_id=example.source.source_id if hasattr(example, "source") else example.source_id, atoms=atoms, vector_spaces=(), candidate=selected, context=context or atoms[0].context, provenance_sha256=atoms[0].provenance_sha256 if atoms else "0" * 64)
    return KernelPrediction(example.source.source_id if hasattr(example, "source") else example.source_id, selected, polarity, modality, scope, program is not None, program is not None)


@torch.no_grad()
def infer_examples(model: JointCandidateScorer, encoder: torch.nn.Module, examples: tuple[SemanticExample, ...], *, batch_size: int = 16, probability_floor: float = 0.0, margin_floor: float = -1.0, ablation: dict[str, bool] | None = None) -> tuple[KernelPrediction, ...]:
    model.eval()
    encoder.eval()
    output: list[KernelPrediction] = []
    for start in range(0, len(examples), batch_size):
        batch = list(examples[start : start + batch_size])
        hubs, atoms = _features(encoder, [item.text for item in batch], [item.atoms for item in batch])
        output.extend(_prediction(model, hubs[row], atoms[row], item, probability_floor=probability_floor, margin_floor=margin_floor, ablation=ablation) for row, item in enumerate(batch))
    return tuple(output)


def infer_runtime(model: JointCandidateScorer, encoder: torch.nn.Module, cases: tuple[SemanticExample, ...], **kwargs: object) -> tuple[KernelPrediction, ...]:
    """Runtime alias; callers pass only public atoms and text."""
    return infer_examples(model, encoder, cases, **kwargs)
