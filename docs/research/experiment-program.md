# LTM Experimental Program

This is the consolidated first-principles evaluation program for LTM. The
[canonical architecture](../architecture.md) defines the system, while the
[experimental report](../report.md) records what has actually been measured.

The program separates four claims:

1. the complete latent-field pipeline can execute;
2. field optimization adds value beyond retrieval or averaging;
3. a native typed topology supports reasoning;
4. sparse activation preserves quality as persistent knowledge grows.

Success on one claim does not establish the others. In particular, the
completed semantic-surrogate POC validates pipeline mechanics but does not test
the native reasoning topology.

## Dated frontier context

The following public values were recorded on **2026-07-28** as comparison
context, not as LTM results. Vendor harnesses may differ and should be
independently reproduced before direct comparison.

| Benchmark | GPT-5.6 Sol | Claude Fable 5 |
| --- | ---: | ---: |
| Artificial Analysis Intelligence Index | 58.9 | 59.9 |
| Agents' Last Exam | 52.7% | 40.5% |
| SWE-Bench Pro | 64.6% | 80.0% |
| Terminal-Bench 2.1 | 88.8% | 83.1% |
| GPQA Diamond | 94.6% | 92.6% |
| FrontierMath Tier 1–3 | 89.0% | 87.0% |
| FrontierMath Tier 4 | 83.0% | 87.8% |
| HealthBench Professional | 60.5% | 60.9% |
| AutomationBench | 18.1% | 17.4% |
| Toolathlon | 58.0% | 61.7% |

Sources:

