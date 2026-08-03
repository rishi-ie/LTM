# MICRO-LTM-2 — Structured Causal Relaxation Report

**Classification: `MICRO-LTM-2-E`**

This experiment tests whether temporary structured field variables can reach a directed fixed point and compress that result into one latent state that is decoded without facts, rules or proofs.

## Locked results

- Cases: 4320 (2160 counterfactual pairs)
- Compressed latent accuracy: **0.926**; macro F1: **0.926**
- Direct structured accuracy: **1.000**
- Depth-8 compressed accuracy: **0.890**
- Fact-only: **0.331**; undirected: **0.530**; MICRO-LTM-1: **0.572**
- State swap: **0.857**; interpolation: **1.000**
- Rule removal: **0.929**; reversal: **0.929**
- Runtime: **29.80s**; peak RSS: **274.1 MiB**

## Gates

| Gate | Result |
|---|---|
| compressed_accuracy | FAIL |
| compressed_macro_f1 | FAIL |
| structured_accuracy | PASS |
| depth_eight | FAIL |
| compression_gap | FAIL |
| fact_margin | PASS |
| direction_margin | PASS |
| state_swap | FAIL |
| rule_removal | FAIL |
| rule_reversal | FAIL |
| interpolation | PASS |
| fixed_point | PASS |
| no_collisions | PASS |
| runtime | PASS |
| memory | PASS |

## Interpretation

A passing result would establish a bounded mechanism result: a typed topology can relax locally to a directed fixed point and compress that state into a causally readable latent representation. It would not establish unrestricted language reasoning, superiority to symbolic closure, or single-vector reasoning without temporary structure.
