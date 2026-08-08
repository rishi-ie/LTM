# G2.8 — Versioned Golden-Atom Structured Topology Compiler

**Classification: G2.8-B — TOPOLOGY KERNEL FAILURE (development boundary)**

G2.8 evaluates a versioned G1-derived AtomBank, a selectively adapted MiniLM,
complete legal graph scoring, synchronized FieldIR factors, and atomic topology
insertion. The development renderer used relation wording, entities and framing
disjoint from training. The result below is therefore a held-out development
measurement, not a locked result.

## Measured result

| Metric | Value |
|---|---:|
| accepted_cases | 5760 |
| accepted_exact_precision | 0.5876136123441132 |
| all_case_exact | 0.4861111111111111 |
| cases | 7200 |
| disposition_accuracy | 0.7570833333333333 |
| field_round_trip | 1.0 |
| invalid_insertions | 0 |
| named_role_exact | 0.4826388888888889 |
| operator_macro_f1 | 0.4976629273504274 |
| relation_set_exact | 0.4826388888888889 |
| reversal_or_polarity_errors | 0 |
| safe_coverage | 0.4826388888888889 |

The kernel was trained for the compute-capped `700` optimizer steps after
batching the one MiniLM forward across each 16-sentence optimizer batch. Peak
RSS was `2814.52 MB`; no network access or model-file mutation was observed.

## Gate decision

The minimum kernel requirements were accepted complete-graph precision `0.97`,
safe coverage `0.95`, all-case topology exactness `0.95`, operator macro F1
`0.97`, named-role exactness `0.97`, and disposition accuracy `0.97`. This run
missed all of those accuracy/coverage gates. It did preserve the zero-tolerance
safety properties measured here: no accepted reversal/polarity error, no
invalid G1 insertion, and a successful G1/FieldIR round trip for every created
artifact.

## Boundary

The run is fail-fast. The development kernel failure refuses the kernel freeze
and fresh locked suite, so it also prevents claims about raw-span extraction,
persistent identity, AtomBank migration, document composition, or downstream
G3–G9 integration.

Exact G1 factors remain factual authority. Operator coordinates, deltas and FieldIR sidecars are continuous compiler and field artifacts; they never authorize topology without a validated sparse G1 graph.
