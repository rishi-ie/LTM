# G9 — Independent Result Verifier Report

## Classification

**G9-A — PASS**

## Locked experiment

G9 evaluated 48 valid reasoning-result bundles and 48 plausible corrupted
twins. The verifier independently replayed hard proof steps, source hashes,
scope, supersession, conflicts, hard factors, coverage, provenance and the
registered separable soft objective. It imported no G5–G8 engine or optimizer.

| Measurement | Result |
| --- | ---: |
| assistant self evidence rejection | 1 |
| conflict disclosure accuracy | 1 |
| corrupted rejection | 1 |
| coverage validation accuracy | 1 |
| energy residual accuracy | 1 |
| hard factor recall | 1 |
| no coverage attack false accept | 1 |
| primary failure code agreement | 1 |
| proof replay accuracy | 1 |
| registered false accepts | 0 |
| scope time supersession accuracy | 1 |
| soft state branch accuracy | 1 |
| source provenance integrity | 1 |
| valid status agreement | 1 |
| valid structural handling | 1 |

## Weak authorization controls

Values are corrupted-bundle false-accept rates.

| Control | False accepts |
| --- | ---: |
| energy threshold | 1 |
| hash only | 0.91666667 |
| no coverage | 0.083333333 |
| self critique | 1 |

Runtime: `0.0080 s`; peak RSS: `26.50 MB`.

## Bounded conclusion

This result tests a small self-contained verifier contract. It demonstrates that the independently implemented verifier rejected every registered plausible corruption before authorizing a result. It does not demonstrate cross-workspace integration, unrestricted-language correctness, decoder faithfulness, production security, or 100M-context reliability.
