"""Exact controlled-language compiler and schema-instance gate."""

from __future__ import annotations

import hashlib

from ltm_inference_i3.formal import expression_hash, instantiate, match, standard_axioms
from ltm_inference_i3.schemas import FormalExpression
from ltm_inference_i31.schemas import TheoremProblem
from ltm_limit_l2.mumbrane import body_program

from .parser import ParseError, looks_open_ended, parse_proposition
from .schemas import L3Body, L3Question, L3Source


def source(text: str, *, source_id: str = "source:local", reality_key: str = "standard-v1") -> L3Source:
    digest = hashlib.sha256(text.encode()).hexdigest()
    return L3Source(source_id, text, digest, reality_key, digest)


def _body_hash(left: FormalExpression, right: FormalExpression, reality_key: str) -> str:
    return hashlib.sha256(repr((left, right, reality_key)).encode()).hexdigest()


def _schema_match(left: FormalExpression, right: FormalExpression, reality_key: str) -> tuple[str, str] | None:
    if reality_key != "standard-v1":
        return None
    for schema in standard_axioms():
        bindings = match(schema.left, left)
        if bindings is not None and instantiate(schema.right, bindings) == right:
            return schema.axiom_id, "forward"
        if schema.reversible:
            reverse_bindings = match(schema.right, left)
            if reverse_bindings is not None and instantiate(schema.left, reverse_bindings) == right:
                return schema.axiom_id, "reverse"
    return None


def compile_body(src: L3Source) -> L3Body | None:
    try:
        left, right = parse_proposition(src.text)
    except ParseError:
        return None
    matched = _schema_match(left, right, src.reality_key)
    if matched is None:
        return None
    body_hash = _body_hash(left, right, src.reality_key)
    body_id = f"{src.reality_key}:l3-body:{body_hash[:20]}"
    return L3Body(
        body_id, src.reality_key, left, right, matched[0], matched[1], src.text, src.source_hash,
        body_hash, body_program(body_id, left, right, src.reality_key, src.text),
    )


def validate_body_source(src: L3Source) -> tuple[FormalExpression, FormalExpression, str] | None:
    """Validate controlled source without constructing a new Mumbrane program.

    Batch compiler evaluation needs to measure parsing and registered-schema
    recovery.  Rebuilding the already-validated sidecar program for every
    archived row would only duplicate a serialization cost.
    """
    try:
        left, right = parse_proposition(src.text)
    except ParseError:
        return None
    matched = _schema_match(left, right, src.reality_key)
    return (left, right, matched[0]) if matched is not None else None


def compile_question(src: L3Source) -> L3Question:
    if looks_open_ended(src.text):
        return L3Question(src, None, None, None, "clarification_required", ("GOAL_DISCOVERY_REQUIRED",))
    try:
        left, right = parse_proposition(src.text)
    except ParseError as error:
        return L3Question(src, None, None, None, "clarification_required", (str(error),))
    problem = TheoremProblem(src.source_id, src.reality_key, left, right, 64, 64)
    return L3Question(src, left, right, problem, "accept", ())


def expression_digest(value: FormalExpression) -> str:
    return expression_hash(value)
