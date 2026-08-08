"""One-pass public compiler runtime. Gold is never imported here."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch

from .field import build_program
from .projector import project
from .schemas import CompilationArtifact, PublicAtom, SourceExample

KIND_NAMES = ("claim", "value", "event")
SCOPE_NAMES = ("global", "fictional")
MODALITY_NAMES = ("asserted", "conditional")
DISPOSITIONS = ("accept", "clarification_required", "quarantine")


def _span_masks(offsets: torch.Tensor, atoms: tuple[PublicAtom, ...]) -> torch.Tensor:
    return torch.stack(tuple((offsets[:, 1] > atom.start) & (offsets[:, 0] < atom.end) for atom in atoms)).unsqueeze(0)


def _content(tokens: torch.Tensor, masks: torch.Tensor) -> tuple[tuple[float, ...], ...]:
    rows = []
    for index in range(masks.shape[1]):
        vector = (tokens[0] * masks[0, index].float().unsqueeze(-1)).sum(0) / masks[0, index].float().sum().clamp_min(1)
        rows.append(tuple(float(value) for value in torch.nn.functional.normalize(vector, dim=0)))
    return tuple(rows)


def _raw_atoms(source: SourceExample, output: dict[str, torch.Tensor], offsets: torch.Tensor) -> tuple[PublicAtom, ...]:
    starts = torch.topk(output["start"][0], min(12, output["start"].shape[1])).indices.tolist()
    ends = torch.topk(output["end"][0], min(12, output["end"].shape[1])).indices.tolist()
    choices = []
    for left in starts:
        for right in ends:
            if left > right or right - left > 32:
                continue
            start, end = int(offsets[left, 0]), int(offsets[right, 1])
            if end <= start:
                continue
            score = float(output["start"][0, left] + output["end"][0, right])
            choices.append((score, start, end, left, right))
    choices.sort(key=lambda item: (-item[0], item[1], item[2]))
    selected = []
    for _score, start, end, left, right in choices:
        if any(not (end <= prior_start or start >= prior_end) for prior_start, prior_end, _kind in selected):
            continue
        kind_logits = output["kind"][0, left : right + 1].mean(0)
        kind = KIND_NAMES[int(torch.argmax(kind_logits))]
        selected.append((start, end, kind))
        if len(selected) == 2:
            break
    if len(selected) != 2:
        return ()
    return tuple(PublicAtom(f"a{index + 1}", kind, source.text[start:end], start, end, source.source_hash) for index, (start, end, kind) in enumerate(sorted(selected)))


@torch.no_grad()
def compile_source(model, encoder, source: SourceExample, sidecars: Path, *, supplied: bool, distance: float, margin: float, port: float) -> CompilationArtifact:
    tokens = encoder.tokenize([source.text]); offsets = tokens.pop("offset_mapping")[0]
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    if supplied:
        atoms = source.atoms
        if len(atoms) != 2:
            return CompilationArtifact(source.source_id, project(np.zeros(1704), ("", ""), ("claim", "claim"), 0.0), "global", "asserted", (), None, (), None, ("SUPPLIED_ATOMS_REQUIRED",))
        masks = _span_masks(offsets, atoms)
        output = model(states, tokens["attention_mask"], masks)
    else:
        dummy = torch.zeros((1, 2, states.shape[1]), dtype=torch.bool)
        dummy[:, :, 0] = True
        first = model(states, tokens["attention_mask"], dummy)
        atoms = _raw_atoms(source, first, offsets)
        if len(atoms) != 2:
            decision = project(np.zeros(1704), ("", ""), ("claim", "claim"), 0.0, distance_limit=distance, margin_limit=margin)
            return CompilationArtifact(source.source_id, decision, "global", "asserted", (), None, (), None, ("MISSING_CONTENT_SPANS",))
        masks = _span_masks(offsets, atoms)
        output = model(states, tokens["attention_mask"], masks)
    signature = output["signature"][0].cpu().numpy()
    pair_scores = torch.sigmoid(output["ports"][0]); order = ("a1", "a2") if float(pair_scores[0]) >= float(pair_scores[1]) else ("a2", "a1")
    probability = float(pair_scores.max())
    decision = project(signature, order, tuple(atom.kind for atom in atoms), probability, distance_limit=distance, margin_limit=margin)
    scope = SCOPE_NAMES[int(torch.argmax(output["scope"][0]))]
    modality = MODALITY_NAMES[int(torch.argmax(output["modality"][0]))]
    disposition = DISPOSITIONS[int(torch.argmax(output["disposition"][0]))]
    if disposition != "accept" or probability < port:
        decision = decision.__class__(None, (), "clarification_required" if disposition == "clarification_required" else "quarantine", decision.distance, decision.margin, probability, ("DISPOSITION_OR_PORT",))
    if decision.disposition != "accept" or decision.cell_id is None:
        return CompilationArtifact(source.source_id, decision, scope, modality, atoms, None, (), None, decision.failure_codes)
    try:
        content = _content(states, masks)
        program, operations, digest = build_program(source.source_id, source.source_hash, atoms, decision.cell_id, decision.atom_ids, scope, modality, content, tuple(float(value) for value in signature), sidecars)
    except (KeyError, ValueError) as error:
        failure = type(error).__name__
        decision = decision.__class__(None, (), "quarantine", decision.distance, decision.margin, probability, (failure,))
        return CompilationArtifact(source.source_id, decision, scope, modality, atoms, None, (), None, (failure,))
    return CompilationArtifact(source.source_id, decision, scope, modality, atoms, program, operations, digest, ())


def target_masks(offsets: torch.Tensor, gold) -> torch.Tensor:
    atoms = tuple(PublicAtom(f"a{index + 1}", kind, text, start, end, "") for index, (kind, text, start, end) in enumerate(gold.atom_records))
    return _span_masks(offsets, atoms)


def source_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
