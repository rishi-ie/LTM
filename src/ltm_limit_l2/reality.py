"""Atomic reality assembly for compiled mathematical bodies."""

from __future__ import annotations

import hashlib

from .schemas import CompiledMathStatement, MathRealityTransaction


def commit(statements: tuple[CompiledMathStatement, ...], *, reality_key: str, confirmed: bool = False) -> MathRealityTransaction:
    active = []
    for statement in statements:
        if statement.source.reality_key != reality_key:
            continue
        if statement.disposition != "accept" or statement.body is None:
            continue
        if statement.activation_state == "pending_confirmation" and not confirmed:
            continue
        active.append(statement.body)
    body_ids = tuple(sorted(item.body_id for item in active))
    digest = hashlib.sha256(repr((reality_key, body_ids, tuple(item.body_hash for item in active))).encode()).hexdigest()
    return MathRealityTransaction(f"tx:{digest[:16]}", reality_key, body_ids, "0" * 64, digest, "committed" if active else "no_change")
