# MICRO-LTM-3 — Causal Latent Compression Experiment

## Purpose

MICRO-LTM-3 isolates the smallest claim needed for a latent-dynamic-field
breakthrough: after a typed field has been evaluated, can a query-agnostic
compressor preserve its unseen multi-step conclusion in one fixed-size state?
The experiment intentionally excludes language, retrieval, conversation and a
large decoder. It uses a symbolic field, a differentiable optimizer, fresh
random proposition codebooks, and a two-coordinate logistic readout.

## Protocol

Each case contains 24 or 96 abstract propositions, signed facts, one- or
two-premise directed rules, a target proposition, and a balanced entailed,
contradicted or unknown label. Training uses depths 1–4. The locked suite uses
depths 6–12, fresh codebooks and 1,800 counterfactual twin pairs (3,600 rows).
The symbolic forward-chaining oracle is never supplied to the runtime.

The runtime is:

```text
facts and rules
→ differentiable typed field
→ query-neutral latent initialization
→ projected/backtracked gradient optimization
→ query-agnostic state compression
→ target-code readout
```

The compressor does not receive the query proposition or gold label. Only the
decoder receives the two target code vectors needed to interpret the final
state. Ridge reconstruction is compared with normalized sums, active dual
reconstruction, a fact barycenter, the initial state and a legacy query-anchored
control.

## Causal controls

The locked run includes state swaps, decisive-rule removal, decisive-rule
reversal, twin interpolation, shuffled states and mismatched codebooks. These
controls are required because high accuracy alone could come from the query,
the proposition address, or a fixed class bias rather than from the optimized
state.

## Gates

The candidate must reach at least 98% overall accuracy, 97% at 96 propositions,
95% at depth 12, 98% state-swap accuracy and 98% intervention accuracy. It must
also remain below 600 seconds, have no numerical failures, and collapse under
state/codebook mismatch. A failure is classified mechanically and does not
invalidate the exact symbolic field control.

## Reproduction

```bash
PYTHONPATH=src python -m micro_ltm3 run-all --workspace workspaces/micro-ltm-3
PYTHONPATH=src python -m micro_ltm3 report --workspace workspaces/micro-ltm-3
PYTHONPATH=src python -m micro_ltm3 verify --workspace workspaces/micro-ltm-3
```

The locked result is recorded in [micro-ltm-3-report.md](micro-ltm-3-report.md).
Generated suites and raw rows remain in the ignored workspace directory.
