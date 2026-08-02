# MICRO-LTM-1: Causal Latent Equilibrium Experiment

This is the compact, CPU-only test of the central LTM mechanism. It generates typed acyclic micro-topologies, compiles every signed proposition into a fresh 128-dimensional codebook, optimizes one state under fact and directed-rule energies, and trains a nine-parameter decoder that sees only the optimized state's cosine with the queried positive and negative codes.

The experiment intentionally excludes language, embeddings, RAG, memory, and a generative decoder. A successful locked run would demonstrate only that a topology-relative equilibrium can carry an unseen multi-step conclusion causally. It would not establish general reasoning or frontier-model equivalence.

## Stages

`develop` creates balanced training/development problems, selects one of 12 field configurations, and trains the two-feature logistic decoder. `freeze` records immutable hashes. `evaluate` creates the three locked seed groups once, runs controls and interventions, and refuses a second locked run. `report` writes `docs/micro-ltm-report.md`; `verify` checks frozen inputs.

## Required controls

The locked run compares the full directed field with initial state, fact barycenter, fact-only optimization, undirected-rule optimization, shuffled state and codebook mismatch. It also tests state swaps, decisive-rule removal/reversal, trajectory confidence, interpolation, and numerical monotonicity.

## Pass boundary

`MICRO-LTM-A` requires high held-out accuracy, depth-eight generalization, large margins over averaging and fact-only controls, state-swap causal accuracy, low initial/shuffled/mismatched accuracy, finite-difference agreement, monotonic energy, reproducibility, and the ten-minute/one-GB envelope. Any failed gate is reported mechanically as B–F; no result is promoted to the canonical architecture until the locked report exists.

