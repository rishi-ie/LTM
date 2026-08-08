# I1 — Relation-Free Mumbrane Latent Inference

## Classification

**I1-B — BODY REPRESENTATION FAILURE**

This experiment tests supplied atomic Mumbranes and a compact learned energy
field. It does not test raw text segmentation, factual insertion, or unrestricted
language reasoning. Historical G2 and LTM-I1 results are unchanged.

## Measured results

| Metric | Development | Locked |
| --- | ---: | ---: |
| Cases | 4000 | 8000 |
| Accepted precision | 0.1312 | 0.0000 |
| Safe coverage | 0.0932 | 0.0000 |
| All-case exactness | 0.0932 | 0.0000 |
| Incorrect accepted | 2471 | 0 |
| One-step exactness | 0.4648 | 0.0000 |
| Energy increases | 0 | 0 |
| Runtime seconds | — | 5.98 |

The evaluator compares the latent candidate with hidden semantic gold. Runtime
receives no relation labels, logical closure, or evaluator path. Every result
emits an empty factual-operation tuple.

## Interpretation

The first failed boundary is the stored-body kernel: development one-step
exactness is below the required 0.90 gate, and cross-body chains do not compose.
This is therefore a representation failure, not evidence that the latent field
is safe for reasoning. The naturalistic MiniLM panel is diagnostic only.

The locked calibration selected abstention for every locked query (`confidence
0.60`, `margin 0.00`) because no tested threshold on development achieved a
zero-false-accept operating point with useful coverage. Consequently the locked
zero-coverage result is a safety-preserving abstention result, not a claim that
the underlying scores were exact. The decisive failure remains the development
kernel gate: one-step stored-body completion reached only 46.48%, and the
depth-2, 3, 5 and 6 composition panels reached 0% exactness.

Integrity checks passed in the authoritative `r5` workspace: no relation labels
or closure were visible to runtime, factual operations were always empty, the
source hash matched the frozen manifest, all 32 locked shards were immutable,
and 16 replayed predictions matched exactly. The naturalistic 1,200-case panel
was recorded as diagnostic-only and did not affect classification.

Intervention artifact: `workspaces/ltm-inference-i1-r5/intervention-results.json`.

## Next boundary

I1 does not authorize I2. The next engineering step is to redesign and retest
the field law on stored-body completion—specifically a compositional transition
state that can be carried from one body into the next—before adding raw-data
compilation or any factual handoff. G6/G9 remain the only factual authority.
