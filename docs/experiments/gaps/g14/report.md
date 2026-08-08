# G14 — Unified Benchmark Report

## Two verdicts

| Verdict | Result |
| --- | --- |
| Structured controlled architecture | `G14-C-A — PASS` |
| Raw-language product path | `G14-P-NOT-READY` |

The verdicts intentionally answer different questions. The controlled result
uses public, evaluator-separated typed facts and rules; the runtime cannot read
the gold conclusion. It exercises G3 addressing, G4 traversal, G5 widening,
G6 exact execution, G7 reconciliation, and G9 independent verification. It
does not establish raw-language compilation, fluent model decoding, or broad
benchmark quality.

## Controlled locked result

| Method | Accuracy | Required-factor recall |
| --- | ---: | ---: |
| Full controlled LTM | 1.000 | 1.000 |
| Bounded retrieval control | 0.683 | 1.000 |
| No exact propagation | 0.317 | 1.000 |
| No session overlay | 0.933 | 0.967 |
| No coverage widening | 0.850 | 0.921 |

The paired bootstrap interval for full minus bounded retrieval is
`[0.263, 0.370]`.
The independent G9 verifier rejected `1.000`
of deliberately fabricated hard-state bundles. Semantic replay matched exactly;
the measured peak RSS was `4784.8 MB`, below the 20-GB ceiling.

G7 soft reconciliation was executed but did not change the symbolic labels in
this hard-reasoning suite; this run therefore does not demonstrate a separate
end-to-end answer-quality contribution from soft optimization. G8 batching,
G11 lifecycle, G12 persistence, and G13 scaling remain upstream component
evidence rather than newly composed per-request claims in this small benchmark.

## Public benchmark status

LongMemEval items discovered: `500`.
LoCoMo QA items discovered: `1986`.

The current raw-language product path is **not ready** because the frozen G2,
G2.1 and G10 results already fail their required input and decoder gates. Public
data was catalogued without injecting its answers or evidence into runtime.
Published online scores are contextual references only and do not affect this
classification.
