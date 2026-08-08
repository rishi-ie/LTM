# I2.3 — Hermetic Multiscale Relation-Free Field Inference (Proposal)

**Status:** implementation in progress. The frozen locked suite is not yet generated.  
**Purpose:** retest the original I2 theory after the post-hoc I2.2 audit found that its result was a deterministic observed-successor walk rather than a verified learned field law.

## Objective

I2.3 asks:

> Given supplied atomic Mumbranes and complete observed bodies with no runtime relation names, named roles, closure, answer IDs, or query-specific hints, can a compact learned multiscale field law use a bounded movable latent state to retrieve and compose source-backed transitions across non-regular graphs while remaining hermetically separated from evaluator gold?

The experiment is intentionally no-goal. It tests terminal completion and source-backed abstention only. Goal-conditioned questions remain I3 and are prohibited until I2.3 passes.

## Exact claim boundary

A pass supports this limited statement:

> In a held-out non-regular observed-transition field, a compact learned shared energy law and learned hierarchical summaries can move a bounded latent state through source-backed bodies, dynamically reopen relevant regions, and return only certified terminal candidates or abstentions without runtime access to evaluator gold.

It does not establish arbitrary user-goal selection, raw language compilation, factual insertion, proof generation, universal reasoning, or replacement of G6/G9.

## Required difference from I2.2

| Requirement | I2.2 status | I2.3 requirement |
| --- | --- | --- |
| Evaluator separation | Public and gold files loaded in the same process. | Runtime and evaluator are separate commands/processes; runtime has no gold path/capability. |
| Field update | Exact selected outcome-state replacement. | Projected/backtracking update of an explicit differentiable field energy. |
| Minimap | Deterministic median-split source-vector tree. | Shared learned cell summaries and learned frontier-value scores, with a static-tree baseline. |
| Graph data | Regular 64-step numerical successor chains. | Opaque non-monotonic branching/merging graphs, conjunctions, conflicts, scopes and distractors. |
| State features | Explicit numerical state coordinate. | Opaque state tokens with no ordinal/numeric terminal clue; semantic vectors are randomized factor combinations with held-out combinations. |
| Evidence | Traversal metric only. | Mechanism, causal, isolation and shared-evidence counterfactual panels. |

## Runtime contracts

```text
AtomicMumbrane:
  unit_id, body_id, semantic_vector_ref, local_index, phase_index,
  polarity, modality, scope_key, valid_from, valid_to, identity_key, provenance_id

RuntimePrompt:
  prompt_id, clamped_unit_ids, scope_key, valid_at, maximum_bodies, maximum_steps

RuntimeResult:
  prompt_id, disposition, selected_candidate_id, supporting_body_ids,
  opened_cell_ids, energy_trajectory, coverage_disposition, failure_codes,
  factual_operations = empty
```

Forbidden in every runtime schema, vector sidecar, index, minimap cell, checkpoint metadata and environment variable:

- G1 relation names and named roles;
- answer IDs, terminal IDs, expected depth, path IDs and closure;
- evaluator source paths or hashes;
- direct numerical state rank or an ordinal terminal marker;
- query-specific cached summaries.

## Hermetic lifecycle

```text
dataset-build
  → public-field archive + evaluator-gold archive, independently hashed
  → freeze
  → runtime-infer subprocess (public archive only) writes immutable prediction shards
  → evaluator-score subprocess (gold archive plus prediction shards) writes metrics
  → verifier checks source/config/model/archive capability manifests and replay
```

The runtime process receives a capability manifest listing only field, public prompt, model and profile files. Gold-file opens, evaluator imports, hidden-environment variables and parent-directory traversal are denied and tested. The evaluator is the only process permitted to load gold.

## Learned field architecture

Use one shared kernel with no per-body trainable edges:

```text
semantic projection:             384 → 128
body source/outcome encoder:     shared 128D
transition potential:            shared MLP
multi-input set potential:       shared permutation-invariant MLP
cell summary encoder:            shared pooling + MLP
frontier-value head:             scalar shared MLP
candidate energy head:           scalar shared MLP
maximum trainable parameters:    2,000,000
```

Each minimap cell retains at most eight learned summary vectors, uncertainty, a context applicability mask, a lower energy bound, child identifiers, member count, and a hash. It stores no body-to-answer mapping, transitive closure, terminal list or query-specific content.

For immutable prompt anchor q, movable state z, body activations a, opened cells M and opened bodies F:

```text
E(z, a) =
  anchor(z, q)
+ Σ cell_gate(z, m) × cell_summary_energy(z, m)
+ Σ body_gate(z, b) × transition_energy(z, a, b)
+ context_energy(z, a)
+ conflict_energy(z, a)
+ sparsity(a)
+ frontier_cost(F)
```

Backtracking projected updates must reject every energy-increasing proposal. The state, activations and frontier may change; the prompt anchor may not.

## Dataset

Use evaluator-owned semantic programs to generate bodies, then render opaque Mumbrane vectors. Every semantic state is identified with an independent opaque token in each split; no token encodes sequence position.

Locked field:

```text
100,000 bodies
12,000 prompts
maximum active bodies: 64
maximum active detailed Mumbranes: 512
maximum optimization steps: 32
certified maximum terminal path: 64 bodies
```

Required held-out motifs:

