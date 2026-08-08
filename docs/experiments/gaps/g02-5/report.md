# G2.5 — Typed Atom Coordinate Compiler and Latent-Field Handoff

## Kernel decision

**G2.5-C — REPRESENTATION KERNEL FAILURE**

This is the locked, gold-atom representation-kernel decision. It measures operator, role and context decoding before complete span extraction or persistent-identity composition.

## Locked measurements

| Metric | Value |
| --- | ---: |
| accepted cases | 2800 |
| cases | 4000 |
| complete g1 exact | 0.8175 |
| direction errors | 0 |
| disposition accuracy | 1.0 |
| field round trip | 1.0 |
| g1 valid rate | 1.0 |
| invalid g1 insertions | 0 |
| modality accuracy | 0.92225 |
| named role exact | 0.8175 |
| operator accuracy | 0.8175 |
| polarity accuracy | 1.0 |
| reversal false accepts | 199 |
| scope accuracy | 1.0 |
| sparse role recoverability | 1.0 |

## Boundary

A kernel failure stops G2.5 by design: it rejects this typed-coordinate representation before additional compiler training is spent. A kernel pass is necessary but not sufficient for a controlled G2 pass; sentence extraction, identity, document composition and field handoff then remain to be evaluated on a separately frozen suite.

## Subsequent engineering decision

On `2026-08-04`, the project owner adopted G2.5 as the provisional compiler
baseline for building the modular end-to-end LTM pipeline. This is an
engineering waiver, not a reclassification of the locked experiment. The
measurements and `G2.5-C` classification above remain unchanged. Integration
must retain atomic G1 validation, FieldIR round-trip checks, provenance,
abstention and replaceable compiler subcomponents.
