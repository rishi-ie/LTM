# Phase 1.1 Multi-State Latent Optimization Results

**Date:** 2026-07-29  
**Classification:** Result B — objective still inadequate  
**Decision:** keep `ask` unchanged; do not promote multi-state semantic
diversity as reasoning

## Implemented experiment

Phase 1.1 adds an isolated set-valued latent field with:

- two or four unit-normalized 384-dimensional latent slots;
- deterministic MMR initialization from the top 16 direct candidates;
- query-conditioned density energy for each slot;
- pairwise similarity penalties above a configurable cap;
- tangent-projected gradient descent and spherical retraction;
- distinct evidence resolution with slot provenance;
- a fixed 24-configuration development grid;
- a locked 100-query held-out suite across 20 unseen domains;
- direct, MMR, mean-shift, single-state, multi-state, and two ablation controls.

The embedding model, decoder, ingestion pipeline, and normal `ask` path were
not changed.

## Selected development configuration

| Setting | Value |
| --- | ---: |
| Slots | 4 |
| Seed mixture | 0.30 |
| Diversity weight | 0.25 |
| Similarity cap | 0.60 |
| Steps | 8 |
| Set evaluations | 9 |
| Slot-energy evaluations | 36 |

Development Recall@4 was 0.980. Because development results determined this
configuration, only the held-out suite determines the phase result.

## Held-out results

| Method | Recall@4 | Precision@4 | Mean latency |
| --- | ---: | ---: | ---: |
| Direct cosine retrieval | 0.880 | 0.440 | 0.044 ms |
| MMR | 0.750 | 0.375 | 0.062 ms |
| Directional mean shift | 0.915 | 0.458 | 0.097 ms |
| Existing single-state optimizer | 0.930 | 0.465 | 0.243 ms |
| Selected multi-state optimizer | 0.885 | 0.443 | 0.915 ms |
| Multi-state without diversity | 0.890 | 0.445 | 0.915 ms |
| Multi-state with query-only initialization | 0.945 | 0.473 | 0.909 ms |

Decision-gate observations:

- multi-state improvement over direct retrieval: 0.005, below the required
  0.050;
- paired bootstrap 95% interval: `[-0.035, 0.040]`, which includes zero;
- maximum domain Recall@4 loss: 0.300, above the permitted 0.100;
- evidence differed from MMR in 64% of cases;
- numerical failures: zero;
- peak RSS: approximately 463 MB;
- selected configuration, evidence, energies, and quality outputs were
  identical across two offline runs.

## Interpretation

The implementation proves that multiple latent states can be initialized,
optimized, separated, and resolved into distinct evidence under a bounded
energy budget. The analytic gradients, unit-sphere constraints, energy guard,
evaluation limit, and reproducibility checks pass.

The selected diversity objective does not provide a reliable evidence
advantage. Its held-out performance is effectively tied with direct retrieval,
below mean shift and the existing single-state optimizer, and worse than both
ablations. The development-to-test drop from 0.980 to 0.885 also shows that the
small development suite selected a configuration that did not generalize.

The query-only ablation is diagnostically interesting, but it was observed on
the held-out set and therefore cannot be promoted or tuned using these results.
It requires a new pre-registered experiment and a new untouched test suite.

## Decision

Phase 1.1 is Result B. Do not integrate multi-state inference into `ask`, and
do not treat semantic diversity as evidence that a native reasoning topology
will work. This experiment does not test typed reasoning relations, so it also
cannot be used to reject a separately specified native-topology experiment.

Raw results are generated at
`results/phase-1.1/phase-1.1-test-results.json`.
