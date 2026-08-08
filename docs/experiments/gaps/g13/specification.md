# G13 — 1M-to-100M Context Scale Experiment

G13 is the controlled scale gate for the already-tested structured components.
It stores 100M actual `uint32` token IDs, compiles eight fixed-width disk factors
per 32-token chunk, and evaluates 1M, 10M, 30M, and 100M prefixes. The locked
100M scale contains 25M 64-byte factor records in 256-factor blocks.

The authoritative path uses structured queries and gold-validated topology. It
exercises compact adapters for G3–G5, the real G6/G7 computation boundaries,
batch-order invariance, an independent hard-result replay, and scoped session
checks. It does **not** repair G2 natural-language compilation or G10 decoding.

The harness is sequential, disk-backed, and aborts before 18GB RSS; its hard
machine ceiling is 20GB. The permanent result is written after the single frozen
locked execution.
