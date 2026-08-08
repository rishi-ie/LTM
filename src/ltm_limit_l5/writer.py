"""Atomic writer from accepted compiler coordinates to the L5 field substrate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .compiler import CompiledSourceCoordinate
from .dataset import PublicFieldCase
from .schemas import CompiledPromptField, EquilibriumBody, FieldMumbrane


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CompiledFieldArtifact:
    units: tuple[FieldMumbrane, ...]
    bodies: tuple[EquilibriumBody, ...]
    vector_table: tuple[tuple[float, ...], ...]
    source_hashes: tuple[str, ...]
    artifact_hash: str
    factual_operations: tuple[()] = ()

    def __post_init__(self) -> None:
        if not self.units or not self.bodies or not self.vector_table:
            raise ValueError("compiled field artifact cannot be empty")
        if len(self.artifact_hash) != 64 or self.factual_operations:
            raise ValueError("invalid compiled field artifact")


def assemble_sources(
    sources: tuple[CompiledSourceCoordinate, ...],
    *,
    base_weight: float = 0.90,
    authority: float = 1.0,
) -> CompiledFieldArtifact:
    """Commit accepted source candidates to exact phase-0/phase-1 bodies.

    Each source contributes one vector row. Exact input/outcome identity remains
    in sparse occurrence records; a shared vector is never allowed to invent a
    body, role, polarity, context, or source.
    """

    if not sources:
        raise ValueError("no compiled sources supplied")
    if not 0 <= base_weight <= 1 or not 0 <= authority <= 1:
        raise ValueError("field weights must lie in [0,1]")
    units: list[FieldMumbrane] = []
    bodies: list[EquilibriumBody] = []
    vectors: list[tuple[float, ...]] = []
    seen_source_hashes: set[str] = set()
    for source in sources:
        if source.disposition != "accept" or source.content is None:
            raise ValueError("unaccepted source cannot enter the active field")
        if source.failure_codes or source.factual_operations:
            raise ValueError("invalid compiler authority boundary")
        if source.content.content_kind not in {"math", "abstract_body"}:
            raise ValueError("source does not describe a complete body")
        if not source.content.input_keys or not source.content.outcome_keys:
            raise ValueError("source body is incomplete")
        if source.source_hash in seen_source_hashes:
            raise ValueError("duplicate compiled source transaction")
        seen_source_hashes.add(source.source_hash)
        vector_ref = len(vectors)
        vectors.append(source.semantic_position)
        body_id = f"l5-body:{_digest((source.source_hash, source.content.semantic_key))[:24]}"
        independent_source = source.provenance_id
        provenance = source.provenance_id

        def occurrence(
            semantic_key: str,
            phase: int,
            ordinal: int,
            polarity: int,
            *,
            owner_id: str = body_id,
            row_ref: int = vector_ref,
            modality: str = source.modality,
            scope_key: str = source.scope_key,
            reality_key: str = source.reality_key,
            valid_from: int | None = source.valid_at,
            provenance_id: str = provenance,
            source_key: str = independent_source,
        ) -> str:
            unit_id = f"l5-unit:{_digest((owner_id, phase, ordinal, semantic_key, polarity))[:24]}"
            units.append(
                FieldMumbrane(
                    unit_id=unit_id,
                    body_id=owner_id,
                    semantic_key=semantic_key,
                    semantic_vector_ref=row_ref,
                    local_index=len(units),
                    phase_index=phase,
                    polarity=polarity,
                    modality=modality,
                    scope_key=scope_key,
                    reality_key=reality_key,
                    valid_from=valid_from,
                    valid_to=None,
                    identity_key=f"identity:{_digest((reality_key, semantic_key))[:24]}",
                    provenance_id=provenance_id,
                    independent_source_key=source_key,
                )
            )
            return unit_id

        input_ids = tuple(
            occurrence(key, 0, ordinal, 1)
            for ordinal, key in enumerate(source.content.input_keys)
        )
        outcome_ids = tuple(
            occurrence(key, 1, ordinal, source.polarity)
            for ordinal, key in enumerate(source.content.outcome_keys)
        )
        body_payload = {
            "body_id": body_id,
            "inputs": input_ids,
            "outcomes": outcome_ids,
            "weight": base_weight,
            "authority": authority,
            "confidence": source.compiler_confidence,
            "scope": source.scope_key,
            "reality": source.reality_key,
            "valid_from": source.valid_at,
            "source": independent_source,
            "provenance": provenance,
        }
        bodies.append(
            EquilibriumBody(
                body_id=body_id,
                input_unit_ids=input_ids,
                outcome_unit_ids=outcome_ids,
                base_weight=base_weight,
                authority=authority,
                confidence=source.compiler_confidence,
                scope_key=source.scope_key,
                reality_key=source.reality_key,
                valid_from=source.valid_at,
                valid_to=None,
                independent_source_key=independent_source,
                provenance_ids=(provenance,),
                body_hash=_digest(body_payload),
            )
        )
    source_hashes = tuple(sorted(seen_source_hashes))
    payload = {
        "units": tuple(
            (
                item.unit_id,
                item.body_id,
                item.semantic_key,
                item.phase_index,
                item.polarity,
                item.scope_key,
                item.reality_key,
                item.provenance_id,
            )
            for item in units
        ),
        "bodies": tuple((item.body_id, item.body_hash) for item in bodies),
        "vectors": vectors,
        "sources": source_hashes,
    }
    return CompiledFieldArtifact(
        tuple(units),
        tuple(bodies),
        tuple(vectors),
        source_hashes,
        _digest(payload),
    )


def assemble_public_case(
    prompt: CompiledPromptField,
    sources: tuple[CompiledSourceCoordinate, ...],
) -> PublicFieldCase:
    artifact = assemble_sources(sources)
    return PublicFieldCase(
        prompt.prompt_id,
        prompt,
        artifact.units,
        artifact.bodies,
        artifact.vector_table,
    )


__all__ = ["CompiledFieldArtifact", "assemble_public_case", "assemble_sources"]
