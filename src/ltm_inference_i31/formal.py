"""Exact ground equality application and independent-proof primitives."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

from ltm_inference_i3.formal import (
    at_path,
    expression_hash,
    expression_key,
    instantiate,
    iter_paths,
    match,
    replace_at,
)
from ltm_inference_i3.schemas import FormalExpression

from .schemas import FormalProofStep, MathematicalBody


def apply_body(value: FormalExpression, body: MathematicalBody, path: tuple[int, ...], reverse: bool) -> FormalExpression | None:
    source, target = (body.right, body.left) if reverse else (body.left, body.right)
    bindings = match(source, at_path(value, path))
    return replace_at(value, path, instantiate(target, bindings)) if bindings is not None else None


def enumerate_body_applications(value: FormalExpression, body: MathematicalBody) -> Iterator[tuple[tuple[int, ...], bool, FormalExpression]]:
    for path, _ in iter_paths(value):
        for reverse in (False, True):
            changed = apply_body(value, body, path, reverse)
            if changed is not None and expression_key(changed) != expression_key(value):
                yield path, reverse, changed


def verify_step(step: FormalProofStep, bodies: dict[str, MathematicalBody], reality_key: str) -> bool:
    body = bodies.get(step.body_id)
    return body is not None and body.reality_key == reality_key and apply_body(step.before, body, step.path, step.reverse) == step.after


def verify_proof(source: FormalExpression, goal: FormalExpression, proof: tuple[FormalProofStep, ...], bodies: dict[str, MathematicalBody], reality_key: str) -> bool:
    current = source
    for step in proof:
        if step.before != current or not verify_step(step, bodies, reality_key):
            return False
        current = step.after
    return current == goal


def body_hash(body: MathematicalBody) -> str:
    return hashlib.sha256(repr((body.body_id, body.reality_key, expression_hash(body.left), expression_hash(body.right))).encode()).hexdigest()
