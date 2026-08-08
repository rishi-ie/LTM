import numpy as np

from ltm_inference_i2.dataset import generate_bodies
from ltm_inference_i2.index import FieldIndex, build_cells


def test_every_body_reaches_a_root_summary():
    bodies, units, vectors = generate_bodies("test", 128, 1871)
    cells, summary = build_cells(bodies, units, vectors)
    assert len(summary) == len({cell.semantic_prototype_refs[0] for cell in cells})
    leaves = [cell for cell in cells if cell.body_ids]
    assert set().union(*(set(cell.body_ids) for cell in leaves)) == {body.body_id for body in bodies}
    index = FieldIndex(bodies, units, vectors, cells, summary)
    selected, opened = index.frontier(np.asarray(summary[0, :128], dtype=np.float32))
    assert selected and opened
