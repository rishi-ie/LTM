from __future__ import annotations

from .schemas import NodeKind, RelationSpec, RoleSpec, SchemaError

CLAIM = (NodeKind.CLAIM, NodeKind.FACT, NodeKind.OBSERVATION, NodeKind.HYPOTHESIS)
ANY = tuple(NodeKind)
VALUE_LIKE = CLAIM + (NodeKind.VALUE, NodeKind.STATE)
DERIVABLE = CLAIM + (NodeKind.RULE, NodeKind.ASSISTANT_RESPONSE)


def _spec(name: str, roles: tuple[RoleSpec, ...], hard: str, exact: str, field: str) -> RelationSpec:
    return RelationSpec(name, roles, hard, exact, field, f"verify_{exact}", f"{{relation}}: {name}")


REGISTRY: dict[str, RelationSpec] = {
    "implies": _spec("implies", (RoleSpec("premise", CLAIM), RoleSpec("conclusion", CLAIM)), "hard", "derive", "implication"),
    "conjoins": _spec("conjoins", (RoleSpec("premise", CLAIM, 2, 8), RoleSpec("conclusion", CLAIM)), "hard", "derive_all", "conjunction"),
    "requires": _spec("requires", (RoleSpec("dependent", CLAIM), RoleSpec("prerequisite", CLAIM)), "hard", "obligation", "requirement"),
    "excludes": _spec("excludes", (RoleSpec("left", CLAIM), RoleSpec("right", CLAIM)), "hard", "conflict", "exclusion"),
    "equals": _spec("equals", (RoleSpec("left", VALUE_LIKE), RoleSpec("right", VALUE_LIKE)), "soft", "equal", "equality"),
    "before": _spec("before", (RoleSpec("first", (NodeKind.EVENT,)), RoleSpec("second", (NodeKind.EVENT,))), "hard", "temporal", "temporal"),
    "after": _spec("after", (RoleSpec("first", (NodeKind.EVENT,)), RoleSpec("second", (NodeKind.EVENT,))), "hard", "temporal_inverse", "temporal"),
    "supersedes": _spec("supersedes", (RoleSpec("older", CLAIM), RoleSpec("newer", CLAIM)), "hard", "supersede", "hard_obligation"),
    "supports": _spec("supports", (RoleSpec("evidence", CLAIM), RoleSpec("claim", CLAIM)), "soft", "support", "support"),
    "opposes": _spec("opposes", (RoleSpec("evidence", CLAIM), RoleSpec("claim", CLAIM)), "soft", "oppose", "opposition"),
    "prefers": _spec("prefers", (RoleSpec("preference", (NodeKind.PREFERENCE, NodeKind.INSTRUCTION)), RoleSpec("response", (NodeKind.GOAL, NodeKind.QUESTION))), "soft", "response_constraint", "preference"),
    "refers_to": _spec("refers_to", (RoleSpec("mention", (NodeKind.QUESTION, NodeKind.CONVERSATION_TURN)), RoleSpec("entity", (NodeKind.ENTITY,))), "hard", "bind_reference", "reference"),
    "scoped_to": _spec("scoped_to", (RoleSpec("subject", DERIVABLE), RoleSpec("scope", (NodeKind.SCOPE,))), "hard", "scope_gate", "hard_obligation"),
    "fictional_rule": _spec("fictional_rule", (RoleSpec("premise", CLAIM), RoleSpec("conclusion", CLAIM), RoleSpec("scope", (NodeKind.SCOPE,))), "hard", "fictional_derive", "implication"),
    "causes_hypothetically": _spec("causes_hypothetically", (RoleSpec("cause", CLAIM), RoleSpec("effect", CLAIM)), "soft", "hypothesis_message", "causal_hypothesis"),
    "uncertainty": _spec("uncertainty", (RoleSpec("source", CLAIM), RoleSpec("claim", CLAIM)), "soft", "uncertainty_message", "uncertainty"),
    "assistant_derived_from": _spec("assistant_derived_from", (RoleSpec("response", (NodeKind.ASSISTANT_RESPONSE,)), RoleSpec("evidence", CLAIM)), "hard", "assistant_link", "provenance"),
    "derived_from": _spec("derived_from", (RoleSpec("derived", DERIVABLE), RoleSpec("source", DERIVABLE)), "hard", "provenance_link", "provenance"),
}


def relation_spec(relation_type: str) -> RelationSpec:
    try:
        return REGISTRY[relation_type]
    except KeyError as exc:
        raise SchemaError("UNKNOWN_RELATION", relation_type) from exc


def validate_relation(relation, nodes: dict[str, object]) -> RelationSpec:
    spec = relation_spec(relation.relation_type)
    roles = {role.name: relation.role_ids(role.name) for role in spec.roles}
    supplied = {item.role for item in relation.arguments}
    allowed = {role.name for role in spec.roles}
    if supplied - allowed:
        raise SchemaError("MISSING_ROLE", "unknown argument role")
    for role in spec.roles:
        ids = roles[role.name]
        if not role.minimum <= len(ids) <= role.maximum:
            raise SchemaError("MISSING_ROLE", f"role {role.name} has wrong arity")
        for node_id in ids:
            node = nodes.get(node_id)
            if node is None or node.kind not in role.allowed_kinds:
                raise SchemaError("INVALID_ARGUMENT_TYPE", f"invalid {role.name} argument")
    return spec
