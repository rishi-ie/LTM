"""Controlled shared-coordinate compiler for L5.

Exact mathematical content and public context metadata remain authoritative.
The encoder supplies geometry only and is called exactly once per item.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ltm_inference_i3.formal import expression_hash
from ltm_inference_i3.schemas import FormalExpression
from ltm_limit_l3.parser import ParseError, looks_open_ended, parse_proposition

from .schemas import CompiledPromptField, PromptInfluenceRecord

STATE_DIMENSION = 128
DEFAULT_MINIMUM_CONFIDENCE = 0.95
MODALITY_WEIGHTS = {
    "asserted": 1.0,
    "observed": 1.0,
    "hypothetical": 0.5,
    "uncertain": 0.35,
    "quoted": 0.25,
}


class CompilerIntegrityError(RuntimeError):
    """The encoder violated the one-pass or coordinate contract."""


class CoordinateEncoder(Protocol):
    """A frozen semantic encoder plus the shared learned 384D-to-128D projection."""

    forward_calls: int

    def encode(self, source_id: str, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class ControlledCompilerSource:
    source_id: str
    text: str
    source_hash: str
    scope_key: str
    reality_key: str
    valid_at: int | None
    polarity: int
    modality: str
    compiler_confidence: float
    provenance_id: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.scope_key or not self.reality_key or not self.provenance_id:
            raise ValueError("invalid compiler source identity")
        if self.polarity not in {-1, 1}:
            raise ValueError("invalid compiler polarity")
        if self.modality not in MODALITY_WEIGHTS:
            raise ValueError("invalid compiler modality")
        if not math.isfinite(self.compiler_confidence) or not 0 <= self.compiler_confidence <= 1:
            raise ValueError("invalid compiler confidence")
        if self.source_hash != _source_hash(self):
            raise ValueError("compiler source hash mismatch")


@dataclass(frozen=True, slots=True)
class ParsedControlledContent:
    source_expression: FormalExpression | None
    goal_expression: FormalExpression | None
    semantic_key: str
    content_kind: str
    input_keys: tuple[str, ...]
    outcome_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompiledSourceCoordinate:
    """Non-authoritative candidate produced for later atomic field assembly."""

    source_id: str
    content: ParsedControlledContent | None
    semantic_position: tuple[float, ...]
    scope_key: str
    reality_key: str
    valid_at: int | None
    polarity: int
    modality: str
    modality_weight: float
    compiler_confidence: float
    disposition: str
    failure_codes: tuple[str, ...]
    encoder_calls: int
    source_hash: str
    provenance_id: str
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if len(self.semantic_position) != STATE_DIMENSION or self.encoder_calls != 1:
            raise ValueError("invalid source compilation boundary")
        if self.disposition not in {"accept", "clarification_required", "quarantine"}:
            raise ValueError("invalid source compiler disposition")
        if self.factual_operations:
            raise ValueError("compiler candidates cannot mutate factual topology")


def _source_hash_fields(
    source_id: str,
    text: str,
    scope_key: str,
    reality_key: str,
    valid_at: int | None,
    polarity: int,
    modality: str,
    provenance_id: str,
) -> str:
    payload = json.dumps(
        (source_id, text, scope_key, reality_key, valid_at, polarity, modality, provenance_id),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _source_hash(source: ControlledCompilerSource) -> str:
    return _source_hash_fields(
        source.source_id,
        source.text,
        source.scope_key,
        source.reality_key,
        source.valid_at,
        source.polarity,
        source.modality,
        source.provenance_id,
    )


def controlled_source(
    text: str,
    *,
    source_id: str = "source:local",
    scope_key: str = "global",
    reality_key: str = "standard-v1",
    valid_at: int | None = None,
    polarity: int = 1,
    modality: str = "asserted",
    compiler_confidence: float = 1.0,
    provenance_id: str | None = None,
) -> ControlledCompilerSource:
    provenance = provenance_id or source_id
    digest = _source_hash_fields(
        source_id, text, scope_key, reality_key, valid_at, polarity, modality, provenance
    )
    return ControlledCompilerSource(
        source_id,
        text,
        digest,
        scope_key,
        reality_key,
        valid_at,
        polarity,
        modality,
        compiler_confidence,
        provenance,
    )


_ATOM = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]*")
_ABSTRACT_BODY = re.compile(r"when\s+(.+?)\s+then\s+(.+?)\.?", re.IGNORECASE)
_ABSTRACT_PROMPT = re.compile(r"given\s+(.+?)\s*,\s*what\s+follows\s*\?", re.IGNORECASE)
_FORBIDDEN_METADATA = re.compile(
    r"\b(?:answer|answer_id|answer_candidates|expected_answer|expected_disposition|"
    r"expected_depth|required_body_ids|route|route_identifier|template_identifier|proof|"
    r"evaluator_path)\b",
    re.IGNORECASE,
)


def _atom_key(atom: str) -> str:
    return "atom:" + hashlib.sha256(atom.encode()).hexdigest()


def _atom_keys(value: str) -> tuple[str, ...]:
    atoms = tuple(part.strip() for part in re.split(r"\s+and\s+", value, flags=re.IGNORECASE))
    if not atoms or any(not atom or _ATOM.fullmatch(atom) is None for atom in atoms):
        raise ParseError("ABSTRACT_ATOM_MALFORMED")
    if len(set(atoms)) != len(atoms):
        raise ParseError("ABSTRACT_ATOM_DUPLICATE")
    return tuple(_atom_key(atom) for atom in atoms)


def _abstract_content(text: str) -> ParsedControlledContent | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith("when"):
        match = _ABSTRACT_BODY.fullmatch(stripped)
        if match is None:
            raise ParseError("ABSTRACT_BODY_MALFORMED")
        inputs, outcomes = _atom_keys(match.group(1)), _atom_keys(match.group(2))
        payload = ("abstract_body", inputs, outcomes)
        return ParsedControlledContent(
            None,
            None,
            "abstract:" + hashlib.sha256(repr(payload).encode()).hexdigest(),
            "abstract_body",
            inputs,
            outcomes,
        )
    if lowered.startswith("given"):
        match = _ABSTRACT_PROMPT.fullmatch(stripped)
        if match is None:
            raise ParseError("ABSTRACT_PROMPT_MALFORMED")
        inputs = _atom_keys(match.group(1))
        payload = ("abstract_prompt", inputs)
        return ParsedControlledContent(
            None,
            None,
            "abstract:" + hashlib.sha256(repr(payload).encode()).hexdigest(),
            "abstract_prompt",
            inputs,
            (),
        )
    return None


def parse_controlled_content(text: str) -> ParsedControlledContent:
    if _FORBIDDEN_METADATA.search(text):
        raise ParseError("FORBIDDEN_RUNTIME_METADATA")
    abstract = _abstract_content(text)
    if abstract is not None:
        return abstract
    if looks_open_ended(text):
        raise ParseError("GOAL_DISCOVERY_REQUIRED")
    source_expression, goal_expression = parse_proposition(text)
    semantic_payload = (
        expression_hash(source_expression),
        expression_hash(goal_expression),
    )
    semantic_key = "math:" + hashlib.sha256(repr(semantic_payload).encode()).hexdigest()
    return ParsedControlledContent(
        source_expression,
        goal_expression,
        semantic_key,
        "math",
        (expression_hash(source_expression),),
        (expression_hash(goal_expression),),
    )


def _coordinate(source: ControlledCompilerSource, encoder: CoordinateEncoder) -> tuple[float, ...]:
    before = encoder.forward_calls
    values = tuple(float(value) for value in encoder.encode(source.source_id, source.text))
    if encoder.forward_calls - before != 1:
        raise CompilerIntegrityError("ENCODER_CALL_COUNT_MISMATCH")
    if len(values) != STATE_DIMENSION or any(not math.isfinite(value) for value in values):
        raise CompilerIntegrityError("INVALID_SHARED_COORDINATE")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise CompilerIntegrityError("ZERO_SHARED_COORDINATE")
    return tuple(value / norm for value in values)


def _content_or_failure(text: str) -> tuple[ParsedControlledContent | None, tuple[str, ...]]:
    try:
        return parse_controlled_content(text), ()
    except ParseError as error:
        return None, (str(error),)


def compile_prompt(
    source: ControlledCompilerSource,
    encoder: CoordinateEncoder,
    *,
    minimum_confidence: float = DEFAULT_MINIMUM_CONFIDENCE,
) -> CompiledPromptField:
    """Compile one controlled prompt without granting it factual authority."""

    coordinate = _coordinate(source, encoder)
    content, failures = _content_or_failure(source.text)
    if content is not None and content.content_kind == "abstract_body":
        failures += ("PROMPT_FORM_REQUIRED",)
    if source.compiler_confidence < minimum_confidence:
        failures += ("LOW_COMPILER_CONFIDENCE",)
    accepted = content is not None and not failures
    influences = ()
    if accepted:
        influence_keys = content.input_keys
        influences = tuple(
            PromptInfluenceRecord(
                unit_id=f"prompt:{source.source_hash[:20]}:{index}",
                semantic_key=semantic_key,
                semantic_position=coordinate,
                clamp_strength=1.0,
                query_relevance_weight=source.compiler_confidence,
                polarity_sign=source.polarity,
                modality_weight=MODALITY_WEIGHTS[source.modality],
                scope_key=source.scope_key,
                reality_key=source.reality_key,
                valid_at=source.valid_at,
                compiler_confidence=source.compiler_confidence,
                provenance_id=source.provenance_id,
            )
            for index, semantic_key in enumerate(influence_keys)
        )
    return CompiledPromptField(
        prompt_id=source.source_id,
        influences=influences,
        anchor_position=coordinate,
        disposition="accept" if accepted else "clarification_required",
        failure_codes=failures,
        encoder_calls=1,
        source_hash=source.source_hash,
    )


def compile_source(
    source: ControlledCompilerSource,
    encoder: CoordinateEncoder,
    *,
    minimum_confidence: float = DEFAULT_MINIMUM_CONFIDENCE,
) -> CompiledSourceCoordinate:
    """Compile a stored item as an uncommitted candidate in the shared space."""

    coordinate = _coordinate(source, encoder)
    content, failures = _content_or_failure(source.text)
    if content is not None and content.content_kind == "abstract_prompt":
        failures += ("SOURCE_BODY_REQUIRED",)
    if source.compiler_confidence < minimum_confidence:
        failures += ("LOW_COMPILER_CONFIDENCE",)
    accepted = content is not None and not failures
    return CompiledSourceCoordinate(
        source_id=source.source_id,
        content=content if accepted else None,
        semantic_position=coordinate,
        scope_key=source.scope_key,
        reality_key=source.reality_key,
        valid_at=source.valid_at,
        polarity=source.polarity,
        modality=source.modality,
        modality_weight=MODALITY_WEIGHTS[source.modality],
        compiler_confidence=source.compiler_confidence,
        disposition="accept" if accepted else "clarification_required",
        failure_codes=failures,
        encoder_calls=1,
        source_hash=source.source_hash,
        provenance_id=source.provenance_id,
    )


class DeterministicCoordinateEncoder:
    """Hash coordinate source for tests; never an authoritative semantic model."""

    def __init__(self) -> None:
        self.forward_calls = 0

    def encode(self, source_id: str, text: str) -> tuple[float, ...]:
        del source_id
        self.forward_calls += 1
        raw = hashlib.shake_256(text.encode()).digest(STATE_DIMENSION * 2)
        return tuple(
            (int.from_bytes(raw[index : index + 2], "big") / 32767.5) - 1.0
            for index in range(0, len(raw), 2)
        )


class SharedCoordinateCompiler:
    """One encoder/projection boundary shared by source and prompt compilation."""

    def __init__(
        self,
        encoder: CoordinateEncoder,
        *,
        minimum_confidence: float = DEFAULT_MINIMUM_CONFIDENCE,
    ) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError("invalid compiler threshold")
        self.encoder = encoder
        self.minimum_confidence = minimum_confidence

    def compile_prompt(self, source: ControlledCompilerSource) -> CompiledPromptField:
        return compile_prompt(source, self.encoder, minimum_confidence=self.minimum_confidence)

    def compile_source(self, source: ControlledCompilerSource) -> CompiledSourceCoordinate:
        return compile_source(source, self.encoder, minimum_confidence=self.minimum_confidence)
