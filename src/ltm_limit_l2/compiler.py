"""L2 compiler, registry gate and conservative proof handoff."""

from __future__ import annotations

import hashlib

from ltm_inference_i3.formal import standard_axioms
from ltm_inference_i3.schemas import FormalExpression
from ltm_inference_i31.axioms import standard_axiom_bodies
from ltm_inference_i31.schemas import TheoremProblem

from .mumbrane import body_program, formal_hash
from .parser import ParseError, looks_open_ended, parse_proposition
from .schemas import (
    CompiledMathBody,
    CompiledMathQuestion,
    CompiledMathStatement,
    MathCompilationEvidence,
    MathLanguageSource,
    TypedFormalCandidate,
)


def source(text: str, *, source_id: str = "source:local", reality_key: str = "standard-v1", authority_kind: str = "user") -> MathLanguageSource:
    digest = hashlib.sha256(text.encode()).hexdigest()
    return MathLanguageSource(source_id, text, digest, "en", reality_key, authority_kind, digest)


def _key(value: FormalExpression, variables: dict[str, str] | None = None) -> tuple[object, ...]:
    variables = {} if variables is None else variables
    if value.op == "var":
        name = value.value or ""
        if name not in variables:
            variables[name] = f"v{len(variables)}"
        return ("var", variables[name])
    return (value.op, value.value, tuple(_key(item, variables) for item in value.args))


def _free_vars(value: FormalExpression) -> set[str]:
    return {item.value for _path, item in _walk(value) if item.op == "var" and item.value is not None}


def _walk(value: FormalExpression):
    yield (), value
    for index, child in enumerate(value.args):
        for path, item in _walk(child):
            yield (index,) + path, item


def _candidate(value: FormalExpression, probability: float = 1.0) -> TypedFormalCandidate:
    variables = tuple(sorted(_free_vars(value)))
    return TypedFormalCandidate(value, "scalar", variables, probability, probability, hashlib.sha256(repr(_key(value)).encode()).hexdigest())


def _evidence(src: MathLanguageSource, kind: str, candidates: tuple[TypedFormalCandidate, ...], checks: tuple[str, ...], failures: tuple[str, ...]) -> MathCompilationEvidence:
    payload = (src.source_id, kind, tuple(item.canonical_hash for item in candidates), checks, failures)
    return MathCompilationEvidence(src.source_id, kind, candidates, min((item.probability for item in candidates), default=0.0), min((item.margin for item in candidates), default=0.0), checks, failures, hashlib.sha256(repr(payload).encode()).hexdigest())


def _registry_match(left: FormalExpression, right: FormalExpression, reality_key: str):
    schemas = {schema.axiom_id: schema for schema in standard_axioms()}
    for body in standard_axiom_bodies():
        if body.reality_key != reality_key:
            continue
        axiom_id = body.body_id.rsplit(":", 1)[-1]
        schema = schemas.get(axiom_id)
        if _key(body.left) == _key(left) and _key(body.right) == _key(right):
            return axiom_id, "reversible" if schema and schema.reversible else "forward"
        if schema and schema.reversible and _key(body.right) == _key(left) and _key(body.left) == _key(right):
            return axiom_id, "reversible"
    return None


def _statement_parts(src: MathLanguageSource):
    if looks_open_ended(src.text):
        raise ParseError("goal_discovery_required")
    return parse_proposition(src.text)


def compile_statement(src: MathLanguageSource, *, confirmed: bool = False) -> CompiledMathStatement:
    try:
        left, right = _statement_parts(src)
    except ParseError as error:
        code = str(error)
        evidence = _evidence(src, "unsupported", (), (), (code,))
        return CompiledMathStatement(src, None, None, "clarification_required", "preview", evidence, (code,))
    candidate = _candidate(left)
    candidate_right = _candidate(right)
    match = _registry_match(left, right, src.reality_key)
    known = match is not None
    if not known and not confirmed:
        evidence = _evidence(src, "custom_rule", (candidate, candidate_right), ("AST_VALID",), ("CONFIRMATION_REQUIRED",))
        return CompiledMathStatement(src, None, None, "clarification_required", "pending_confirmation", evidence, ("CONFIRMATION_REQUIRED",))
    policy = match[1] if match else "reversible"
    body_hash = formal_hash(left, right, src.reality_key)
    body = CompiledMathBody(f"{src.reality_key}:body:{body_hash[:16]}", src.reality_key, left, right, policy, match[0] if match else None, src.source_hash, body_hash)
    program = body_program(body.body_id, left, right, src.reality_key, src.text)
    evidence = _evidence(src, "registered_rule" if known else "custom_rule", (candidate, candidate_right), ("AST_VALID", "REALITY_VALID", "REGISTRY_MATCH" if known else "CONFIRMED"), ())
    return CompiledMathStatement(src, body, program, "accept", "active", evidence, ())


def compile_question(src: MathLanguageSource) -> CompiledMathQuestion:
    if looks_open_ended(src.text):
        evidence = _evidence(src, "open_ended", (), (), ("GOAL_DISCOVERY_REQUIRED",))
        return CompiledMathQuestion(src, None, None, None, "clarification_required", evidence, ("GOAL_DISCOVERY_REQUIRED",))
    try:
        left, right = parse_proposition(src.text)
    except ParseError as error:
        code = str(error)
        evidence = _evidence(src, "question", (), (), (code,))
        return CompiledMathQuestion(src, None, None, None, "clarification_required", evidence, (code,))
    candidate = _candidate(left)
    goal = _candidate(right)
    evidence = _evidence(src, "explicit_target_question", (candidate, goal), ("SOURCE_VALID", "GOAL_VALID", "REALITY_VALID"), ())
    problem = TheoremProblem(src.source_id, src.reality_key, left, right, 64, 16)
    return CompiledMathQuestion(src, left, right, problem, "accept", evidence, ())
