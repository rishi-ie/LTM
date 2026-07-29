# Phase 1 Semantic-Field Experiment Results

**Date:** 2026-07-29  
**Pipeline classification:** PASS  
**Semantic-objective classification:** Result B  
**Decision:** preserve the working pipeline; do not promote this semantic
objective as reasoning

## Question

Does the fixed Phase 1 latent optimizer improve prompt-conditioned evidence
selection over direct cosine retrieval and directional mean shift when all
methods use the same frozen embedding model, corpus, query set, active field,
and four-item evidence budget?

## Fixed setup

- embedding model: `sentence-transformers/all-MiniLM-L6-v2`;
- model revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`;
- 40-document shared corpus;
- 50 hand-reviewed queries across ten semantic domains;
- two gold evidence items per query;
- evidence budget: four;
- direct retrieval, eight-step mean shift, and eight-step projected-gradient
  optimization;
- offline execution with local pinned weights.

The initial per-domain diagnostic was rejected because each query searched
only four documents while Recall@4 returned all four. The decision-grade run
searched the shared 40-document corpus.

## Results

| Method | Recall@4 | Precision@4 | Mean method latency | Field evaluations |
| --- | ---: | ---: | ---: | ---: |
| Direct cosine retrieval | 0.950 | 0.475 | 0.032 ms | 0 |
| Directional mean shift | 0.890 | 0.445 | 0.080 ms | 8 |
| Latent optimization | 0.890 | 0.445 | 0.227 ms | 9 |

Additional observations:

- latent energy decreased in all 50 cases;
- direct retrieval recovered both gold items in 45/50 cases;
- latent optimization recovered both gold items in 39/50 cases;
- latent evidence differed from direct retrieval in 42/50 cases;
- latent evidence differed from mean shift in only 4/50 cases;
- latent optimization improved two queries but degraded eight relative to
  direct retrieval;
- the full offline experiment process completed in approximately 2.04 seconds;
- the earlier complete `ask` smoke run recorded peak RSS of approximately
  724 MB and total request time of approximately 234 ms on this environment.

## Interpretation

The implementation proves that the four-component flow is mechanically real:
the corpus induces an explicit differentiable field, gradients are numerically
correct, optimization remains on the unit sphere, energy falls, exact evidence
is recovered, and the final evidence can be decoded.

The current field objective does **not** prove useful latent optimization.
It mostly behaves like directional mean shift and makes evidence retrieval
worse than the unchanged prompt embedding. Lower energy therefore measures
agreement with the implemented density objective, not better semantic
coverage or reasoning.

This is Result B under the binding specification. It falsifies the claim that
the current semantic density field and optimizer already add value over direct
retrieval.

## Next research gate

The Phase 1 pipeline gate is complete. Later Phase 1.1 and Phase 1.2
experiments test alternative semantic objectives. A separate native-topology
phase must introduce typed relations and an independent verifier; this result
neither validates nor rejects that hypothesis.

Raw machine-readable output is generated locally at
`results/phase-1/phase-1-results.json`.
