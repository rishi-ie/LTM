# G11 — Safe Conversation-Memory Lifecycle Report

## Classification

**G11-A — PASS**

## Locked result

G11 ran 32 deterministic twelve-turn conversations against an independent full-history oracle. The candidate uses an immutable base SQLite database plus a copy-on-write session overlay.

| Measurement | Result |
| --- | ---: |
| assistant self contamination accepts | 0 |
| base topology hash preservation | 1.0 |
| compressed uncompressed agreement | 1.0 |
| conflict retention | 1.0 |
| context answer agreement | 1.0 |
| correction supersession | 1.0 |
| cross session leaks | 0 |
| decisive provenance agreement | 1.0 |
| episode reopening accuracy | 1.0 |
| fictional scope containment | 1.0 |
| ordinary full transcript scans | 0 |
| p95 rows read | 3 |
| post clear session influence | 0 |
| preference persistence | 1.0 |
| reference binding agreement | 1.0 |
| restart replay equality | 1.0 |
| targeted deletion residual influence | 0 |

Runtime: `0.4383 s`; peak RSS: `26.50 MB`.

## Bounded conclusion

A pass establishes only the controlled lifecycle contract: session context, corrections, preferences, scoped conflicts, episode summaries, restarts, deletion and clearing preserve the registered state and provenance without mutating base knowledge. Assistant text remains a low-authority discourse event, not independent evidence. This does not establish natural-language compilation, model decoding, integrated conversation quality, or 100M-context reliability.
