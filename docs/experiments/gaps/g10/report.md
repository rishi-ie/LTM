# G10 — Compact Verified Conversational Decoder Report

## Classification

**G10-T-B — SAFE BUT MODEL-LIMITED**

## Locked technical-faithfulness result

The pinned Qwen 0.5B received 64 bounded G9-authorized bundles. A separate
runtime worker saw only public bundles; the evaluator read hidden expected
claims afterwards. Every final response passed authorization, was repaired
once, or used a deterministic verified fallback. Human naturalness was not
scored.

| Metric | Result |
| --- | ---: |
| adversarial cases | 64 |
| authorized claim precision | 1 |
| authorized claim recall | 1 |
| conflict disclosure | 1 |
| correct final disposition | 1 |
| direct generation acceptance | 0.28125 |
| fallback control acceptance | 1 |
| ood abstention | 1 |
| opposite polarity final claims | 0 |
| ordinary fallback rate | 0.67857143 |
| preference adherence | 1 |
| raw unsupported claims | 7 |
| rejected text exposed | 0 |
| repair recovery rate | 0 |
| unsupported final claims | 0 |
| validator adversarial rejection | 1 |

## Structured-state diagnostic

| Diagnostic | Result |
| --- | ---: |
| full conflict disclosure | 1 |
| full panel direct acceptance | 0.375 |
| full preference adherence | 1 |
| full unknown abstention | 1 |
| no state conflict disclosure | 1 |
| no state direct acceptance | 0.3125 |
| no state preference adherence | 0.25 |
| no state unknown abstention | 1 |
| state only direct acceptance | 0.09375 |

Deterministic semantic replay: `True`;
metric replay: `True`. Runtime:
`32.479 s`; peak RSS: `295.08 MB`.

The validator rejected `64/64`
registered adversarial responses. Retained model failures requiring repair or
fallback: `46`.

## Bounded conclusion

This classification describes only controlled verified-bundle rendering. It
does not establish unrestricted language compilation, latent-prefix decoding,
human-rated naturalness, integrated conversation memory or 100M-context
serving.
