# LTM-R1 — Vector-Native Field Representation Compatibility Audit

## Status

**LTM-R1-A — REPRESENTATION HOLDS**

The audit replaces active FieldIR text fields with numeric atom, factor, role-incidence, context, provenance and vector-reference records. Historical experiments remain immutable inputs.

## Implemented evidence

| Check | Result |
| --- | ---: |
| G1 locked fixtures | 80 |
| G1 valid semantic agreement | True |
| G1 text-free core execution | True |
| G1 active-byte non-regression | True |
| Authoritative workspace artifacts present | True |

## Causal representation checks

| Check | Result |
| --- | ---: |
| context mutation detected | True |
| lossless legacy round trip | True |
| role or weight mutation detected | True |
| source text invariant | True |
| source words absent from active state | True |
| vector mutation detected | True |

Changing source wording alone leaves the active numeric field unchanged. Changing role incidence, context, or a vector-row hash changes its semantic digest. This is the required separation between display text and reasoning state.

## G2 boundary

G2 remains **G2.5-C — REPRESENTATION KERNEL FAILURE**. Its controlled compiler output is representation-compatible (`FieldIR/G1 round trip = 1.0`, invalid insertions = 0), but its recorded language-recovery limitations are not reclassified.

## G3–G14 deterministic replay

| Gap | Replay | Historical classification |
| --- | ---: | --- |
| G3 | True | G3-A — PASS |
| G4 | True | G4-A — PASS |
| G5 | True | G5-A — PASS |
| G6 | True | G6-A — PASS |
| G7 | True | G7-A — PASS |
| G8 | True | G8-A — PASS |
| G9 | True | G9-A — PASS |
| G10 | True | G10.1-S-A — STRICT SURFACE REALIZATION PASS |
| G11 | True | G11-A — PASS |
| G12 | True | G12-A — PASS |
| G13 | True | G13-A — PASS |
| G14 | True | G14-C-A — PASS |

Text remains permitted only at explicit boundaries: G3 addressing input, G9 source-hash verification, G10 surface decoding, G11 audit/display events, and G14 ingestion. It is not active field reasoning state.

## Resource contract

The replacement targets the existing 64-byte G13 factor record, reuses vector rows by reference, and adds zero core runtime adapter layers. Across the G1 fixtures the numeric active layout is 26,688 bytes versus 69,544 bytes for the legacy serialized structures.

## Conclusion boundary

The vector-native representation is structurally compatible with G1–G14 and can replace text-bearing active FieldIR records without changing the tested reasoning behavior or widening the fixed-width runtime record. This is an isomorphism and replay audit, not a direct rewrite of every historical package. It does not improve G2 language compilation, G10 language quality, or prove unrestricted-language correctness.
