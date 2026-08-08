"""One-pass atom-slot grounding and role-aware HRM reconciliation."""

from __future__ import annotations

import torch
from torch import Tensor, nn

from .registry import NODE_KINDS, RELATION_LABELS, ROLE_LABELS


def _normalized(values: Tensor) -> Tensor:
    return nn.functional.normalize(values, dim=-1, eps=1e-12)


class AtomSlotGrounder(nn.Module):
    """Derive multiple atom vectors from one contextual token-state matrix."""

    def __init__(
        self,
        hidden_size: int = 384,
        working_size: int = 128,
        slots: int = 12,
        cycles: int = 3,
    ) -> None:
        super().__init__()
        self.slots = slots
        self.cycles = cycles
        self.token_projection = nn.Linear(hidden_size, working_size)
        self.hub_projection = nn.Linear(hidden_size, working_size)
        self.slot_queries = nn.Parameter(torch.randn(slots, working_size) * 0.02)
        self.slot_gru = nn.GRUCell(working_size, working_size)
        self.type_prototypes = nn.Parameter(torch.randn(len(NODE_KINDS), working_size) * 0.02)
        self.start_query = nn.Linear(working_size, working_size, bias=False)
        self.end_query = nn.Linear(working_size, working_size, bias=False)
        self.active_head = nn.Linear(working_size, 1)
        self.semantic_projection = nn.Linear(working_size, hidden_size)

    def forward(self, token_states: Tensor, attention_mask: Tensor) -> dict[str, Tensor]:
        if token_states.ndim != 3 or attention_mask.shape != token_states.shape[:2]:
            raise ValueError("token states and attention mask have incompatible shapes")
        tokens = self.token_projection(token_states)
        mask = attention_mask.bool()
        hub = (token_states * attention_mask.unsqueeze(-1)).sum(1) / attention_mask.sum(1, keepdim=True).clamp_min(1)
        hub = self.hub_projection(hub)
        states = self.slot_queries.unsqueeze(0).expand(token_states.shape[0], -1, -1) + hub.unsqueeze(1)
        attention = None
        for _ in range(self.cycles):
            scores = torch.einsum("bkd,btd->bkt", states, tokens).masked_fill(~mask.unsqueeze(1), -1e9)
            attention = torch.softmax(scores, dim=-1)
            context = torch.einsum("bkt,btd->bkd", attention, tokens)
            states = self.slot_gru(context.reshape(-1, states.shape[-1]), states.reshape(-1, states.shape[-1])).reshape_as(states)
        assert attention is not None
        start = torch.einsum("bkd,btd->bkt", self.start_query(states), tokens).masked_fill(~mask.unsqueeze(1), -1e9)
        end = torch.einsum("bkd,btd->bkt", self.end_query(states), tokens).masked_fill(~mask.unsqueeze(1), -1e9)
        type_logits = torch.einsum("bkd,nd->bkn", _normalized(states), _normalized(self.type_prototypes))
        return {
            "slot_states": states,
            "attention": attention,
            "active_logits": self.active_head(states).squeeze(-1),
            "type_logits": type_logits,
            "start_logits": start,
            "end_logits": end,
            "semantic_vectors": _normalized(self.semantic_projection(states)),
            "sentence_hub": hub,
        }


class RoleAwareHRM(nn.Module):
    """Reconcile atom and legal operator candidates without collapsing roles."""

    def __init__(self, working_size: int = 128, cycles: int = 4) -> None:
        super().__init__()
        self.cycles = cycles
        self.relation_embedding = nn.Embedding(len(RELATION_LABELS), working_size)
        self.role_embedding = nn.Embedding(len(ROLE_LABELS), working_size)
        self.relation_gru = nn.GRUCell(working_size, working_size)
        self.atom_gru = nn.GRUCell(working_size, working_size)
        self.hub_gru = nn.GRUCell(working_size, working_size)
        self.message = nn.Linear(working_size, working_size)
        self.role_message = nn.Linear(working_size, working_size, bias=False)
        self.scorer = nn.Sequential(
            nn.Linear(working_size * 3, working_size),
            nn.GELU(),
            nn.Linear(working_size, 1),
        )

    def forward(
        self,
        atom_states: Tensor,
        sentence_hub: Tensor,
        relation_ids: Tensor,
        bound_role_ids: Tensor,
        bound_atom_ids: Tensor,
    ) -> tuple[Tensor, Tensor, Tensor]:
        """Score one bounded candidate set per sentence.

        Shapes are ``[atoms, 128]``, ``[1, 128]``, ``[relations]``,
        ``[relations, bound arguments]`` twice: atom IDs and role IDs.
        ``-1`` bound IDs are padding and receive no message.
        """
        if atom_states.ndim != 2 or sentence_hub.shape != (1, atom_states.shape[-1]):
            raise ValueError("invalid atom or sentence hub shape")
        if bound_role_ids.shape != bound_atom_ids.shape:
            raise ValueError("every bound atom requires a role ID")
        if relation_ids.numel() == 0:
            return relation_ids.new_empty((0,), dtype=torch.float32), atom_states, sentence_hub
        atoms = atom_states
        relations = self.relation_embedding(relation_ids)
        hub = sentence_hub
        for _ in range(self.cycles):
            bound = atoms[bound_atom_ids.clamp_min(0)]
            active = (bound_atom_ids >= 0).unsqueeze(-1)
            roles = self.role_embedding(bound_role_ids.clamp_min(0))
            aggregate = ((bound + roles) * active).sum(1) / active.sum(1).clamp_min(1)
            relations = self.relation_gru(aggregate + hub.expand_as(aggregate), relations)
            messages = self.message(relations)
            # Aggregate all relation-to-atom messages before one GRU update.
            # This keeps every named role distinct but avoids Python-level
            # relation/argument loops during CPU training.
            atom_messages = torch.zeros_like(atoms)
            atom_counts = torch.zeros((atoms.shape[0], 1), device=atoms.device, dtype=atoms.dtype)
            flat_ids = bound_atom_ids.reshape(-1)
            flat_active = flat_ids >= 0
            flat_messages = (
                messages.unsqueeze(1).expand(-1, bound_atom_ids.shape[1], -1)
                + self.role_message(roles)
            ).reshape(-1, atoms.shape[-1])
            atom_messages.index_add_(0, flat_ids[flat_active], flat_messages[flat_active])
            atom_counts.index_add_(0, flat_ids[flat_active], torch.ones((int(flat_active.sum()), 1), device=atoms.device, dtype=atoms.dtype))
            update_mask = atom_counts.squeeze(-1) > 0
            proposed = self.atom_gru(atom_messages / atom_counts.clamp_min(1), atoms)
            atoms = torch.where(update_mask.unsqueeze(-1), proposed, atoms)
            hub = self.hub_gru((relations + aggregate).mean(0, keepdim=True), hub)
        bound = atoms[bound_atom_ids.clamp_min(0)]
        active = (bound_atom_ids >= 0).unsqueeze(-1)
        roles = self.role_embedding(bound_role_ids.clamp_min(0))
        aggregate = ((bound + roles) * active).sum(1) / active.sum(1).clamp_min(1)
        score = self.scorer(torch.cat((relations, aggregate, hub.expand_as(relations)), dim=-1)).squeeze(-1)
        return score, atoms, hub
