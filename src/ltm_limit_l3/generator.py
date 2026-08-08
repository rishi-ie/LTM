"""Deterministic 45-hop corpus and question generators."""

from __future__ import annotations

import hashlib
import random

from ltm_inference_i3.formal import (
    e,
    enumerate_applications,
    expression_hash,
    expression_size,
    standard_axioms,
)
from ltm_inference_i3.schemas import FormalExpression

from .compiler import _schema_match, compile_body, compile_question, source
from .schemas import L3Body, L3LockedSuite, L3Problem, ShortestProofCertificate


def _text(value: FormalExpression) -> str:
    if value.op in {"atom", "int", "var"}:
        return value.value or "x"
    if value.op == "neg":
        result = f"(-{_text(value.args[0])})"
    elif value.op in {"add", "mul"}:
        symbol = "+" if value.op == "add" else "*"
        result = f"({_text(value.args[0])} {symbol} {_text(value.args[1])})"
    else:
        raise ValueError(f"unsupported generator operator: {value.op}")
    return result


def _body(case_id: str, index: int, left: FormalExpression, right: FormalExpression) -> L3Body:
    text = f"{_text(left)} = {_text(right)}"
    compiled = compile_body(source(text, source_id=f"{case_id}:body:{index}"))
    if compiled is None:
        raise ValueError("generated transition did not match the registry")
    return compiled


def grounded_case(depth: int = 45, serial: int = 0) -> L3Problem:
    case_id = f"grounded:{serial:06d}"
    current = FormalExpression("atom", value=f"g{serial}")
    bodies: list[L3Body] = []
    for index in range(depth):
        following = e("add", current, FormalExpression("int", value="0"))
        bodies.append(_body(case_id, index, current, following))
        current = following
    question = compile_question(source(f"prove {_text(FormalExpression('atom', value=f'g{serial}'))} = {_text(current)}", source_id=f"{case_id}:question"))
    if question.theorem_problem is None:
        raise ValueError("generated question did not compile")
    certificate_payload = (case_id, question.source.source_hash, expression_hash(current), depth, tuple(item.body_id for item in bodies))
    certificate_hash = hashlib.sha256(repr(certificate_payload).encode()).hexdigest()
    certificate = ShortestProofCertificate(case_id, question.source.source_hash, expression_hash(current), depth, tuple(item.body_id for item in bodies), certificate_hash)
    return L3Problem(case_id, "grounded", question, depth, certificate, tuple(item.body_id for item in bodies), tuple(bodies))


def mixed_case(depth: int = 45, serial: int = 0) -> L3Problem:
    case_id = f"mixed:{serial:06d}"
    rng = random.Random(991000 + serial)
    current = e("add", e("mul", FormalExpression("atom", value=f"a{serial}"), FormalExpression("atom", value=f"b{serial}")), FormalExpression("atom", value=f"c{serial}"))
    states = [current]
    bodies: list[L3Body] = []
    used: list[str] = []
    def supported(value: FormalExpression) -> bool:
        return value.op in {"atom", "int", "var", "add", "mul", "neg"} and all(supported(item) for item in value.args)

    def ground(value: FormalExpression) -> bool:
        return value.op != "var" and all(ground(item) for item in value.args)

    schemas = tuple(item for item in standard_axioms() if supported(item.left) and supported(item.right))
    for index in range(depth):
        options: list[tuple[str, bool, tuple[int, ...], FormalExpression]] = []
        for schema in schemas:
            for path, reverse, after in enumerate_applications(current, schema):
                matched = _schema_match(current, after, "standard-v1")
                if ground(after) and matched is not None and matched[0] == schema.axiom_id and expression_size(after) <= 120 and expression_hash(after) not in {expression_hash(item) for item in states}:
                    options.append((schema.axiom_id, reverse, path, after))
        if not options:
            raise ValueError("mixed generator exhausted legal transitions")
        unused = [item for item in options if item[0] not in used]
        selected = rng.choice(unused if len(used) < 8 and unused else options)
        used.append(selected[0])
        following = selected[3]
        # Store the exact concrete transition; the compiler independently
        # recovers the schema and direction from the two expressions.
        bodies.append(_body(case_id, index, current, following))
        current = following
        states.append(current)
    if len(set(used)) < 8:
        # Some random walks collapse into a narrow algebraic subspace.  Retry
        # with a disjoint deterministic filler namespace rather than allowing
        # an under-diverse path into a locked mixed-axiom panel.
        if serial >= 10_000_000:
            raise ValueError("mixed generator could not cover eight schemas")
        return mixed_case(depth, serial + 1_000_000)
    question = compile_question(source(f"prove {_text(states[0])} = {_text(current)}", source_id=f"{case_id}:question"))
    if question.theorem_problem is None:
        raise ValueError("generated mixed question did not compile")
    body_ids = tuple(item.body_id for item in bodies)
    certificate_payload = (case_id, question.source.source_hash, expression_hash(current), depth, body_ids, tuple(sorted(set(used))))
    certificate_hash = hashlib.sha256(repr(certificate_payload).encode()).hexdigest()
    certificate = ShortestProofCertificate(case_id, question.source.source_hash, expression_hash(current), depth, body_ids, certificate_hash)
    return L3Problem(case_id, "mixed", question, depth, certificate, body_ids, tuple(bodies))


