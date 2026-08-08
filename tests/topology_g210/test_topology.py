import numpy as np

from topology_g210.dataset import generate, load_gold
from topology_g210.topology import (
    CELLS,
    SIGNATURE_WIDTH,
    Probe,
    canonical_response,
    response,
    signature,
    signature_distance,
)


def test_all_cells_have_stable_full_signatures() -> None:
    values = [signature(cell) for cell in CELLS]
    assert all(value.shape == (SIGNATURE_WIDTH,) for value in values)
    assert len({value.tobytes() for value in values}) == len(CELLS)


def test_implication_does_not_write_its_premise() -> None:
    cell = next(item for item in CELLS if item.cell_id == "transfer.derive")
    row = response(cell, Probe("active", (1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0)))
    delta = row[18:30]
    assert delta[0] == 0
    assert delta[6] > 0


def test_symmetric_cells_are_order_invariant() -> None:
    cell = next(item for item in CELLS if item.cell_id == "constraint.equal")
    probe = Probe("asymmetric", (.25, 0, 0, 0, 1, 0, .75, 0, 0, 0, 1, 0))
    assert np.allclose(response(cell, probe), canonical_response(response(cell, probe, swapped=True), swapped=True))


def test_after_surface_keeps_canonical_before_ports() -> None:
    _sources, gold = generate("development")
    row = next(item for item in gold if item.surface_relation == "after")
    assert row.cell_id == "precedes"
    assert row.atom_ids == ("a1", "a2")


def test_gold_loader_preserves_exact_tuple_roles(tmp_path) -> None:
    path = tmp_path / "gold" / "gold.jsonl"; path.parent.mkdir()
    path.write_text('{"source_id":"x","cell_id":"transfer.derive","atom_ids":["a1","a2"],"scope_id":"global","modality":"asserted","disposition":"accept","surface_relation":"implies","atom_records":[["claim","a",0,1],["claim","b",2,3]]}\n')
    assert load_gold(path)[0].atom_ids == ("a1", "a2")


def test_behavioral_distance_prefers_its_own_cell() -> None:
    for cell in CELLS:
        assert signature_distance(signature(cell), cell) == 0
