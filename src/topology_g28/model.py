"""Joint golden-operator, role and complete-graph scorer for G2.8."""

from __future__ import annotations

import hashlib

import torch
from torch import Tensor, nn

from .atom_bank import RELATIONS, AtomBankManifest
from .decoder import GraphCandidate


def _unit(value: Tensor) -> Tensor:
    return nn.functional.normalize(value, dim=-1, eps=1e-8)


def _stable_index(value: str, size: int) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:4], "little") % size


class GoldenGraphKernel(nn.Module):
    """All final graph decisions depend on learned operator/role/pair scores."""

    def __init__(self, bank: AtomBankManifest, hidden_size: int = 384) -> None:
        super().__init__()
        self.bank = bank
        self.relation_index = {relation: index for index, relation in enumerate(RELATIONS)}
        self.sentence_projection = nn.Sequential(nn.Linear(hidden_size, 192), nn.GELU(), nn.Linear(192, 192))
        self.span_projection = nn.Sequential(nn.Linear(hidden_size, 192), nn.GELU(), nn.Linear(192, 192))
        self.structural_projection = nn.Sequential(nn.Linear(64, 192), nn.GELU())
        self.anchor_projection = nn.Linear(hidden_size, 192)
        self.operator_residual = nn.Parameter(torch.zeros(len(RELATIONS), 192))
        self.role_embedding = nn.Embedding(64, 64)
        self.role_query = nn.Sequential(nn.Linear(192 + 64, 192), nn.GELU(), nn.Linear(192, 192))
        self.role_scorer = nn.Bilinear(192, 192, 1)
        self.binding_projection = nn.Sequential(nn.Linear(192 + 192 + 64, 128), nn.GELU(), nn.Linear(128, 128))
        self.pair_left = nn.Linear(192, 192, bias=False)
        self.pair_right = nn.Linear(192, 192, bias=False)
        self.pair_score = nn.Sequential(nn.Linear(192 * 3, 192), nn.GELU(), nn.Linear(192, 1))
        self.operator_head = nn.Linear(192, len(RELATIONS))
        self.context_head = nn.Linear(192, 13)
        self.disposition_head = nn.Linear(192, 3)
        self.atom_update = nn.GRUCell(192, 192)
        self.sentence_update = nn.GRUCell(192, 192)
        self.graph_head = nn.Sequential(nn.Linear(192 * 4, 192), nn.GELU(), nn.Linear(192, 1))
        self.register_buffer("anchor_vectors", torch.zeros(len(RELATIONS), hidden_size))
        self.register_buffer("structural_vectors", self._structural_vectors())

    def _structural_vectors(self) -> Tensor:
        vectors = []
        for operator in self.bank.operators:
            digest = hashlib.sha256(repr(operator).encode()).digest()
            raw = [((digest[index % len(digest)] / 255.0) * 2.0 - 1.0) for index in range(64)]
            vectors.append(raw)
        return torch.tensor(vectors, dtype=torch.float32)

    def initialize_anchors(self, encode_anchor_texts) -> None:
        """Receive a fixed encoder callback once during setup, never at runtime."""
        texts = ["; ".join(item.semantic_anchors) for item in self.bank.operators]
        with torch.no_grad():
            self.anchor_vectors.copy_(encode_anchor_texts(texts))

    def states(self, sentence_state: Tensor, atom_states: Tensor) -> tuple[Tensor, Tensor]:
        sentence = _unit(self.sentence_projection(sentence_state))
        atoms = _unit(self.span_projection(atom_states))
        for _ in range(4):
            message = atoms.mean(0) if len(atoms) else sentence
            sentence = _unit(self.sentence_update(message, sentence))
            if len(atoms):
                atoms = _unit(self.atom_update(sentence.unsqueeze(0).expand_as(atoms), atoms))
        return sentence, atoms

    def operator_states(self) -> Tensor:
        return _unit(self.structural_projection(self.structural_vectors) + self.anchor_projection(self.anchor_vectors) + self.operator_residual)

    def operator_logits(self, sentence: Tensor) -> Tensor:
        return torch.mv(self.operator_states(), sentence) + self.operator_head(sentence)

    def role_state(self, relation: str, role: str) -> Tensor:
        relation_state = self.operator_states()[self.relation_index[relation]]
        role_vector = self.role_embedding.weight[_stable_index(f"{relation}:{role}", 64)]
        return _unit(self.role_query(torch.cat((relation_state, role_vector)))), _unit(role_vector)

    def score_graphs(self, sentence_state: Tensor, atom_states: Tensor, atom_ids: tuple[str, ...], candidates: tuple[GraphCandidate, ...]) -> tuple[Tensor, dict[str, Tensor]]:
        sentence, atoms = self.states(sentence_state, atom_states)
        # All graph candidates for a sentence share these values.  Computing
        # them inside the candidate loop was semantically redundant and made
        # the legal 512-candidate lattice impractical on the four-core CPU.
        operator_states = self.operator_states()
        logits = torch.mv(operator_states, sentence) + self.operator_head(sentence)
        disposition = self.disposition_head(sentence)
        positions = {atom_id: index for index, atom_id in enumerate(atom_ids)}
        relation_vectors_by_name = {
            relation: operator_states[index]
            for index, relation in enumerate(RELATIONS)
        }
        role_cache = {
            (relation, role.role_name): self.role_state_from_operators(operator_states, relation, role.role_name)
            for relation in self.relation_index
            for role in self.bank.operators[self.relation_index[relation]].roles
        }
        values: list[Tensor] = []
        for candidate in candidates:
            if candidate.disposition != "accept":
                values.append(disposition[1 if candidate.disposition == "clarification_required" else 2])
                continue
            relation_vectors = []
            role_vectors = []
            pair_vectors = []
            score = sentence.new_zeros(())
            for relation in candidate.relations:
                relation_index = self.relation_index[relation.relation_type]
                relation_vector = relation_vectors_by_name[relation.relation_type]
                relation_vectors.append(relation_vector)
                score = score + logits[relation_index] + torch.dot(sentence, relation_vector)
                bound = []
                for role, ids in relation.role_bindings:
                    query, _role_vector = role_cache[(relation.relation_type, role)]
                    for atom_id in ids:
                        atom = atoms[positions[atom_id]]
                        role_vectors.append(query * atom)
                        bound.append(atom)
                        score = score + self.role_scorer(query, atom).squeeze()
                if len(bound) >= 2:
                    pair = self.pair_left(bound[0]) * self.pair_right(bound[1])
                    pair_vectors.append(pair)
                    score = score + self.pair_score(torch.cat((sentence, relation_vector, pair))).squeeze()
            relation_summary = _unit(torch.stack(relation_vectors).mean(0))
            role_summary = _unit(torch.stack(role_vectors).mean(0)) if role_vectors else sentence
            pair_summary = _unit(torch.stack(pair_vectors).mean(0)) if pair_vectors else sentence
            score = score + self.graph_head(torch.cat((sentence, relation_summary, role_summary, pair_summary))).squeeze()
            values.append(score)
        return torch.stack(values), {"sentence": sentence, "atoms": atoms, "operator_logits": logits, "disposition_logits": disposition}

    def role_state_from_operators(self, operator_states: Tensor, relation: str, role: str) -> tuple[Tensor, Tensor]:
        relation_state = operator_states[self.relation_index[relation]]
        role_vector = self.role_embedding.weight[_stable_index(f"{relation}:{role}", 64)]
        return _unit(self.role_query(torch.cat((relation_state, role_vector)))), _unit(role_vector)
