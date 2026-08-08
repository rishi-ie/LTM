"""Deterministic, leakage-free semantic fixtures for L5.

The generator is deliberately lazy: a case is derived only from its seed and
index, so million-body diagnostics do not require a million objects in memory.
Runtime-facing cases contain the field and prompt but never evaluator labels.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from .schemas import (
    FORBIDDEN_PUBLIC_FIELDS,
    CompiledPromptField,
    EquilibriumBody,
    FieldMumbrane,
    PromptInfluenceRecord,
)

FAMILIES = (
    "one_body",
    "dependency_2_4",
    "dependency_5_8",
    "dependency_9_16",
    "conjunction",
    "weighted_contradiction",
    "balanced_contradiction",
    "alternatives",
    "scope_isolation",
    "unknown",
)


def _sha(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def _opaque(*parts: object, width: int = 20) -> str:
    return _sha(parts)[:width]


def _basis(key: str) -> tuple[float, ...]:
    raw = bytearray()
    block = 0
    while len(raw) < 128:
        raw.extend(hashlib.sha256(f"{key}|{block}".encode()).digest())
        block += 1
    values = tuple((item - 127.5) / 127.5 for item in raw[:128])
    norm = math.sqrt(sum(item * item for item in values))
    return tuple(item / norm for item in values)


def semantic_position(semantic_key: str) -> tuple[float, ...]:
    """Return a stable unit vector with a shared topic component.

    Generated keys use ``domain|topic|content``. The shared topic makes the
    vectors useful to a semantic index without encoding a route or depth.
    """

    pieces = semantic_key.split("|", 2)
    topic = pieces[1] if len(pieces) == 3 else semantic_key
    topic_vector = _basis(f"topic:{topic}")
    item_vector = _basis(f"item:{semantic_key}")
    mixed = tuple(0.85 * left + 0.15 * right for left, right in zip(topic_vector, item_vector, strict=True))
    norm = math.sqrt(sum(item * item for item in mixed))
    return tuple(item / norm for item in mixed)


@dataclass(frozen=True, slots=True)
class PublicFieldCase:
    case_id: str
    prompt: CompiledPromptField
    units: tuple[FieldMumbrane, ...]
    bodies: tuple[EquilibriumBody, ...]
    vector_table: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if self.prompt.prompt_id != self.case_id:
            raise ValueError("prompt/case identity mismatch")
        unit_ids = {item.unit_id for item in self.units}
        rows = {item.unit_id: item for item in self.units}
        if len(unit_ids) != len(self.units):
            raise ValueError("duplicate Mumbrane unit ID")
        if any(item.semantic_vector_ref >= len(self.vector_table) for item in self.units):
            raise ValueError("invalid semantic vector reference")
        if any(len(row) != 128 or any(not math.isfinite(value) for value in row) for row in self.vector_table):
            raise ValueError("invalid semantic vector table")
        for body in self.bodies:
            if not set(body.input_unit_ids + body.outcome_unit_ids) <= unit_ids:
                raise ValueError("body references an unknown Mumbrane")
            if any(rows[item].body_id != body.body_id for item in body.input_unit_ids + body.outcome_unit_ids):
                raise ValueError("body does not own all of its Mumbrane occurrences")
            if any(rows[item].phase_index != 0 for item in body.input_unit_ids) or any(
                rows[item].phase_index != 1 for item in body.outcome_unit_ids
            ):
                raise ValueError("body phase mismatch")


@dataclass(frozen=True, slots=True)
class ExpectedCandidate:
    semantic_key: str
    polarity: int
    support_mass: float


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    case_id: str
    family: str
    domain: str
    dependency_count: int
    disposition: str
    candidates: tuple[ExpectedCandidate, ...]
    selected: tuple[str, int] | None


@dataclass(frozen=True, slots=True)
class GeneratedCase:
    public: PublicFieldCase
    expected: ExpectedOutcome


class _Builder:
    def __init__(self, case_id: str, topic: str, reality: str, scope: str, valid_at: int = 100) -> None:
        self.case_id = case_id
        self.topic = topic
        self.reality = reality
        self.scope = scope
        self.valid_at = valid_at
        self.units: list[FieldMumbrane] = []
        self.units_by_id: dict[str, FieldMumbrane] = {}
        self.bodies: list[EquilibriumBody] = []
        self.vectors: list[tuple[float, ...]] = []
        self.vector_refs: dict[str, int] = {}
        self.influences: list[PromptInfluenceRecord] = []

    def _vector_ref(self, semantic_key: str) -> int:
        if semantic_key not in self.vector_refs:
            self.vector_refs[semantic_key] = len(self.vectors)
            self.vectors.append(semantic_position(semantic_key))
        return self.vector_refs[semantic_key]

    def unit(
        self,
        semantic_key: str,
        *,
        body_id: str,
        phase: int,
        polarity: int = 1,
        source_key: str,
        modality: str = "asserted",
        scope: str | None = None,
        reality: str | None = None,
        provenance: str | None = None,
    ) -> str:
        unit_id = f"u:{_opaque(self.case_id, len(self.units), semantic_key, polarity)}"
        unit = FieldMumbrane(
                unit_id=unit_id,
                body_id=body_id,
                semantic_key=semantic_key,
                semantic_vector_ref=self._vector_ref(semantic_key),
                local_index=len(self.units),
                phase_index=phase,
                polarity=polarity,
                modality=modality,
                scope_key=scope or self.scope,
                reality_key=reality or self.reality,
                valid_from=0,
                valid_to=1_000,
                identity_key=f"id:{_opaque(semantic_key)}",
                provenance_id=provenance or f"prov:{_opaque(self.case_id, semantic_key, len(self.units))}",
                independent_source_key=source_key,
            )
        self.units.append(unit)
        self.units_by_id[unit_id] = unit
        return unit_id

    def prompt_unit(self, semantic_key: str, *, polarity: int = 1) -> str:
        source_key = f"prompt:{self.case_id}"
        unit_id = self.unit(
            semantic_key,
            body_id=f"prompt:{self.case_id}",
            phase=0,
            polarity=polarity,
            source_key=source_key,
            provenance=f"prov:prompt:{self.case_id}",
        )
        self.influences.append(
            PromptInfluenceRecord(
                unit_id=unit_id,
                semantic_key=semantic_key,
                semantic_position=semantic_position(semantic_key),
                clamp_strength=1.0,
                query_relevance_weight=1.0,
                polarity_sign=polarity,
                modality_weight=1.0,
                scope_key=self.scope,
                reality_key=self.reality,
                valid_at=self.valid_at,
                compiler_confidence=1.0,
                provenance_id=f"prov:prompt:{self.case_id}",
            )
        )
        return unit_id

    def body(
        self,
        inputs: tuple[str, ...],
        semantic_key: str,
        *,
        polarity: int = 1,
        weight: float = 0.9,
        source_key: str | None = None,
        scope: str | None = None,
        reality: str | None = None,
        valid_from: int = 0,
        valid_to: int = 1_000,
    ) -> tuple[str, str]:
        input_rows = tuple(self.units_by_id[item] for item in inputs)
        body_id = f"b:{_opaque(self.case_id, len(self.bodies), inputs, semantic_key, polarity)}"
        source_key = source_key or f"source:{_opaque(self.case_id, len(self.bodies))}"
        provenance = f"prov:{_opaque(body_id, source_key)}"
        owned_inputs = tuple(
            self.unit(
                item.semantic_key,
                body_id=body_id,
                phase=0,
                polarity=item.polarity,
                source_key=source_key,
                modality=item.modality,
                scope=scope,
                reality=reality,
                provenance=provenance,
            )
            for item in input_rows
        )
        output = self.unit(
            semantic_key,
            body_id=body_id,
            phase=1,
            polarity=polarity,
            source_key=source_key,
            scope=scope,
            reality=reality,
            provenance=provenance,
        )
        body_scope = scope or self.scope
        body_reality = reality or self.reality
        payload = (
            body_id,
            owned_inputs,
            (output,),
            weight,
            body_scope,
            body_reality,
            valid_from,
            valid_to,
            source_key,
            provenance,
        )
        self.bodies.append(
            EquilibriumBody(
                body_id=body_id,
                input_unit_ids=owned_inputs,
                outcome_unit_ids=(output,),
                base_weight=weight,
                authority=1.0,
                confidence=1.0,
                scope_key=body_scope,
                reality_key=body_reality,
                valid_from=valid_from,
                valid_to=valid_to,
                independent_source_key=source_key,
                provenance_ids=(provenance,),
                body_hash=_sha(payload),
            )
        )
        return output, body_id

    def finish(self) -> PublicFieldCase:
        if not self.influences:
            raise ValueError("case has no prompt")
        mean = tuple(
            sum(item.semantic_position[index] for item in self.influences) / len(self.influences)
            for index in range(128)
        )
        norm = math.sqrt(sum(item * item for item in mean))
        anchor = tuple(item / norm for item in mean)
        prompt = CompiledPromptField(
            prompt_id=self.case_id,
            influences=tuple(self.influences),
            anchor_position=anchor,
            disposition="accept",
            failure_codes=(),
            encoder_calls=1,
            source_hash=_sha(tuple((item.semantic_key, item.polarity_sign) for item in self.influences)),
        )
        return PublicFieldCase(self.case_id, prompt, tuple(self.units), tuple(self.bodies), tuple(self.vectors))


def _math_states(topic: str, depth: int) -> tuple[str, ...]:
    variable = f"x_{topic[:6]}"
    expressions = [variable]
    for index in range(depth):
        operator = "+0" if index % 2 == 0 else "*1"
        expressions.append(f"({expressions[-1]}{operator})")
    return tuple(f"math|{topic}|{item}" for item in reversed(expressions))


def _abstract_state(topic: str, index: int) -> str:
    return f"abstract|{topic}|s_{_opaque(topic, index, width=16)}"


def _chain_keys(domain: str, topic: str, depth: int) -> tuple[str, ...]:
    if domain == "math":
        return _math_states(topic, depth)
    return tuple(_abstract_state(topic, index) for index in range(depth + 1))


def _math_branch_keys(topic: str) -> tuple[str, str, str, str]:
    variable = f"x_{topic[:6]}"
    return (
        f"math|{topic}|(({variable}+0)*1)",
        f"math|{topic}|({variable}+0)",
        f"math|{topic}|({variable}*1)",
        f"math|{topic}|{variable}",
    )


def _depth_for(family: str, index: int) -> int:
    cycle = index // len(FAMILIES)
    if family == "one_body":
        return 1
    if family == "dependency_2_4":
        return 2 + cycle % 3
    if family == "dependency_5_8":
        return 5 + cycle % 4
    if family == "dependency_9_16":
        return 9 + cycle % 8
    if family == "conjunction":
        return 2 + cycle % 3
    return 1


def build_case(
    index: int,
    seed: int,
    *,
    split: str = "development",
    family: str | None = None,
    domain: str | None = None,
) -> GeneratedCase:
    """Build one deterministic public/gold pair without global state."""

    family = family or FAMILIES[index % len(FAMILIES)]
    if family not in FAMILIES:
        raise ValueError(f"unknown L5 fixture family: {family}")
    domain = domain or ("math" if (index // len(FAMILIES)) % 2 == 0 else "abstract")
    if domain not in {"math", "abstract"}:
        raise ValueError(f"unknown L5 fixture domain: {domain}")
    case_id = f"l5:{split}:{_opaque(split, seed, index)}"
    topic = _opaque("topic", split, seed, index, width=16)
    reality = "standard-math" if domain == "math" else f"user-reality:{topic}"
    builder = _Builder(case_id, topic, reality, "global")
    depth = _depth_for(family, index)

    if family in {"one_body", "dependency_2_4", "dependency_5_8", "dependency_9_16"}:
        keys = _chain_keys(domain, topic, depth)
        current = builder.prompt_unit(keys[0])
        for key in keys[1:]:
            current, _ = builder.body((current,), key, weight=0.9)
        expected = ExpectedOutcome(
            case_id, family, domain, depth, "candidate", (ExpectedCandidate(keys[-1], 1, 0.9),), (keys[-1], 1)
        )
    elif family == "conjunction":
        keys = _chain_keys(domain, topic, depth)
        left = builder.prompt_unit(keys[0])
        second_key = f"{domain}|{topic}|input_{_opaque(topic, 'second', width=12)}"
        right = builder.prompt_unit(second_key)
        current, _ = builder.body((left, right), keys[1], weight=0.88)
        for key in keys[2:]:
            current, _ = builder.body((current,), key, weight=0.88)
        expected = ExpectedOutcome(
            case_id, family, domain, depth, "candidate", (ExpectedCandidate(keys[-1], 1, 0.88),), (keys[-1], 1)
        )
    elif family in {"weighted_contradiction", "balanced_contradiction"}:
        if domain == "math":
            _branch, origin, _second, answer = _math_branch_keys(topic)
        else:
            origin = _chain_keys(domain, topic, 1)[0]
            answer = f"{domain}|{topic}|outcome_{_opaque(topic, 'contradiction', width=12)}"
        prompt_id = builder.prompt_unit(origin)
        positive_weight = 0.9 if family == "weighted_contradiction" else 0.75
        negative_weight = 0.35 if family == "weighted_contradiction" else 0.75
        repeated_source = f"source:{_opaque(case_id, 'positive')}"
        builder.body((prompt_id,), answer, polarity=1, weight=positive_weight, source_key=repeated_source)
        if family == "weighted_contradiction":
            builder.body((prompt_id,), answer, polarity=1, weight=0.8, source_key=repeated_source)
        builder.body((prompt_id,), answer, polarity=-1, weight=negative_weight)
        disposition = "candidate" if family == "weighted_contradiction" else "ambiguous"
        selected = (answer, 1) if family == "weighted_contradiction" else None
        expected = ExpectedOutcome(
            case_id,
            family,
            domain,
            1,
            disposition,
            (
                ExpectedCandidate(answer, 1, positive_weight),
                ExpectedCandidate(answer, -1, negative_weight),
            ),
            selected,
        )
    elif family == "alternatives":
        if domain == "math":
            origin, first, second, _terminal = _math_branch_keys(topic)
        else:
            origin = _chain_keys(domain, topic, 1)[0]
            first = f"{domain}|{topic}|alternative_{_opaque(topic, 0, width=10)}"
            second = f"{domain}|{topic}|alternative_{_opaque(topic, 1, width=10)}"
        prompt_id = builder.prompt_unit(origin)
        builder.body((prompt_id,), first, weight=0.8)
        builder.body((prompt_id,), second, weight=0.8)
        expected = ExpectedOutcome(
            case_id,
            family,
            domain,
            1,
            "alternatives",
            (ExpectedCandidate(first, 1, 0.8), ExpectedCandidate(second, 1, 0.8)),
            None,
        )
    elif family == "scope_isolation":
        if domain == "math":
            _branch, origin, _second, correct = _math_branch_keys(topic)
            wrong = correct
        else:
            origin = _chain_keys(domain, topic, 1)[0]
            correct = f"{domain}|{topic}|in_scope"
            wrong = f"{domain}|{topic}|out_of_scope"
        prompt_id = builder.prompt_unit(origin)
        builder.body((prompt_id,), correct, weight=0.85)
        builder.body((prompt_id,), wrong, weight=0.99, scope="session:other")
        builder.body((prompt_id,), wrong, weight=0.99, reality=f"other-reality:{topic}")
        expected = ExpectedOutcome(
            case_id, family, domain, 1, "candidate", (ExpectedCandidate(correct, 1, 0.85),), (correct, 1)
        )
    else:
        keys = _chain_keys(domain, topic, 1)
        prompt_id = builder.prompt_unit(keys[0])
        missing = builder.unit(
            f"{domain}|{topic}|missing_{_opaque(topic, 'missing', width=10)}",
            body_id=f"substrate:{case_id}",
            phase=0,
            source_key=f"source:{_opaque(case_id, 'missing')}",
        )
        builder.body((prompt_id, missing), keys[1], weight=0.9)
        expected = ExpectedOutcome(case_id, family, domain, 1, "unknown", (), None)

    public = builder.finish()
    return GeneratedCase(public, expected)


def iter_cases(
    count: int,
    seed: int,
    *,
    split: str = "development",
    family: str | None = None,
    domain: str | None = None,
) -> Iterator[GeneratedCase]:
    if count < 0:
        raise ValueError("case count cannot be negative")
    for index in range(count):
        yield build_case(index, seed, split=split, family=family, domain=domain)


def build_dependency_case(
    index: int,
    seed: int,
    *,
    depth: int,
    split: str = "stress",
    domain: str = "abstract",
) -> GeneratedCase:
    """Build an explicit-depth chain without exposing depth to runtime IDs."""

    if not 1 <= depth <= 64:
        raise ValueError("L5 dependency depth must lie in [1,64]")
    if domain not in {"math", "abstract"}:
        raise ValueError("unknown L5 fixture domain")
    case_id = f"l5:{split}:{_opaque(split, seed, index, 'dependency')}"
    topic = _opaque("topic", split, seed, index, "dependency", width=16)
    reality = "standard-math" if domain == "math" else f"user-reality:{topic}"
    builder = _Builder(case_id, topic, reality, "global")
    keys = _chain_keys(domain, topic, depth)
    current = builder.prompt_unit(keys[0])
    for key in keys[1:]:
        current, _ = builder.body((current,), key, weight=0.9)
    expected = ExpectedOutcome(
        case_id,
        "dependency_stress",
        domain,
        depth,
        "candidate",
        (ExpectedCandidate(keys[-1], 1, 0.9),),
        (keys[-1], 1),
    )
    return GeneratedCase(builder.finish(), expected)


def public_payload(case: PublicFieldCase) -> dict[str, object]:
    payload = asdict(case)

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, (tuple, list)):
            return set().union(*(keys(item) for item in value))
        return set()

    if FORBIDDEN_PUBLIC_FIELDS.intersection(keys(payload)):
        raise RuntimeError("forbidden evaluator field in public fixture")
    return payload


def expected_payload(expected: ExpectedOutcome) -> dict[str, object]:
    return asdict(expected)
