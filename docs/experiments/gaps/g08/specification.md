# G8 — Memory-Bounded Batch Execution

## Hypothesis

For a fixed request-specific G6/G7 field, physical block batching must not
change the logical result or structured soft reconciliation result. The system
must combine hard factors as a set union and soft factor contributions through
a canonical reduction before performing a single global update.

## Compact locked design

- 96 locked requests over a deterministic 65,536-factor field.
- Each request selects 16 blocks of 256 factors; all remaining factors are
  distractors.
- Candidate configurations: batch widths `1`, `4`, `16`; each with ascending,
  descending and seeded-random delivery order.
- Reference: all 16 selected blocks are materialized and executed together.
- Controls: last-block-wins, average-local-final-states and sequential local
  updates.
- CPU-only, NumPy and standard-library Python; target below 60 seconds and
  512 MB peak RSS.

## Fixed execution rule

1. Read at most the configured number of physical blocks at once.
2. Union G6 facts and rules deterministically, then execute G6 once.
3. Sum G7 quadratic contributions using canonical factor order.
4. Optimize the one global structured G7 state once.
5. Compare hard state, soft state, branches, disposition and decisive
   provenance with the reference.

The experiment does not test language, frontier coverage, generic distributed
optimization, or 100M-context serving.

## Gates

The result passes only with exact hard/branch/provenance agreement for all
nine candidate configurations; state L2 error at most `1e-8`; cosine at least
`0.999999`; energy and residual error at most `1e-10`; no residency violation
or full-field materialization; every incorrect-composition control failing on
at least 20% of requests; reproducibility; and the compute caps.
