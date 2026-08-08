"""One-pass runtime inference from public source records only."""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import torch

from topology_field_ir import GoldenAtom

from .atom_bank import RELATIONS, AtomBankManifest
from .decoder import GraphCandidate, enumerate_graphs
from .field import build_program
from .model import GoldenGraphKernel
from .schemas import (
    CompiledSentenceArtifact,
    CompleteGraphHypothesis,
    ContentCandidate,
    OperatorCoordinate,
)

_ATOM_PATTERN = re.compile(r"\b(?P<kind>[a-z_]+)_(?P<id>[TDKL]\d{5}_\d+)\b")
_KNOWN_KINDS = {
    "event", "scope", "preference", "instruction", "question", "assistant_response", "entity", "goal",
    "value", "state", "rule", "conversation_turn", "claim", "fact", "observation", "hypothesis",
}


def public_atoms(source) -> tuple[GoldenAtom, ...]:
    if source.atoms:
        return tuple(source.atoms)
    result = []
    source_hash = hashlib.sha256(source.text.encode()).hexdigest()
    for index, match in enumerate(_ATOM_PATTERN.finditer(source.text)):
        kind = match.group("kind")
        if kind not in _KNOWN_KINDS:
            continue
        text = match.group(0)
        result.append(GoldenAtom(f"a{index + 1}", kind, text, text, source.source_id, match.start(), match.end(), source.context, source_hash))
    return tuple(result)


def _feature_states(encoder, source, atoms: tuple[GoldenAtom, ...]):
    return _feature_states_batch(encoder, ((source, atoms),))[0]


def _feature_states_batch(encoder, sources_and_atoms):
    """Extract one feature record per sentence with one encoder forward for the batch.

    Runtime calls this with one sentence, while training supplies a sixteen-case
    batch.  This keeps G2.8's one-forward-per-sentence contract and avoids an
    unnecessary sixteen separate MiniLM passes per optimizer step.
    """
    records = tuple(sources_and_atoms)
    tokens = encoder.tokenize([source.text for source, _atoms in records])
    offsets = tokens.pop("offset_mapping")
    extra = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask"}}
    all_states = encoder(tokens["input_ids"], tokens["attention_mask"], **extra)
    output = []
    for index, (_source, atoms) in enumerate(records):
        states = all_states[index]
        row_offsets = offsets[index]
        mask = tokens["attention_mask"][index].float().unsqueeze(-1)
        sentence = (states * mask).sum(0) / mask.sum().clamp_min(1)
        atom_states = []
        contents = []
        for atom in atoms:
            overlap = (row_offsets[:, 1] > atom.source_start) & (row_offsets[:, 0] < atom.source_end)
            weights = overlap.float().unsqueeze(-1)
            value = (states * weights).sum(0) / weights.sum().clamp_min(1)
            atom_states.append(value)
            contents.append(ContentCandidate(atom.atom_id, atom.occurrence_text, atom.source_start, atom.source_end, ((atom.kind, 1.0),), tuple(float(item.detach()) for item in torch.nn.functional.normalize(value, dim=0))))
        output.append((sentence, torch.stack(atom_states) if atom_states else states.new_zeros((0, states.shape[-1])), tuple(contents)))
    return tuple(output)


def _probabilities(scores: torch.Tensor) -> tuple[float, float, int]:
    values = torch.softmax(scores.detach(), dim=0)
    order = sorted(range(len(values)), key=lambda index: (-float(values[index]), index))
    best, second = order[0], order[1] if len(order) > 1 else order[0]
    return float(values[best]), float(values[best] - values[second]), best


@torch.no_grad()
def compile_source(kernel: GoldenGraphKernel, encoder, source, bank: AtomBankManifest, sidecar_dir: Path, *, confidence: float = .50, margin: float = .02) -> CompiledSentenceArtifact:
    started = time.perf_counter()
    atoms = public_atoms(source)
    if not atoms:
        return CompiledSentenceArtifact(source.source_id, bank.revision, (), None, (), None, "quarantine", ("NO_CONTENT_CANDIDATE",), (time.perf_counter() - started) * 1000)
    sentence, atom_states, contents = _feature_states(encoder, source, atoms)
    candidates = enumerate_graphs(tuple((atom.atom_id, atom.kind) for atom in atoms))
    scores, signals = kernel.score_graphs(sentence, atom_states, tuple(atom.atom_id for atom in atoms), candidates)
    probability, gap, best_index = _probabilities(scores)
    selected = candidates[best_index]
    if selected.disposition != "accept" or probability < confidence or gap < margin:
        selected = GraphCandidate((), "clarification_required")
    coordinates = tuple(
        OperatorCoordinate(relation, float(torch.sigmoid(signals["operator_logits"][index])), 0, tuple(float(item) for item in (signals["sentence"] - kernel.operator_states()[index]).detach()), 0.0)
        for index, relation in enumerate(RELATIONS)
    )
    role_rows = []
    binding_rows = []
    for relation in selected.relations:
        for role, ids in relation.role_bindings:
            _query, role_vector = kernel.role_state(relation.relation_type, role)
            for atom_id in ids:
                atom_index = tuple(atom.atom_id for atom in atoms).index(atom_id)
                atom_state = signals["atoms"][atom_index]
                role_rows.append(tuple(float(item) for item in role_vector.detach()))
                binding_rows.append(tuple(float(item) for item in torch.nn.functional.normalize(kernel.binding_projection(torch.cat((signals["sentence"], atom_state, role_vector))), dim=0).detach()))
    hypothesis = CompleteGraphHypothesis(
        "g28-hypothesis-" + hashlib.sha256(repr(selected).encode()).hexdigest()[:20], selected.relation_types,
        selected.role_bindings, source.context, coordinates, float(scores[best_index]), probability, gap, selected.disposition,
    )
    program = operations = artifact = None
    failures = []
    if selected.disposition == "accept":
        try:
            program, operations, _semantic, artifact = build_program(
                program_id=source.source_id, atoms=atoms, graph=selected, context=source.context, bank=bank,
                content_rows=tuple(item.content_vector for item in contents), operator_coordinate=tuple(item.activation for item in coordinates), role_rows=tuple(role_rows), binding_rows=tuple(binding_rows), sidecar_dir=sidecar_dir,
            )
        except (KeyError, ValueError) as exc:
            failures.append(type(exc).__name__)
            selected = GraphCandidate((), "quarantine")
    return CompiledSentenceArtifact(source.source_id, bank.revision, (hypothesis,), program, operations or (), artifact, selected.disposition, tuple(failures), (time.perf_counter() - started) * 1000)
