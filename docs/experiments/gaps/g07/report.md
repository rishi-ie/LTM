# G7 — Structured Latent Optimizer and Soft Reconciliation Report

## Classification

**G7-A — PASS**

## What was tested

G7 held the G6 exact result fixed, enumerated at most two admissible soft
branches in this compact suite, then optimized confidence, preference,
reference and uncertainty variables with deterministic projected gradient
descent. An independently constructed quadratic oracle checked the selected
branch, state and energy. The 240 locked cases covered authority conflicts,
ambiguous references, observations, preferences, uncertainty and mixed G6
proofs.

| Metric | Result |
| --- | ---: |
| accepted energy increases | 0 |
| ambiguity retention accuracy | 1 |
| conflict winner accuracy | 1 |
| hard conclusions preserved | 1 |
| hard constraint violations | 0 |
| improvement over neutral points | 100 |
| neutral no optimization accuracy | 0 |
| numerical failures | 0 |
| optimizer oracle disposition agreement | 1 |
| optimizer oracle state agreement | 1 |
| preference adherence | 1 |
| provenance integrity | 1 |
| reference resolution accuracy | 1 |
| soft decision accuracy | 1 |
| uncertainty abstention accuracy | 1 |
| unresolved conflict collapse count | 0 |

## Controls

| Control | Decision accuracy |
| --- | ---: |
| highest weight | 0.416667 |
| neutral | 0 |
| no branch | 0.416667 |
| untyped | 0.416667 |
| weighted average | 0.416667 |

Runtime: `0.3707 s`; peak RSS: `44.84 MB`; repeated-result agreement: `True`.

## Bounded conclusion

This is a controlled mechanics result. It demonstrates that the registered
structured optimizer can reconcile the generated soft signals without changing
the G6 hard conclusion, and agrees with an independent quadratic oracle. It
does **not** demonstrate natural-language ingestion, a learned latent geometry,
decoder quality, or that soft optimization itself derives G6 logical truths.
