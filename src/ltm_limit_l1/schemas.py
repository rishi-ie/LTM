from __future__ import annotations

from dataclasses import dataclass

from ltm_inference_i31.schemas import MathematicalBody, TheoremProblem


@dataclass(frozen=True, slots=True)
class LimitCase:
    case_id: str
    panel: str
    certified_depth: int
    problem: TheoremProblem
    bodies: tuple[MathematicalBody, ...]
    branching_factor: int
    answerable: bool = True


@dataclass(frozen=True, slots=True)
class LimitObservation:
    case_id: str
    panel: str
    certified_depth: int
    disposition: str
    discovered_depth: int
    proof_valid: bool
    bodies_opened: int
    states_explored: int
    legal_proposals: int
    runtime_ms: float
    failure_boundary: str