- [OpenAI GPT-5.6 launch evaluation](https://openai.com/index/gpt-5-6/)
- [OpenAI GPT-5.6 Sol model reference](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Anthropic Claude Fable 5 model reference](https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5)

## Planning targets, not measurements

These ranges are hypotheses retained for future experiment design.

| Evaluation | First credible POC | Mature domain LTM |
| --- | ---: | ---: |
| MRCR-style retrieval at 512K–1M | 65–85% | 85–95% |
| GraphWalks-style BFS at 1M | 70–88 F1 | 88–97 F1 |
| MRCR-style retrieval at 10M | 55–75% | 75–90% |
| MRCR-style retrieval at 20M | 50–70% | 70–88% |
| Evidence-grounded multi-hop QA | 55–75% | 75–90% |
| Configured constraint validity | 80–95% | 92–99% |
| Contradiction resolution with citations | 65–85% | 85–95% |

No completed LTM experiment has established these values.

**Status:** Specification for review; implementation has not started.  
**Target machine:** 16 GB Apple Silicon MacBook Pro.  
**Research question:** Can a configured reasoning topology induce a query-conditioned latent field whose optimization solves unseen structured problems more usefully than retrieval alone and with a credible path to sparse scaling?

## 1. Decision gates

The program is deliberately staged. A later gate should not be used to explain away failure at an earlier gate.

| Gate | Question | Pass condition |
| --- | --- | --- |
| G0 | Is the harness reproducible? | Same seed reproduces data hashes and metrics within numerical tolerance. |
| G1 | Can the topology represent the relations? | It generalizes on held-out edges and compositions and distinguishes direction. |
| G2 | Does the explicit field encode useful attractors? | Valid targets are reached more often than nearest-neighbor and random baselines where optimization is relevant. |
| G3 | Can a small neural field preserve the explicit field? | It preserves gradients, attractors and rankings on held-out states. |
| G4 | Does latent optimization perform verified multi-step reasoning? | It generalizes beyond trained path depth and beats non-reasoning ablations. |
| G5 | Is the decoder only an interface? | Correctness tracks the verified state; the decoder does not repair invalid states by guessing. |
| G6 | Does modular activation improve the quality–cost frontier? | Sparse routing retains quality while active work grows sublinearly with stored modules. |

Passing every gate would establish a credible bounded-domain LTM POC. It would not establish general intelligence, 20M-token production performance or frontier-model parity.

## 2. Operating constraints

- Core experiments require no paid API and no proprietary model.
- Use synthetic or small public datasets; cache any optional downloaded asset.
- Default model size: at most 2 million trainable parameters.
- Extended model size: at most 10 million parameters, run only after the default passes.
- Peak resident memory target: below 8 GB; hard ceiling: 12 GB.
- Smoke test target: below 60 seconds per experiment.
- Standard run target: below 20 minutes per seed.
- Use five seeds for reported numbers; one seed is acceptable for development.
- Every learned method has a deterministic or simpler baseline.
- Every run writes config, seed, Git revision, data hash, timings and metrics.
- No natural-language teacher or decoder is allowed in the core topology/field tests.

## 3. Proposed technical stack

- Python 3.11 or newer;
- NumPy and SciPy for generators, exact energies and solvers;
- PyTorch with MPS when supported and CPU fallback;
- NetworkX for transparent graph baselines;
- scikit-learn for calibration and retrieval baselines;
- Pydantic for topology and result schemas;
- pandas and Matplotlib for tables and plots;
- pytest for unit, property and regression tests.

Avoid distributed frameworks, vector databases and experiment servers in the first implementation. JSONL, CSV and local plots are sufficient.

## 4. Proposed project layout

```text
ltm/
  config.py
  schemas.py
  data/
    relational.py
    constraints.py
    memory.py
  topology/
    explicit.py
    embeddings.py
    energies.py
  fields/
    analytic.py
    neural.py
    modular.py
  optim/
    gradient.py
    stochastic.py
    fixed_point.py
  decode/
    symbolic.py
    neural.py
  verify/
    constraints.py
    evidence.py
  baselines/
    retrieval.py
    graph_search.py
    brute_force.py
  experiments/
    registry.py
    runner.py
    definitions/
tests/
configs/
results/
```

Proposed commands:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest
python -m ltm.experiments.runner --experiment T1 --preset smoke --seed 0
python -m ltm.experiments.runner --suite gate1 --preset standard --seeds 0,1,2,3,4
```

## 5. Shared harness: E0

### E0.1 Deterministic world generator

Generate entities, typed directed relations, rules, conflicts, source IDs and confidence values from a seed.

Acceptance:

- identical seed and config produce identical canonical JSON and SHA-256 hash;
- different seeds change at least 95% of entity identifiers;
- generated positive and negative sets have no overlap;
- a reference symbolic evaluator labels every query.

### E0.2 Run record

Every run stores:

```json
{
  "experiment": "T1",
  "config": {},
  "seed": 0,
  "data_hash": "...",
  "git_revision": "...",
  "device": "mps",
  "peak_memory_mb": 0,
  "wall_seconds": 0,
  "metrics": {}
}
```

### E0.3 Statistical reporting

Report median and interquartile range across five seeds. Where a paired example-level comparison is available, also report a bootstrap 95% confidence interval. Never select the best seed.

## 6. Reasoning-topology experiments

### T1 — Directionality

**Question:** Can the representation distinguish \(A\rightarrow B\) from \(B\rightarrow A\)?

Data:

- 256 entities;
- four directed relation types;
- 2,048 true edges;
- equal numbers of reversed and random negatives;
- 70/15/15 split with entities shared but edges held out.

Methods:

- undirected cosine embedding;
- TransE-style translation;
- proposed Origin/Target dual vectors;
- small bilinear relation model.

Sweep:

- dimension 8, 16, 32 and 64;
- 1K, 2K and 4K training edges;
- three noise levels: 0%, 5% and 15% flipped labels.

Metrics:

- ROC-AUC;
- Hits@10;
- reverse-edge false-positive rate;
- expected calibration error;
- parameters and training time.

Pass:

- dual or typed representation achieves AUC at least 0.90;
- reverse-edge false-positive rate below 10%;
- improvement over cosine is at least five percentage points on the reverse-negative subset.

Falsifies:

- the proposed dual representation if it does not beat the simpler typed alternatives.

### T2 — Relation-family expressivity

**Question:** Which operators are required for symmetry, antisymmetry, inversion, composition and transitivity?

Generate separate worlds with exactly one relation family, then mixed worlds. Hold out relation compositions, not just edges.

Metrics:

- accuracy per relation family;
- mixed-world interference;
- composition accuracy at path lengths 2–6;
- parameter-normalized accuracy.

Pass:

- at least 90% on in-distribution relation tests;
- at least 75% on held-out compositions;
- no relation family loses more than 15 points when mixed.

### T3 — Hierarchical geometry

**Question:** Does hyperbolic or order geometry improve hierarchical storage?

Data:

- balanced and unbalanced trees;
- branching factors 2, 4 and 8;
- depths 4–10;
- held-out ancestor and sibling queries.

Compare:

- Euclidean point embeddings;
- Poincaré embeddings;
- order/density embeddings;
- exact tree distance.

Metrics:

- parent link prediction;
- ancestor accuracy;
- average distance distortion;
- performance per depth;
- numerical instability count.

Pass:

- a learned geometry retains at least 85% ancestor accuracy at two depths beyond training;
- it shows a material advantage over Euclidean embeddings at fixed dimension.

### T4 — Typed constraints and energy terms

**Question:** Is a shared set of primitives enough to express useful domain reasoning?

Create three tiny domains with the same abstract primitives:

1. package dependencies;
2. task scheduling;
3. access-control policies.

Each domain supplies a JSON configuration mapping its relations to dependency, conflict, evidence, goal and uncertainty energies.

Compare:

- one undifferentiated edge type;
- typed relations without constraints;
- typed relations plus domain validators;
- exact brute-force solution.

Metrics:

- valid-solution rate;
- invalid transition rate;
- cross-domain config reuse;
- number of custom code paths required.

Pass:

- at least 90% of generated instances are expressible without changing the shared schema;
- validators catch at least 95% of deliberately invalid states.

### T5 — Contradiction, confidence and provenance

**Question:** Does conflicting evidence remain explicit instead of being averaged away?

Generate claims supported and contradicted by sources of varying reliability and recency. Include cases where the minority source is authoritative.

Metrics:

- final belief Brier score;
- contradiction recall;
- authoritative-minority accuracy;
- provenance precision/recall;
- unresolved rate.

Pass:

- contradiction recall at least 95%;
- every resolved answer retains the decisive source;
- calibrated weighting beats majority vote on authoritative-minority cases.

### T6 — Incremental updates

**Question:** Can knowledge be added without global retraining or destructive drift?

Train on version \(V_1\), add 1%, 5% and 10% new states, and explicitly retract 1% of old facts.

Compare:

- global retraining;
- local module update;
- append-only index;
- no-update control.

Metrics:

- new-fact accuracy;
- retained-fact accuracy;
- retraction success;
- unrelated-state drift;
- update time and bytes rewritten.

Pass:

- at least 95% retention and 90% new-fact accuracy;
- retracted facts fall below 10% confidence;
- local update uses less than 20% of global retraining time.

## 7. Latent-field experiments

### F1 — Analytic attractor sanity

**Question:** Does the simplest field behave as intended?

Construct two-dimensional Gaussian or Epanechnikov mixtures with known modes. Start a query grid over the plane and optimize every point.

Sweep:

- 2–20 clusters;
- balanced and 100:1 imbalanced density;
- separation 0.5–5 standard deviations;
- query-anchor weight 0–10.

Metrics:

- basin assignment;
- mode-location error;
- convergence rate;
- spurious minima;
- collapse into the largest cluster.

Pass:

- at least 98% agreement with analytic/numerical reference modes in well-separated cases;
- documented phase boundary for collapse and mode merging.

This is a mechanics test, not an LTM success claim.

### F2 — Query anchoring

**Question:** Can the field preserve user intent while using corpus influence?

Place a small relevant cluster near the query and a much larger irrelevant cluster farther away. Sweep anchor weight, density imbalance and distance.

Compare:

- no anchor;
- fixed quadratic anchor;
- learned query-conditioned gate;
- nearest neighbor.

Pass:

- at least 90% relevant-cluster arrival across a predeclared stable parameter interval;
- field optimization must improve something other than reproducing nearest-neighbor output.

### F3 — Explicit topology energy

**Question:** Does lower energy correlate with true constraint satisfaction?

Enumerate every state for small dependency, scheduling and access-control instances. Compute exact validity and the proposed energy.

Metrics:

- Spearman correlation between negative energy and number of satisfied constraints;
- fraction of global minima that are valid;
- energy margin between best valid and best invalid states;
- calibration by domain.

Pass:

- every hard-constraint task has a valid global minimum;
- at least 95% of global minima are valid across generated instances;
- positive valid–invalid energy margin in at least 90% of instances.

If this fails, do not train a neural field.

### F4 — Field distillation

**Question:** Can a small neural model preserve an explicit energy landscape?

Train:

- scalar MLP \(E_\phi(x,q)\), with field obtained through \(-\nabla_xE_\phi\);
- unconstrained vector MLP \(F_\phi(x,q)\);
- low-rank scalar field;
- explicit energy reference.

Sweep:

- latent dimensions 8, 16, 32 and 64;
- 50K–500K sampled states;
- 50K, 250K, 1M and 2M parameters.

Metrics:

- energy RMSE;
- gradient cosine similarity;
- attractor agreement;
- ranking agreement;
- numerical curl for the vector model;
- held-out topology accuracy.

Pass:

- gradient cosine at least 0.90;
- attractor agreement at least 90%;
- no more than five-point loss in verified solution rate.

### F5 — Capacity and catastrophic smoothing

**Question:** How does a fixed-capacity field degrade as stored structure grows?

Store 100, 1K, 10K, 50K and 100K states. Repeat with independent, clustered and highly correlated states.

Metrics:

- exact-state recall;
- rare-state recall;
- pairwise distinguishability;
- spurious minima per 1K probes;
- bits stored per parameter;
- fit of error against states/parameter and correlation.

Decision:

- derive an empirical capacity curve;
- reject any “unlimited weights-only memory” interpretation if error rises without modular or external storage.

### F6 — Modular versus monolithic fields

**Question:** Does sharding reduce interference?

Train 2, 4, 8, 16 and 32 domain modules. Compare one monolithic model, oracle routing, learned top-k routing and all-module activation.

Metrics:

- router recall@k;
- verified answer rate;
- cross-domain query accuracy;
- active parameters;
- wall time;
- interference after adding a module.

Pass:

- top-k activation retains at least 95% of all-module accuracy;
- active parameters remain approximately flat as total modules increase on single-domain queries.

### F7 — Associative-memory baseline

**Question:** Is LTM’s field more than an associative memory?

Corrupt stored patterns by 5–50% and compare:

- nearest neighbor;
- kernel mean shift;
- modern Hopfield update;
- explicit LTM energy;
- distilled LTM field.

Report retrieval capacity by dimension and feature correlation. LTM only wins this experiment if it improves constraint-aware recovery, not merely pattern recall.

## 8. Latent-optimization experiments

### O1 — Solver comparison

Run the same fixed fields with:

- gradient descent;
- momentum;
- Adam;
- L-BFGS;
- Langevin dynamics;
- multi-start gradient descent;
- SciPy root finding where applicable.

Metrics:

- verified success;
- field evaluations;
- wall time;
- energy at termination;
- invalid-minimum rate;
- sensitivity to initialization.

Choose the solver by Pareto frontier, not final energy alone.

### O2 — Local-minimum escape

Create fields with one valid narrow minimum and several attractive invalid minima. Sweep noise, temperature schedule, restarts and particle count.

Pass:

- selected method doubles valid-minimum arrival over plain gradient descent at no more than 4× field evaluations.

### O3 — Convergence versus correctness

Seed easy-to-reach invalid equilibria. Evaluate stopping based on:

- gradient norm only;
- energy only;
- energy plus hard constraints;
- independent verifier;
- verifier-triggered restart.

Pass:

- verifier reduces accepted invalid states by at least 90%;
- verifier false rejection below 5%.

### O4 — Sequentially streamed optimization

Partition a field into 4–128 shards and compare:

- exact full-gradient accumulation before each update;
- update after every shard;
- random shard order;
- importance-weighted shard sampling;
- cached hot shards plus streamed cold shards.

Metrics:

- agreement with unsharded solution;
- passes over all shards;
- bytes read;
- order variance;
- time-to-verified-answer.

This small experiment is the first direct test of the proposed SSD-streaming idea.

### O5 — Adaptive activation

Start with top-1 routed module. Expand to top-2, top-4 or all modules only when confidence or verification fails.

Pass:

- same verified accuracy within two points of all-module activation;
- at least 50% fewer module evaluations on the mixed workload.

### O6 — Latent dimension

Sweep dimensions 2, 4, 8, 16, 32, 64 and 128 at fixed dataset sizes. Measure accuracy, optimizer steps, collisions, memory and time. Select the smallest dimension within two points of peak verified accuracy.

## 9. Decoder experiments

### D1 — Exact symbolic decoder

Map final states to canonical JSON answers and deterministic text templates.

Pass:

- 100% round-trip accuracy for valid representable states;
- malformed or incomplete states produce an explicit error, not a guessed answer.

### D2 — Small learned decoder

Train an MLP or small GRU to map:

- final state only;
- final state plus selected evidence;
- optimization trajectory;
- initial query only.

Metrics:

- exact answer;
- evidence fidelity;
- unsupported claims;
- performance of query-only leakage baseline.

Pass:

- final-state-plus-evidence improves materially over query only;
- unsupported-claim rate below 2%.

### D3 — Decoder leakage and fabrication

Give the decoder correct, corrupted, swapped and random latent states while keeping the query fixed.

Desired behavior:

- output changes when the verified state changes;
- invalid states are rejected;
- the decoder cannot recover the answer from benchmark artifacts.

Fail if a query-only or corrupted-state decoder approaches the full system. That means the decoder or dataset is doing the reasoning.

### D4 — Optional local language decoder

Only after D1–D3 pass, connect a quantized local 0.5–1.5B language model. Give it structured conclusions, evidence IDs and a verifier report; do not give it the whole original problem.

Measure:

- semantic preservation;
- citation fidelity;
- hallucination rate;
- latency and memory.

Natural-language fluency is a product test, not evidence of topology reasoning.

## 10. End-to-end experiments

### I1 — Rule-world generalization

Generate typed facts and Horn-like rules. Train on proof depths 1–3 and test depths 1–10, unseen entity names, shuffled rule order, irrelevant facts and contradictions.

Compare:

- breadth-first symbolic inference;
- brute-force solver;
- retrieval only;
- small MLP;
- graph neural network;
- explicit-field LTM;
- distilled-field LTM;
- every LTM ablation.

Primary metric: verified answer accuracy by proof depth.  
POC pass: distilled LTM exceeds retrieval and MLP by at least 10 points at unseen depths while remaining within five points of explicit LTM.

The exact solver is an upper bound, not a baseline LTM is expected to beat on correctness.

### I2 — Package dependency resolver

Generate packages, versions, optional features, requirements and conflicts. Ask for a valid minimal installation satisfying a goal.

Metrics:

- valid plan rate;
- optimality gap from brute force on small instances;
- update latency after a version or vulnerability change;
- explanation/evidence completeness.

Pass:

- at least 95% valid plans on small instances;
- median optimality gap below 10%;
- incremental update preserves unrelated solutions.

### I3 — Semantic field navigation

Use a small controlled corpus with paraphrases, topics, conflicting claims and rare facts. Use frozen local sentence embeddings only as input features.

Compare:

- cosine retrieval;
- kernel mean shift;
- explicit field;
- distilled field;
- field plus exact payload.

Field navigation passes only if it improves multi-evidence or contradiction tasks. Equal retrieval accuracy with more computation is a negative result.

### I4 — Scaling matrix

Run the successful configuration across:

- states: 1K, 10K, 50K, 100K;
- modules: 1, 4, 16, 64 simulated modules;
- active modules: 1, 2, 4, 8;
- dimensions: selected dimension and 2× selected dimension;
- optimizer budgets: 8, 16, 32, 64 field evaluations.

Fit and report empirical slopes for:

- storage versus states;
- compile time versus states;
- routing time versus modules;
- inference time versus active modules;
- error versus states per parameter;
- optimizer steps versus reasoning depth.

Do not extrapolate to 20M tokens unless the fitted regime spans at least two orders of magnitude without a phase change.

### I5 — Required ablation matrix

Remove one component at a time:

- typed topology;
- query anchor;
- constraint energy;
- provenance weighting;
- neural field distillation;
- iterative optimization;
- verifier;
- modular router;
- decoder evidence input.

The central architecture is supported only if topology plus optimization improves verified multi-step accuracy over retrieval and one-shot scoring.

## 11. Testing strategy

### Unit tests

- schema validation and canonical serialization;
- exact energy terms on hand-computed examples;
- analytic gradients versus finite differences;
- optimizer stopping and budget limits;
- verifier acceptance/rejection;
- decoder round trips.

### Property tests

- reversing a directed edge changes its score;
- adding an irrelevant disconnected module does not change an oracle-routed result;
- adding a violated hard constraint cannot lower total energy;
- permuting entity identifiers does not change accuracy;
- retracted evidence cannot remain in a verified proof;
- exact and unsharded accumulated gradients agree within tolerance.

### Regression tests

Store small golden configs and metric ranges, not large binary checkpoints. A change that moves any gate metric by more than its declared tolerance requires explanation.

## 12. Stop, pivot and scale rules

### Stop or redesign the representation if

- T1–T4 fail after comparing at least three established relation models;
- explicit energy minima do not align with valid solutions;
- results depend primarily on entity names or data leakage.

### Keep explicit topology and drop neural distillation if

- F4 loses more than five points of verified accuracy;
- field capacity scales worse than direct indexed storage at the tested sizes;
- updates require near-global retraining.

### Treat LTM as retrieval/memory, not reasoning, if

- I1 does not beat retrieval and one-shot scoring on unseen proof depths;
- iterative optimization can be removed without loss;
- decoder leakage explains the apparent performance.

### Treat LTM as a specialized neural solver if

- it works in configured domains but each new domain requires substantial custom code;
- exact solvers remain cheaper and more reliable wherever formalization is available.

### Proceed to a larger workstation only if

- G0–G5 pass;
- I1 and one applied domain pass;
- I5 shows that the proposed components contribute;
- the I4 curves indicate a plausible modular scaling regime.

## 13. Recommended execution order

1. E0 harness.
2. T1 directionality.
3. F1 analytic attractors.
4. F2 query anchoring.
5. T4 typed constraints.
6. F3 explicit topology energy.
7. O1 solver comparison.
8. O3 convergence versus correctness.
9. I1 explicit-field rule world.
10. F4 field distillation.
11. D1 and D3 decoder boundary.
12. I1 distilled-field rerun and ablations.
13. T5 contradictions and T6 updates.
14. F5 capacity and F6 modularity.
15. O4 streaming and O5 adaptive activation.
16. I2 applied domain.
17. I3 semantic navigation.
18. I4 scaling matrix.

The first decisive milestone is step 9. If explicit topology plus optimization cannot solve unseen rule-world compositions, increasing model size is unlikely to rescue the architectural claim.

## 14. POC definition

A definitive first POC is achieved when all of the following are reproduced across five seeds on the target Mac:

- topology distinguishes direction and held-out relation composition;
- explicit energy minima strongly correlate with verified validity;
- optimization reaches verified solutions beyond trained reasoning depth;
- a distilled field remains within five accuracy points of the explicit field;
- the verifier rejects at least 90% of converged invalid states;
- the decoder cannot fabricate success from corrupted latent states;
- sparse modules retain at least 95% of all-module accuracy on single-domain queries;
- the complete system beats retrieval and non-iterative ablations on multi-step tasks;
- run artifacts contain enough information for exact dataset regeneration.

This outcome would justify a larger-scale LTM program. It would still leave natural-language ingestion, real-world topology quality, 10–20M-token scaling and production economics as separate later stages.
