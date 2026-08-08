from __future__ import annotations

import hashlib

import numpy as np

from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.optimizer import optimize
from ltm_limit_l5.schemas import (
    CompiledPromptField,
    EquilibriumBody,
    FieldMumbrane,
    PromptInfluenceRecord,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _vector(index: int) -> np.ndarray:
    row = np.zeros(128, dtype=np.float32)
    row[index] = 1.0
    return row


def _unit(unit_id: str, body_id: str, key: str, ref: int, phase: int, polarity: int = 1) -> FieldMumbrane:
    return FieldMumbrane(unit_id, body_id, key, ref, ref, phase, polarity, "asserted", "global", "standard", None, None, key, f"prov:{unit_id}", f"source:{body_id}")


def _body(body_id: str, inputs: tuple[str, ...], outcomes: tuple[str, ...], source: str | None = None, weight: float = 1.0) -> EquilibriumBody:
    return EquilibriumBody(body_id, inputs, outcomes, weight, 1.0, 1.0, "global", "standard", None, None, source or f"source:{body_id}", tuple(f"prov:{item}" for item in outcomes), _sha(body_id))


def _prompt(*items: tuple[str, str, np.ndarray]) -> CompiledPromptField:
    influences = tuple(
        PromptInfluenceRecord(unit_id, key, tuple(float(value) for value in vector), 1.0, 1.0, 1, 1.0, "global", "standard", None, 1.0, f"prompt:{unit_id}")
        for unit_id, key, vector in items
    )
    anchor = np.mean([item[2] for item in items], axis=0)
    anchor /= np.linalg.norm(anchor)
    return CompiledPromptField("prompt", influences, tuple(float(value) for value in anchor), "accept", (), 1, _sha("prompt"))


def _index(bodies: tuple[EquilibriumBody, ...], units: tuple[FieldMumbrane, ...], vectors: np.ndarray, *, leaf_limit: int = 1) -> EquilibriumFieldIndex:
    cells, summaries = build_minimap(bodies, units, vectors, leaf_limit=leaf_limit, fanout=2)
    return EquilibriumFieldIndex(bodies, units, vectors, cells, summaries)


def test_two_body_equilibrium_reopens_frontier_and_keeps_anchor_fixed() -> None:
    vectors = np.stack((_vector(0), _vector(1), _vector(2)))
    units = (
        _unit("u:a", "b:ab", "A", 0, 0),
        _unit("u:b", "b:ab", "B", 1, 1),
        _unit("u:c", "b:bc", "C", 2, 1),
    )
    bodies = (_body("b:ab", ("u:a",), ("u:b",)), _body("b:bc", ("u:b",), ("u:c",)))
    prompt = _prompt(("p:a", "A", vectors[0]))
    result = optimize(_index(bodies, units, vectors), prompt, maximum_bodies=1, confidence_threshold=0.7)
    assert result.disposition == "candidate"
    assert result.candidates[0].semantic_key == "C"
    assert result.initial_modes[0].semantic_position == prompt.anchor_position
    assert result.final_modes[0].semantic_position != prompt.anchor_position
    assert any(snapshot.opened_body_ids == ("b:bc",) for snapshot in result.frontiers)
    assert all(later.energy <= earlier.energy + 1e-7 for earlier, later in zip(result.trajectory, result.trajectory[1:]))
    assert not result.factual_operations


def test_conjunction_requires_every_compiled_input() -> None:
    vectors = np.stack((_vector(0), _vector(1), _vector(2)))
    units = (
        _unit("u:a", "b:all", "A", 0, 0),
        _unit("u:d", "b:all", "D", 1, 0),
        _unit("u:e", "b:all", "E", 2, 1),
    )
    body = _body("b:all", ("u:a", "u:d"), ("u:e",))
    index = _index((body,), units, vectors)
    missing = optimize(index, _prompt(("p:a", "A", vectors[0])))
    complete = optimize(index, _prompt(("p:a", "A", vectors[0]), ("p:d", "D", vectors[1])))
    assert missing.disposition == "unknown"
    assert not missing.candidates
    assert complete.disposition == "candidate"
    assert complete.candidates[0].semantic_key == "E"


def test_opposing_equal_support_remains_two_modes_and_ambiguous() -> None:
    vectors = np.stack((_vector(0), _vector(1)))
    units = (
        _unit("u:a", "b:yes", "A", 0, 0),
        _unit("u:yes", "b:yes", "X", 1, 1, 1),
        _unit("u:no", "b:no", "X", 1, 1, -1),
    )
    bodies = (
        _body("b:yes", ("u:a",), ("u:yes",), "independent:yes"),
        _body("b:no", ("u:a",), ("u:no",), "independent:no"),
    )
    result = optimize(_index(bodies, units, vectors), _prompt(("p:a", "A", vectors[0])))
    assert result.disposition == "ambiguous"
    assert {mode.polarity for mode in result.final_modes} == {-1, 1}
    assert {(item.semantic_key, item.polarity) for item in result.candidates} == {("X", -1), ("X", 1)}


def test_independent_sources_outweigh_opposition_but_duplicates_do_not() -> None:
    vectors = np.stack((_vector(0), _vector(1)))
    units = (
        _unit("u:a", "b:p1", "A", 0, 0),
        _unit("u:p1", "b:p1", "X", 1, 1, 1),
        _unit("u:p2", "b:p2", "X", 1, 1, 1),
        _unit("u:pd", "b:pd", "X", 1, 1, 1),
        _unit("u:n", "b:n", "X", 1, 1, -1),
    )
    bodies = (
        _body("b:p1", ("u:a",), ("u:p1",), "positive:one"),
        _body("b:p2", ("u:a",), ("u:p2",), "positive:two"),
        _body("b:pd", ("u:a",), ("u:pd",), "positive:one"),
        _body("b:n", ("u:a",), ("u:n",), "negative:one"),
    )
    result = optimize(_index(bodies, units, vectors), _prompt(("p:a", "A", vectors[0])))
    assert result.disposition == "candidate"
    assert result.candidates[0].polarity == 1
    positive = next(item for item in result.candidates if item.polarity == 1)
    assert set(positive.supporting_source_keys) == {"positive:one", "positive:two"}


def test_optional_compatibility_changes_geometry_not_exact_authority() -> None:
    vectors = np.stack((_vector(0), _vector(1)))
    units = (_unit("u:a", "b:ab", "A", 0, 0), _unit("u:b", "b:ab", "B", 1, 1))
    body = _body("b:ab", ("u:a",), ("u:b",))
    index = _index((body,), units, vectors)
    prompt = _prompt(("p:a", "A", vectors[0]))
    baseline = optimize(index, prompt)
    result = optimize(index, prompt, compatibility=lambda *_: 0.0)
    assert result.disposition == baseline.disposition == "candidate"
    assert result.selected_candidate_id == baseline.selected_candidate_id
    assert result.final_modes[0].semantic_position != baseline.final_modes[0].semantic_position


def test_alternative_children_close_siblings_without_claiming_their_support() -> None:
    vectors = np.stack((_vector(0), _vector(1), _vector(2)))
    units = (
        _unit("u:a", "b:x", "A", 0, 0),
        _unit("u:x", "b:x", "X", 1, 1),
        _unit("u:y", "b:y", "Y", 2, 1),
    )
    bodies = (
        _body("b:x", ("u:a",), ("u:x",), "source:x"),
        _body("b:y", ("u:a",), ("u:y",), "source:y"),
    )
    result = optimize(_index(bodies, units, vectors), _prompt(("p:a", "A", vectors[0])))
    assert result.disposition == "alternatives"
    supports = {item.semantic_key: item.supporting_body_ids for item in result.candidates}
    assert supports == {"X": ("b:x",), "Y": ("b:y",)}
