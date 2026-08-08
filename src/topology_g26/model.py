"""Joint G1 candidate scorer for the G2.6 compiler.

The important invariant is that a relation and its ordered role fillers are
scored as one candidate.  There is no independent relation argmax followed by
role repair.
"""

from __future__ import annotations

import torch
from torch import Tensor, nn

from .cards import CARDS, RELATIONS, ROLES
from .decoder import StructuredCandidate


def _unit(value: Tensor) -> Tensor:
    return nn.functional.normalize(value, dim=-1, eps=1e-8)


class JointCandidateScorer(nn.Module):
    def __init__(self, hidden_size: int = 384, score_size: int = 128, cycles: int = 2) -> None:
        super().__init__()
        self.cycles = cycles
        self.sentence_projection = nn.Sequential(nn.Linear(hidden_size, score_size), nn.GELU())
        self.atom_projection = nn.Sequential(nn.Linear(hidden_size, score_size), nn.GELU())
        self.registry_projection = nn.Sequential(nn.Linear(64, score_size), nn.GELU())
        self.relation_text_projection = nn.Sequential(nn.Linear(hidden_size, score_size), nn.GELU())
        self.register_buffer("relation_text_features", torch.zeros(len(RELATIONS), hidden_size))
        self.linguistic_prototypes = nn.Parameter(torch.randn(len(RELATIONS), score_size) * 0.02)
        self.relation_gate = nn.Parameter(torch.zeros(len(RELATIONS)))
        self.relation_embedding = nn.Embedding(len(RELATIONS), score_size)
        self.role_embedding = nn.Embedding(len(ROLES), score_size)
        self.polarity_embedding = nn.Embedding(2, score_size)
        self.modality_embedding = nn.Embedding(5, score_size)
        self.scope_embedding = nn.Embedding(5, score_size)
        self.atom_update = nn.GRUCell(score_size, score_size)
        self.sentence_update = nn.GRUCell(score_size, score_size)
        self.pair_source = nn.Linear(score_size, score_size, bias=False)
        self.pair_target = nn.Linear(score_size, score_size, bias=False)
        self.pair_bias = nn.Linear(score_size * 3, 1)
        self.graph_score = nn.Sequential(
            nn.Linear(score_size * 4, score_size), nn.GELU(), nn.Linear(score_size, 1)
        )
        self.context_head = nn.Linear(score_size, 2 + 5 + 5)
        self.operator_head = nn.Linear(score_size, len(RELATIONS))
        self.disposition_head = nn.Linear(score_size, 3)

    def _relation_state(self, relation_id: int) -> Tensor:
        structural = self.registry_projection(
            torch.tensor(CARDS[relation_id].structural_vector, dtype=self.linguistic_prototypes.dtype, device=self.linguistic_prototypes.device)
        )
        learned = self.linguistic_prototypes[relation_id]
        gate = torch.sigmoid(self.relation_gate[relation_id])
        text = self.relation_text_projection(self.relation_text_features[relation_id])
        return _unit(gate * learned + (1.0 - gate) * structural + text + self.relation_embedding.weight[relation_id])

    def encode_states(self, sentence_state: Tensor, atom_states: Tensor) -> tuple[Tensor, Tensor]:
        sentence = _unit(self.sentence_projection(sentence_state))
        atoms = _unit(self.atom_projection(atom_states))
        for _ in range(self.cycles):
            messages = atoms.mean(0)
            sentence = _unit(self.sentence_update(messages, sentence))
            atom_message = sentence.unsqueeze(0).expand_as(atoms)
            atoms = _unit(self.atom_update(atom_message, atoms))
        return sentence, atoms

    def context_logits(self, sentence_state: Tensor) -> Tensor:
        return self.context_head(sentence_state)

    def disposition_logits(self, sentence_state: Tensor) -> Tensor:
        return self.disposition_head(sentence_state)

    def score_candidates(
        self,
        sentence_state: Tensor,
        atom_states: Tensor,
        atom_ids: tuple[str, ...],
        candidates: tuple[StructuredCandidate, ...],
        *,
        disable_registry: bool = False,
        disable_pairs: bool = False,
        disable_roles: bool = False,
        disable_context: bool = False,
    ) -> Tensor:
        if sentence_state.ndim != 1 or atom_states.ndim != 2:
            raise ValueError("expected unbatched sentence and atom states")
        sentence, atoms = self.encode_states(sentence_state, atom_states)
        operator_logits = self.operator_head(sentence)
        positions = {atom_id: index for index, atom_id in enumerate(atom_ids)}
        values: list[Tensor] = []
        for candidate in candidates:
            if candidate.relation_type is None:
                null = self.disposition_head(sentence)
                values.append(null[1 if candidate.disposition == "clarification_required" else 2])
                continue
            relation_id = RELATIONS.index(candidate.relation_type)
            relation = self._relation_state(relation_id)
            if disable_registry:
                relation = _unit(self.linguistic_prototypes[relation_id] + self.relation_embedding.weight[relation_id])
            score = torch.dot(sentence, relation) + operator_logits[relation_id]
            role_vectors: list[Tensor] = []
            pair_vectors: list[Tensor] = []
            for role, selected_ids in candidate.role_bindings:
                role_id = ROLES.index(role)
                role_vector = self.role_embedding.weight[role_id]
                for atom_id in selected_ids:
                    atom = atoms[positions[atom_id]]
                    role_vectors.append(role_vector * atom if not disable_roles else atom)
                if len(selected_ids) >= 2 and not disable_pairs:
                    left = atoms[positions[selected_ids[0]]]
                    right = atoms[positions[selected_ids[1]]]
                    pair = self.pair_source(left) * self.pair_target(right)
                    pair_vectors.append(pair)
                elif len(selected_ids) >= 1:
                    pair_vectors.append(atoms[positions[selected_ids[0]]])
            if role_vectors:
                role_state = _unit(torch.stack(role_vectors).mean(0))
                score = score + torch.dot(sentence, role_state)
            if pair_vectors:
                pair_state = _unit(torch.stack(pair_vectors).mean(0))
                if not disable_pairs:
                    score = score + self.pair_bias(torch.cat((sentence, relation, pair_state)).unsqueeze(0)).squeeze()
                else:
                    score = score + torch.dot(sentence, pair_state) * 0.25
            graph = torch.stack(
                [sentence, relation, _unit(torch.stack(role_vectors).mean(0)) if role_vectors else sentence, _unit(torch.stack(pair_vectors).mean(0)) if pair_vectors else sentence]
            ).mean(0)
            score = score + self.graph_score(torch.cat((sentence, relation, graph, sentence)).unsqueeze(0)).squeeze()
            if not disable_context:
                score = score + 0.1 * self.context_head(sentence).max()
            values.append(score)
        return torch.stack(values)

    def score_candidates_with_logits(self, *args, **kwargs) -> tuple[Tensor, Tensor, Tensor]:
        sentence_state, atom_states = args[:2]
        sentence, _atoms = self.encode_states(sentence_state, atom_states)
        return self.score_candidates(*args, **kwargs), self.context_logits(sentence), self.disposition_logits(sentence)


def directional_margin_loss(scores: Tensor, gold_index: int, reversed_indices: tuple[int, ...], margin: float = 0.35) -> Tensor:
    if not reversed_indices:
        return scores.sum() * 0
    gold = scores[gold_index]
    reverse = scores[torch.tensor(reversed_indices, device=scores.device)]
    return torch.relu(margin - gold + reverse).mean()
