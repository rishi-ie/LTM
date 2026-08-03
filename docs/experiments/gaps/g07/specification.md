# G7 — Structured Latent Optimizer and Soft Reconciliation

## Question

> After exact G6 reasoning fixes the hard result, can a small structured
> optimizer reconcile soft evidence, reference choices, preferences,
> uncertainty and conflict branches without changing that hard result?

## Design

G7 receives a G6 program and its exact result. The G6 active/inactive claims,
proof, obligations and constraints are immutable. G7 optimizes only a state
`(c, r, p, u, b)`: confidence, reference probabilities, preferences,
uncertainty and a small enumerated set of admissible branches.

Each soft factor has an explicit target and weight:

\[
w=\operatorname{clamp}(b\,a\,c, 0.0001, 8)
\]

with squared residuals for evidence, preference, reference, branch support and
uncertainty. Confidence, preference and uncertainty use `[0,1]` projections;
reference groups are projected onto a probability simplex. At most four
branches may be enumerated. A tie inside `0.05` energy units remains explicit;
it is never hidden by stable tie-breaking.

The compact locked suite contains 240 cases: 40 each for unequal-authority
conflicts, ambiguous references, competing observations, preferences,
uncertainty/abstention, and mixed cases containing a G6 proof. It runs on CPU
with NumPy only. Every generated locked case uses only quadratic soft factors,
allowing a separately implemented exact constrained quadratic oracle. The
runtime also implements registered product/hinge factor derivatives for unit
tests, but those non-quadratic terms are deliberately outside this first
oracle-controlled evaluation.

## Freeze and decision

Development has 120 cases (seed `1735`); locked evaluation has 240 cases (seed
`20260808`). The optimizer uses at most 48 projected steps, learning rate
`0.05`, four backtracking retries, a 240-evaluation limit, and a 60-second /
512-MB envelope. Freeze hashes G6 and G7 source, configuration and development
results before the locked suite is built. Locked results cannot be overwritten.

`G7-A` requires preservation of all hard conclusions, no hard violations or
accepted energy increases, at least 90% soft-decision accuracy, at least 95%
on conflicts/references/preferences/uncertainty, a ten-point gain over neutral
state, at least 99% agreement with the independent oracle, reproducibility,
and the compact compute envelope.

## Boundary

A pass demonstrates controlled post-logical soft reconciliation. It does not
prove language ingestion, learned latent geometry, decoding quality, or that a
continuous optimizer derives logical conclusions. G6 remains the authority for
hard logical truth.
