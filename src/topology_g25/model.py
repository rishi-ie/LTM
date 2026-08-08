"""One-pass four-space representation kernel."""

from __future__ import annotations

import torch
from torch import Tensor, nn

from .registry import MODALITIES, NODE_KINDS, POLARITIES, RELATIONS, ROLES, SCOPES


def _normal(values: Tensor) -> Tensor:
    return nn.functional.normalize(values, dim=-1, eps=1e-12)


class TypedAtomKernel(nn.Module):
    """Sentence context + supplied atom spans -> operator, role, and context spaces."""

    def __init__(
        self, encoder: nn.Module, hidden_size: int = 384, *, reconciliation_cycles: int = 4
    ) -> None:
        super().__init__()
        self.encoder = encoder
        self.reconciliation_cycles = reconciliation_cycles
        self.sentence_projection = nn.Linear(hidden_size, 128)
        self.content_projection = nn.Linear(hidden_size * 2, 128)
        self.node_kind_embedding = nn.Embedding(
            len(NODE_KINDS) + 1, 128, padding_idx=len(NODE_KINDS)
        )
        self.operator_prototypes = nn.Parameter(torch.randn(len(RELATIONS), 4, 128) * 0.02)
        self.role_vectors = nn.Parameter(torch.randn(len(ROLES), 64) * 0.02)
        self.role_projection = nn.Linear(64, 128, bias=False)
        self.role_query = nn.Sequential(nn.Linear(128 * 3, 256), nn.GELU(), nn.Linear(256, 128))
        self.operator_message = nn.Linear(128 * 2, 128)
        self.operator_update = nn.GRUCell(128, 128)
        self.content_update = nn.GRUCell(128, 128)
        self.sentence_update = nn.GRUCell(128, 128)
        self.context_vector = nn.Sequential(nn.Linear(128, 128), nn.GELU(), nn.Linear(128, 64))
        self.polarity_head = nn.Linear(128, len(POLARITIES))
        self.modality_head = nn.Linear(128, len(MODALITIES))
        self.scope_head = nn.Linear(128, len(SCOPES))
        self.disposition_head = nn.Linear(128, 3)
        self.content_to_384 = nn.Linear(128, 384)
        self.binding_projection = nn.Sequential(
            nn.Linear(128 * 3, 512), nn.GELU(), nn.Linear(512, 256)
        )

    def forward(
        self, tokens: dict[str, Tensor], span_masks: Tensor, atom_kind_ids: Tensor
    ) -> dict[str, Tensor]:
        extras = {
            key: value
            for key, value in tokens.items()
            if key not in {"input_ids", "attention_mask", "offset_mapping"}
        }
        states = self.encoder(tokens["input_ids"], tokens["attention_mask"], **extras)
        attention = tokens["attention_mask"].unsqueeze(-1).float()
        hub = (states * attention).sum(1) / attention.sum(1).clamp_min(1)
        sentence = _normal(self.sentence_projection(hub))
        # ``span_masks`` has shape [batch, atoms, tokens], including no special
        # content in empty/padded atom slots.
        span_weights = span_masks.float()
        span_pool = torch.einsum("bat,bth->bah", span_weights, states)
        span_pool = span_pool / span_weights.sum(-1, keepdim=True).clamp_min(1)
        content = _normal(
            self.content_projection(
                torch.cat((span_pool, hub.unsqueeze(1).expand_as(span_pool)), dim=-1)
            )
            + self.node_kind_embedding(atom_kind_ids)
        )
        prototypes = _normal(self.operator_prototypes)
        operator_state = _normal(prototypes.mean(1).unsqueeze(0) + sentence.unsqueeze(1))
        # Do not collapse candidate relation families early: every operator
        # exchanges typed messages with every plausible content span for four
        # deterministic reconciliation cycles.
        for _ in range(self.reconciliation_cycles):
            attention_logits = torch.einsum("brh,bah->bra", operator_state, content)
            attention_logits = attention_logits.masked_fill(~span_masks.any(-1).unsqueeze(1), -1e9)
            attention = torch.softmax(attention_logits, dim=-1)
            gathered = torch.einsum("bra,bah->brh", attention, content)
            operator_input = self.operator_message(
                torch.cat((gathered, sentence.unsqueeze(1).expand_as(gathered)), dim=-1)
            )
            operator_state = _normal(
                self.operator_update(
                    operator_input.reshape(-1, 128), operator_state.reshape(-1, 128)
                ).reshape_as(operator_state)
            )
            content_message = torch.einsum("bra,brh->bah", attention, operator_state)
            content = _normal(
                self.content_update(
                    content_message.reshape(-1, 128), content.reshape(-1, 128)
                ).reshape_as(content)
            )
            sentence = _normal(self.sentence_update(operator_state.mean(1), sentence))
        similarities = torch.einsum("bh,rph->brp", sentence, prototypes)
        operator_logits = similarities.max(-1).values + torch.einsum(
            "brh,bh->br", operator_state, sentence
        )
        return {
            "sentence": sentence,
            "content": content,
            "operator_logits": operator_logits,
            "prototype_scores": similarities,
            "operator_state": operator_state,
            "polarity_logits": self.polarity_head(sentence),
            "modality_logits": self.modality_head(sentence),
            "scope_logits": self.scope_head(sentence),
            "disposition_logits": self.disposition_head(sentence),
            "context_vector": _normal(self.context_vector(sentence)),
            "content_384": _normal(self.content_to_384(content)),
        }

    def role_logits(
        self,
        sentence: Tensor,
        content: Tensor,
        relation_ids: Tensor,
        role_ids: Tensor,
        atom_mask: Tensor,
        operator_state: Tensor | None = None,
    ) -> Tensor:
        """Return scores [batch, roles, atoms] for G1-named role placement."""
        relation = (
            operator_state[torch.arange(sentence.shape[0], device=sentence.device), relation_ids]
            if operator_state is not None
            else _normal(self.operator_prototypes.mean(1))[relation_ids]
        )
        role = self.role_projection(self.role_vectors[role_ids])
        query_input = torch.cat(
            (
                sentence.unsqueeze(1).expand(-1, role.shape[1], -1),
                relation.unsqueeze(1).expand(-1, role.shape[1], -1),
                role,
            ),
            dim=-1,
        )
        query = _normal(self.role_query(query_input))
        scores = torch.einsum("brh,bah->bra", query, content)
        return scores.masked_fill(~atom_mask.unsqueeze(1), -1e9)

    def binding_vectors(
        self, content: Tensor, relation_ids: Tensor, role_ids: Tensor, atom_ids: Tensor
    ) -> Tensor:
        """Low-rank 256D contributions for selected sparse bindings."""
        operator = _normal(self.operator_prototypes.mean(1))[relation_ids]
        role = _normal(self.role_projection(self.role_vectors[role_ids]))
        selected = content[torch.arange(content.shape[0], device=content.device), atom_ids]
        return _normal(
            self.binding_projection(
                torch.cat((selected * role, selected * operator, role * operator), dim=-1)
            )
        )
