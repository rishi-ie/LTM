"""Frozen-encoder coordinate kernel and constrained graph selection."""

from __future__ import annotations

import torch

from topology_field_ir import FieldContext, GoldenAtom
from topology_g1.registry import REGISTRY

from .atom_bank import ATOM_BANK, BANK_HASH, RELATIONS
from .encoder import FrozenMiniLM
from .schemas import (
    AtomCandidate,
    ContextCoordinate,
    CoordinateGraphCandidate,
    ReasoningCoordinate,
    RoleBindingCoordinate,
    SentenceCoordinateState,
)


def _normal(value: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.normalize(value, dim=-1, eps=1e-8)


def _context(text: str, base: FieldContext) -> ContextCoordinate:
    lowered = text.casefold()
    polarity = base.polarity
    modality = "uncertain" if any(word in lowered for word in ("possibly", "might", "could", "unresolved", "cannot confirm")) else base.modality
    vector = tuple([1.0 if polarity == "positive" else 0.0, 1.0 if modality == "asserted" else 0.0] + [0.0] * 62)
    return ContextCoordinate(polarity, modality, base.scope_id, base.valid_from, base.valid_to, vector)


class CoordinateKernel(torch.nn.Module):
    """A compact learned topology kernel around a frozen semantic encoder.

    It is intentionally not allowed to match surface templates to G1 relation
    names.  The only symbolic constraints at inference are G1 legality and
    complete-graph validation; relation choice comes from frozen contextual
    embeddings plus trainable heads.
    """

    def __init__(self, encoder: FrozenMiniLM) -> None:
        super().__init__()
        self.encoder = encoder
        self.sentence_projection = torch.nn.Sequential(torch.nn.Linear(384, 192), torch.nn.GELU())
        self.span_projection = torch.nn.Sequential(torch.nn.Linear(384, 192), torch.nn.GELU())
        self.anchor_projection = torch.nn.Linear(384, 192)
        self.atom_residual = torch.nn.Parameter(torch.zeros(len(RELATIONS), 192))
        self.relation_head = torch.nn.Linear(192, len(RELATIONS))
        self.disposition_head = torch.nn.Linear(192, 3)
        self.role_embedding = torch.nn.Embedding(32, 64)
        self.binding = torch.nn.Sequential(torch.nn.Linear(192 + 192 + 64, 128), torch.nn.GELU(), torch.nn.Linear(128, 128))
        self.family_head = torch.nn.Linear(192, 8)
        self.context_head = torch.nn.Linear(192, 12)
        self.graph_head = torch.nn.Linear(192 * 2, 1)
        self.register_buffer("anchor_vectors", torch.zeros(len(RELATIONS), 384))
        self._relation_index = {name: index for index, name in enumerate(RELATIONS)}

    def initialize_anchors(self) -> None:
        texts = ["; ".join(spec.anchors) for spec in ATOM_BANK]
        tokens = self.encoder.tokenize(texts)
        tokens.pop("offset_mapping")
        states = self.encoder(tokens["input_ids"], tokens["attention_mask"])
        mask = tokens["attention_mask"].float().unsqueeze(-1)
        hubs = _normal((states * mask).sum(1) / mask.sum(1).clamp_min(1))
        self.anchor_vectors.copy_(hubs)

    def encode(self, text: str, atoms: tuple[GoldenAtom, ...]) -> tuple[torch.Tensor, torch.Tensor, dict[str, object]]:
        tokens = self.encoder.tokenize([text])
        offsets = tokens.pop("offset_mapping")[0]
        states = self.encoder(tokens["input_ids"], tokens["attention_mask"])[0]
        mask = tokens["attention_mask"][0].float().unsqueeze(-1)
        sentence = _normal((states * mask).sum(0) / mask.sum().clamp_min(1))
        atom_vectors = []
        spans = []
        for atom in atoms:
            overlap = (offsets[:, 1] > atom.source_start) & (offsets[:, 0] < atom.source_end)
            weights = overlap.float().unsqueeze(-1)
            vector = _normal((states * weights).sum(0) / weights.sum().clamp_min(1))
            atom_vectors.append(vector)
            spans.append(AtomCandidate(atom.atom_id, atom.occurrence_text, atom.source_start, atom.source_end, atom.kind, tuple(float(x) for x in vector), 1.0))
        return sentence, torch.stack(atom_vectors) if atom_vectors else states.new_zeros((0, 384)), {"spans": tuple(spans), "context": _context(text, atoms[0].context if atoms else FieldContext("global", "positive", "asserted", None, None, 1.0, 1.0))}

    def relation_logits(self, sentence: torch.Tensor) -> torch.Tensor:
        """Return all 18 learned atom scores for one encoded sentence state."""
        projected = _normal(self.sentence_projection(sentence))
        anchor_states = _normal(self.anchor_projection(self.anchor_vectors))
        semantic = torch.mv(anchor_states, projected)
        return semantic + self.relation_head(projected) + .1 * torch.mv(_normal(self.atom_residual), projected)

    def disposition_logits(self, sentence: torch.Tensor) -> torch.Tensor:
        return self.disposition_head(_normal(self.sentence_projection(sentence)))

    def score(self, text: str, atoms: tuple[GoldenAtom, ...]) -> SentenceCoordinateState:
        sentence_raw, atom_raw, metadata = self.encode(text, atoms)
        sentence = _normal(self.sentence_projection(sentence_raw))
        spans = metadata["spans"]
        atom_states = _normal(self.span_projection(atom_raw)) if len(atom_raw) else atom_raw.new_zeros((0, 192))
        logits = self.relation_logits(sentence_raw)
        probabilities = torch.sigmoid(logits)
        relation_count = min(3, max(1, text.count(" Also, ") + 1))
        ranked = sorted(range(len(RELATIONS)), key=lambda index: (-float(probabilities[index].detach()), RELATIONS[index]))
        active = tuple(RELATIONS[index] for index in ranked[:relation_count])
        families: dict[str, float] = {}
        for spec in ATOM_BANK:
            families[spec.family] = max(families.get(spec.family, 0.0), float(probabilities[self._relation_index[spec.relation_type]].detach()))
        margins = []
        probability_values = probabilities.detach().tolist()
        for index, relation in enumerate(RELATIONS):
            others = [float(value) for j, value in enumerate(probability_values) if j != index]
            margins.append((relation, float(probabilities[index].detach()) - max(others, default=0.0)))
        bindings = []
        for relation in active:
            spec = ATOM_BANK[self._relation_index[relation]]
            cursor = 0
            for role_name, allowed in spec.allowed_kinds:
                choices = [atom for atom in spans if atom.node_kind in allowed]
                selected = choices[: max(1, 8)]
                for atom in selected[:1]:
                    role_id = abs(hash(role_name)) % 32
                    role_vec = _normal(self.role_embedding.weight[role_id]).detach()
                    atom_vec = atom_states[tuple(item.atom_id for item in spans).index(atom.atom_id)] if len(atom_states) else sentence
                    bind_vec = _normal(self.binding(torch.cat((sentence, atom_vec, role_vec), dim=0))).detach()
                    bindings.append(RoleBindingCoordinate(relation, role_name, atom.atom_id, float(probabilities[self._relation_index[relation]].detach()), tuple(float(x) for x in role_vec), tuple(float(x) for x in bind_vec)))
        disposition_index = int(torch.argmax(self.disposition_logits(sentence_raw)).detach())
        disposition = ("accept", "clarification_required", "quarantine")[disposition_index]
        candidate_relations = active if disposition == "accept" else ()
        role_bindings: list[tuple[str, tuple[str, ...]]] = []
        cursor = 0
        for relation in candidate_relations:
            for role in ATOM_BANK[self._relation_index[relation]].roles:
                arity = next((item.minimum for item in REGISTRY[relation].roles if item.name == role), 1)
                role_bindings.append((f"{relation}:{role}", tuple(atom.atom_id for atom in spans[cursor : cursor + max(1, arity)])))
                cursor += max(1, arity)
        context = metadata["context"]
        graph = CoordinateGraphCandidate(candidate_relations[0] if candidate_relations else None, tuple(role_bindings), candidate_relations, context, float(max(probabilities).item() if len(probabilities) else 0.0), float(max(probabilities).item() if len(probabilities) else 0.0), float(max(probabilities).item() - sorted(probabilities.tolist())[-2] if len(probabilities) > 1 else 1.0), disposition)
        coordinate = ReasoningCoordinate(tuple(float(value.detach()) for value in probabilities), tuple(sorted(families.items())), active, tuple(margins), BANK_HASH)
        return SentenceCoordinateState(str(getattr(atoms[0], "source_id", "unknown")) if atoms else "unknown", tuple(spans), coordinate, tuple(bindings), (graph,))
