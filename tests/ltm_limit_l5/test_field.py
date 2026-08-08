from __future__ import annotations

import hashlib

import numpy as np

from ltm_limit_l5.field import EquilibriumFieldIndex, build_minimap
from ltm_limit_l5.schemas import EquilibriumBody, FieldMumbrane


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _vector(index: int) -> np.ndarray:
    row = np.zeros(128, dtype=np.float32)
    row[index] = 1.0
    return row


def _unit(unit_id: str, body_id: str, key: str, ref: int, phase: int, *, polarity: int = 1, scope: str = "global", reality: str = "standard") -> FieldMumbrane:
    return FieldMumbrane(unit_id, body_id, key, ref, ref, phase, polarity, "asserted", scope, reality, None, None, key, f"prov:{unit_id}", f"source:{body_id}")


def _body(body_id: str, inputs: tuple[str, ...], outputs: tuple[str, ...], *, source: str | None = None, weight: float = 1.0, scope: str = "global", reality: str = "standard", valid_to: int | None = None) -> EquilibriumBody:
    return EquilibriumBody(body_id, inputs, outputs, weight, 1.0, 1.0, scope, reality, None, valid_to, source or f"source:{body_id}", tuple(f"prov:{item}" for item in outputs), _sha(body_id))


def _chain() -> tuple[tuple[EquilibriumBody, ...], tuple[FieldMumbrane, ...], np.ndarray]:
    units = (
        _unit("u:a", "b:ab", "A", 0, 0),
        _unit("u:b", "b:ab", "B", 1, 1),
        # b:bc consumes the occurrence emitted by b:ab.
        _unit("u:c", "b:bc", "C", 2, 1),
    )
    bodies = (
        _body("b:ab", ("u:a",), ("u:b",)),
        _body("b:bc", ("u:b",), ("u:c",)),
    )
    return bodies, units, np.stack((_vector(0), _vector(1), _vector(2)))


def test_cross_body_chain_reopens_from_new_semantic_position() -> None:
    bodies, units, vectors = _chain()
    cells, summaries = build_minimap(bodies, units, vectors, leaf_limit=1, fanout=2)
    index = EquilibriumFieldIndex(bodies, units, vectors, cells, summaries)
    _, first = index.frontier(vectors[0], "global", "standard", None, 1, frozenset({"A"}))
    _, second = index.frontier(vectors[1], "global", "standard", None, 1, frozenset({"A", "B"}))
    assert tuple(item.body_id for item in first) == ("b:ab",)
    assert tuple(item.body_id for item in second) == ("b:bc",)


def test_frontier_uses_cached_roots_and_records_indexed_access() -> None:
    bodies, units, vectors = _chain()
    cells, summaries = build_minimap(bodies, units, vectors, leaf_limit=1, fanout=2)
    index = EquilibriumFieldIndex(bodies, units, vectors, cells, summaries)

    class IndexedOnly(dict):
        def values(self):
            raise AssertionError("frontier rescanned every minimap cell")

    index.cells = IndexedOnly(index.cells)
    before = index.access_accounting()
    _, opened = index.frontier(vectors[0], "global", "standard", None, 1, frozenset({"A"}))
    after = index.access_accounting()
    assert opened and after.frontier_calls - before.frontier_calls == 1
    assert after.root_cell_reads - before.root_cell_reads == 1
    assert after.consumer_index_lookups - before.consumer_index_lookups == 1
    assert after.body_records_read > before.body_records_read
    assert after.full_field_scans == before.full_field_scans == 0


def test_minimap_is_insertion_invariant_and_accounts_for_every_body() -> None:
    bodies, units, vectors = _chain()
    cells, summaries = build_minimap(bodies, units, vectors, leaf_limit=1, fanout=2)
    reversed_cells, reversed_summaries = build_minimap(tuple(reversed(bodies)), tuple(reversed(units)), vectors, leaf_limit=1, fanout=2)
    assert cells == reversed_cells
    np.testing.assert_array_equal(summaries, reversed_summaries)
    leaves = [cell for cell in cells if not cell.child_ids]
    roots = [cell for cell in cells if cell.parent_id is None]
    assert [body_id for cell in leaves for body_id in cell.body_ids].count("b:ab") == 1
    assert set(roots[0].body_ids) == {body.body_id for body in bodies}


def test_exact_duplicates_collapse_but_independent_sources_accumulate_and_cap() -> None:
    inputs = (_unit("u:a", "b:one", "A", 0, 0),)
    outputs = (
        _unit("u:b1", "b:one", "B", 1, 1),
        _unit("u:b2", "b:two", "B", 1, 1),
        _unit("u:b3", "b:three", "B", 1, 1),
    )
    bodies = (
        _body("b:one", ("u:a",), ("u:b1",), source="same", weight=0.4),
        _body("b:two", ("u:a",), ("u:b2",), source="same", weight=0.8),
        _body("b:three", ("u:a",), ("u:b3",), source="independent", weight=0.7),
    )
    vectors = np.stack((_vector(0), _vector(1)))
    cells, summaries = build_minimap(bodies, inputs + outputs, vectors, source_mass_cap=1.0)
    index = EquilibriumFieldIndex(bodies, inputs + outputs, vectors, cells, summaries, source_mass_cap=1.0)
    weights = index.normalized_body_weights({body.body_id: 1.0 for body in bodies})
    assert weights["b:one"] == 0.0
    assert np.isclose(weights["b:two"], 0.8 / 1.5)
    assert np.isclose(weights["b:three"], 0.7 / 1.5)
    assert np.isclose(sum(weights.values()), 1.0)
    root = next(cell for cell in cells if cell.parent_id is None)
    assert root.positive_source_mass == 1.0


def test_scope_reality_and_time_are_exact_frontier_gates() -> None:
    units = (
        _unit("u:a", "b:ok", "A", 0, 0, scope="session"),
        _unit("u:b", "b:ok", "B", 1, 1, scope="session"),
        _unit("u:c", "b:foreign", "C", 2, 0, reality="other"),
        _unit("u:d", "b:foreign", "D", 3, 1, reality="other"),
    )
    bodies = (
        _body("b:ok", ("u:a",), ("u:b",), scope="session", valid_to=10),
        _body("b:foreign", ("u:c",), ("u:d",), reality="other"),
    )
    vectors = np.stack(tuple(_vector(i) for i in range(4)))
    cells, summaries = build_minimap(bodies, units, vectors, leaf_limit=1)
    index = EquilibriumFieldIndex(bodies, units, vectors, cells, summaries)
    _, active = index.frontier(vectors[0], "session", "standard", 5, 8, frozenset({"A"}))
    _, expired = index.frontier(vectors[0], "session", "standard", 11, 8, frozenset({"A"}))
    assert tuple(item.body_id for item in active) == ("b:ok",)
    assert not expired
    selected, active = index.frontier(vectors[0], "session", "standard", 5, 8, frozenset({"A"}))
    assert index.coverage_bound(selected, active, frozenset(), "session", "standard", 5) == 1.0
