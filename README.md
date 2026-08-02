# Latent Topology Models

This repository contains the canonical research documents and compact CPU-only
mechanism experiments for **Latent Topology Models (LTM)**. LTM compiles typed
knowledge and reasoning structure into a latent dynamic field, optimizes a
state inside that field, independently verifies the result, and decodes the
authorized state.

Read the documents in this order:

1. [Canonical architecture](docs/architecture.md)
2. [Scaling laws and runtime metrics](docs/scaling-laws.md)
3. [CNTG-1-R2 experiment report](docs/report.md)
4. [MICRO-LTM-1 specification](docs/micro-ltm-experiment.md)
5. [MICRO-LTM-1 locked report](docs/micro-ltm-report.md)
6. [MICRO-LTM-2 compression report](docs/micro-ltm-2-report.md)
7. [MICRO-LTM-3 causal compression report](docs/micro-ltm-3-report.md)

The CNTG-1-R2 experiment showed that a controlled conversational topology,
field, optimizer, verifier, and grounded decoder can work together. MICRO-LTM-1
then tested the narrower causal field mechanism and classified the locked run
mechanically. Neither experiment shows unrestricted language-to-topology
compilation, frontier-model quality, or constant worst-case inference.

MICRO-LTM-3 is the current locked result. The exact symbolic field reached
100%, but the explicit differentiable optimizer plus query-agnostic compressor
reached only 49.9% and failed the causal state-swap gate. The earlier 99.17%
closure-only result is retained as a diagnostic, not counted as a latent-
optimization breakthrough. This is a bounded mechanism study, not a claim of
unrestricted language reasoning or frontier-model quality.

Source packages and configurations are intentionally small; generated suites,
fields, raw results, and audit files remain in ignored local workspaces. Local
environments and downloaded models may remain on a development machine for
future experiments.
