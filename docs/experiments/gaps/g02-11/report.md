# G2.11 — Atomic Attention-to-Mumbrane Compiler

**Latest authoritative attempt:** `workspaces/topology-g2-11-r3/`  
**Classification:** **G2.11-B — ATOMIC BASIS / KERNEL FAILURE**

Attempts `r1` and `r2` are retained unchanged. `r2` corrected a renderer
defect; `r3` additionally added an explicit G1-derived operator coordinate to
the atomic basis. No locked artifact was overwritten.

## What was executed

The fail-fast portion was implemented and executed offline:

- G1-derived atomic basis: 163 structural features, 18 relation signatures and 22 named roles;
- one-pass local `all-MiniLM-L6-v2` preflight with pinned model hashes;
- semantic-program datasets (18,000 training, 3,600 development, 3,600 kernel-locked, 6,000 locked cases);
- 1,200-step CPU kernel training with the upper two MiniLM layers trainable;
- checkpoint reload and one-pass atomic-coordinate inference;
- evaluator-only separation for the kernel-locked suite.

The MiniLM files remained byte-identical. The latest `r3` measurement head
contained 621,471 parameters, below the 2M head limit. The preflight was
deterministic and confirmed four lower layers frozen. The `r3` training
checkpoint recorded 1,200 encoder forwards and a final mean training loss of
`0.2692558718` (`r1`: `0.2672134925`).

## Locked kernel result

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Cases | 3,600 | 3,600 | PASS |
| Accepted predictions | 2,658 | — | measured |
| Accepted exact predictions | 2,260 | — | measured |
| Accepted precision | `0.8503` | `>=0.98` | FAIL |
| Safe coverage | `0.7278` | `>=0.95` | FAIL |
| All-case exactness | `0.7278` | `>=0.90` | FAIL |
| Severe accepted relation errors | `398` | `0` | FAIL |

Representative reversals/confusions included `excludes → equals`, `equals → excludes`, `implies ↔ conjoins`, and `opposes → supports`. These are exactly the high-risk distinctions the atomic basis is intended to preserve, so the result cannot be promoted to extraction, identity or document stages.

### Latest corrected attempt (`r3`)

The relation-specific renderer correction improved the locked result, and the
additional explicit G1-derived operator coordinate improved precision again:

| Metric | `r1` | `r2` | `r3` |
| --- | ---: | ---: | ---: |
| Accepted precision | `0.8503` | `0.8270` | `0.9357` |
| Safe coverage | `0.7278` | `0.7997` | `0.7025` |
| Severe errors | `398` | `527` | `149` |

The `r3` result remains below both the precision and coverage gates, so it is
the final classification for this G2.11 sequence.

## Interpretation

The deterministic basis itself is sound: every registered relation has a unique structural signature and round-trips exactly. The failure is in the learned measurement kernel, not in G1-to-basis construction or model loading. In particular, the current small head does not reliably separate relation families that share role shapes (for example, `supports` and `opposes`) from the contextual sentence state. Because unsafe accepted reversals remain, abstention thresholds cannot turn this run into a pass without reducing coverage below the locked gate.

The result therefore does **not** establish raw-language compilation or a complete Mumbrane compiler. It establishes that this atomic-coordinate training harness is operational and that the explicit operator coordinate materially improves precision, but it remains below the safety/coverage boundary. No later G2.11 stages were authorized, and no G2.5 or LTM-R2 historical result was changed.

## Boundary and next action

This attempt is recorded as **G2.11-B**. The next permissible engineering step is a fresh workspace after correcting implementation/data defects and adding explicit contrast diagnostics for role-sharing relation pairs. It must not overwrite the frozen `r1` artifacts or reinterpret the failed locked result.
