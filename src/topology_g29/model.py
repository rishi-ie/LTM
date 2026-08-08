"""Dynamic golden-query cross-attention kernel for topology compilation."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from .atom_bank import RELATIONS
from .decoder import GraphCandidate


def _unit(value: Tensor) -> Tensor:
    return nn.functional.normalize(value, dim=-1, eps=1e-8)


@dataclass(frozen=True, slots=True)
class QueryLayout:
    operator_count: int
    role_keys: tuple[tuple[str, str], ...]


class QueryBlock(nn.Module):
    def __init__(self, dimension: int = 192, heads: int = 6) -> None:
        super().__init__()
        self.cross = nn.MultiheadAttention(dimension, heads, batch_first=True)
        self.self_attention = nn.MultiheadAttention(dimension, heads, batch_first=True)
        self.feed_forward = nn.Sequential(nn.Linear(dimension, dimension * 2), nn.GELU(), nn.Linear(dimension * 2, dimension))
        self.cross_norm = nn.LayerNorm(dimension)
        self.self_norm = nn.LayerNorm(dimension)
        self.ff_norm = nn.LayerNorm(dimension)

    def forward(self, queries: Tensor, tokens: Tensor, key_padding_mask: Tensor) -> tuple[Tensor, Tensor]:
        cross, weights = self.cross(queries, tokens, tokens, key_padding_mask=key_padding_mask, need_weights=True, average_attn_weights=False)
        queries = self.cross_norm(queries + cross)
        self_values, _ = self.self_attention(queries, queries, queries, need_weights=False)
        queries = self.self_norm(queries + self_values)
        return self.ff_norm(queries + self.feed_forward(queries)), weights


class GoldenQueryKernel(nn.Module):
    """A non-generative compiler: contextual tokens are compared with golden queries."""

    def __init__(self, bank, hidden_size: int = 384, dimension: int = 192) -> None:
        super().__init__()
        self.bank = bank
        self.dimension = dimension
        self.relation_index = {name: index for index, name in enumerate(RELATIONS)}
        role_keys = tuple((operator.relation_type, role.role_name) for operator in bank.operators for role in operator.roles)
        self.layout = QueryLayout(len(RELATIONS), role_keys)
        self.role_index = {key: index for index, key in enumerate(role_keys)}
        self.token_projection = nn.Sequential(nn.Linear(hidden_size, dimension), nn.GELU(), nn.Linear(dimension, dimension))
        self.span_projection = nn.Sequential(nn.Linear(hidden_size, dimension), nn.GELU(), nn.Linear(dimension, dimension))
        self.operator_anchor_projection = nn.Linear(hidden_size, dimension)
        self.role_anchor_projection = nn.Linear(hidden_size, dimension)
        self.structural_projection = nn.Sequential(nn.Linear(64, dimension), nn.GELU(), nn.Linear(dimension, dimension))
        self.operator_residual = nn.Parameter(torch.zeros(len(RELATIONS), dimension))
        self.instance_embedding = nn.Embedding(3, dimension)
        self.blocks = nn.ModuleList([QueryBlock(dimension) for _ in range(3)])
        self.activation_head = nn.Linear(dimension, 1)
        self.null_head = nn.Linear(dimension, 3)
        self.role_embedding = nn.Embedding(len(role_keys), 64)
        self.role_projection = nn.Linear(64, dimension, bias=False)
        self.role_cross = nn.MultiheadAttention(dimension, 6, batch_first=True)
        self.role_score = nn.Bilinear(dimension, dimension, 1)
        self.pair_left = nn.Linear(dimension, dimension, bias=False)
        self.pair_right = nn.Linear(dimension, dimension, bias=False)
        self.pair_score = nn.Sequential(nn.Linear(dimension * 3, dimension), nn.GELU(), nn.Linear(dimension, 1))
        self.graph_head = nn.Sequential(nn.Linear(dimension * 4, dimension), nn.GELU(), nn.Linear(dimension, 1))
        self.context_head = nn.Linear(dimension, 13)
        self.binding_projection = nn.Sequential(nn.Linear(dimension * 2 + 64, 128), nn.GELU(), nn.Linear(128, 128))
        self.register_buffer("structural_features", self._structural_features())

    def _structural_features(self) -> Tensor:
        kinds = sorted({kind for operator in self.bank.operators for role in operator.roles for kind in role.allowed_node_kinds})
        role_names = sorted({role.role_name for operator in self.bank.operators for role in operator.roles})
        features = []
        for operator_index, operator in enumerate(self.bank.operators):
            value = torch.zeros(64)
            value[operator_index] = 1.0
            for role in operator.roles:
                value[18 + role_names.index(role.role_name)] = 1.0
                value[40] += role.minimum / 8.0
                value[41] += role.maximum / 8.0
                value[42] += len(role.allowed_node_kinds) / max(1, len(kinds))
            value[43] = 1.0 if operator.hard_or_soft == "hard" else 0.0
            value[44] = operator.base_field_weight
            value[45] = len(operator.contrast_operator_ids) / 4.0
            features.append(value)
        return torch.stack(features)

    def anchor_texts(self) -> tuple[str, ...]:
        operators = tuple("; ".join(item.semantic_anchors) for item in self.bank.operators)
        roles = tuple("; ".join(role.semantic_anchors) for item in self.bank.operators for role in item.roles)
        return operators + roles

    def dynamic_queries(self, anchor_states: Tensor) -> tuple[Tensor, Tensor, Tensor]:
        operator_count = self.layout.operator_count
        if anchor_states.shape != (operator_count + len(self.layout.role_keys), 384):
            raise ValueError("dynamic golden-query anchor shape mismatch")
        operators = _unit(self.operator_anchor_projection(anchor_states[:operator_count]) + self.structural_projection(self.structural_features) + self.operator_residual)
        roles = _unit(self.role_anchor_projection(anchor_states[operator_count:]))
        slots = torch.arange(3, device=anchor_states.device)
        queries = _unit(operators[:, None, :] + self.instance_embedding(slots)[None, :, :])
        return operators, roles, queries.reshape(-1, self.dimension)

    def contextualize(self, token_states: Tensor, attention_mask: Tensor, anchor_states: Tensor) -> dict[str, Tensor]:
        """Run the three query blocks over one or more contextualized sentences."""
        if token_states.ndim != 3:
            raise ValueError("token states must have batch, token, hidden dimensions")
        tokens = _unit(self.token_projection(token_states))
        operators, role_anchors, base_queries = self.dynamic_queries(anchor_states)
        batch = tokens.shape[0]
        queries = base_queries.unsqueeze(0).expand(batch, -1, -1)
        weights = None
        for block in self.blocks:
            queries, weights = block(queries, tokens, ~attention_mask.bool())
        slot_logits = self.activation_head(queries).squeeze(-1).reshape(batch, len(RELATIONS), 3)
        operator_logits = torch.logsumexp(slot_logits, dim=-1)
        hub = _unit((tokens * attention_mask.unsqueeze(-1)).sum(1) / attention_mask.sum(1, keepdim=True).clamp_min(1))
        return {"tokens": tokens, "hub": hub, "operators": operators, "role_anchors": role_anchors, "queries": queries.reshape(batch, len(RELATIONS), 3, self.dimension), "slot_logits": slot_logits, "operator_logits": operator_logits, "disposition_logits": self.null_head(hub), "context_logits": self.context_head(hub), "attention": weights}

    def span_states(self, token_states: Tensor, span_masks: Tensor) -> Tensor:
        weights = span_masks.float()
        pooled = torch.einsum("bat,bth->bah", weights, token_states)
        return _unit(self.span_projection(pooled / weights.sum(-1, keepdim=True).clamp_min(1)))

    def role_scores(self, state: dict[str, Tensor], spans: Tensor, span_mask: Tensor, relation: str, role: str) -> tuple[Tensor, Tensor, Tensor, Tensor]:
        relation_index = self.relation_index[relation]
        slots = state["queries"][:, relation_index]
        slot_weight = torch.softmax(state["slot_logits"][:, relation_index], dim=-1).unsqueeze(-1)
        relation_query = _unit((slots * slot_weight).sum(1))
        role_index = self.role_index[(relation, role)]
        role_vector = _unit(self.role_embedding.weight[role_index])
        query = _unit(relation_query + state["role_anchors"][role_index] + self.role_projection(role_vector))
        attended, attention = self.role_cross(query.unsqueeze(1), spans, spans, key_padding_mask=~span_mask.bool(), need_weights=True)
        attended = _unit(attended.squeeze(1))
        scores = self.role_score(attended.unsqueeze(1).expand_as(spans), spans).squeeze(-1).masked_fill(~span_mask, -1e9)
        binding = _unit(self.binding_projection(torch.cat((relation_query, attended, role_vector.expand(relation_query.shape[0], -1)), dim=-1)))
        return scores, role_vector, binding, attention.squeeze(1)

    def score_graphs(self, state: dict[str, Tensor], spans: Tensor, span_mask: Tensor, atom_ids: tuple[str, ...], candidates: tuple[GraphCandidate, ...]) -> tuple[Tensor, dict[str, Tensor]]:
        if state["hub"].shape[0] != 1:
            raise ValueError("complete graph scoring is deliberately per sentence")
        positions = {atom_id: index for index, atom_id in enumerate(atom_ids)}
        role_cache: dict[tuple[str, str], tuple[Tensor, Tensor, Tensor, Tensor]] = {}
        values = []
        for candidate in candidates:
            if candidate.disposition != "accept":
                values.append(state["disposition_logits"][0, 1 if candidate.disposition == "clarification_required" else 2])
                continue
            relation_vectors = []
            role_vectors = []
            pair_vectors = []
            score = state["hub"].new_zeros(())
            for relation in candidate.relations:
                relation_index = self.relation_index[relation.relation_type]
                relation_vector = state["operators"][relation_index]
                relation_vectors.append(relation_vector)
                score = score + state["operator_logits"][0, relation_index]
                bound = []
                for role, ids in relation.role_bindings:
                    key = (relation.relation_type, role)
                    cached = role_cache.get(key)
                    if cached is None:
                        cached = self.role_scores(state, spans, span_mask, relation.relation_type, role)
                        role_cache[key] = cached
                    role_scores, role_vector, _binding, _attention = cached
                    # The compact 64D role sidecar is preserved separately;
                    # graph composition uses its learned 192D projection.
                    role_vectors.append(self.role_projection(role_vector))
                    for atom_id in ids:
                        atom_index = positions[atom_id]
                        score = score + role_scores[0, atom_index]
                        bound.append(spans[0, atom_index])
                if len(bound) >= 2:
                    pair = self.pair_left(bound[0]) * self.pair_right(bound[1])
                    pair_vectors.append(pair)
                    score = score + self.pair_score(torch.cat((state["hub"][0], relation_vector, pair))).squeeze()
            relation_summary = _unit(torch.stack(relation_vectors).mean(0))
            role_summary = _unit(torch.stack(role_vectors).mean(0)) if role_vectors else state["hub"][0]
            pair_summary = _unit(torch.stack(pair_vectors).mean(0)) if pair_vectors else state["hub"][0]
            values.append(score + self.graph_head(torch.cat((state["hub"][0], relation_summary, role_summary, pair_summary))).squeeze())
        return torch.stack(values), {**state, "role_cache": role_cache}
