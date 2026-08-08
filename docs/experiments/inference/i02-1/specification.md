# I2.1 — Aligned Transition and Minimap Navigation Audit

## Objective

I2.1 is a conservative repair experiment for I2. It asks whether an anonymous
transition field can support bounded multihop navigation once its prompt,
body-input, body-outcome, and minimap summaries occupy the **same learned
128-dimensional coordinate system**.

It does not claim a universal proof. A pass is evidence for the explicit,
controlled claim below; a failure identifies the first mechanism that is
insufficient.

> Given supplied atomic Mumbranes with input/outcome phase only, an aligned
> shared transition representation can recover one-step outcomes, retrieve the
> required next body through a minimap, and then compose a certified sequence
> of bounded state updates without G1 relation names, named roles, closure, or
> supplied answer candidates.

I2.1 evaluates **terminal completion**, not an arbitrary user-selected hop
count. The original I2 public prompt supplied only an initial Mumbrane while
the evaluator expected a hidden depth-specific target. That task is
underdetermined: identical public prompts cannot tell a runtime whether to
stop after one body or sixty-four. In I2.1, a query asks for the stable
source-backed completion of the prompt state. The hidden path length is an
evaluation property, never a runtime input; inference stops only when no
compatible observed transition remains.

I2 remains immutable. I2.1 uses a new package and workspace:

```text
config:     configs/ltm-inference-i21.json
package:    src/ltm_inference_i21/
tests:      tests/ltm_inference_i21/
docs:       docs/experiments/inference/i02-1/
workspace:  workspaces/ltm-inference-i21-r1/
```

## I2 audit finding

I2 trained `TransitionKernel.project(source)` and
`TransitionKernel.project(outcome)`, then at runtime compared the learned
prompt position against `state_projection(source)`, a deterministic raw
128-dimensional slice. These are different coordinate systems. A frozen I2
diagnostic over 256 development bodies measured:

| Retrieval representation | Same-body recall@64 | Median rank |
| --- | ---: | ---: |
| I2 runtime learned-query/raw-body comparison | 0.000 | 12,493 |
| Aligned learned-query/learned-body comparison | 1.000 | 1 |

This makes I2's `0.0005` required-body frontier recall uninterpretable as a
test of the broader theory. I2.1 repairs this specific mismatch before testing
any long path.

## Architecture

For every atomic Mumbrane semantic vector `v`, learn one shared transform:

```text
x = normalize(T_phi(v))   # 384D -> 128D
```

For body `b`:

```text
u_b = pool({x_i | phase(i) = input})
o_b = pool({x_i | phase(i) = outcome})
d_b = normalize(o_b - u_b)
```

The runtime may see only `u_b`, `o_b`, `d_b`, phase membership, scope/time
coordinates, provenance, and minimap cell summaries. It never receives a G1
relation name, named role, answer identifier, proof depth, closure, or
query-specific cache.

The immutable prompt anchor is `q0 = pool(T_phi(prompt Mumbranes))`; the
movable inference state starts as `z0 = q0`. At each accepted step, a body is
retrieved by learned source compatibility and context compatibility, then
proposes:

```text
z_next = normalize(z + alpha * d_b)
```

It is accepted only when a single registered energy decreases and the proposed
position scores closer to `o_b` than its source/corrupt alternatives. A
candidate is discovered only from outcome Mumbranes in opened bodies.

### Minimap summaries

Every cell stores only shared learned summaries:

```text
source prototypes:  up to 8 vectors in T_phi space
outcome prototypes: up to 8 vectors in T_phi space
transition modes:   up to 8 low-rank d_b vectors
context mask, radius, dispersion, child lower bound, membership hash
```

Every body contributes to one leaf and all ancestors; no cell stores paths,
answers, closure, or query endpoints. I2.1 uses the captured stable Mumbrane
identity to address the current leaf exactly, then uses learned source-state
compatibility to select within that bounded leaf. This is deliberate: it
isolates aligned local transition/navigation. It does **not** claim that its
minimap has already learned global child descent from a semantic centroid.

The controlled field requires each observed body to move both semantic state
and a stable identity address to a distinct next leaf. Therefore a depth-`d`
completion reopens `d` different minimap leaves. The exact identity index is
an allowed Mumbrane feature and bounds the search space; it is never an
origin-to-terminal mapping, because the next identity is revealed only by the
outcome of an opened body.

## Diagnostic ladder and gates

I2.1 proceeds strictly in order. Later stages are not executed if an earlier
one fails.

| Stage | Runtime condition | Purpose | Mandatory gate |
| --- | --- | --- | --- |
| D0 | Exact body source vector only | Coordinate alignment | source-body recall@64 `>=0.995`; source/outcome separation `>=0.95` |
| D1 | Correct body supplied | Local transition | one-step exactness `>=0.95`; direction/context twins `>=0.99`; no energy increases |
| D2 | Prompt + minimap, one hop | Hierarchical retrieval | required-body recall@64 `>=0.99`; candidate discovery recall `1.00`; no full scan |
| D3 | Dynamic reopening, 2–4 hops | Short composition | answerable exactness `>=0.90`; precision `>=0.95`; zero severe accepted errors |
| D4 | Dynamic reopening, 5–16 hops | Medium composition | answerable exactness `>=0.85`; intervention accuracy `>=0.95` |
| D5 | Dynamic reopening, 17–64 hops | Long controlled composition | answerable exactness `>=0.80`; coverage `>=0.85`; zero severe accepted errors |

