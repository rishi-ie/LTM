"""Trainable one-pass sentence compiler for G2.4.

The decoder is deliberately constrained: it may only emit G1 registry relations
over grounded atom slots.  It contains no surface-template parser.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import Tensor, nn

from .encoder import OnePassMiniLM
from .model import AtomSlotGrounder, RoleAwareHRM
from .registry import RELATION_LABELS, ROLE_LABELS

DISPOSITIONS = ("accept", "clarification_required", "quarantine")


@dataclass(frozen=True, slots=True)
class DecodedSlots:
    active: tuple[int, ...]
    kinds: tuple[int, ...]
    starts: tuple[int, ...]
    ends: tuple[int, ...]
    relation: int
    disposition: int
    confidence: float


class AtomTopologyCompiler(nn.Module):
    """MiniLM -> atom slots -> legal role-aware relation candidates."""

    def __init__(self, *, encoder_trainable: bool) -> None:
        super().__init__()
        self.encoder = OnePassMiniLM(trainable=encoder_trainable)
        self.grounder = AtomSlotGrounder(hidden_size=self.encoder.hidden_size)
        self.hrm = RoleAwareHRM()
        self.disposition_head = nn.Linear(128, len(DISPOSITIONS))

    def _candidate_tensors(self, slots: int, device: torch.device) -> tuple[Tensor, Tensor, Tensor]:
        """One legal candidate per registered relation over ordered atom slots."""
        relations: list[int] = []
        roles: list[list[int]] = []
        atoms: list[list[int]] = []
        width = 3
        for index, relation in enumerate(RELATION_LABELS):
            spec_roles = __import__("topology_g1.registry", fromlist=["REGISTRY"]).REGISTRY[relation].roles
            bound_roles: list[int] = []
            bound_atoms: list[int] = []
            slot = 0
            for spec in spec_roles:
                for _ in range(spec.minimum):
                    bound_roles.append(ROLE_LABELS.index(spec.name))
                    bound_atoms.append(slot if slot < slots else -1)
                    slot += 1
            relations.append(index)
            roles.append((bound_roles + [-1] * width)[:width])
            atoms.append((bound_atoms + [-1] * width)[:width])
        return (
            torch.tensor(relations, device=device),
            torch.tensor(roles, device=device),
            torch.tensor(atoms, device=device),
        )

    def forward(self, tokens: dict[str, Tensor]) -> dict[str, Tensor]:
        extras = {key: value for key, value in tokens.items() if key not in {"input_ids", "attention_mask", "offset_mapping"}}
        states = self.encoder(tokens["input_ids"], tokens["attention_mask"], **extras)
        grounded = self.grounder(states, tokens["attention_mask"])
        relation_ids, role_ids, atom_ids = self._candidate_tensors(self.grounder.slots, states.device)
        relation_scores: list[Tensor] = []
        hubs: list[Tensor] = []
        for batch_index in range(states.shape[0]):
            score, _atoms, hub = self.hrm(
                grounded["slot_states"][batch_index],
                grounded["sentence_hub"][batch_index : batch_index + 1],
                relation_ids,
                role_ids,
                atom_ids,
            )
            relation_scores.append(score)
            hubs.append(hub[0])
        relation_logits = torch.stack(relation_scores)
        hub = torch.stack(hubs)
        return {**grounded, "relation_logits": relation_logits, "disposition_logits": self.disposition_head(hub)}

    @torch.no_grad()
    def decode(self, tokens: dict[str, Tensor]) -> tuple[DecodedSlots, ...]:
        output = self(tokens)
        result: list[DecodedSlots] = []
        for index in range(tokens["input_ids"].shape[0]):
            active = torch.sigmoid(output["active_logits"][index]) >= 0.5
            start = output["start_logits"][index].argmax(-1)
            end = output["end_logits"][index].argmax(-1)
            start, end = torch.minimum(start, end), torch.maximum(start, end)
            confidence = float(torch.softmax(output["relation_logits"][index], -1).max())
            result.append(
                DecodedSlots(
                    tuple(int(value) for value in active),
                    tuple(int(value) for value in output["type_logits"][index].argmax(-1)),
                    tuple(int(value) for value in start),
                    tuple(int(value) for value in end),
                    int(output["relation_logits"][index].argmax()),
                    int(output["disposition_logits"][index].argmax()),
                    confidence,
                )
            )
        return tuple(result)
