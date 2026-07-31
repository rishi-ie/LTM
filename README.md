# Latent Topology Models

This repository contains the architecture specification for **Latent Topology
Models (LTM)**: a proposed system that compiles knowledge and reasoning
structure into a persistent latent dynamic field, optimizes a prompt state
inside that field, verifies the resulting state, and decodes it into natural
language.

The current design defines one general reasoning topology containing
hierarchical, multi-label domain regions, typed cross-domain bridges, and
nested event or reasoning capsules. Domain-specialist topologies may later be
derived from the general topology, but they are not the first target.

The complete specification is in
[docs/architecture.md](docs/architecture.md).

The size, compute, hardware-envelope, and scaling definitions are in
[docs/scaling-laws.md](docs/scaling-laws.md).

This repository intentionally contains architecture only. It does not contain
benchmark data, experimental results, model weights, implementation code, or
claims that the architecture has already been validated.
