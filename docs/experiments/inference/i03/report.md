# I3 — Latent-Guided Formal Mathematical Hopping

## Status

Development has stopped at the required causal-control boundary. No locked
suite has been generated or evaluated, so I3 has no mechanical classification.

## First development evidence

After replacing the structural heuristic with a learned proof-prefix potential,
the current 3,600-problem development field produced:

| Metric | Result |
| --- | ---: |
| Accepted proof precision | `1.0000` |
| Incorrect accepted proofs | `0` |
| Independent proof replay | `1.0000` |
| Safe coverage | `0.9517` |
| All-case exactness | `0.9517` |
| Required-axiom frontier recall | `0.9986` |
| Accepted energy increases | `0` |

This validates the exact formal kernel and independent proof replay for the
current constrained rewrite fragment. It is not a latent-inference pass.

## Development control stop

On a deterministic 600-case stratified development control panel:

| Variant | Proved exactness |
| --- | ---: |
| Full method | `0.9767` |
| Random scorer | `0.0000` |
| No goal anchor | `0.9567` |
| No energy constraint | `0.9967` |
| Field removed | `0.0000` |

The learned potential preserves zero accepted energy increases, but disabling
it increases success by two points. Removing the goal anchor reduces success by
only two points, far short of the required 20-point causal sensitivity. The
current generator also gives development only provable rewrite tasks, rather
than the required proved/refuted/unknown mixture. Consequently, the result is
best described as a learned local rewrite selector with exact verification—not
goal-conditioned latent proof-state movement. The required control sensitivity
gate fails, so freeze, locked execution, length stress and counterfactual
reality evaluation are not authorized.

The next engineering task is not threshold tuning. It requires a branching
formal corpus with goal-dependent choices, proved/refuted/unknown development
cases, source-backed minimap retrieval rather than a globally exposed axiom
list, and a learned proof-prefix potential that improves those decisions. Only
then can fresh development controls authorize a locked result.
