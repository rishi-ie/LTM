"""Construction and canonical hashing of typed topology factors."""

from __future__ import annotations

import hashlib
import json

import torch

from topology_g1.codec import digest
from topology_g1.registry import REGISTRY

from .schemas import ContentAtomOccurrence, ContextCoordinates, RolePlacement, TopologyFactor


def _tuple(value: torch.Tensor) -> tuple[float, ...]:
    return tuple(float(item) for item in value.detach().cpu().float())


def make_factor(
    *,
    source_id: str,
    atoms: tuple[ContentAtomOccurrence, ...],
    relation_type: str,
    role_bindings: tuple[tuple[str, tuple[str, ...]], ...],
    confidence: float,
    polarity: str,
    modality: str,
    scope_id: str,
    operator_vector: torch.Tensor,
    role_vectors: torch.Tensor,
    binding_vectors: torch.Tensor,
    role_scores: tuple[float, ...],
    context_vector: torch.Tensor,
) -> TopologyFactor:
    atom_map = {atom.atom_id: atom for atom in atoms}
    placements: list[RolePlacement] = []
    incidence: list[tuple[str, str]] = []
    index = 0
    for role, atom_ids in role_bindings:
        for atom_id in atom_ids:
            placements.append(
                RolePlacement(
                    relation_type, role, atom_id, role_scores[index], _tuple(role_vectors[index])
                )
            )
            incidence.append((role, atom_id))
            index += 1
    context = ContextCoordinates(
        polarity, modality, scope_id, None, None, 1.0, _tuple(context_vector)
    )
    specification = REGISTRY[relation_type]
    payload = {
        "source": source_id,
        "relation": relation_type,
        "incidence": incidence,
        "scope": scope_id,
        "polarity": polarity,
        "modality": modality,
        "provenance": tuple(
            sorted({value for atom in atom_map.values() for value in atom.provenance_ids})
        ),
        "operator": [round(value, 7) for value in _tuple(operator_vector)],
        "binding": [[round(value, 7) for value in _tuple(vector)] for vector in binding_vectors],
    }
    factor_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return TopologyFactor(
        f"factor:{factor_hash[:24]}",
        relation_type,
        _tuple(operator_vector),
        tuple(placements),
        tuple(incidence),
        tuple(_tuple(vector) for vector in binding_vectors),
        context,
        specification.hard_or_soft == "hard",
        specification.field_operator,
        confidence,
        payload["provenance"],
        factor_hash,
    )


def channel_hashes(factors: tuple[TopologyFactor, ...]) -> tuple[str, str, str, str, str, str]:
    content = digest(
        tuple(sorted((role, atom) for factor in factors for role, atom in factor.sparse_incidence))
    )
    operator = digest(
        tuple(sorted((factor.relation_type, factor.operator_vector) for factor in factors))
    )
    roles = digest(
        tuple(
            sorted(
                (placement.role, placement.atom_id)
                for factor in factors
                for placement in factor.role_placements
            )
        )
    )
    context = digest(
        tuple(
            sorted(
                (factor.context.polarity, factor.context.modality, factor.context.scope_id)
                for factor in factors
            )
        )
    )
    binding = digest(tuple(sorted(factor.factor_hash for factor in factors)))
    field = digest((content, operator, roles, context, binding))
    return content, operator, roles, context, binding, field
