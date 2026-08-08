# G2.12 — Factorized Atomic Operator–Role Compiler

**Latest authoritative attempt:** `workspaces/topology-g2-12-r3/`  
**Classification:** **G2.12-B — FACTORIZED KERNEL FAILURE**

## Executed boundary

The following stages completed offline:

- G1-derived relation and role inventories;
- one-pass pinned MiniLM model preflight;
- split-separated semantic-program datasets;
- factorized operator, named-role, pair-direction, context, and disposition heads;
- 1,500-step gold-span kernel training;
- checkpoint freeze and evaluator-separated 3,600-case kernel evaluation.

The encoder model files remained hash-stable. The latest checkpoint recorded
1,500 training forwards, and the model retained the four lower frozen layers.

## Locked kernel results

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Cases | `3,600` | `3,600` | PASS |
| Accepted predictions | `2,880` | — | measured |
| Accepted exact predictions | `1,722` | — | measured |
| Accepted precision | `0.5979` | `>=0.95` | FAIL |
| Safe coverage | `0.6783` | `>=0.90` | FAIL |
| All-case exactness | `0.6783` | `>=0.90` | FAIL |
| Operator macro-F1 | `0.8439` | `>=0.95` | FAIL |
| Direction/role exactness | `0.5979` | `>=0.995 / >=0.95` | FAIL |
| Disposition accuracy | `0.9078` | `>=0.95` | FAIL |
| Severe accepted errors | `1,158` | `0` | FAIL |

## Attempt history

| Attempt | Change | Accepted precision | Safe coverage | Severe errors |
| --- | --- | ---: | ---: | ---: |
| `r1` | initial factorized kernel | `0.0000` | `0.2000` | `2,880` |
| `r2` | class-balanced operator loss and set decoding | `0.0424` | `0.2339` | `2,758` |
| `r3` | explicit 18-way operator head | `0.5979` | `0.6783` | `1,158` |

The operator head improved substantially by `r3`, but named-role and direction
errors still reach the final accepted output. The key failure is therefore not
the existence of operator coordinates; it is reliable role-conditioned binding
and explicit directional discrimination.

## Boundary

The kernel failure stops G2.12 before raw span extraction, identity, document
composition, FieldIR/Mumbrane handoff, and G3–G9 integration. This result does
not reclassify G2.5, does not close G2, and does not invalidate the LTM-R2
representation audit. It shows that factorization is a measurable improvement
inside the operator subproblem but is not yet a safe compiler.

