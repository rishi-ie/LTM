# MICRO-LTM-3 — Causal Latent Compression Report

**Classification: `MICRO-LTM-3-E`**

This experiment tests whether a query-agnostic compressed latent state can preserve a symbolic field's answer for unseen multi-step rule problems. It is a controlled mechanism test, not a natural-language or general-reasoning claim.

## What was tested

A typed field was compiled from facts and directed rules. A differentiable energy optimizer moved one latent state from a query-neutral initialization; the query-agnostic compressor saw only the optimized activation vector and proposition codebook, while the query was provided only to the two-coordinate decoder. Two capacities were evaluated: 24 propositions (48 signed codes in 128 dimensions) and 96 propositions (192 signed codes, overcomplete).

## Locked results

- Rows: **3600**, twin pairs: **1800**.
- Selected compressor: `{'method': 'ridge', 'ridge': 1e-06}`.
- Selected accuracy: **0.499**; macro-F1: **0.488**.
- Direct structured-field accuracy: **1.000**.
- Capacity 24: **0.502**; capacity 96: **0.496**.
- State-swap causal accuracy: **0.254**.
- Interpolation monotonicity: **0.917**.
- Intervention accuracy: `{'add': 0.8816666666666667, 'remove': 0.6908333333333333, 'reverse': 0.2683333333333333}`.
- Locked seed groups: `{'locked-20261021': 0.5166666666666667, 'locked-20261022': 0.48333333333333334, 'locked-20261023': 0.505, 'locked-20261024': 0.4866666666666667, 'locked-20261025': 0.49, 'locked-20261026': 0.51}`.
- Runtime: **257.89s**; support-consistency failures: **0**.

## Accuracy by proof depth

| Depth | Accuracy |
|---:|---:|
| 6 | 0.485 |
| 7 | 0.514 |
| 8 | 0.522 |
| 9 | 0.498 |
| 10 | 0.480 |
| 11 | 0.495 |
| 12 | 0.494 |

## Compressor controls

| Method | Accuracy |
|---|---:|
| `active_dual_0.001` | 0.486 |
| `active_dual_1e-06` | 0.485 |
| `direct` | 1.000 |
| `fact_barycenter` | 0.333 |
| `initial` | 0.333 |
| `legacy` | 0.388 |
| `mismatched_codebook` | 0.337 |
| `normalized_sum` | 0.363 |
| `ridge_0.001` | 0.499 |
| `ridge_1e-06` | 0.499 |
| `selected` | 0.499 |
| `shuffled_state` | 0.225 |

The selected-minus-fact-barycenter bootstrap difference was **0.165** with 95% interval **[0.146, 0.184]** over 2,000 resamples.

## Decision gates

| Gate | Result |
|---|---|
| overall | FAIL |
| micro_capacity | FAIL |
| large_capacity | FAIL |
| depth_12 | FAIL |
| capacity_gap | PASS |
| compression_gap | FAIL |
| state_swap | FAIL |
| interventions | FAIL |
| interpolation | FAIL |
| shuffled_state | PASS |
| mismatched_codebook | PASS |
| fixed_point | PASS |
| runtime | PASS |

## Numerical and causal diagnostics

The optimized activations were internally support-consistent in all rows (reported failure count **0**). This is not the same as proving convergence to a useful global minimum. Mean reconstruction RMSE was **0.0653**, and the maximum reported condition number was **2780316.3**. No compressor fallback was used (0 cases). The shuffled-state and mismatched-codebook controls collapsed as expected, but state swaps and topology interventions did not remain reliable; this is why the causal gate fails.

## Interpretation

The strict optimizer run did not preserve the symbolic conclusions: selected accuracy was 49.86%, and state-swap accuracy was 25.39%. The mismatched-codebook and shuffled-state controls collapsed as expected, so the decoder was not simply reading the query or a fixed identity. The exact structured field still reached 100%, which localizes the failure to the differentiable latent state/optimization/compression contract. The earlier closure-only implementation reached 99.17%, but it is not counted as a latent-optimization breakthrough because it bypassed the differentiable optimizer. This is a useful negative result, not evidence of unrestricted language reasoning or a production-scale LTM.

Raw locked rows and the frozen manifest are retained under the ignored workspace directory for reproducibility.
