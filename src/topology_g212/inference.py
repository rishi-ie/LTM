"""Factorized kernel decoding with explicit role and direction checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch

from topology_g1.registry import REGISTRY

from .model import FactorizedCompiler
from .registry import DISPOSITIONS, MODALITIES, POLARITIES, RELATIONS, ROLES, SCOPES
from .schemas import (
    AtomicCase,
    CompleteFactorCandidate,
    ContextDecision,
    DirectionDecision,
    RoleAssignment,
)
from .training import make_batch


@dataclass(frozen=True, slots=True)
class KernelPrediction:
    source_id: str
    relations: tuple[str, ...]
    role_bindings: tuple[tuple[str, str, str], ...]
    polarity: str
    modality: str
    scope_id: str
    disposition: str
    candidates: tuple[CompleteFactorCandidate, ...]


def load_checkpoint(path: Path) -> FactorizedCompiler:
    model = FactorizedCompiler().eval()
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    return model


def _choose_roles(model: FactorizedCompiler, output: dict[str, torch.Tensor], row: int, relation: str, spans: tuple, span_count: int) -> tuple[tuple[RoleAssignment, ...], float]:
    relation_index = RELATIONS.index(relation)
    used: set[int] = set()
    assignments: list[RoleAssignment] = []
    confidence = 1.0
    for role in REGISTRY[relation].roles:
        role_index = ROLES.index(role.name)
        scores = output["role_scores"][row, relation_index, role_index, :span_count]
        probabilities = torch.softmax(scores, dim=-1)
        ordered = torch.argsort(probabilities, descending=True).tolist()
        chosen = next((index for index in ordered if index not in used), None)
        if chosen is None:
            return (), 0.0
        used.add(chosen)
        probability = float(probabilities[chosen])
        confidence *= probability
        assignments.append(RoleAssignment(relation, role.name, spans[chosen].span_id, probability))
    return tuple(assignments), confidence


@torch.no_grad()
def predict_case(model: FactorizedCompiler, case: AtomicCase, *, confidence_threshold: float = 0.05, direction_margin: float = 0.1) -> KernelPrediction:
    tokens, masks = make_batch(model, [case])
    output = model(tokens, masks)
    disposition_index = int(output["disposition_logits"][0].argmax())
    disposition = DISPOSITIONS[disposition_index]
    polarity = POLARITIES[int(output["polarity_logits"][0].argmax())]
    modality = MODALITIES[int(output["modality_logits"][0].argmax())]
    scope = SCOPES[int(output["scope_logits"][0].argmax())]
    if disposition != "accept":
        return KernelPrediction(case.source_id, (), (), polarity, modality, scope, disposition, ())
    operator_probabilities = torch.sigmoid(output["operator_logits"][0])
    ordered = torch.argsort(operator_probabilities, descending=True).tolist()[:6]
    top = ordered[:1]
    if len(ordered) > 1 and float(operator_probabilities[ordered[1]]) >= 0.8 * float(operator_probabilities[ordered[0]]):
        top.append(ordered[1])
    candidates: list[CompleteFactorCandidate] = []
    for relation_index in top:
        probability = float(operator_probabilities[relation_index])
        if probability < confidence_threshold:
            continue
        relation = RELATIONS[relation_index]
        assignments, role_confidence = _choose_roles(model, output, 0, relation, case.spans, len(case.spans))
        if not assignments:
            continue
        role_positions = {assignment.role_name: next(index for index, span in enumerate(case.spans) if span.span_id == assignment.span_id) for assignment in assignments}
        roles = tuple(role.name for role in REGISTRY[relation].roles)
        if len(roles) >= 2:
            first = role_positions[roles[0]]
            second = role_positions[roles[1]]
            forward = float(torch.sigmoid(output["pair_scores"][0, relation_index, first, second]))
            reverse = float(torch.sigmoid(output["pair_scores"][0, relation_index, second, first]))
            margin = abs(forward - reverse)
            accepted_order = (case.spans[first].span_id, case.spans[second].span_id) if forward >= reverse else (case.spans[second].span_id, case.spans[first].span_id)
            direction = DirectionDecision(relation, forward, reverse, margin, accepted_order if margin >= direction_margin else None)
        else:
            direction = DirectionDecision(relation, 1.0, 1.0, 1.0, tuple(assignment.span_id for assignment in assignments))
        context = ContextDecision(polarity, modality, scope, None, None, probability)
        if direction.accepted_order is None:
            continue
        if len(roles) >= 2 and direction.reverse_score > direction.forward_score:
            swapped = list(assignments)
            first_index = next(index for index, item in enumerate(swapped) if item.role_name == roles[0])
            second_index = next(index for index, item in enumerate(swapped) if item.role_name == roles[1])
            swapped[first_index], swapped[second_index] = (
                RoleAssignment(relation, roles[0], assignments[second_index].span_id, assignments[second_index].probability),
                RoleAssignment(relation, roles[1], assignments[first_index].span_id, assignments[first_index].probability),
            )
            assignments = tuple(swapped)
        candidates.append(CompleteFactorCandidate(relation, assignments, direction, context, probability * role_confidence, margin))
    candidates.sort(key=lambda candidate: candidate.probability, reverse=True)
    selected = tuple(candidates[:2])
    relations = tuple(candidate.relation_type for candidate in selected)
    bindings = tuple((candidate.relation_type, assignment.role_name, assignment.span_id) for candidate in selected for assignment in candidate.role_assignments)
    final_disposition = "accept" if selected else "clarification_required"
    return KernelPrediction(case.source_id, relations, bindings, polarity, modality, scope, final_disposition, selected)
