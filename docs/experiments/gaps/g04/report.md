# G4 — Prompt-Conditioned Active Frontier Report

## Classification

**G4-A — PASS**

G4 used gold topology and gold starting addresses. It tests bounded typed traversal, not coverage certification or latent optimization.

## Locked metrics

| Metric | Result |
| --- | ---: |
| bridge factor recall | 1 |
| budget exhaustion rate | 0 |
| complete scans | 0 |
| conclusion agreement | 1 |
| conflict branch recall | 1 |
| decisive provenance recall | 1 |
| exact exception recall | 1 |
| false resolved conclusions | 0 |
| hard constraint recall | 1 |
| median opened fraction | 7e-05 |
| p95 opened fraction | 9e-05 |
| proof path exact match | 1 |
| required factor recall | 1 |
| session factor recall | 1 |
| unexplained omissions | 0 |

Runtime: `56.552 s`; peak RSS: `1134.70 MB`.

## Controls

| Method | Required-factor recall | Conclusion agreement |
| --- | ---: | ---: |
| forward_only | 0.408 | 0.533 |
| full | 1.000 | 1.000 |
| no_conflict | 0.976 | 1.000 |
| no_correction | 0.973 | 0.833 |
| no_safety | 0.962 | 0.833 |
| no_session | 0.981 | 1.000 |
| semantic_topk | 0.352 | 0.280 |
| untyped_bfs | 1.000 | 1.000 |

The frozen-MiniLM semantic retrieval control was far weaker than the typed
frontier (`0.352` required-factor recall and `0.280` conclusion agreement).
Forward-only traversal also missed prerequisites and reached only `0.533`
conclusion agreement. Removing correction or exact-safety indexes reduced
conclusion agreement to `0.833`, showing that those topology-native paths are
material to this controlled task.

The generic untyped-BFS control tied the full traversal on this synthetic,
low-degree distribution. Consequently, this result demonstrates that the
registered typed traversal works sparsely and correctly; it does **not** yet
demonstrate an advantage over generic BFS. A later stress test needs denser
irrelevant branches and high-degree hubs while preserving the same answer
paths.

The reported end-to-end runtime includes the frozen semantic-retrieval control;
the core typed-frontier work is only one component of that total.

## G3 integration diagnostic

The actual frozen G3 resolver received controlled structured signatures and reached starting-address agreement `1.000` with `0` unsafe resolutions. This diagnostic does not alter the G4-Core classification.

A pass authorizes G5 only. G2/G2.1 remain failed, and G4 does not establish
that unopened regions are harmless, raw-language ingestion works, or latent
optimization is valid.
