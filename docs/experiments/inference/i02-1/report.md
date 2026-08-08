# I2.1 — Aligned Transition and Minimap Navigation Audit

## Classification

**`I2.1-A — ALIGNED TERMINAL-COMPLETION PASS`**

I2.1 passes the bounded, supplied-Mumbrane claim: a fixed prompt anchor can move through up to 64 source-backed observed transitions, reopen the next identity-addressed field leaf after each accepted transition, and stop at a terminal state without relation labels, named roles, closure, a supplied answer candidate, or a factual topology operation.

## Locked evidence

The locked field contained 100,000 bodies and 4,000 hidden-evaluator queries. The runtime saw only public initial Mumbranes, scope, and fixed budgets.

| Metric | Development | Locked |
| --- | ---: | ---: |
| Source-body recall@64 (aligned) | 1.0000 | 1.0000 |
| Source-body recall@64 (I2 raw-space control) | 0.0059 | 0.0020 |
| One-step exactness | 1.0000 | 1.0000 |
| Required-body frontier recall | 1.0000 | 1.0000 |
| Answerable exactness, depths 1–64 | 1.0000 | 1.0000 |
| Accepted precision | 1.0000 | 1.0000 |
| Safe coverage | 0.9230 | 0.9230 |
| All-case exactness | 1.0000 | 1.0000 |
| Incorrect accepted results | 0 | 0 |
| Certified energy increases | 0 | 0 |

The `0.9230` coverage is the answerable fraction of the suite; the remaining queries began from a terminal state and correctly returned `unknown`. They are included in all-case exactness rather than silently accepted as conclusions.

The shared transition kernel has 65,792 trainable parameters. The 1,024-case aligned-retrieval diagnostic and the 100,000-body field both passed minimap membership accounting. The public runtime contained no G1 relation identifiers, named roles, proof depth, answer ID, closure, network call, or factual operation.

## Sensitivity and interventions

| Control or intervention | Result |
| --- | ---: |
| Full aligned field answerable exactness | 1.0000 |
| No-movement all-case upper bound | 0.0117 |
| Shuffled body-membership answerable exactness | 0.0000 |
| Raw-space mismatch recall@64 | 0.0020 |
| Remove decisive body | abstains |
| Wrong scope | abstains |
| Stale minimap | fail closed |

These controls identify the cause of the historical I2 failure: its learned prompt state was compared against deterministic raw body slices. In the same I2 development field that mismatch gave 0% same-body retrieval@64 with median rank 12,493; comparing both sides through the learned transform gave 100% retrieval@64 with median rank 1.

## What this supports—and what it does not

This is a **controlled existence result** for latent terminal completion.

```text
fixed prompt anchor
→ compatible observed body
→ unnamed outcome displacement
→ new latent position and identity address
→ reopened next leaf
→ terminal source-backed state
```

It does not prove that a relation-free field can answer arbitrary questions, infer unstored rules, choose among unrelated goals, or replace G6/G9 factual reasoning. The field uses stable Mumbrane identity as a bounded address; it does not demonstrate global learned routing without that address. It also does not authorize raw-language compilation or a decoder claim.

The research basis is consistent with, but does not prove, this result: [Neural Relational Inference](https://proceedings.mlr.press/v80/kipf18a.html) shows that latent interactions and dynamics can be learned from observations; [Hopfield Networks Is All You Need](https://openreview.net/forum?id=tL89RnzIiCd) connects attention-style retrieval to continuous associative energy updates; and [Du et al.](https://proceedings.mlr.press/v202/du23a.html) show why sampler and inference design must be evaluated separately from a compositional model. [Lake and Baroni](https://proceedings.mlr.press/v80/lake18a.html) remains the reason to avoid treating this controlled path result as systematic general reasoning.

Authoritative workspace: `workspaces/ltm-inference-i21-r2/`.
