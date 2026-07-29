# Spec: Phase 1.2 Hierarchical Semantic Equilibrium

## Objective

Test whether a prompt-conditioned conservative field can combine influence
from an entire semantic corpus more usefully than direct retrieval and a
closed-form weighted barycenter. Exact execution is the small-corpus oracle;
a deterministic hierarchy must approximate it with bounded active work.

Success is E-A only when every numerical, quality, hierarchy, memory, and
latency gate in this document passes on the locked suite.

## Tech stack

- Python 3.11;
- NumPy and the existing Pydantic records;
- frozen `all-MiniLM-L6-v2` embeddings;
- pytest and Ruff;
- no new dependency, trained weight, or decoder model.

## Commands

```bash
python -m ltm_poc evaluate-equilibrium \
  --workspace workspaces/e2e \
  --dev-suite eval/phase-1.2/development.json \
  --test-suite eval/phase-1.2/held-out.json \
  --output results/phase-1.2

pytest -q
ruff check .
python -m compileall -q src tests eval
```

## Project structure

- `src/ltm_poc/experiments/equilibrium.py`: field, hierarchy, optimizer,
  evidence bundle;
- `src/ltm_poc/experiments/phase_1_2.py`: frozen grid, controls, gates,
  reports;
- `eval/phase-1.2/development.json`: inspected-suite development manifest;
- `eval/phase-1.2/held-out.json`: static locked 120-case suite;
- `tests/experiments/test_equilibrium.py`: numerical and structural tests;
- `tests/experiments/test_phase_1_2.py`: suite and selection tests;
- `results/phase-1.2/`: generated experiment artifacts.

## Field contract

For each item, metadata prior is priority × confidence × authority × recency.
Prompt relevance applies a temperature-scaled exponential with a nonzero
floor. The energy combines query anchoring, average weighted residual, and a
smooth maximum of relative weighted residuals. Its analytic gradient is
optimized on the unit sphere with bounded backtracking.

The hierarchy uses deterministic spherical k-means. A fixed frontier
represents each non-excluded item exactly once as either an exact item or one
aggregate ancestor. The exact oracle uses the same energy contract.

Representative style:

```python
energy, gradient = field.energy_and_gradient(state)
tangent = gradient - float(gradient @ state) * state
candidate = unit(state - learning_rate * tangent)
```

Data records are deterministic and serializable. Existing public behavior is
not modified.

## Testing strategy

Unit tests cover finite-difference gradients, unit normalization, monotonic
accepted energy, metadata validation, symmetry, priority intervention,
barycenter equivalence, corpus partitioning, bounded evidence, and fallback
output. Integration tests cover the fixed 18-item grid, locked-suite balance,
all six controls, exact/hierarchy comparisons, reproducible artifacts, and
100/1,000/10,000-vector scaling.

## Boundaries

- Always: freeze development selection before reading held-out data; preserve
  provenance; report contradictions as residual tension; compare with simpler
  controls.
- Ask first: new dependencies, learned weights, changes to workspace schema,
  or integration into normal `ask`.
- Never: tune after reading held-out results; let the decoder read outside its
  evidence bundle; claim semantic compatibility proves truth or causality.

## Success criteria

E-A requires all approved gates: ≥10% worst-residual improvement over the
barycenter, ≤5% average-residual loss, ≥5-point Recall@4 improvement over
direct retrieval with positive paired-bootstrap interval, prompt cosine ≥0.60,
95% priority monotonicity, irrelevant drift ≤0.05, hierarchy/exact cosine
≥0.99, energy error ≤2%, evidence overlap ≥90%, no numerical failure, peak RSS
<8 GB, and warm 10,000-vector optimization <5 seconds.

E-B means the mechanics work without objective value. E-C means exact
equilibrium passes while hierarchy fails. E-D means a numerical, conservative,
or provenance failure.
