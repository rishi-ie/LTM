# G13 — 1M-to-100M Context Scale Report

## Mechanical classification

**G13-A — PASS**

## Measured result

| Measure | Result |
| --- | ---: |
| Cross-scale conclusion agreement | 1.0000 |
| Required-factor recall | 1.0000 |
| S4 physical-layout agreement | True |
| S4 warm p95 core latency | 0.106 ms |
| Maximum opened factor fraction | 0.00000032 |
| Peak RSS | 146.84 MB |
| Total locked runtime | 3.99 s |

## Scale and storage evidence

| Item | Measured value |
| --- | ---: |
| Source representation | `100,000,000` actual `uint32` token IDs |
| Compiled factors | `25,000,000` fixed-width 64-byte records |
| Logical factor blocks | `97,657` blocks of 256 factors |
| Token arena | `400,000,000` bytes |
| Each physical factor layout | `1,600,012,288` bytes |
| S4 layouts | identity, reverse, affine |
| Actual exhaustive physical scans | `4`, one for each identity scale |
| True uncached reads | enabled through macOS `F_NOCACHE` |
| Network calls | `0` |
| Deterministic semantic replay | identical |

The full locked panel contained 1,000 structured requests at each of the S1,
S2, S3 and S4 identity scales, with five warm repeats per request. S4 was also
run through the reverse and affine physical layouts. The result preserved all
4,000 identity-scale conclusions, independently replayed every hard result,
and retained physical-layout agreement at S4.

## Exact claim boundary

This run stored the registered source as actual `uint32` token IDs and materialized
fixed-width factor records on disk through the 100M-token / 25M-factor scale. It
ran a controlled adapter chain for typed addressing, bounded frontier selection,
coverage widening, G6 hard propagation, G7 soft reconciliation, G8 batch-order
invariance, independent hard replay, and session-overlay checks.

The query-relevant typed factors are deliberately held in the common S1 prefix;
the added S2–S4 factors are addressable persistent distractors. Thus this is a
definitive test of sparse access, physical storage, and preservation of the
registered core contracts under a 100M-token field. It is not evidence that the
unresolved G2 compiler can ingest arbitrary 100M-token natural-language context,
nor that arbitrary far-field semantic influences are covered.

The result therefore authorizes the controlled G14 unified-benchmark work. It
does not authorize a 100M-context conversational product: G2/G2.1 ingestion,
the model-limited G10 decoding boundary, broader semantic distant-influence
coverage, and production serving remain open.
