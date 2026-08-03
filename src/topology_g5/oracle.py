from __future__ import annotations

import numpy as np

from topology_g4.execute import execute
from topology_g4.schemas import TraversalRequest

from .frontier import _applicable
from .latent import equilibrium


def exhaustive(dataset: dict, row: dict) -> dict:
    value = row["request"]; request = TraversalRequest(**{**value, "starting_entity_ids": tuple(value["starting_entity_ids"]), "starting_predicate_ids": tuple(value["starting_predicate_ids"])})
    result = execute(request, dataset["factors"]); forces = []
    for item in dataset["influences"]:
        factor = dataset["store"].factors[item.factor_id]
        if request.target_literal in item.influence_keys and _applicable(factor, request): forces.append(np.array(item.force_vector, dtype=np.float64))
    state = equilibrium(request.request_id, forces)
    return {"request_id": request.request_id, "conclusion": result.conclusion, "state": tuple(state), "proof_factor_ids": result.proof_factor_ids, "provenance": result.decisive_provenance_ids}
