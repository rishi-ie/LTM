"""Public-only runtime: one sentence pass plus one frozen query-bank pass."""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import torch

from topology_field_ir import GoldenAtom

from .atom_bank import RELATIONS
from .decoder import GraphCandidate, enumerate_graphs
from .field import build_program
from .schemas import (
    CompiledSentenceArtifact,
    ContentCandidate,
    OperatorQueryMatch,
    RelationSetPrediction,
    RoleQueryMatch,
)

_ATOM = re.compile(r"\b(?P<kind>[a-z_]+)_(?P<id>[TDKL]\d{5}_\d+)\b")
_KNOWN = {"event", "scope", "preference", "instruction", "question", "assistant_response", "entity", "goal", "value", "state", "rule", "conversation_turn", "claim", "fact", "observation", "hypothesis"}


def public_atoms(source) -> tuple[GoldenAtom, ...]:
    if source.atoms:
        return tuple(source.atoms)
    digest = hashlib.sha256(source.text.encode()).hexdigest()
    atoms = []
    for index, match in enumerate(_ATOM.finditer(source.text)):
        kind = match.group("kind")
        if kind in _KNOWN:
            text = match.group(0)
            atoms.append(GoldenAtom(f"a{index + 1}", kind, text, text, source.source_id, match.start(), match.end(), source.context, digest))
    return tuple(atoms)


def _batch_features(encoder, records):
    """One encoder call for a batch; each source contributes exactly one row."""
    tokens = encoder.tokenize([source.text for source, _atoms in records])
    offsets = tokens.pop("offset_mapping")
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    output = []
    for index, (source, atoms) in enumerate(records):
        row = states[index]
        content = []
        masks = []
        for atom in atoms:
            overlap = (offsets[index, :, 1] > atom.source_start) & (offsets[index, :, 0] < atom.source_end)
            masks.append(overlap)
            pooled = (row * overlap.float().unsqueeze(-1)).sum(0) / overlap.float().sum().clamp_min(1)
            content.append(ContentCandidate(atom.atom_id, atom.occurrence_text, atom.source_start, atom.source_end, ((atom.kind, 1.0),), tuple(float(value.detach()) for value in torch.nn.functional.normalize(pooled, dim=0))))
        if masks:
            span_masks = torch.stack(masks).unsqueeze(0)
        else:
            span_masks = torch.zeros((1, 0, row.shape[0]), dtype=torch.bool)
        output.append((row.unsqueeze(0), tokens["attention_mask"][index:index + 1], span_masks, tuple(content), offsets[index]))
    return tuple(output)


def encode_query_bank(encoder, kernel) -> torch.Tensor:
    """Dynamic anchors are encoded with the same current encoder checkpoint."""
    tokens = encoder.tokenize(list(kernel.anchor_texts()))
    tokens.pop("offset_mapping")
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    mask = tokens["attention_mask"].float().unsqueeze(-1)
    return torch.nn.functional.normalize((states * mask).sum(1) / mask.sum(1).clamp_min(1), dim=-1)


def _probabilities(scores: torch.Tensor) -> tuple[float, float, int]:
    probabilities = torch.softmax(scores.detach(), dim=0)
    order = sorted(range(len(probabilities)), key=lambda index: (-float(probabilities[index]), index))
    best, second = order[0], order[1] if len(order) > 1 else order[0]
    return float(probabilities[best]), float(probabilities[best] - probabilities[second]), best


def _attended_offsets(weights: torch.Tensor, offsets: torch.Tensor, count: int = 3) -> tuple[tuple[int, int], ...]:
    values = weights.detach().mean(0) if weights.ndim == 2 else weights.detach()
    order = sorted(range(len(values)), key=lambda index: (-float(values[index]), index))[:count]
    return tuple((int(offsets[index, 0]), int(offsets[index, 1])) for index in order if int(offsets[index, 1]) > int(offsets[index, 0]))


