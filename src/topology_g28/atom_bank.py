"""Versioned golden-operator banks derived from the canonical G1 registry."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from topology_field_ir.validate import registry_digest
from topology_g1.registry import REGISTRY

from .schemas import AtomBankManifest, GoldenOperatorDefinition, GoldenRoleDefinition

FAMILIES = {
    "implies": "logical", "conjoins": "logical", "fictional_rule": "logical",
    "requires": "dependency", "supersedes": "dependency",
    "before": "temporal", "after": "temporal",
    "supports": "evidence", "opposes": "evidence", "uncertainty": "evidence",
    "derived_from": "provenance", "assistant_derived_from": "provenance",
    "causes_hypothetically": "causal",
    "equals": "compatibility", "excludes": "compatibility",
    "prefers": "discourse", "refers_to": "discourse", "scoped_to": "discourse",
}

ANCHORS = {
    "implies": ("a premise logically entails a conclusion", "if a premise is true the conclusion follows", "logical implication", "derive a conclusion from a premise"),
    "conjoins": ("multiple premises jointly entail a conclusion", "all conditions establish a claim", "logical conjunction", "every premise is needed"),
    "requires": ("a dependent claim needs a prerequisite", "one item requires another", "requirement relation", "a prerequisite is necessary"),
    "excludes": ("two claims are incompatible", "the alternatives cannot coexist", "exclusion relation", "one claim conflicts with another"),
    "equals": ("two values are equal", "both expressions denote one value", "equality relation", "the values coincide"),
    "before": ("the first event happens earlier", "temporal precedence", "an event occurs before another", "earlier than relation"),
    "after": ("the first event happens later", "inverse temporal precedence", "an event occurs after another", "later than relation"),
    "supersedes": ("a new claim replaces an old claim", "a correction takes precedence", "newer information displaces older information", "supersession relation"),
    "supports": ("evidence favors a claim", "an observation supports a proposition", "positive evidence relation", "support without logical entailment"),
    "opposes": ("evidence counts against a claim", "an observation challenges a proposition", "negative evidence relation", "opposition without logical contradiction"),
    "prefers": ("a preference selects a response", "a user chooses a response form", "response preference relation", "a preference constrains output"),
    "refers_to": ("a mention identifies an entity", "a question points to an entity", "reference binding", "resolve a mention to an object"),
    "scoped_to": ("a subject applies within a scope", "a claim is limited to a domain", "scope attachment", "a rule is governed by a scope"),
    "fictional_rule": ("a rule holds in a fictional scope", "imagined-domain implication", "fictional premise entails conclusion", "invented setting rule"),
    "causes_hypothetically": ("a possible cause may produce an effect", "hypothetical causation", "an event could cause another", "uncertain causal relation"),
    "uncertainty": ("evidence leaves a claim unresolved", "a source does not establish certainty", "uncertain evidence relation", "the claim cannot be confirmed"),
    "assistant_derived_from": ("an assistant response is linked to evidence", "response provenance relation", "assistant output derives from evidence", "answer cites supporting evidence"),
    "derived_from": ("a derived item has a source", "one claim originates from another", "provenance relation", "a result is obtained from a source"),
}

CONTRASTS = {
    "before": ("after",), "after": ("before",),
    "supports": ("opposes", "derived_from", "causes_hypothetically"),
    "opposes": ("supports",),
    "requires": ("implies", "supersedes"),
    "implies": ("requires",), "supersedes": ("requires",),
    "derived_from": ("assistant_derived_from", "causes_hypothetically", "supports",),
    "causes_hypothetically": ("derived_from", "supports",),
    "uncertainty": ("supports", "opposes", "causes_hypothetically"),
    "assistant_derived_from": ("derived_from",),
}


def _role_anchors(relation: str, role: str) -> tuple[str, ...]:
    return (
        f"the {role} role of {relation}",
        f"content filling {relation} {role}",
        f"named argument {role} in relation {relation}",
        f"semantic filler for {role}",
    )


def _operator(name: str, *, revision: str) -> GoldenOperatorDefinition:
    spec = REGISTRY[name]
    roles = tuple(
        GoldenRoleDefinition(
            role.name,
            tuple(kind.value for kind in role.allowed_kinds),
            role.minimum,
            role.maximum,
            _role_anchors(name, role.name),
        )
        for role in spec.roles
    )
    weight = .75 if revision == "v1.1" and name == "causes_hypothetically" else 1.0
    if revision == "v1.1" and name == "supports":
        roles = tuple(
            GoldenRoleDefinition(
                role.role_name,
                ("fact", "observation") if role.role_name == "evidence" else role.allowed_node_kinds,
                role.minimum,
                role.maximum,
                role.semantic_anchors,
            )
            for role in roles
        )
    return GoldenOperatorDefinition(
        f"g28:{revision}:{name}", name, FAMILIES[name], ANCHORS[name],
        tuple(f"g28:{revision}:{item}" for item in CONTRASTS.get(name, ())), roles,
        spec.hard_or_soft, spec.exact_operator, spec.field_operator,
        ("global", "conversation-local", "fictional", "hypothetical", "temporally-bounded"), weight,
    )


def build_atom_bank(revision: str = "v1") -> AtomBankManifest:
    if revision not in {"v1", "v1.1"}:
        raise ValueError("unsupported AtomBank revision")
    operators = tuple(_operator(name, revision=revision) for name in REGISTRY)
    policy = json.dumps([asdict(item) for item in operators], sort_keys=True, separators=(",", ":"))
    policy_hash = hashlib.sha256(policy.encode()).hexdigest()
    bank_hash = hashlib.sha256(f"{revision}:{registry_digest()}:{policy_hash}".encode()).hexdigest()
    return AtomBankManifest(revision, registry_digest(), operators, policy_hash, bank_hash)


ATOM_BANK_V1 = build_atom_bank()
ATOM_BANK_V11 = build_atom_bank("v1.1")
RELATIONS = tuple(operator.relation_type for operator in ATOM_BANK_V1.operators)
