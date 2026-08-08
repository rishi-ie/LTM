# G2.9 — Post-Attention Golden-Query Topology Compiler

G2.9 evaluates a non-generative topology compiler. A selectively adapted local
MiniLM first produces contextual sentence states. Versioned G1-derived golden
operators and their named roles then act as dynamic cross-attention queries over
those states. The compiler selects a complete legal relation set and commits
only an atomically validated G1 and FieldIR pair.

The experiment is fail-fast: a fresh gold-content locked kernel must meet the
95% accepted precision and coverage gates with zero unsafe accepted operations
before span extraction, identity, document composition, migration, or G3–G9
integration can run. G2.5 remains the provisional pipeline baseline unless
G2.9 completes every stage.