All stages retain the I2 bounded-access constraints: 64 active bodies, 512
active Mumbranes, no factual operation, no network access, CPU float32, four
threads, and no full-field scan. I2's 32-step limit is insufficient to certify
a one-body-per-update depth-64 path without an untested macro-transition or
cached closure, so I2.1 permits **up to 64 accepted state updates** for D5.
Any request outside certified depth or
coverage returns `unknown` or `incomplete_frontier`.

## Training

Training uses complete observed bodies and corruptions, not relation labels or
question-answer supervision.

1. **Alignment and local transition:** train same-space source retrieval,
   outcome attraction, source/outcome discrimination, and swapped/corrupt
   transition margins.
2. **Minimap distillation:** train cell lower bounds and transition modes to
   preserve the ranking of their descendant bodies in the shared state space.
3. **Navigation:** train only on open-body continuation states up to depth 4;
   deep paths remain held out for D4/D5.

Hard negatives include another state of the same entity, the same state of a
different entity, reversed phase bodies, missing conjunction inputs, wrong
scope/time, and semantically similar confounders. This prevents success from
being attributable to entity identity, state order, or a single nearest
semantic vector.

## Controls and causal tests

The locked suite compares the full method with:

1. raw-vector versus learned-query mismatch (the original I2 defect);
2. learned vector but no transition displacement;
3. correct body supplied (D1 upper diagnostic);
4. fixed frontier;
5. no minimap summaries;
6. no state movement;
7. shuffled body membership;
8. random shared transition kernel;
9. removed decisive body, reversed phase, removed conjunction input,
   scope/time change, relevant-region change, irrelevant-region change, and
   stale-summary corruption.

The full method must outperform fixed-frontier and no-movement controls by at
least 20 points on the stage they are evaluated. Shuffled membership and random
kernels must collapse to near chance. No output may become a factual G1 or
Mumbrane insertion.

## Research basis

The design is plausible but not guaranteed. The following primary sources
support its individual mechanisms, while also setting a high falsification
bar:

- [Kipf et al., *Neural Relational Inference* (ICML 2018)](https://proceedings.mlr.press/v80/kipf18a.html)
  shows that latent interactions and dynamics can be learned from observations;
  I2.1 keeps the interaction representation unnamed.
- [Ramsauer et al., *Hopfield Networks Is All You Need* (ICLR 2021)](https://openreview.net/forum?id=tL89RnzIiCd)
  establishes the connection between attention-style retrieval and continuous
  associative-energy updates.
- [Salvatori et al., *Associative Memories via Predictive Coding* (NeurIPS 2021)](https://proceedings.neurips.cc/paper_files/paper/2021/hash/1fb36c4ccf88f7e67ead155496f02338-Abstract.html)
  supports testing iterative completion from partial observations rather than
  treating a single retrieval score as inference.
- [Du et al., *Reduce, Reuse, Recycle* (ICML 2023)](https://proceedings.mlr.press/v202/du23a.html)
  demonstrates that compositional failure can be caused by the sampler;
  I2.1 therefore tests transition learning, retrieval, and dynamics separately.
- [Lake and Baroni, *Generalization without Systematicity* (ICML 2018)](https://proceedings.mlr.press/v80/lake18a.html)
  is the reason that split-disjoint paths, reversals, and held-out depth remain
  mandatory: local completion alone is not evidence of systematic composition.

## Commands

```bash
python -m ltm_inference_i21 model-check --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 dataset-build --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 minimap-build --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 develop --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 calibrate --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 freeze --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 locked-suite-build --workspace workspaces/ltm-inference-i21-r1
python -m ltm_inference_i21 evaluate --workspace workspaces/ltm-inference-i21-r1 --offline
python -m ltm_inference_i21 intervene --workspace workspaces/ltm-inference-i21-r1 --offline
python -m ltm_inference_i21 verify --workspace workspaces/ltm-inference-i21-r1 --offline
python -m ltm_inference_i21 report --workspace workspaces/ltm-inference-i21-r1
```

## Project structure and tests

```text
src/ltm_inference_i21/      aligned field, minimap, evaluator adapters and CLI
tests/ltm_inference_i21/    unit, leakage, intervention and replay tests
docs/experiments/inference/i02-1/  frozen design and measured report
```

Tests must prove: one shared state transform is used for every runtime
comparison; the prompt anchor is unchanged; body outcome candidates are
discovered rather than supplied; summaries have no closure/query endpoints;
every accepted step lowers energy; D0/D1/D2 fail independently when their
mechanism is removed; stale summaries fail closed; and factual operations are
always empty.

## Boundaries

- Always: preserve I1/I2 artifacts, evaluator/runtime separation, bounded
  access, split disjointness, and fail-closed abstention.
- Ask first: introduce a larger encoder, add a dependency, alter G1/G6/G9, or
  relax a gate after locked generation.
- Never: use relation labels, roles, proof depths, closure, answer candidates,
  query-specific caching, or factual commits at runtime.

## Open decision

I2.1 can rigorously test the repaired mechanism, but cannot "perfectly prove"
all possible latent-field laws. Its strongest honest outcome is a controlled
mechanism pass through depth 64 with the above intervention evidence. Approval
is required before implementation because it creates a new experimental
package, dataset, and locked execution lineage.
