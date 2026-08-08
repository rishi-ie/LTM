# G8 — Memory-Bounded Batch Execution Report

## Classification

**G8-A — PASS**

## Question

Can the same selected G6 hard program and G7 soft reconciliation problem be
loaded in physical blocks, reduced in any batch width or order, and solved once
globally without changing the result or materializing the whole field?

## Locked method

The locked run used 96 generated requests. Each request selected 16 physical
blocks of 256 factors from a 65,536-factor field. It compared nine candidate
executions: batch widths 1, 4 and 16 crossed with ascending, descending and
seeded-random block orders. The reference loaded all 16 selected blocks. The
candidate never averaged independently optimized block states: it unioned G6
hard objects, canonically reduced G7 soft contributions, then ran one global
soft optimization.

| Measurement | Result |
| --- | ---: |
| branch disposition provenance agreement | 1 |
| complete field materializations | 0 |
| cross order semantic agreement | 1 |
| decisive provenance agreement | 1 |
| energy error max | 1.110223e-16 |
| full hard state agreement | 1 |
| hard conclusion agreement | 1 |
| memory cap agreement | 1 |
| memory cap violations | 0 |
| residual error max | 0 |
| state cosine min | 1 |
| state l2 max | 0 |

## Incorrect-composition controls

The values below are failure rates against the reference. They test why a
global canonical reduction is necessary.

| Control | Failure rate |
| --- | ---: |
| average local states | 1 |
| last block wins | 0.98958333 |
| sequential update | 1 |

Runtime: `7.5080 s`; peak RSS: `61.53 MB`.

## Bounded conclusion

This pass result concerns the generated G6/G7-compatible field
only. It demonstrates that physical batching and delivery order do not change the registered hard result, soft state, branch/disposition, or decisive provenance while the configured residency cap is honored. It does **not** demonstrate arbitrary asynchronous message passing, full-field coverage, language ingestion, decoder quality, or 100-million-token serving.
