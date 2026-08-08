"""Typed recurrent sentence and link reasoning over raw MiniLM token states.

The module intentionally scores only legal G1 relation/role candidates.  It has no independent
direction or role classifier capable of emitting an invalid topology relation.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from .registry import NODE_KINDS, RELATION_LABELS

ROLE_LABELS = tuple(sorted({role.name for spec in __import__("topology_g1.registry", fromlist=["REGISTRY"]).REGISTRY.values() for role in spec.roles}))
SCOPE_LABELS = ("global", "conversation_local", "fictional", "hypothetical", "temporally_bounded")
DISPOSITION_LABELS = ("accept", "clarification_required", "quarantine")


@dataclass(frozen=True, slots=True)
class CandidateBatch:
    relation_ids: Tensor  # (candidates,)
    role_ids: Tensor  # (candidates, max_roles)
    span_ids: Tensor  # (candidates, max_bound_spans), -1 padded
    mask: Tensor  # (candidates,)


class TypedRecurrentHRM(nn.Module):
    """Four-cycle typed GRU message passing among spans, relations, and sentence hub."""

    def __init__(self, encoder_hidden: int = 384, state_dim: int = 128, cycles: int = 4, recurrent: bool = True) -> None:
        super().__init__()
        self.state_dim = state_dim
        self.cycles = cycles
        self.recurrent = recurrent
        self.token_projection = nn.Linear(encoder_hidden, state_dim)
        self.start_heads = nn.Linear(state_dim, len(NODE_KINDS) + 1)
        self.end_heads = nn.Linear(state_dim, len(NODE_KINDS) + 1)
        self.node_kind = nn.Embedding(len(NODE_KINDS) + 1, state_dim)
        self.relation = nn.Embedding(len(RELATION_LABELS), state_dim)
        self.role = nn.Embedding(len(ROLE_LABELS) + 1, state_dim)
        self.scope = nn.Embedding(len(SCOPE_LABELS), state_dim)
        self.disposition = nn.Linear(state_dim, len(DISPOSITION_LABELS))
        self.scope_head = nn.Linear(state_dim, len(SCOPE_LABELS))
        self.time_head = nn.Linear(state_dim, 2)
        self.link_type_head = nn.Linear(state_dim, len(RELATION_LABELS))
        self.relation_gru = nn.GRUCell(state_dim, state_dim)
        self.span_gru = nn.GRUCell(state_dim, state_dim)
        self.hub_gru = nn.GRUCell(state_dim, state_dim)
        self.relation_message = nn.Linear(state_dim, state_dim)
        self.span_context = nn.Linear(state_dim * 2, state_dim)
        self.candidate_score = nn.Sequential(nn.Linear(state_dim * 3, state_dim), nn.GELU(), nn.Linear(state_dim, 1))
        self.link_score = nn.Sequential(nn.Linear(state_dim * 3, state_dim), nn.GELU(), nn.Linear(state_dim, 1))

    @staticmethod
    def masked_mean(values: Tensor, mask: Tensor) -> Tensor:
        weights = mask.unsqueeze(-1).to(values.dtype)
        return (values * weights).sum(1) / weights.sum(1).clamp_min(1.0)

    def token_states(self, token_states: Tensor, attention_mask: Tensor) -> tuple[Tensor, Tensor, dict[str, Tensor]]:
        states = self.token_projection(token_states)
        hub = self.masked_mean(states, attention_mask)
        return states, hub, {
            "start": self.start_heads(states),
            "end": self.end_heads(states),
            "scope": self.scope_head(hub),
            "time": self.time_head(hub),
            "disposition": self.disposition(hub),
            "link_type": self.link_type_head(hub),
        }

    def span_states(self, states: Tensor, span_starts: Tensor, span_ends: Tensor, kinds: Tensor) -> Tensor:
        """Endpoint-aware representations for a padded collection of proposed spans."""
        _batch, tokens, _ = states.shape
        start = span_starts.clamp(0, tokens - 1)
        end = (span_ends - 1).clamp(0, tokens - 1)
        gather_start = states.gather(1, start.unsqueeze(-1).expand(-1, -1, self.state_dim))
        gather_end = states.gather(1, end.unsqueeze(-1).expand(-1, -1, self.state_dim))
        return self.span_context(torch.cat((gather_start, gather_end), -1)) + self.node_kind(kinds)

    def score_candidates(self, spans: Tensor, hub: Tensor, candidates: CandidateBatch) -> Tensor:
        """Score one sentence's registry-legal candidates with typed recurrent messages."""
        if candidates.relation_ids.numel() == 0:
            return torch.empty(0, device=hub.device)
        local_spans = spans[0]
        relation_state = self.relation(candidates.relation_ids)
        role_state = self.role(candidates.role_ids).mean(1)
        valid_ids = candidates.span_ids.clamp_min(0)
        bound = local_spans[valid_ids]
        span_mask = (candidates.span_ids >= 0).unsqueeze(-1)
        bound_mean = (bound * span_mask).sum(1) / span_mask.sum(1).clamp_min(1)
        hub_state = hub.expand_as(relation_state)
        relation_state = relation_state + role_state + bound_mean
        if self.recurrent:
            for _ in range(self.cycles):
                relation_state = self.relation_gru(bound_mean + hub_state, relation_state)
                message = self.relation_message(relation_state)
                # Candidate-specific span updates are folded back into its bound representation.
                bound_mean = self.span_gru(message, bound_mean)
                hub_state = self.hub_gru((relation_state + bound_mean) * 0.5, hub_state)
        score_features = torch.cat((relation_state, bound_mean, hub_state), -1)
        return self.candidate_score(score_features).squeeze(-1).masked_fill(~candidates.mask, float("-inf"))

    def score_links(self, source_state: Tensor, target_states: Tensor, type_ids: Tensor) -> Tensor:
        """The same typed geometry for sparse context candidates; target count is bounded at 16."""
        relation = self.relation(type_ids)
        source = source_state.expand_as(target_states)
        return self.link_score(torch.cat((source, target_states, relation), -1)).squeeze(-1)
