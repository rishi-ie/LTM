# Phase 1.2 Hierarchical Semantic Equilibrium

**Date:** 2026-07-29  
**Classification:** E-B — mechanically valid, no value over simpler controls  
**Decision:** keep `ask` unchanged; retire this semantic equilibrium objective

## Objective

Phase 1.2 tests the proposed “whole corpus acts like gravity” interpretation as
a conservative semantic field. Every active corpus item contributes directly
in the exact oracle or once through a deterministic hierarchy aggregate.
Metadata and prompt similarity determine influence. Contradictions remain
visible as residual tension.

This is a semantic-compatibility experiment, not a test of logical truth,
implication, or causality.

## Implementation

The isolated experiment adds:

- exact prompt-conditioned equilibrium energy and analytic gradient;
- tangent-projected spherical optimization with backtracking;
- closed-form weighted barycenter control;
- deterministic spherical k-means hierarchy;
- fixed-frontier whole-corpus approximation;
- evidence, residual, provenance, aggregate-force, and tension bundles;
- deterministic non-generative evidence-table fallback;
- an 18-configuration development grid;
- a locked 120-query suite over 24 new semantic domains;
- exact-oracle and 100/1,000/10,000-chunk scaling checks.

The existing density field, multi-state experiment, decoder, and normal
`ask` command are unchanged.

## Frozen configuration

| Setting | Value |
| --- | ---: |
| Query anchor | 0.5 |
| Average consensus | 1.0 |
| Smooth worst residual | 2.0 |
| Smooth maximum beta | 10 |
| Relevance floor | 0.0001 |
| Relevance temperature | 0.05 |
| Updates | 8 |
| Evaluation hard limit | 16 |

The selected configuration was written before the held-out suite was opened.
It was not retuned after the result.

## Locked held-out result

| Method | Recall@4 | Precision@4 | Worst important residual |
| --- | ---: | ---: | ---: |
| Direct cosine | 0.239 | 0.179 | — |
| Existing density optimizer | 0.156 | 0.117 | — |
| Weighted barycenter | 0.261 | 0.196 | 0.519 |
| Exact equilibrium | 0.253 | 0.190 | 0.637 |
| Hierarchical equilibrium | 0.189 | 0.142 | 0.633 |

The exact equilibrium improved Recall@4 over direct retrieval by 0.014. Its
paired-bootstrap 95% interval was `[-0.006, 0.036]`, so the improvement was
not reliable. Compared with the barycenter, its worst important residual was
22.7% worse and its average weighted residual was 19.3% worse.

The hierarchy was computationally sound but missed its fidelity gates:

- minimum final-state cosine versus exact: 0.980, below 0.990;
- maximum relative oracle-energy error: 3.05%, above 2%;
- mean top-evidence overlap: 70.4%, below 90%.

Numerical failures were zero. Raising a controlled item weight moved the
equilibrium toward it in 100% of controlled cases. Low-priority irrelevant
expansion produced negligible controlled drift.

## Scaling

| Corpus | Build | Frontier | Optimization | Peak RSS |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 0.6 ms | 0.1 ms | 0.1 ms | 521 MB |
| 1,000 | 7.4 ms | 0.6 ms | 0.4 ms | 522 MB |
| 10,000 | 173 ms | 2.3 ms | 0.5 ms | 591 MB |

These are synthetic-vector engineering measurements, not quality evidence.
They show that bounded frontier evaluation is practical on the target
hardware, but not that it preserves sufficient information.

## Interpretation

The experiment validates the implementation mechanics:

- the field is conservative;
- gradients match finite differences;
- accepted updates do not increase energy;
- the hierarchy partitions all active items without duplication;
- memory and latency remain comfortably within the POC limits.

It rejects the current objective as a reasoning advantage. The smooth
worst-residual term did not improve consensus over the closed-form barycenter,
and the hierarchy lost additional evidence fidelity. More scale would not fix
this measured objective failure.

The held-out fixture is static and pre-registered, but intentionally synthetic
and template-generated. Its low absolute retrieval scores limit external
validity; the comparative failure against the simpler controls remains the
relevant result.

## Decision

Phase 1.2 is **E-B**. Do not integrate it into `ask`. A future experiment needs
a different mathematical object—most likely explicit typed constraints and
relations—rather than another semantic-vector equilibrium variant. This result
does not test that native topology and therefore neither validates nor rejects
it.

Raw artifacts are in `results/phase-1.2/`.
