"""Explicit execution capability bridge for current G1/G6/G7 primitives."""

from __future__ import annotations

from dataclasses import dataclass

from topology_g6.schemas import Rule

from .schemas import TypedFactor


@dataclass(frozen=True, slots=True)
class OptimizationCapability:
    factor_id: str
    exact_engine: str
    g6_rule: Rule | None
    g7_supported: bool
    diagnostic: str | None


def capability(factor: TypedFactor) -> OptimizationCapability:
    """Expose optimization support; every factor still has a G1 exact path."""
    bindings = dict(factor.role_bindings)
    if factor.relation_type in {"implies", "fictional_rule"}:
        rule = Rule(factor.factor_id, factor.relation_type, bindings["premise"], bindings["conclusion"][0], factor.context.scope_id, factor.context.confidence, factor.context.authority)
        return OptimizationCapability(factor.factor_id, "g1", rule, False, "G7_PARAMETERS_REQUIRED")
    if factor.relation_type == "conjoins":
        rule = Rule(factor.factor_id, "conjoins", bindings["premise"], bindings["conclusion"][0], factor.context.scope_id, factor.context.confidence, factor.context.authority)
        return OptimizationCapability(factor.factor_id, "g1", rule, False, "G7_PARAMETERS_REQUIRED")
    return OptimizationCapability(factor.factor_id, "g1", None, False, "NO_G6_G7_ADAPTER")
