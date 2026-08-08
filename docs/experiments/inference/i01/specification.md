# I1 — Relation-Free Mumbrane Latent Inference

## Boundary

I1 tests whether a compact learned energy law can compose complete reasoning
bodies from simple atomic Mumbranes without receiving explicit G1 relation
names, roles, rules or logical closure. The authoritative input is supplied
atomic semantic data; the frozen-MiniLM naturalistic panel is diagnostic only.

Runtime may see semantic vectors, body membership, local order/phase, polarity,
modality, scope/time, identity and provenance. It may not see relation labels,
named roles, proof depth, template IDs, evaluator paths or precomputed closure.
Every result is a soft candidate and `factual_operations` is always empty.

## Field law

The trainable kernel is a shared pair/set energy potential (15,457 parameters
in the measured run). It retrieves at most 32 bodies and 256 active Mumbranes,
clamps the prompt state, and performs eight projected updates from a neutral
answer state. Candidate activations remain in `[0,1]`; an accepted update may
never increase the measured energy. The field is trained on masked complete
bodies and semantic corruptions (reversal, polarity, missing input, scope and
confounder changes), never on relation labels or answer-specific templates.

## Suites and gates

The run generates 24,000 training bodies, 8,000 development bodies/4,000
queries, and 50,000 locked bodies/8,000 queries. Locked queries cover unseen
fillers, two-to-six-hop chains, conjunctions, direction/polarity, context,
ambiguity and unknown outcomes. The first mandatory boundary is stored-body
completion (one-step exactness ≥0.90); later gates require ≥0.90 two-to-four-hop
exactness, ≥0.85 five-to-six-hop exactness, ≥0.95 accepted precision, ≥0.85
safe coverage, ≥0.95 intervention accuracy, candidate/frontier recall 1.00,
zero severe errors, monotonic trajectories, no scans, and no factual commits.

Commands are provided by `python -m ltm_inference_i1` for model checking,
dataset generation, development, calibration, freeze, locked evaluation,
intervention, naturalistic diagnostics, verification, reporting and resume.

Research basis: [Neural Relational Inference](https://proceedings.mlr.press/v80/kipf18a.html),
[Relational Potentials](https://proceedings.mlr.press/v202/comas23a.html),
[Hopfield Networks Is All You Need](https://openreview.net/forum?id=tL89RnzIiCd),
[Associative Memories via Predictive Coding](https://proceedings.neurips.cc/paper_files/paper/2021/hash/1fb36c4ccf88f7e67ead155496f02338-Abstract.html),
and [Generalization without Systematicity](https://proceedings.mlr.press/v80/lake18a.html).
