# L3 — Compiled 45-Hop Mathematical Reality Validation

L3 tests whether controlled mathematical prose and notation can be compiled
into a persistent, source-backed mathematical reality and then queried through
the frozen I3.1 proof-search lane at exactly 45 verified hops.

The grounded 45-hop panel is authoritative. A mixed-axiom 45-hop panel is a
separate stronger diagnostic. The exact controlled compiler is used so language
parsing does not obscure the field and proof-search question. MiniLM-based raw
language compilation remains outside this experiment.

## Boundaries

- Standard reality and the frozen 46-schema I3.1 axiom bank only.
- ASCII and frozen Unicode mathematical notation with controlled prose wrappers.
- Explicit source and goal questions only; open-ended goal discovery abstains.
- Every accepted body is an exact concrete instance of a registered schema.
- Every authoritative grounded answer has an evaluator-certified shortest proof
  of 45 steps. The mixed panel requires a replayable 45-step path across at
  least eight schemas and is reported separately because algebraic rewrites
  can admit alternate shorter derivations.
- No direct source-to-goal body, inverse padding, route metadata, or closure.
- I3.1 source, checkpoint, thresholds, search settings, and reports remain immutable.

## Commands

```bash
python -m ltm_limit_l3 model-check --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 corpus-build --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 compiler-evaluate --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 freeze --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 locked-suite-build --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 grounded-evaluate --workspace workspaces/ltm-limit-l3-r1 --offline
python -m ltm_limit_l3 mixed-evaluate --workspace workspaces/ltm-limit-l3-r1 --offline
python -m ltm_limit_l3 controls --workspace workspaces/ltm-limit-l3-r1 --offline
python -m ltm_limit_l3 attacks --workspace workspaces/ltm-limit-l3-r1 --offline
python -m ltm_limit_l3 verify --workspace workspaces/ltm-limit-l3-r1 --offline
python -m ltm_limit_l3 report --workspace workspaces/ltm-limit-l3-r1
python -m ltm_limit_l3 run-all --workspace workspaces/ltm-limit-l3-r1 --offline
```

## Gates

Compiler gates require accepted body precision `1.00`, body coverage at least
`0.95`, AST exactness at least `0.98`, question precision `1.00`, question
coverage at least `0.95`, exact provenance/reality agreement, and zero incorrect
active insertions.

Grounded L3-A requires exact 45-hop success at least `0.95`, accepted proof
precision `1.00`, independent replay `1.00`, end-to-end safe coverage at least
`0.90`, required-body recall at least `0.99`, ambiguity/unknown recall at least
`0.95`, and zero incorrect accepted conclusions.

Mixed-45-PASS requires verified success at least `0.80`, proof precision `1.00`,
at least eight schemas across three families per path, and zero incorrect
accepted conclusions. It is reported separately from L3-A.

## Safety and artifacts

Every source transaction is atomic. Source text is archive-only during numeric
execution. The runtime receives no answer, route, depth, or proof-path metadata.
Each accepted proof is replayed by the independent exact verifier. Failed,
ambiguous, missing-body, wrong-reality, and corrupted-proof cases abstain.
Locked artifacts are immutable; a failed attempt continues under `r2`.
