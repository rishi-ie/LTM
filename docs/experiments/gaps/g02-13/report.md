# G2.13 — Conversational Mumbrane Compiler Report

## Classification

**G2.13-B — CONVERSATIONAL KERNEL FAILURE**

## Authoritative execution

Workspace: `workspaces/topology-g2-13-r1/`  
Suite: 2,400 gold-span kernel cases  
Training: 1,000 optimizer steps  
Encoder: one-pass local `all-MiniLM-L6-v2`; model hashes remained stable.

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Accepted structured-event precision | `0.9425` | `>=0.97` | FAIL |
| Safe coverage | `0.9146` | `>=0.95` | FAIL |
| All-case exactness | `0.9146` | — | measured |
| Discourse-act macro-F1 | `0.9992` | `>=0.97` | PASS |
| Memory-action macro-F1 | `1.0000` | `>=0.97` | PASS |
| Reference accuracy | `0.9167` | `>=0.99` | FAIL |
| Context accuracy | `0.9996` | `>=0.97` | PASS |
| Disposition accuracy | `0.9167` | `>=0.97` | FAIL |
| Incorrect accepted predictions | `115` | `0` | FAIL |

The compiler learned conversational act and memory-action classification very
well. Remaining failures are concentrated in reference/disposition handling
and safe abstention. The incorrect predictions were measured before any event
commit, so this is a kernel failure rather than a lifecycle-integrity failure.

## Boundary

The fail-fast rule stopped raw span extraction, persistent identity linking,
G11 lifecycle execution, and FieldIR/Mumbrane downstream handoff. No later
metrics were fabricated. G11's independent structured lifecycle pass remains
valid, and G2.5 remains the provisional compiler.
