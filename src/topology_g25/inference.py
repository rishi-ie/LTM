"""Gold-atom kernel inference without access to relation or role labels."""

from __future__ import annotations

from dataclasses import replace

import torch

from topology_g1.registry import REGISTRY

from .assembly import assemble_handoff
from .field import make_factor
from .model import TypedAtomKernel
from .registry import DISPOSITIONS, MODALITIES, POLARITIES, RELATIONS, ROLES, SCOPES
from .schemas import ContentAtomOccurrence, KernelPrediction, KernelRuntimeCase
from .training import make_batch


def _bindings(
    model: TypedAtomKernel,
    output: dict[str, torch.Tensor],
    row: int,
    atoms: tuple[ContentAtomOccurrence, ...],
    relation: str,
    atom_mask: torch.Tensor,
) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], tuple[float, ...], torch.Tensor, torch.Tensor]:
    specification = REGISTRY[relation]
    relation_id = torch.tensor([RELATIONS.index(relation)])
    role_ids = torch.tensor([[ROLES.index(role.name) for role in specification.roles]])
    scores = model.role_logits(
        output["sentence"][row : row + 1],
        output["content"][row : row + 1],
        relation_id,
        role_ids,
        atom_mask[row : row + 1],
        output["operator_state"][row : row + 1],
    )[0]
    used: set[int] = set()
    bindings: list[tuple[str, tuple[str, ...]]] = []
    flat_roles: list[int] = []
    flat_atoms: list[int] = []
    flat_scores: list[float] = []
    for role_index, role in enumerate(specification.roles):
        ordered = torch.argsort(scores[role_index], descending=True).tolist()
        selected: list[int] = []
        for atom_index in ordered:
            if atom_index < len(atoms) and atom_index not in used:
                selected.append(atom_index)
                used.add(atom_index)
            if len(selected) == role.minimum:
                break
        if len(selected) != role.minimum:
            return (), (), torch.empty((0, 64)), torch.empty((0, 256))
        bindings.append((role.name, tuple(atoms[atom_index].atom_id for atom_index in selected)))
        for atom_index in selected:
            flat_roles.append(ROLES.index(role.name))
            flat_atoms.append(atom_index)
            flat_scores.append(float(scores[role_index, atom_index]))
    roles = torch.tensor(flat_roles)
    selected_atoms = torch.tensor(flat_atoms)
    role_vectors = model.role_vectors[roles]
    relation_ids = torch.full((len(flat_atoms),), RELATIONS.index(relation), dtype=torch.long)
    repeated_content = output["content"][row : row + 1].expand(len(flat_atoms), -1, -1)
    binding = model.binding_vectors(repeated_content, relation_ids, roles, selected_atoms)
    return tuple(bindings), tuple(flat_scores), role_vectors, binding


@torch.no_grad()
def infer_kernel(
    model: TypedAtomKernel, examples: tuple[KernelRuntimeCase, ...], *, batch_size: int = 16
) -> tuple[KernelPrediction, ...]:
    predictions: list[KernelPrediction] = []
    model.eval()
    for start in range(0, len(examples), batch_size):
        batch = list(examples[start : start + batch_size])
        tokens, masks, kinds, atom_mask = make_batch(model, batch)
        output = model(tokens, masks, kinds)
        for row, example in enumerate(batch):
            disposition = DISPOSITIONS[int(output["disposition_logits"][row].argmax())]
            polarity = POLARITIES[int(output["polarity_logits"][row].argmax())]
            modality = MODALITIES[int(output["modality_logits"][row].argmax())]
            scope = SCOPES[int(output["scope_logits"][row].argmax())]
            relation = (
                RELATIONS[int(output["operator_logits"][row].argmax())]
                if disposition == "accept"
                else None
            )
            confidence = float(torch.softmax(output["operator_logits"][row], dim=-1).max())
            bindings: tuple[tuple[str, tuple[str, ...]], ...] = ()
            factor = None
            if relation is not None:
                bindings, scores, role_vectors, binding_vectors = _bindings(
                    model, output, row, example.atoms, relation, atom_mask
                )
                if bindings:
                    occurrences = tuple(
                        replace(
                            atom,
                            occurrence_vector=tuple(
                                float(value) for value in output["content_384"][row, index]
                            ),
                        )
                        for index, atom in enumerate(example.atoms)
                    )
                    factor = make_factor(
                        source_id=example.source.source_id,
                        atoms=occurrences,
                        relation_type=relation,
                        role_bindings=bindings,
                        confidence=confidence,
                        polarity=polarity,
                        modality=modality,
                        scope_id=scope,
                        operator_vector=model.operator_prototypes[RELATIONS.index(relation)].mean(
                            0
                        ),
                        role_vectors=role_vectors,
                        binding_vectors=binding_vectors,
                        role_scores=scores,
                        context_vector=output["context_vector"][row],
                    )
                    # G1 validity is a final safety boundary; no partial factor is emitted.
                    if assemble_handoff(example.source, occurrences, (factor,)) is None:
                        factor = None
                        relation = None
                        bindings = ()
                        disposition = "quarantine"
            predictions.append(
                KernelPrediction(
                    example.source.source_id,
                    relation,
                    bindings,
                    polarity,
                    modality,
                    scope,
                    disposition,
                    confidence,
                    factor,
                )
            )
    return tuple(predictions)
