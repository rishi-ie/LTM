"""G1-derived, versioned golden operator definitions for G2.9."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from topology_field_ir.validate import registry_digest
from topology_g1.registry import REGISTRY

from .schemas import AtomBankManifest, GoldenOperatorDefinition, GoldenRoleDefinition

FAMILIES = {
    "implies": "logical", "conjoins": "logical", "fictional_rule": "logical",
    "requires": "dependency", "supersedes": "dependency", "before": "temporal", "after": "temporal",
    "supports": "evidence", "opposes": "evidence", "uncertainty": "evidence",
    "derived_from": "provenance", "assistant_derived_from": "provenance",
    "causes_hypothetically": "causal", "equals": "compatibility", "excludes": "compatibility",
    "prefers": "discourse", "refers_to": "discourse", "scoped_to": "discourse",
}

ANCHORS = {
    "implies": ("a premise logically entails a conclusion", "if true, the conclusion follows", "logical implication", "derive conclusion from premise"),
    "conjoins": ("premises jointly entail a conclusion", "all conditions establish a claim", "logical conjunction", "every premise is necessary"),
    "requires": ("a dependent needs a prerequisite", "one item requires another", "requirement relation", "necessary prerequisite"),
    "excludes": ("two claims are incompatible", "alternatives cannot coexist", "exclusion relation", "one rules out another"),
    "equals": ("two values are equal", "expressions denote one value", "equality relation", "values coincide"),
    "before": ("the first event is earlier", "temporal precedence", "occurs before another", "earlier than relation"),
    "after": ("the first event is later", "inverse temporal precedence", "occurs after another", "later than relation"),
    "supersedes": ("a new claim replaces old claim", "a correction takes precedence", "newer information displaces older", "supersession"),
    "supports": ("evidence favors a claim", "observation supports proposition", "positive evidence", "support without entailment"),
    "opposes": ("evidence counts against a claim", "observation challenges proposition", "negative evidence", "opposition without contradiction"),
    "prefers": ("preference selects a response", "user chooses response form", "response preference", "preference constrains output"),
    "refers_to": ("a mention identifies entity", "question points to entity", "reference binding", "resolve mention"),
    "scoped_to": ("subject applies within a scope", "claim is limited to domain", "scope attachment", "rule governed by scope"),
    "fictional_rule": ("rule holds in fictional scope", "imagined-domain implication", "fictional premise entails conclusion", "invented rule"),
    "causes_hypothetically": ("possible cause may produce effect", "hypothetical causation", "event could cause another", "uncertain cause"),
    "uncertainty": ("evidence leaves claim unresolved", "source does not establish certainty", "uncertain evidence", "cannot confirm claim"),
    "assistant_derived_from": ("assistant response links to evidence", "response provenance", "output derives from evidence", "answer cites evidence"),
    "derived_from": ("derived item has source", "claim originates from another", "provenance relation", "result obtained from source"),
}

CONTRASTS = {
    "before": ("after",), "after": ("before",), "supports": ("opposes", "derived_from", "causes_hypothetically"),
    "opposes": ("supports",), "requires": ("implies", "supersedes"), "implies": ("requires",),
    "supersedes": ("requires",), "derived_from": ("assistant_derived_from", "causes_hypothetically", "supports"),
    "causes_hypothetically": ("derived_from", "supports"), "uncertainty": ("supports", "opposes", "causes_hypothetically"),
    "assistant_derived_from": ("derived_from",),
}


def _role_anchors(relation: str, role: str) -> tuple[str, ...]:
    return (f"the {role} role of {relation}", f"content filling {relation} {role}", f"named argument {role}", f"semantic filler for {role}")


def _operator(relation: str, revision: str) -> GoldenOperatorDefinition:
    spec = REGISTRY[relation]
    roles = []
    for role in spec.roles:
        kinds = tuple(kind.value for kind in role.allowed_kinds)
        if revision == "v1.1" and relation == "supports" and role.name == "evidence":
            kinds = ("fact", "observation")
        roles.append(GoldenRoleDefinition(role.name, kinds, role.minimum, role.maximum, _role_anchors(relation, role.name)))
    weight = .75 if revision == "v1.1" and relation == "causes_hypothetically" else 1.0
    return GoldenOperatorDefinition(f"g29:{revision}:{relation}", relation, FAMILIES[relation], ANCHORS[relation], tuple(f"g29:{revision}:{item}" for item in CONTRASTS.get(relation, ())), tuple(roles), spec.hard_or_soft, spec.exact_operator, spec.field_operator, weight)


def build_atom_bank(revision: str = "v1") -> AtomBankManifest:
    if revision not in {"v1", "v1.1"}:
        raise ValueError("unsupported AtomBank revision")
    operators = tuple(_operator(name, revision) for name in REGISTRY)
    policy_hash = hashlib.sha256(json.dumps([asdict(item) for item in operators], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    bank_hash = hashlib.sha256(f"{revision}:{registry_digest()}:{policy_hash}".encode()).hexdigest()
    return AtomBankManifest(revision, registry_digest(), operators, policy_hash, bank_hash)


ATOM_BANK_V1 = build_atom_bank()
ATOM_BANK_V11 = build_atom_bank("v1.1")
RELATIONS = tuple(item.relation_type for item in ATOM_BANK_V1.operators)
