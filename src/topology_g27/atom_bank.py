"""Immutable reasoning-atom inventory derived from the G1 registry."""

from __future__ import annotations

import hashlib

from topology_g1.registry import REGISTRY

from .schemas import ReasoningAtomSpec

FAMILIES = {
    "implies": "logical", "conjoins": "logical", "fictional_rule": "logical",
    "requires": "dependency_and_revision", "supersedes": "dependency_and_revision",
    "before": "temporal", "after": "temporal",
    "supports": "evidence_and_epistemic", "opposes": "evidence_and_epistemic", "uncertainty": "evidence_and_epistemic",
    "derived_from": "provenance", "assistant_derived_from": "provenance",
    "causes_hypothetically": "causal",
    "equals": "compatibility", "excludes": "compatibility",
    "prefers": "context_and_discourse", "refers_to": "context_and_discourse", "scoped_to": "context_and_discourse",
}

ANCHORS = {
    "implies": ("a premise entails a conclusion", "if one claim holds another follows", "logical implication from premise to conclusion", "derive a conclusion from a premise"),
    "conjoins": ("multiple premises jointly entail a conclusion", "all conditions together establish a claim", "conjunction of premises", "every premise is required for the conclusion"),
    "requires": ("a dependent claim needs a prerequisite", "requirement relation between dependent and prerequisite", "one claim cannot hold without another", "prerequisite for a dependent claim"),
    "excludes": ("two claims are incompatible", "one alternative excludes another", "the claims cannot both hold", "conflict between two propositions"),
    "equals": ("two values are equal", "both expressions denote the same value", "equality between values", "the values coincide"),
    "before": ("the first event occurs before the second", "earlier event followed by later event", "temporal precedence", "event ordering with first before second"),
    "after": ("the first event occurs after the second", "later event follows an earlier event", "inverse temporal ordering", "event ordering with first after second"),
    "supersedes": ("a newer claim replaces an older claim", "replacement record takes authority over an old record", "correction supersedes prior information", "new version displaces old version"),
    "supports": ("evidence supports a claim", "evidence favors a proposition", "supporting evidence for a claim", "one claim provides support for another"),
    "opposes": ("evidence opposes a claim", "evidence challenges a proposition", "opposing evidence for a claim", "one claim counts against another"),
    "prefers": ("a preference selects a response", "a user prefers one response over another", "response preference relation", "style preference for a goal"),
    "refers_to": ("a mention identifies an entity", "a question refers to an entity", "reference binding from mention to entity", "resolve a mention to an object"),
    "scoped_to": ("a subject is limited to a scope", "claim applies within a named domain", "scope restriction on a subject", "relation attaches a subject to a scope"),
    "fictional_rule": ("within a fictional scope a premise entails a conclusion", "imagined domain rule", "fictional implication with a scope", "a rule valid only in an invented setting"),
    "causes_hypothetically": ("a possible cause produces a possible effect", "hypothetical causal relation", "under a hypothesis one event causes another", "uncertain cause and effect"),
    "uncertainty": ("evidence leaves a claim unresolved", "a source does not establish certainty", "uncertain support for a proposition", "the claim cannot be confirmed"),
    "assistant_derived_from": ("an assistant response is derived from evidence", "response provenance points to source evidence", "assistant statement linked to evidence", "answer cites an underlying claim"),
    "derived_from": ("a derived item has a source", "one claim is obtained from another", "provenance link between derived and source", "the result originates from the source"),
}

CONTRASTS = {
    "before": ("after",), "after": ("before",), "derived_from": ("causes_hypothetically",), "causes_hypothetically": ("derived_from",),
    "supersedes": ("requires",), "requires": ("supersedes",), "uncertainty": ("supports", "causes_hypothetically"),
}


def _structural(name: str) -> tuple[float, ...]:
    digest = hashlib.sha256(("g27-structure:" + name).encode()).digest()
    return tuple(((byte / 255.0) * 2.0 - 1.0) for byte in (digest * 3)[:64])


def build_atom_bank() -> tuple[ReasoningAtomSpec, ...]:
    output = []
    for name, spec in REGISTRY.items():
        output.append(ReasoningAtomSpec(name, FAMILIES[name], tuple(role.name for role in spec.roles), tuple((role.name, tuple(kind.value for kind in role.allowed_kinds)) for role in spec.roles), spec.hard_or_soft, spec.exact_operator, spec.field_operator, _structural(name), ANCHORS[name], CONTRASTS.get(name, ())))
    return tuple(output)


ATOM_BANK = build_atom_bank()
RELATIONS = tuple(item.relation_type for item in ATOM_BANK)
BANK_HASH = hashlib.sha256(repr(ATOM_BANK).encode()).hexdigest()
