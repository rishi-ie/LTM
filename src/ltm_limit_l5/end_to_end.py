"""Fresh raw compiler-to-equilibrium chains for the locked L5 handoff panel."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np

from .compiler import (
    ControlledCompilerSource,
    CoordinateEncoder,
    SharedCoordinateCompiler,
    controlled_source,
)
from .compiler_eval import atom_semantic_key, controlled_atom
from .decoder import authorize, realize
from .field import EquilibriumFieldIndex, build_minimap
from .optimizer import Compatibility, optimize
from .verifier import certify_result
from .writer import assemble_public_case


@dataclass(frozen=True, slots=True)
class RawChainCase:
    case_id: str
    sources: tuple[ControlledCompilerSource, ...]
    prompt: ControlledCompilerSource
    expected_semantic_key: str | None
    depth: int
    expected_disposition: str = "candidate"
    expected_candidates: tuple[tuple[str, int], ...] = ()


def _public_token(seed: int, split: str, index: int, variant: str) -> str:
    """Hide evaluator construction labels behind a stable public identity."""

    return hashlib.sha256(f"{seed}|{split}|{index}|{variant}".encode()).hexdigest()[:20]


def build_raw_chain_case(index: int, seed: int, *, split: str) -> RawChainCase:
    depth = 1 + index % 16
    atoms = tuple(
        controlled_atom(seed, index * 17 + ordinal, "state")
        for ordinal in range(depth + 1)
    )
    token = _public_token(seed, split, index, "ordinary")
    case_id = f"{split}:item:{token}"
    reality = f"reality:{split}:{token}"
    sources = tuple(
        controlled_source(
            f"when {atoms[ordinal]} then {atoms[ordinal + 1]}",
            source_id=f"{case_id}:source:{ordinal}",
            reality_key=reality,
            provenance_id=f"{case_id}:document:{ordinal}",
        )
        for ordinal in range(depth)
    )
    prompt = controlled_source(
        f"given {atoms[0]}, what follows?",
        source_id=f"{case_id}:prompt",
        reality_key=reality,
        provenance_id=f"{case_id}:request",
    )
    return RawChainCase(
        case_id,
        sources,
        prompt,
        atom_semantic_key(atoms[-1]),
        depth,
        "candidate",
        ((atom_semantic_key(atoms[-1]), 1),),
    )


def _raw_special_case(
    index: int,
    seed: int,
    *,
    split: str,
    family: str,
) -> RawChainCase:
    origin = controlled_atom(seed, index * 17, "state")
    missing = controlled_atom(seed, index * 17 + 1, "state")
    first = controlled_atom(seed, index * 17 + 2, "state")
    second = controlled_atom(seed, index * 17 + 3, "state")
    token = _public_token(seed, split, index, family)
    case_id = f"{split}:item:{token}"
    reality = f"reality:{split}:{token}"
    common = {
        "scope_key": "global",
        "reality_key": reality,
    }
    if family == "unknown":
        sources = (
            controlled_source(
                f"when {origin} and {missing} then {first}",
                source_id=f"{case_id}:source:0",
                provenance_id=f"{case_id}:document:0",
                **common,
            ),
        )
        disposition = "unknown"
        expected = ()
    elif family == "balanced_conflict":
        sources = tuple(
            controlled_source(
                f"when {origin} then {first}",
                source_id=f"{case_id}:source:{ordinal}",
                provenance_id=f"{case_id}:document:{ordinal}",
                polarity=polarity,
                **common,
            )
            for ordinal, polarity in enumerate((1, -1))
        )
        disposition = "ambiguous"
        expected = ((atom_semantic_key(first), -1), (atom_semantic_key(first), 1))
    elif family == "alternatives":
        sources = tuple(
            controlled_source(
                f"when {origin} then {outcome}",
                source_id=f"{case_id}:source:{ordinal}",
                provenance_id=f"{case_id}:document:{ordinal}",
                **common,
            )
            for ordinal, outcome in enumerate((first, second))
        )
        disposition = "alternatives"
        expected = tuple(
            sorted(((atom_semantic_key(first), 1), (atom_semantic_key(second), 1)))
        )
    else:
        raise ValueError(f"unknown raw end-to-end family: {family}")
    prompt = controlled_source(
        f"given {origin}, what follows?",
        source_id=f"{case_id}:prompt",
        provenance_id=f"{case_id}:request",
        **common,
    )
    return RawChainCase(
        case_id,
        sources,
        prompt,
        None,
        1,
        disposition,
        expected,
    )


def build_raw_end_to_end_panel(
    count: int,
    seed: int,
    *,
    split: str,
) -> tuple[RawChainCase, ...]:
    """Keep most cases answerable while including every safe-null branch."""

    if count < 21:
        raise ValueError("raw end-to-end panel requires at least twenty-one cases")
    special_count = max(3, count // 4)
    answerable_count = count - special_count
    rows = [
        build_raw_chain_case(index, seed, split=split)
        for index in range(answerable_count)
    ]
    families = ("unknown", "balanced_conflict", "alternatives")
    rows.extend(
        _raw_special_case(
            index,
            seed,
            split=split,
            family=families[index % len(families)],
        )
        for index in range(special_count)
    )
    return tuple(rows)


def raw_chain_public_payload(case: RawChainCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "sources": tuple(asdict(item) for item in case.sources),
        "prompt": asdict(case.prompt),
    }


def raw_chain_gold_payload(case: RawChainCase) -> dict[str, object]:
    certificate_counts = tuple(
        (semantic_key, polarity, case.depth if case.expected_disposition == "candidate" else 1)
        for semantic_key, polarity in case.expected_candidates
    )
    return {
        "case_id": case.case_id,
        "expected_semantic_key": case.expected_semantic_key,
        "depth": case.depth,
        "expected_disposition": case.expected_disposition,
        "expected_candidates": case.expected_candidates,
        "expected_certificate_body_counts": certificate_counts,
        "family": (
            "answerable"
            if case.expected_disposition == "candidate"
            else "balanced_conflict"
            if case.expected_disposition == "ambiguous"
            else case.expected_disposition
        ),
    }


def compile_raw_chain(
    public: dict[str, object],
    encoder: CoordinateEncoder,
    *,
    compatibility: Compatibility | None = None,
    compiler_confidence_threshold: float = 0.95,
    confidence_threshold: float = 0.50,
    margin_threshold: float = 0.05,
    coverage_threshold: float = 0.90,
    convergence_residual: float = 1e-3,
    maximum_steps: int = 64,
    maximum_bodies: int = 128,
    maximum_cumulative_bodies: int = 2048,
    maximum_modes: int = 8,
    inner_updates: int = 4,
) -> dict[str, object]:
    """Runtime path that has no expected answer or depth argument."""

    calls_before = encoder.forward_calls
    source_rows = public["sources"]
    prompt_row = public["prompt"]
    if not isinstance(source_rows, (tuple, list)) or not isinstance(prompt_row, dict):
        raise TypeError("invalid raw chain public payload")
    compiler = SharedCoordinateCompiler(
        encoder, minimum_confidence=compiler_confidence_threshold
    )
    sources = tuple(
        compiler.compile_source(ControlledCompilerSource(**row))
        for row in source_rows
    )
    prompt = compiler.compile_prompt(ControlledCompilerSource(**prompt_row))
    case = assemble_public_case(prompt, sources)
    vectors = np.asarray(case.vector_table, dtype=np.float32)
    cells, summaries = build_minimap(case.bodies, case.units, vectors)
    index = EquilibriumFieldIndex(case.bodies, case.units, vectors, cells, summaries)
    result = certify_result(
        case,
        optimize(
            index,
            prompt,
            compatibility=compatibility,
            confidence_threshold=confidence_threshold,
            margin_threshold=margin_threshold,
            coverage_threshold=coverage_threshold,
            convergence_residual=convergence_residual,
            maximum_steps=maximum_steps,
            maximum_bodies=maximum_bodies,
            maximum_cumulative_bodies=maximum_cumulative_bodies,
            maximum_modes=maximum_modes,
            inner_updates=inner_updates,
        ),
    )
    view = authorize(result)
    output = realize(view, {item.semantic_key: item.semantic_key for item in case.units})
    selected = next(
        (
            item.semantic_key
            for item in result.candidates
            if item.unit_id == result.selected_candidate_id
        ),
        None,
    )
    candidate_states = tuple(
        sorted((item.semantic_key, item.polarity) for item in result.candidates)
    )
    certificate_counts = tuple(
        sorted(
            (
                item.semantic_key,
                item.polarity,
                len(certificate.body_ids),
            )
            for item in result.candidates
            for certificate in result.certificates
            if certificate.candidate_unit_id == item.unit_id
        )
    )
    return {
        "case_id": public["case_id"],
        "disposition": result.disposition,
        "selected_semantic_key": selected,
        "certificate_body_count": (
            len(result.certificates[0].body_ids) if result.certificates else 0
        ),
        "candidate_states": candidate_states,
        "certificate_body_counts": certificate_counts,
        "decoder_authorized": not output.failure_codes,
        "encoder_calls": encoder.forward_calls - calls_before,
        "factual_operations": result.factual_operations,
    }


def score_raw_chains(
    public_rows: tuple[dict[str, object], ...],
    gold_rows: tuple[dict[str, object], ...],
    predictions: tuple[dict[str, object], ...],
) -> dict[str, object]:
    if not (len(public_rows) == len(gold_rows) == len(predictions)):
        raise ValueError("raw chain panel length mismatch")
    correct = accepted = accepted_correct = exact_calls = 0
    depth: dict[str, list[bool]] = {}
    family: dict[str, list[bool]] = {}
    for public, gold, predicted in zip(public_rows, gold_rows, predictions, strict=True):
        if public["case_id"] != gold["case_id"] or public["case_id"] != predicted["case_id"]:
            raise ValueError("raw chain case identity mismatch")
        expected_candidates = tuple(
            sorted(tuple(item) for item in gold["expected_candidates"])
        )
        predicted_candidates = tuple(
            sorted(tuple(item) for item in predicted["candidate_states"])
        )
        expected_certificates = tuple(
            sorted(tuple(item) for item in gold["expected_certificate_body_counts"])
        )
        predicted_certificates = tuple(
            sorted(tuple(item) for item in predicted["certificate_body_counts"])
        )
        agrees = (
            predicted["disposition"] == gold["expected_disposition"]
            and predicted["selected_semantic_key"] == gold["expected_semantic_key"]
            and predicted_candidates == expected_candidates
            and predicted_certificates == expected_certificates
            and predicted["decoder_authorized"] is True
            and not predicted["factual_operations"]
        )
        accepted_now = predicted["disposition"] == "candidate"
        accepted += int(accepted_now)
        accepted_correct += int(accepted_now and agrees)
        correct += int(agrees)
        exact_calls += int(predicted["encoder_calls"] == len(public["sources"]) + 1)
        family.setdefault(str(gold["family"]), []).append(agrees)
        if gold["family"] == "answerable":
            depth.setdefault(str(gold["depth"]), []).append(agrees)
    safe_families = tuple(
        value
        for key, values in family.items()
        if key != "answerable"
        for value in values
    )
    return {
        "cases": len(public_rows),
        "accepted_precision": accepted_correct / accepted if accepted else 1.0,
        "safe_coverage": correct / len(public_rows) if public_rows else 1.0,
        "all_case_exactness": correct / len(public_rows) if public_rows else 1.0,
        "one_pass_per_item": exact_calls / len(public_rows) if public_rows else 1.0,
        "incorrect_accepted_predictions": accepted - accepted_correct,
        "unknown_or_alternative_agreement": (
            sum(safe_families) / len(safe_families) if safe_families else 1.0
        ),
        "family": {
            key: sum(values) / len(values) for key, values in sorted(family.items())
        },
        "depth": {
            key: sum(values) / len(values)
            for key, values in sorted(depth.items(), key=lambda item: int(item[0]))
        },
    }


__all__ = [
    "RawChainCase",
    "build_raw_chain_case",
    "build_raw_end_to_end_panel",
    "compile_raw_chain",
    "raw_chain_gold_payload",
    "raw_chain_public_payload",
    "score_raw_chains",
]
