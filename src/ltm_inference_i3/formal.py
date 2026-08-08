"""Small exact formal kernel used by I3 runtime and an independently invoked evaluator.

This deliberately supports a constrained mathematical fragment.  It is not a
general proof assistant; its role is to make every accepted I3 hop replayable.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator

from .schemas import AxiomSchema, FormalExpression, FormalProofStep, FormalProposition


def v(name: str) -> FormalExpression:
    return FormalExpression("var", value=f"?{name}")


def c(value: int | str) -> FormalExpression:
    return FormalExpression("int", value=str(value))


def e(op: str, *args: FormalExpression) -> FormalExpression:
    return FormalExpression(op, tuple(args))


def expression_key(value: FormalExpression) -> tuple[object, ...]:
    return (value.op, value.value, tuple(expression_key(item) for item in value.args))


def expression_hash(value: FormalExpression) -> str:
    return hashlib.sha256(repr(expression_key(value)).encode()).hexdigest()


def expression_size(value: FormalExpression) -> int:
    return 1 + sum(expression_size(item) for item in value.args)


def iter_paths(value: FormalExpression, prefix: tuple[int, ...] = ()) -> Iterator[tuple[tuple[int, ...], FormalExpression]]:
    yield prefix, value
    for index, item in enumerate(value.args):
        yield from iter_paths(item, prefix + (index,))


def at_path(value: FormalExpression, path: tuple[int, ...]) -> FormalExpression:
    current = value
    for index in path:
        current = current.args[index]
    return current


def replace_at(value: FormalExpression, path: tuple[int, ...], replacement: FormalExpression) -> FormalExpression:
    if not path:
        return replacement
    index = path[0]
    args = list(value.args)
    args[index] = replace_at(args[index], path[1:], replacement)
    return FormalExpression(value.op, tuple(args), value.value)


def match(pattern: FormalExpression, value: FormalExpression, bindings: dict[str, FormalExpression] | None = None) -> dict[str, FormalExpression] | None:
    bound = {} if bindings is None else dict(bindings)
    if pattern.op == "var" and pattern.value and pattern.value.startswith("?"):
        existing = bound.get(pattern.value)
        if existing is not None:
            return bound if expression_key(existing) == expression_key(value) else None
        bound[pattern.value] = value
        return bound
    if pattern.op != value.op or pattern.value != value.value or len(pattern.args) != len(value.args):
        return None
    for left, right in zip(pattern.args, value.args, strict=True):
        bound = match(left, right, bound)
        if bound is None:
            return None
    return bound


def instantiate(pattern: FormalExpression, bindings: dict[str, FormalExpression]) -> FormalExpression:
    if pattern.op == "var" and pattern.value in bindings:
        return bindings[pattern.value]
    return FormalExpression(pattern.op, tuple(instantiate(item, bindings) for item in pattern.args), pattern.value)


def apply_schema(value: FormalExpression, schema: AxiomSchema, path: tuple[int, ...], reverse: bool) -> FormalExpression | None:
    source, destination = (schema.right, schema.left) if reverse else (schema.left, schema.right)
    bindings = match(source, at_path(value, path))
    if bindings is None:
        return None
    return replace_at(value, path, instantiate(destination, bindings))


def enumerate_applications(value: FormalExpression, schema: AxiomSchema) -> Iterator[tuple[tuple[int, ...], bool, FormalExpression]]:
    for path, _ in iter_paths(value):
        changed = apply_schema(value, schema, path, False)
        if changed is not None and expression_key(changed) != expression_key(value):
            yield path, False, changed
        if schema.reversible:
            changed = apply_schema(value, schema, path, True)
            if changed is not None and expression_key(changed) != expression_key(value):
                yield path, True, changed


def verify_step(step: FormalProofStep, schemas: dict[str, AxiomSchema]) -> bool:
    schema = schemas.get(step.axiom_id)
    return schema is not None and apply_schema(step.before, schema, step.path, step.reverse) == step.after


def verify_proof(proposition: FormalProposition, steps: tuple[FormalProofStep, ...], schemas: dict[str, AxiomSchema]) -> bool:
    current = proposition.left
    for step in steps:
        if step.before != current or not verify_step(step, schemas):
            return False
        current = step.after
    return current == proposition.right


def tree_distance(left: FormalExpression, right: FormalExpression) -> float:
    if left == right:
        return 0.0
    head = 0.0 if left.op == right.op and left.value == right.value else 1.0
    overlap = min(len(left.args), len(right.args))
    child = sum(tree_distance(left.args[index], right.args[index]) for index in range(overlap))
    return head + child + abs(len(left.args) - len(right.args)) + .05 * abs(expression_size(left) - expression_size(right))


def _row(axiom_id: str, family: str, left: FormalExpression, right: FormalExpression, reversible: bool = True) -> AxiomSchema:
    return AxiomSchema(axiom_id, family, left, right, reversible, "standard-v1")


def standard_axioms() -> tuple[AxiomSchema, ...]:
    """The frozen 46-schema I3 inventory; all entries are exact AST rewrites."""
    x, y, z = v("x"), v("y"), v("z")
    rows = (
        # Equality/substitution (5)
        _row("eq.refl", "equality", x, x, False),
        _row("eq.symmetry", "equality", e("eq", x, y), e("eq", y, x)),
        _row("eq.congruence_add", "equality", e("add", x, z), e("add", y, z)),
        _row("eq.congruence_mul", "equality", e("mul", x, z), e("mul", y, z)),
        _row("eq.substitution", "equality", e("substitute", x), x),
        # Commutative ring (12)
        _row("ring.add_zero", "ring", e("add", x, c(0)), x),
        _row("ring.zero_add", "ring", e("add", c(0), x), x),
        _row("ring.add_comm", "ring", e("add", x, y), e("add", y, x)),
        _row("ring.add_assoc", "ring", e("add", e("add", x, y), z), e("add", x, e("add", y, z))),
        _row("ring.add_inverse", "ring", e("add", x, e("neg", x)), c(0)),
        _row("ring.double_neg", "ring", e("neg", e("neg", x)), x),
        _row("ring.mul_one", "ring", e("mul", x, c(1)), x),
        _row("ring.one_mul", "ring", e("mul", c(1), x), x),
        _row("ring.mul_zero", "ring", e("mul", x, c(0)), c(0)),
        _row("ring.mul_comm", "ring", e("mul", x, y), e("mul", y, x)),
        _row("ring.mul_assoc", "ring", e("mul", e("mul", x, y), z), e("mul", x, e("mul", y, z))),
        _row("ring.distributive", "ring", e("mul", x, e("add", y, z)), e("add", e("mul", x, y), e("mul", x, z))),
        # Ordered arithmetic (7)
        _row("order.add_left", "order", e("lt", e("add", z, x), e("add", z, y)), e("lt", x, y)),
        _row("order.add_right", "order", e("lt", e("add", x, z), e("add", y, z)), e("lt", x, y)),
        _row("order.le_add_left", "order", e("le", e("add", z, x), e("add", z, y)), e("le", x, y)),
        _row("order.le_add_right", "order", e("le", e("add", x, z), e("add", y, z)), e("le", x, y)),
        _row("order.lt_to_le", "order", e("lt", x, y), e("le", x, y), False),
        _row("order.negate", "order", e("lt", x, y), e("lt", e("neg", y), e("neg", x))),
        _row("order.scale_positive", "order", e("lt", x, y), e("lt", e("mul", c(2), x), e("mul", c(2), y))),
        # Divisibility/modular congruence (7)
        _row("mod.add_zero", "modular", e("mod", e("add", x, c(0)), y), e("mod", x, y)),
        _row("mod.mul_one", "modular", e("mod", e("mul", x, c(1)), y), e("mod", x, y)),
        _row("mod.negate", "modular", e("mod", x, y), e("mod", e("neg", x), y)),
        _row("mod.add_congruent", "modular", e("mod", x, y), e("mod", e("add", x, z), e("add", y, z))),
        _row("divides.zero", "modular", e("divides", x, c(0)), c(1)),
        _row("divides.self", "modular", e("divides", x, x), c(1)),
        _row("divides.negate", "modular", e("divides", x, y), e("divides", x, e("neg", y))),
        # Finite-set algebra (7)
        _row("set.union_empty", "sets", e("union", x, e("empty")), x),
        _row("set.empty_union", "sets", e("union", e("empty"), x), x),
        _row("set.inter_universe", "sets", e("inter", x, e("universe")), x),
        _row("set.union_comm", "sets", e("union", x, y), e("union", y, x)),
        _row("set.inter_comm", "sets", e("inter", x, y), e("inter", y, x)),
        _row("set.union_assoc", "sets", e("union", e("union", x, y), z), e("union", x, e("union", y, z))),
        _row("set.inter_assoc", "sets", e("inter", e("inter", x, y), z), e("inter", x, e("inter", y, z))),
        # Propositional natural deduction as formula rewrites (8)
        _row("logic.and_true_right", "logic", e("and", x, e("true")), x),
        _row("logic.and_true_left", "logic", e("and", e("true"), x), x),
        _row("logic.or_false_right", "logic", e("or", x, e("false")), x),
        _row("logic.or_false_left", "logic", e("or", e("false"), x), x),
        _row("logic.double_not", "logic", e("not", e("not", x)), x),
        _row("logic.and_comm", "logic", e("and", x, y), e("and", y, x)),
        _row("logic.or_comm", "logic", e("or", x, y), e("or", y, x)),
        _row("logic.de_morgan", "logic", e("not", e("and", x, y)), e("or", e("not", x), e("not", y))),
    )
    if len(rows) != 46:
        raise AssertionError(f"expected 46 schemas, found {len(rows)}")
    return rows
