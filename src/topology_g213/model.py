from __future__ import annotations

import torch
from torch import Tensor, nn

from .encoder import OnePassMiniLM
from .registry import (
    ACTIONS,
    ACTS,
    DISPOSITIONS,
    MODALITIES,
    POLARITIES,
    REFERENCE_STATES,
    SCOPES,
    SLOT_TYPES,
)


class ConversationCompiler(nn.Module):
    """One encoder pass with independent conversational decisions."""

    def __init__(self, encoder: OnePassMiniLM | None = None) -> None:
        super().__init__()
        self.encoder = encoder or OnePassMiniLM()
        self.projection = nn.Sequential(nn.Linear(384, 192), nn.GELU())
        self.span_projection = nn.Sequential(nn.Linear(384, 192), nn.GELU())
        self.act_head = nn.Linear(192, len(ACTS))
        self.action_head = nn.Linear(192, len(ACTIONS))
        self.reference_head = nn.Linear(192, len(REFERENCE_STATES))
        self.polarity_head = nn.Linear(192, len(POLARITIES))
        self.modality_head = nn.Linear(192, len(MODALITIES))
        self.scope_head = nn.Linear(192, len(SCOPES))
        self.disposition_head = nn.Linear(192, len(DISPOSITIONS))
        self.slot_head = nn.Linear(192, len(SLOT_TYPES))
        self.span_score = nn.Linear(192, 1)

    def forward(self, tokens: dict[str, Tensor], span_masks: Tensor) -> dict[str, Tensor]:
        extras = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask", "offset_mapping"}}
        hidden = self.encoder(tokens["input_ids"], tokens["attention_mask"], **extras)
        mask = tokens["attention_mask"].float().unsqueeze(-1)
        hub = (hidden * mask).sum(1) / mask.sum(1).clamp_min(1.0)
        sentence = self.projection(hub)
        spans = torch.einsum("bst,bth->bsh", span_masks.float(), hidden)
        spans = spans / span_masks.sum(-1, keepdim=True).clamp_min(1.0)
        span_state = self.span_projection(spans)
        return {
            "sentence": sentence,
            "span": span_state,
            "act_logits": self.act_head(sentence),
            "action_logits": self.action_head(sentence),
            "reference_logits": self.reference_head(sentence),
            "polarity_logits": self.polarity_head(sentence),
            "modality_logits": self.modality_head(sentence),
            "scope_logits": self.scope_head(sentence),
            "disposition_logits": self.disposition_head(sentence),
            "slot_logits": self.slot_head(span_state),
            "span_logits": self.span_score(span_state).squeeze(-1),
        }

