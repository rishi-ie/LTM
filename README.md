# Latent Topology Models

This repository is the documentation-only research record for **Latent
Topology Models (LTM)**: a proposed system that compiles typed knowledge and
reasoning structure into a persistent latent dynamic field, optimizes a prompt
state inside that field, independently verifies the result, and decodes the
authorized state into natural language.

Read the documents in this order:

1. [Canonical architecture](docs/architecture.md)
2. [Scaling laws and runtime metrics](docs/scaling-laws.md)
3. [CNTG-1-R2 experiment report](docs/report.md)

The CNTG-1-R2 experiment showed that a controlled conversational topology,
field, optimizer, verifier, and grounded decoder can work together. It did not
show unrestricted language-to-topology compilation, frontier-model quality,
or constant worst-case inference. The next research target is the learned
reasoning-topology compiler.

Implementation code, generated corpora, fields, model weights, raw results,
and audit files are intentionally not part of this public documentation
repository. Local ignored workspaces and downloaded models may remain on a
development machine for future experiments.
