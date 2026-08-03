from __future__ import annotations

from topology_g1.registry import relation_spec

from .dataset import RELATIONS
from .schemas import ReasoningCase, ReasoningPrediction


def valid_topology(case: ReasoningCase, prediction: ReasoningPrediction) -> bool:
    if prediction.disposition != "accept": return prediction.relation in {"ambiguous", "no_relation"}
    if prediction.relation == "no_relation": return True
    if prediction.relation not in RELATIONS: return False
    spec = relation_spec(prediction.relation)
    if len(case.arguments) != len(prediction.roles): return False
    supplied = set(prediction.roles)
    expected = {role.name for role in spec.roles}
    return supplied == expected and prediction.scope in {"global", "fictional", "hypothetical", "conversation_local", "temporally_bounded"}
