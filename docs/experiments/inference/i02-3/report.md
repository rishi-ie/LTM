# I2.3 — Hermetic Multiscale Relation-Free Field Inference

## Status

Implementation is in progress. No locked metric has been recorded, and this
report must not be treated as a result.

## Unfrozen development evidence

On the current 8,000-body opaque-label development field and 2,000 public
prompts, the aligned two-force prototype achieved:

| Metric | Result |
| --- | ---: |
| Accepted precision | `1.0000` |
| Safe coverage | `0.9230` |
| All-case exactness | `1.0000` |
| Answerable exactness | `1.0000` |
| Required-body frontier recall | `1.0000` |
| Incorrect accepted candidates | `0` |
| Energy increases | `0` |
| Depth 1–64 exactness | `1.0000` each |

This is an unfrozen development result only. It demonstrates that the repaired
public-only prototype can traverse opaque state labels within the 32 macro-step
budget by applying two source-backed body forces per update. It does not yet
meet I2.3's graph-diversity, learned-summary-ablation, causal-intervention, or
locked-evaluator requirements.

## Development stop

The required summary-ablation control was then run. Zeroing every learned cell
summary produced output agreement of `1.0000` with the full prototype. The
summary head therefore has no causal effect on routing or candidate selection.
The development gate correctly failed its `summary_influence` check, so the
`r2` workspace is not frozen and the locked suite is not authorized.

This is a useful negative result: the current system is an opaque,
content-addressed vector traversal with a public-only runtime boundary, not yet
a learned multiscale latent field. Further work must make summary information
necessary to resolve held-out fields rather than merely storing it alongside a
deterministic split index.

I2.3 is the post-audit replacement for the narrow I2.2 traversal demonstration. Its required evidence is a public-only runtime process, evaluator-only scoring process, opaque non-ordinal field graphs, an explicit learned field energy, learned minimap summaries, causal controls and a frozen locked evaluation.

Until those gates pass, the classification remains **unclassified**.

## Follow-up summary-dependent routing attempts

The deterministic split route was removed in subsequent, still-unfrozen
development work.  The hierarchy now uses cosine k-means in the learned
128-dimensional coordinate space and routes only by the resulting cell
centroids.  This made the minimap materially causal: replacing every cell
summary with zero changed `91.9%` of development outputs (`0.081` output
agreement).  It also exposed the actual retrieval limitation rather than
masking it behind an exact index.

| Metric | Summary-dependent development result |
| --- | ---: |
| Accepted precision | `0.9799` |
| Safe coverage | `0.9015` |
| All-case exactness | `0.9785` |
| Answerable exactness | `0.9767` |
| Required-body frontier recall | `0.9785` |
| Incorrect accepted candidates | `37 / 2,000` |
| Energy increases | `0` |
| Summary-ablation agreement | `0.0810` |

The required frontier gate is `1.0000`, so the run is correctly blocked before
freeze or locked scoring.  A four-branch centroid-opening control was also
tested under the same 64-body budget. It performed substantially worse
(`0.2215` frontier recall and `0.5780` accepted precision): broadening a lossy
centroid beam is not a substitute for summaries that preserve transition-relevant
information.

Confidence analysis also rules out a calibration-only repair.  Rejecting every
observed false accepted development candidate required a confidence threshold
of `0.031`, which reduced safe coverage to `0.6855`.  Therefore a future I2
revision needs a more expressive but bounded learned minimap representation
(for example, multiple transition modes and a learned frontier-value model),
with fresh split and causal controls.  It must not report this result as proof
that arbitrary multi-hop latent inference works.

## Frontier-LLM comparison boundary

The tested depth is one through 64 observed Mumbrane-body transitions. A hop in
this suite starts from an already supplied semantic state, locates a compatible
stored body, and moves to its supplied outcome state. It does not include raw
language interpretation, entity extraction, relation induction, goal parsing,
or answer realization. Consequently, the result must not be described as
outperforming a frontier language model at 64-hop natural-language reasoning.

The closest defensible comparison is a paired structured-state benchmark in
which both systems receive the same opaque transition bodies, the same public
query state, no answer candidates, and the same 64-body access budget. That
comparison has not been executed. The current evidence establishes only the
following measured candidate baseline:

| Matched dimension | I2.3 development evidence |
| --- | ---: |
| Maximum attempted transition depth | `64` |
| Answerable exactness, depths 1–64 combined | `0.9767` |
| Accepted precision | `0.9799` |
| Required-body frontier recall | `0.9785` |
| Learned kernel parameters | `65,792` |
| Raw-language capability | not tested |
| Paired frontier-LLM score | not measured |

A future paired evaluation must compare exactness by depth, incorrect accepted
answers, required-body recall, latency, bytes read, memory, distractor
sensitivity, causal interventions, and extrapolation to unseen graph motifs.
Until then, I2.3 is evidence for a potentially efficient specialized latent
transition substrate, not evidence of superiority over a general-purpose LLM.
