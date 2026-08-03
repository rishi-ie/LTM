# MICRO-LTM-1 — Causal Latent Equilibrium Report

**Classification: `MICRO-LTM-B`**

This compact CPU experiment tests whether a typed topology can move one fixed-size latent state through unseen multi-step relations and whether a decoder using only the final state can recover the target label.

## Results

- Locked cases: 4320 (2160 counterfactual pairs)
- Full-field accuracy: **0.660**
- Latent-only decoder development accuracy: **0.910** (locked results use this frozen decoder).
- Depth-8 accuracy: **0.510**
- Symbolic oracle: **1.000**
- Barycenter control: **0.333**
- Fact-only control: **0.333**
- Undirected-rule control: **0.596**
- State-swap causal accuracy: **0.517**

The optimizer had zero numerical failures and zero accepted energy increases. It
therefore moved states stably, but the single state did not preserve a reliably
decodable multi-hop conclusion at depths 7–8. Directed optimization beat the
fact barycenter by **32.7 percentage points**, while the undirected control
reached **0.596**: directed structure is contributing, but it is not yet
isolated strongly enough for the causal breakthrough gate.

## Gate status

| Gate | Result |
|---|---|
| full_accuracy | FAIL |
| depth_eight | FAIL |
| seed_floor | FAIL |
| barycenter_margin | PASS |
| fact_only_margin | PASS |
| undirected_margin | FAIL |
| state_swap | FAIL |
| no_energy_increases | PASS |
| no_numerical_failures | PASS |

## Interpretation

A passing result is deliberately narrow: it would show causal latent encoding for the registered symbolic topology, not unrestricted language reasoning. A B result means the optimizer is mechanically useful but the single 128-dimensional state or decoder does not yet meet the causal gates.

## Reproducibility

Raw locked artifacts are kept under the ignored workspace. The selected field weights, decoder parameters, suite hashes and all per-case outputs are recorded in JSON so the run can be audited without changing the locked result.
