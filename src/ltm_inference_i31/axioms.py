"""Signed standard axiom bodies available to a standard mathematical reality."""

from __future__ import annotations

from ltm_inference_i3.formal import standard_axioms

from .formal import body_hash
from .schemas import MathematicalBody


def standard_axiom_bodies() -> tuple[MathematicalBody, ...]:
    result = []
    for index, axiom in enumerate(standard_axioms()):
        body = MathematicalBody(f"standard-v1:axiom:{axiom.axiom_id}", "standard-v1", axiom.left, axiom.right, "", index)
        result.append(MathematicalBody(body.body_id, body.reality_key, body.left, body.right, body_hash(body), body.vector_index))
    return tuple(result)