def compile_from_features(kernel, source, atoms, token_states, attention_mask, span_masks, contents, offsets, anchor_states, bank, sidecar_dir: Path, *, confidence: float = .50, margin: float = .02, grad: bool = False) -> tuple[CompiledSentenceArtifact, torch.Tensor | None, dict[str, object] | None, tuple[GraphCandidate, ...]]:
    started = time.perf_counter()
    if not atoms:
        artifact = CompiledSentenceArtifact(source.source_id, bank.revision, (), (), None, None, (), None, "quarantine", ("NO_CONTENT_CANDIDATE",), (time.perf_counter() - started) * 1000)
        return artifact, None, None, ()
    state = kernel.contextualize(token_states, attention_mask, anchor_states)
    spans = kernel.span_states(token_states, span_masks)
    span_mask = span_masks.any(-1)
    candidates = enumerate_graphs(tuple((atom.atom_id, atom.kind) for atom in atoms))
    scores, signals = kernel.score_graphs(state, spans, span_mask, tuple(atom.atom_id for atom in atoms), candidates)
    probability, gap, best_index = _probabilities(scores)
    selected = candidates[best_index]
    if selected.disposition != "accept" or probability < confidence or gap < margin:
        selected = GraphCandidate((), "clarification_required")
    matches = []
    attention = state["attention"]
    for relation_index, relation in enumerate(RELATIONS):
        slot_scores = state["slot_logits"][0, relation_index]
        slot = int(torch.argmax(slot_scores))
        selected_delta = state["tokens"][0] - state["queries"][0, relation_index, slot]
        matches.append(OperatorQueryMatch(relation, slot, float(torch.sigmoid(state["operator_logits"][0, relation_index])), float(torch.sigmoid(slot_scores[slot]) - torch.sigmoid(slot_scores[torch.argsort(slot_scores)[-2]])), _attended_offsets(attention[0, :, relation_index * 3 + slot] if attention is not None else state["tokens"][0].new_zeros((token_states.shape[1],)), offsets), tuple(float(item) for item in selected_delta.mean(0).detach())))
    role_matches = []
    role_rows = []
    binding_rows = []
    positions = {atom.atom_id: index for index, atom in enumerate(atoms)}
    for relation in selected.relations:
        relation_slot = int(torch.argmax(state["slot_logits"][0, kernel.relation_index[relation.relation_type]]))
        for role, ids in relation.role_bindings:
            role_scores, role_vector, binding, _role_attention = kernel.role_scores(state, spans, span_mask, relation.relation_type, role)
            values = torch.softmax(role_scores[0], 0)
            ranked = torch.argsort(values, descending=True)
            role_rows.append(tuple(float(item.detach()) for item in role_vector))
            binding_rows.append(tuple(float(item.detach()) for item in binding[0]))
            for atom_id in ids:
                position = positions[atom_id]
                second = ranked[1] if len(ranked) > 1 else ranked[0]
                role_matches.append(RoleQueryMatch(relation.relation_type, relation_slot, role, atom_id, float(values[position]), float(values[position] - values[second]), tuple(float(item.detach()) for item in role_vector), tuple(float(item.detach()) for item in binding[0])))
    prediction = RelationSetPrediction(selected.relation_types, selected.role_bindings, float(scores[best_index].detach()), probability, gap, selected.disposition)
    failures: list[str] = []
    program = None
    operations = ()
    sidecar_hash = None
    if selected.disposition == "accept":
        try:
            program, operations, _semantic, _artifact, sidecar_hash = build_program(program_id=source.source_id, atoms=atoms, graph=selected, context=source.context, bank=bank, content_rows=tuple(item.content_vector for item in contents), operator_coordinate=tuple(float(torch.sigmoid(state["operator_logits"][0, index]).detach()) for index in range(len(RELATIONS))), role_rows=tuple(role_rows), binding_rows=tuple(binding_rows), delta_rows=tuple(match.delta_vector for match in matches), sidecar_dir=sidecar_dir)
        except (KeyError, ValueError) as error:
            failures.append(type(error).__name__)
            selected = GraphCandidate((), "quarantine")
            prediction = RelationSetPrediction((), (), float(scores[best_index].detach()), probability, gap, "quarantine")
    artifact = CompiledSentenceArtifact(source.source_id, bank.revision, tuple(matches), tuple(role_matches), prediction, program, operations, sidecar_hash, selected.disposition, tuple(failures), (time.perf_counter() - started) * 1000)
    return artifact, scores, {"state": state, "spans": spans, "signals": signals, "selected": selected}, candidates


@torch.no_grad()
def compile_source(kernel, encoder, anchor_states: torch.Tensor, source, bank, sidecar_dir: Path, *, confidence: float = .50, margin: float = .02) -> CompiledSentenceArtifact:
    atoms = public_atoms(source)
    token_states, attention_mask, span_masks, contents, offsets = _batch_features(encoder, ((source, atoms),))[0]
    artifact, _scores, _signal, _candidates = compile_from_features(kernel, source, atoms, token_states, attention_mask, span_masks, contents, offsets, anchor_states, bank, sidecar_dir, confidence=confidence, margin=margin)
    return artifact