- non-monotonic state transitions and shuffled phase order;
- branching and merging paths;
- one-to-many and many-to-one transitions;
- two-input completion in which neither input alone is sufficient;
- context, scope and temporal incompatibilities;
- semantically close confounders and irrelevant distant regions;
- ambiguous terminal candidates and intentionally missing decisive bodies;
- shared initial evidence with different valid terminal continuations, resolved only by observed compatible path/context rather than state rank.

Split disjointness covers opaque entity/state tokens, vector factor combinations, complete graph motifs, branches, contexts, scopes, body membership and path composition.

## Training

Training sees complete bodies and masked/corrupted bodies, never standalone query-answer labels, relation names or closure.

1. Local transition discrimination: masked outcome, phase reverse, missing input, wrong context and confounder corruptions.
2. Summary distillation: parent summary lower bounds and transition-support distributions must approximate child aggregates without answer supervision.
3. Dynamic composition: depth 2–16 paths with frontier opening/reopening rewards derived only from required source-backed body availability.
4. Deep and adversarial composition: depth 17–64, branches, merges, conjunctions, scope/time and intervention twins.

## Mandatory gates

| Area | Gate |
| --- | ---: |
| Runtime evaluator-gold reads | 0 |
| Runtime relation/role labels, closure, answer IDs and ordinal-state clues | 0 |
| Candidate discovery recall | 1.00 |
| Required-body frontier recall | >=0.99 |
| Cell membership and summary hash verification | 1.00 |
| Incremental versus clean minimap rebuild equality | 1.00 |
| Accepted exact precision | >=0.95 |
| Safe coverage | >=0.85 |
| All-case exactness | >=0.85 |
| Answerable exactness | >=0.90 |
| Depth 2–4 / 5–8 / 9–16 / 17–32 / 33–64 exactness | >=0.92 / 0.90 / 0.88 / 0.85 / 0.80 |
| Conjunction exactness | >=0.90 |
| Ambiguous and unknown recall | >=0.95 |
| Accepted severe context/direction errors | 0 |
| Accepted energy increases | 0 |
| Accepted convergence and certified frontier stability | >=0.99 |
| Required remote-region sensitivity | >=0.95 |
| Irrelevant-region invariance | >=0.99 |
| Full minus static-tree and full minus fixed-frontier deep-path gain | >=0.20 each |
| Factual operations | 0 |
| Deterministic replay | 1.00 |

## Controls and causal interventions

Run identical locked prompts through:

1. full learned multiscale field;
2. nearest single-body retrieval;
3. initial prompt state only;
4. fixed frontier;
5. fixed inference state;
6. deterministic I2.2-style vector tree;
7. summary-only field with no detailed bodies;
8. shuffled body membership;
9. random shared kernel;
10. evaluator-only exact semantic upper bound.

Required interventions:

- remove or reverse decisive intermediate body;
- negate or alter a required outcome;
- remove one conjunction input;
- expire or rescope a decisive body;
- inject a near semantic confounder;
- modify a distant relevant region;
- modify a distant irrelevant region;
- corrupt/stale a minimap ancestor;
- swap final states of counterfactual twins.

## Commands and layout

```bash
python -m ltm_inference_i23 model-check --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 dataset-build --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 minimap-build --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 develop --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 freeze --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 locked-suite-build --workspace workspaces/ltm-inference-i23-r1
python -m ltm_inference_i23 runtime-infer --workspace workspaces/ltm-inference-i23-r1 --offline
python -m ltm_inference_i23 evaluator-score --workspace workspaces/ltm-inference-i23-r1 --offline
python -m ltm_inference_i23 intervene --workspace workspaces/ltm-inference-i23-r1 --offline
python -m ltm_inference_i23 verify --workspace workspaces/ltm-inference-i23-r1 --offline
python -m ltm_inference_i23 report --workspace workspaces/ltm-inference-i23-r1
```

```text
configs/ltm-inference-i23.json
src/ltm_inference_i23/
tests/ltm_inference_i23/
docs/experiments/inference/i02-3/
workspaces/ltm-inference-i23-r1/  # ignored
```

## Boundaries

- Always: evaluator separation, source/config/archive hashes, independent oracle, exact capability tests, immutable prediction shards, deterministic replay and full repository checks.
- Ask first: new dependencies, changes to Mumbrane/G1/G6/G9 public schemas, increasing resource budgets, or making candidates factual.
- Never: answer/path/depth leakage; relation or role labels; full field scans; arbitrary code in the field profile; silent fallback after failed coverage; historical artifact modification.

## Research basis

- [Neural Relational Inference](https://proceedings.mlr.press/v80/kipf18a.html) motivates learning interactions from observations, not assuming regular successor chains.
- [Multigrid Neural Memory](https://openreview.net/forum?id=ByxKo04tvr) motivates testing learned multiscale memory summaries.
- [Learning to Route in Similarity Graphs](https://proceedings.mlr.press/v97/baranchuk19a.html) motivates routing controls and global retrieval comparisons.
- [Compositional Energy-Based Models](https://proceedings.mlr.press/v202/du23a.html) motivates direct energy-law and composition ablations.
- [Generalization without Systematicity](https://proceedings.mlr.press/v80/lake18a.html) motivates opaque held-out graph motifs and counterfactual controls.

## Success interpretation

I2.3 is the minimum test needed to support the original I2 mechanism. If it passes, I3 can test a goal Mumbrane. If it fails, the architecture must report which of field-law learning, multiscale summary routing, or compositional data representation is insufficient; it must not use I2.2 traversal scores as proof.