def unknown_case(serial: int = 0) -> L3Problem:
    """A source-backed request whose decisive transition is deliberately absent."""
    case_id = f"unknown:{serial:06d}"
    left = FormalExpression("atom", value=f"u{serial}_start")
    right = e("add", left, FormalExpression("int", value="0"))
    question = compile_question(source(f"prove {_text(left)} = {_text(right)}", source_id=f"{case_id}:question"))
    if question.theorem_problem is None:
        raise ValueError("generated unknown question did not compile")
    certificate = ShortestProofCertificate(case_id, question.source.source_hash, expression_hash(right), 0, (), hashlib.sha256(case_id.encode()).hexdigest())
    return L3Problem(case_id, "safety", question, 0, certificate, (), ())


def _noise_body(index: int) -> L3Body:
    """A legal, isolated body used to make the locked field genuinely large."""
    atom = FormalExpression("atom", value=f"noise_{index:06d}")
    return _body("locked:noise", index, e("add", atom, FormalExpression("int", value="0")), atom)


def locked_suite(*, grounded_cases: int = 256, mixed_cases: int = 128, safety_cases: int = 128, field_size: int = 50_000, depth: int = 45) -> L3LockedSuite:
    """Build the complete deterministic L3 corpus once before freezing.

    Every answerable problem receives its own isolated 45-body chain.  The
    remaining legal source bodies are intentionally unrelated distractors; no
    public identifier includes a route, answer, or proof-depth token.
    """
    grounded = tuple(grounded_case(depth, index) for index in range(grounded_cases))
    mixed = tuple(mixed_case(depth, index) for index in range(mixed_cases))
    safety = tuple(unknown_case(index) for index in range(safety_cases))
    relevant = {body.body_id: body for case in grounded + mixed for body in case.bodies}
    needed_noise = field_size - len(relevant)
    if needed_noise < 0:
        raise ValueError("field size is smaller than the required source-backed paths")
    noise = tuple(_noise_body(index) for index in range(needed_noise))
    all_bodies = tuple(sorted((*relevant.values(), *noise), key=lambda item: item.body_id))
    if len(all_bodies) != field_size or len({item.body_id for item in all_bodies}) != field_size:
        raise AssertionError("locked field must contain exactly one copy of every body")
    payload = (
        tuple(item.body_hash for item in all_bodies),
        tuple(item.case_id for item in grounded),
        tuple(item.case_id for item in mixed),
        tuple(item.case_id for item in safety),
    )
    return L3LockedSuite(all_bodies, grounded, mixed, safety, hashlib.sha256(repr(payload).encode()).hexdigest())
