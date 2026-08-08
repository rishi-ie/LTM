"""G1-derived relation cards used by the G2.6 scorer.

The compiler never maintains a second hand-written relation registry.  The
structural side of each prototype is derived from the canonical G1 registry.
"""

from __future__ import annotations

import hashlib

from topology_g1.registry import REGISTRY

from .schemas import RelationCard

RELATIONS = tuple(REGISTRY)
ROLES = tuple(dict.fromkeys(role.name for spec in REGISTRY.values() for role in spec.roles))


def _card_vector(name: str, spec: object) -> tuple[float, ...]:
    """Create a deterministic structural code, not a language shortcut."""
    payload = repr(
        (
            name,
            tuple((r.name, tuple(k.value for k in r.allowed_kinds), r.minimum, r.maximum) for r in spec.roles),
            spec.hard_or_soft,
            spec.exact_operator,
            spec.field_operator,
        )
    ).encode()
    digest = hashlib.sha256(payload).digest()
    values: list[float] = []
    for index in range(64):
        value = digest[index % len(digest)] ^ ((index * 37) & 0xFF)
        values.append((value / 127.5) - 1.0)
    norm = sum(value * value for value in values) ** 0.5
    return tuple(value / norm for value in values)


def build_relation_cards() -> tuple[RelationCard, ...]:
    cards: list[RelationCard] = []
    for name, spec in REGISTRY.items():
        cards.append(
            RelationCard(
                name,
                tuple(role.name for role in spec.roles),
                tuple(
                    (role.name, tuple(kind.value for kind in role.allowed_kinds))
                    for role in spec.roles
                ),
                tuple(role.minimum for role in spec.roles),
                spec.hard_or_soft,
                spec.exact_operator,
                spec.field_operator,
                _card_vector(name, spec),
            )
        )
    return tuple(cards)


CARDS = build_relation_cards()
CARD_BY_NAME = {card.relation_type: card for card in CARDS}

RELATION_DESCRIPTIONS = {
    "implies": "a premise logically entails a conclusion",
    "conjoins": "multiple premises together entail one conclusion",
    "requires": "a dependent claim needs a prerequisite",
    "excludes": "two claims are incompatible and cannot both hold",
    "equals": "two values or claims are equivalent",
    "before": "the first event happens earlier than the second event",
    "after": "the first event happens later than the second event",
    "supersedes": "a newer claim replaces an older claim",
    "supports": "evidence provides positive support for a claim",
    "opposes": "evidence provides negative support against a claim",
    "prefers": "a preference selects a response or goal",
    "refers_to": "a mention identifies an entity",
    "scoped_to": "a subject applies only to a scope",
    "fictional_rule": "inside a fictional scope a premise entails a conclusion",
    "causes_hypothetically": "a possible cause may produce an effect",
    "uncertainty": "evidence leaves a claim unresolved",
    "assistant_derived_from": "an assistant response is derived from evidence",
    "derived_from": "a derived claim follows from a source",
}


def registry_digest() -> str:
    return hashlib.sha256(repr(CARDS).encode()).hexdigest()
