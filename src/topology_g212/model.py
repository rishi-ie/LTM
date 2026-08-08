"""One-pass MiniLM plus factorized operator, role, direction, and context heads."""

from __future__ import annotations

import hashlib

import torch
from torch import Tensor, nn

from topology_g1.registry import REGISTRY

from .encoder import OnePassMiniLM
from .registry import DISPOSITIONS, MODALITIES, POLARITIES, RELATIONS, ROLES, SCOPES


def _fixed_cards(names: tuple[str, ...], width: int) -> Tensor:
    rows = []
    for name in names:
        digest = hashlib.sha256(name.encode()).digest()
        values = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(width)]
        rows.append(values)
    return torch.tensor(rows, dtype=torch.float32)


class FactorizedCompiler(nn.Module):
    """The learned part predicts only information not derivable from G1."""

    def __init__(self, encoder: OnePassMiniLM | None = None) -> None:
        super().__init__()
        self.encoder = encoder or OnePassMiniLM()
        self.sentence_projection = nn.Sequential(nn.Linear(384, 192), nn.GELU())
        self.span_projection = nn.Sequential(nn.Linear(384, 192), nn.GELU())
        self.operator_queries = nn.Parameter(torch.randn(len(RELATIONS), 192) * 0.02)
        self.operator_bias = nn.Parameter(torch.zeros(len(RELATIONS)))
        self.operator_classifier = nn.Linear(192, len(RELATIONS))
        self.operator_card_projection = nn.Linear(32, 192)
        self.role_vectors = nn.Parameter(torch.randn(len(ROLES), 64) * 0.02)
        self.role_projection = nn.Linear(64, 192, bias=False)
        self.role_query = nn.Sequential(nn.Linear(384, 256), nn.GELU(), nn.Linear(256, 192))
        self.pair_projection = nn.Sequential(nn.Linear(192 * 4, 256), nn.GELU(), nn.Linear(256, 128))
        self.pair_queries = nn.Parameter(torch.randn(len(RELATIONS), 128) * 0.02)
        self.polarity_head = nn.Linear(192, len(POLARITIES))
        self.modality_head = nn.Linear(192, len(MODALITIES))
        self.scope_head = nn.Linear(192, len(SCOPES))
        self.disposition_head = nn.Linear(192, len(DISPOSITIONS))
        self.card_vectors = _fixed_cards(RELATIONS, 32)
        role_mask = torch.zeros((len(RELATIONS), len(ROLES)), dtype=torch.bool)
        for relation_index, relation in enumerate(RELATIONS):
            for role in REGISTRY[relation].roles:
                role_mask[relation_index, ROLES.index(role.name)] = True
        self.register_buffer("role_mask", role_mask)

    def forward(self, tokens: dict[str, Tensor], span_masks: Tensor) -> dict[str, Tensor]:
        extras = {
            key: value
            for key, value in tokens.items()
            if key not in {"input_ids", "attention_mask", "offset_mapping"}
        }
        hidden = self.encoder(tokens["input_ids"], tokens["attention_mask"], **extras)
        attention = tokens["attention_mask"].float().unsqueeze(-1)
        hub = (hidden * attention).sum(1) / attention.sum(1).clamp_min(1.0)
        sentence = self.sentence_projection(hub)
        span = torch.einsum("bst,bth->bsh", span_masks.float(), hidden)
        span = span / span_masks.sum(-1, keepdim=True).clamp_min(1.0)
        span_state = self.span_projection(span)
        cards = self.operator_card_projection(self.card_vectors)
        operator_state = self.operator_queries + cards
        operator_state = operator_state.unsqueeze(0) + sentence.unsqueeze(1)
        operator_logits = self.operator_classifier(sentence)
        operator_logits = operator_logits + 0.1 * torch.einsum(
            "brh,brh->br", operator_state, self.operator_queries.unsqueeze(0).expand_as(operator_state)
        ) / operator_state.shape[-1] ** 0.5 + self.operator_bias
        role_base = self.role_projection(self.role_vectors)
        role_queries = self.role_query(
            torch.cat(
                (
                    operator_state.unsqueeze(2).expand(-1, -1, len(ROLES), -1),
                    role_base.unsqueeze(0).unsqueeze(0).expand(span_state.shape[0], len(RELATIONS), -1, -1),
                ),
                -1,
            )
        )
        role_scores = torch.einsum("brkh,bsh->brks", role_queries, span_state)
        role_scores = role_scores.masked_fill(~self.role_mask.unsqueeze(0).unsqueeze(-1), -1e9)
        left = span_state.unsqueeze(2).expand(-1, -1, span_state.shape[1], -1)
        right = span_state.unsqueeze(1).expand(-1, span_state.shape[1], -1, -1)
        pair_input = torch.cat((left, right, left - right, left * right), -1)
        pair_state = self.pair_projection(pair_input)
        pair_scores = torch.einsum("bijh,rh->brij", pair_state, self.pair_queries)
        pair_scores = pair_scores.masked_fill(~span_masks.any(-1).unsqueeze(1).unsqueeze(-1), -1e9)
        return {
            "hidden": hidden,
            "sentence": sentence,
            "span": span_state,
            "operator_logits": operator_logits,
            "role_scores": role_scores,
            "pair_scores": pair_scores,
            "polarity_logits": self.polarity_head(sentence),
            "modality_logits": self.modality_head(sentence),
            "scope_logits": self.scope_head(sentence),
            "disposition_logits": self.disposition_head(sentence),
        }
