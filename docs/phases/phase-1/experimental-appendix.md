# Phase 1 Experimental Appendix

**Status:** Deferred experiments and extensions. The binding minimal specification is
[Phase 1: Minimal Semantic-Field POC](specification.md).  
**Original target machine:** 16 GB Apple Silicon MacBook Pro.  
**Last updated:** 2026-07-29

## 1. Objective

Phase 1 builds the complete LTM inference flow while replacing the unproven reasoning topology with an established semantic embedding engine.

```text
Documents
    ↓
Frozen semantic encoder
    ↓
Semantic topology surrogate
    ↓
Query-conditioned latent dynamic field
    ↓
Latent optimization
    ↓
Exact evidence resolution
    ↓
Grounded decoder
    ↓
Human-readable answer and trace
```

The scientific purpose is to isolate the field, optimizer and decoder from the harder question of how to represent reasoning.

### Phase 1 claim

> A frozen semantic embedding space can act as a temporary topology from which corpus influence is converted into a query-conditioned energy field; iterative latent optimization can navigate this field and produce a grounded output through a separate decoder.

### What Phase 1 can prove

- all four components can be implemented and connected;
- an embedding corpus can induce a scalar energy field;
- the field gradient can be computed correctly;
- an optimizer can move a query state through the field reproducibly;
- the final state can select exact source evidence;
- optimization can be compared with direct retrieval and classical query-refinement baselines;
- the decoder can be prevented from inventing unsupported content;
- the topology-to-field boundary is replaceable.

### What Phase 1 cannot prove

- that semantic similarity is reasoning;
- that a native reasoning topology will work;
- logical, causal or planning competence;
- satisfaction of arbitrary constraints;
- generalization comparable with GPT or Claude;
- lossless storage inside field weights;
- useful 20M-token behavior from small-corpus accuracy;
- constant-cost inference over an unbounded store.

Passing Phase 1 means the architecture’s **mechanical spine** works. It does not validate the central reasoning claim.

## 2. Assumptions

1. The semantic encoder is frozen and used as a known surrogate, not trained as an LTM contribution.
2. The core POC uses no paid API and can run offline after model and optional dataset download.
3. Exact text, identifiers and provenance remain in an external payload store.
4. The latent state initially has the same dimension as the normalized semantic embedding.
5. The explicit analytic field is the reference implementation.
6. Neural field distillation is an extended Phase 1 gate, not required to debug basic field mechanics.
7. The mandatory decoder is deterministic and extractive. A local language decoder is secondary because fluency is not evidence that optimization worked.
8. Optimization must add measurable value over direct retrieval, mean shift and pseudo-relevance feedback on at least one predeclared task.

## 3. Research basis

Phase 1 combines established ideas but tests a new integration.

### Semantic representation

- [Sentence-BERT](https://aclanthology.org/D19-1410/) demonstrates efficient semantically meaningful sentence embeddings that can be compared with cosine similarity.
- [SimCSE](https://aclanthology.org/2021.emnlp-main.552/) studies contrastive sentence embeddings, including alignment, uniformity and anisotropy.
- [MTEB](https://aclanthology.org/2023.eacl-main.148/) demonstrates that embedding quality must be evaluated across retrieval, clustering, classification and semantic-similarity tasks rather than assumed from one benchmark.

These papers justify the surrogate topology. They do not show that proximity represents implication, truth, causality or constraint satisfaction.

### Density fields and mode seeking

- [Mean Shift](https://doi.org/10.1109/34.1000236) relates iterative updates to modes of a kernel density estimate.
- [Consistency of Mean Shift](https://www.jmlr.org/papers/v17/ariascastro16a.html) analyzes estimated density-gradient lines and convergence.
- [Directional Mean Shift](https://www.jmlr.org/papers/v22/20-1194.html) studies kernel smoothing and mean shift on the unit hypersphere, matching normalized cosine embeddings.
- [A Tutorial on Energy-Based Learning](https://yann.lecun.org/exdb/publis/pdf/lecun-06.pdf) formulates inference as minimization of a scalar compatibility energy.

These are the closest foundations for the explicit Phase 1 field. Classical mode seeking is therefore a required baseline, not something LTM may relabel as a novel result.

### Associative fields and iterative inference

- [Modern Hopfield Networks and Attention](https://papers.nips.cc/paper_files/paper/2020/hash/da4902cb0bc38210839714ebdcf0efc3-Abstract.html) connects continuous associative-memory updates with attention.
- [Universal Hopfield Networks](https://proceedings.mlr.press/v162/millidge22a.html) separates similarity, separation and projection choices in associative memory.
- [Deep Equilibrium Models](https://proceedings.neurips.cc/paper/2019/hash/01386bd6d8e091c2ab4c7c7de644d37b-Abstract.html) treats iterative latent computation as a fixed-point solve.
- [Neural Ordinary Differential Equations](https://papers.nips.cc/paper/2018/hash/69386f6bb1dfed68692a24c8686939b9-Abstract.html) provides a continuous-dynamics interpretation.

These works support iterative latent-state updates. They do not guarantee that the reached equilibrium is relevant or correct.

### Retrieval and grounded output

- [Retrieval-Augmented Generation](https://papers.neurips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) combines parametric generation with explicit non-parametric memory and provenance.
- [RETRO](https://proceedings.mlr.press/v162/borgeaud22a.html) shows that external retrieval can expose a model to a database containing trillions of tokens.
- [BEIR](https://arxiv.org/abs/2104.08663) shows that BM25, dense retrieval and reranking have different zero-shot trade-offs and provides a strong retrieval-evaluation framework.
- [SciFact](https://aclanthology.org/2020.emnlp-main.609/) provides claims, supporting or refuting evidence and rationales for an optional grounded evaluation.

These works make direct dense retrieval, lexical retrieval and retrieval-plus-decoding mandatory baselines.

## 4. Hypotheses

Every hypothesis is independently falsifiable.

| ID | Hypothesis | Required evidence |
| --- | --- | --- |
| H1 | Frozen embeddings provide locally meaningful semantic geometry. | Paraphrases and relevant passages rank above unrelated controls on held-out data. |
| H2 | The explicit corpus field is mathematically and numerically correct. | Autograd, analytic and finite-difference gradients agree. |
| H3 | Query-conditioned optimization is stable. | Energy decreases, termination is bounded and trajectories are reproducible. |
| H4 | Query anchoring prevents majority-cluster collapse. | Relevant rare regions remain reachable under declared imbalance levels. |
| H5 | Optimization sometimes improves evidence-set quality beyond one-shot retrieval. | Significant gain over dense kNN, lexical retrieval, mean shift and pseudo-relevance feedback on a predeclared task. |
| H6 | Exact evidence can be recovered from the final latent state. | High evidence precision/recall with complete provenance. |
| H7 | The decoder remains an interface. | Unsupported-claim rate remains near zero and corrupted states cannot produce correct-looking answers. |
| H8 | A scalar neural field can approximate the explicit field. | Held-out gradient and attractor agreement meet the distillation gate. |
| H9 | Candidate activation can bound ordinary field work. | Quality remains stable while field evaluations depend on active candidates rather than all stored chunks. |

H5 is the decisive architectural hypothesis for Phase 1. H1–H4 only demonstrate correct mechanics.

## 5. Four components

### 5.1 Component 1 — Semantic topology surrogate

#### Responsibility

Convert corpus chunks and queries into a normalized semantic space while preserving exact payloads and provenance.

#### Default engine

Use a frozen Sentence-Transformers-compatible encoder suitable for local CPU/MPS inference. The initial implementation candidate is `sentence-transformers/all-MiniLM-L6-v2`, producing 384-dimensional embeddings.

The exact model revision must be pinned during the implementation plan. A second encoder may be tested only as an ablation; model shopping after seeing results is prohibited.

#### Inputs

- UTF-8 documents;
- stable document ID;
- source URI or local identifier;
- optional title and metadata;
- deterministic chunking configuration.

#### Outputs

For each chunk:

```json
{
  "chunk_id": "doc-17::chunk-004",
  "document_id": "doc-17",
  "text": "Exact source text",
  "token_count": 187,
  "embedding": [0.01, -0.02],
  "embedding_norm": 1.0,
  "source_offset": [1432, 2281],
  "metadata": {}
}
```

#### Chunking

Core preset:

- 160–240 tokens per chunk;
- 20% overlap;
- deterministic boundary selection;
- no query-dependent chunking;
- record exact offsets;
- hash normalized text and chunking config.

Chunk-size and overlap sweeps are ablations, not tuning against the test set.

#### Geometry

All embeddings are L2-normalized:

\[
z_i=\frac{f_{\mathrm{embed}}(c_i)}
{\lVert f_{\mathrm{embed}}(c_i)\rVert_2}
\qquad
q=\frac{f_{\mathrm{embed}}(\text{query})}
{\lVert f_{\mathrm{embed}}(\text{query})\rVert_2}.
\]

Cosine similarity becomes \(q^\top z_i\). The topology is the distribution of chunks on the unit hypersphere plus their exact payload references.

#### Required interface

```python
class TopologyBackend(Protocol):
    def compile(self, corpus: Corpus) -> TopologyArtifact: ...
    def encode_query(self, text: str) -> LatentState: ...
    def activate(
        self,
        query: LatentState,
        budget: ActivationBudget,
    ) -> FieldContext: ...
    def resolve(
        self,
        state: LatentState,
        limit: int,
    ) -> EvidenceBundle: ...
```

The later reasoning topology must satisfy the same conceptual contract even if its internal state and activation algorithm differ.

#### Known limitations

- contradictory sentences may be close together;
- directionality is not guaranteed;
- dense regions may reflect corpus repetition rather than importance;
- cosine similarity is not calibrated truth;
- generic embeddings may underperform in specialized domains;
- a single vector can blur multiple meanings.

These limitations must appear in Phase 1 reports.

### 5.2 Component 2 — Latent dynamic field

#### Responsibility

Turn activated semantic states into an inspectable, query-conditioned scalar energy over the latent state.

#### Explicit reference field

For unit-normalized latent state \(x\), query \(q\), active chunks \(z_i\) and nonnegative query relevance weights \(a_i(q)\):

\[
E_{\mathrm{explicit}}(x\mid q)
=
-\log\left[
\epsilon+
\sum_{i\in C(q)}
a_i(q)
\exp\left(\frac{x^\top z_i}{\tau_f}\right)
\right]
+
\lambda_q(1-x^\top q).
\]

Where:

- \(C(q)\) is the activated candidate set;
- \(a_i(q)\) is derived only from the frozen query and declared metadata;
- \(\tau_f\) controls field sharpness;
- \(\lambda_q\) anchors the trajectory to query intent;
- \(\epsilon\) prevents undefined log energy.

The default relevance weight is:

\[
a_i(q)
=
\frac{
p_i\exp(q^\top z_i/\tau_q)
}{
\sum_{j\in C(q)}
p_j\exp(q^\top z_j/\tau_q)
},
\]

where \(p_i=1\) unless a predeclared provenance weight is available. Phase 1 must not learn \(p_i\) from test labels. Both the weight normalization and field energy are implemented with numerically stable log-sum-exp operations.

After every update, \(x\) is projected back to the unit sphere.

The field is equivalent to a query-weighted directional kernel density landscape plus an anchor. It is intentionally simple enough to inspect.

#### Candidate activation

Candidate sets are selected before optimization:

1. retrieve top \(M\) chunks by query cosine;
2. optionally add a declared diversity sample;
3. freeze the set for the request;
4. compute every field evaluation over the same set.

Changing candidates during optimization is a separate ablation because it changes the objective.

Default sweep:

- \(M \in \{32, 128, 512, 2048\}\);
- \(\tau_q \in \{0.02, 0.05, 0.1, 0.2\}\);
- \(\tau_f \in \{0.02, 0.05, 0.1, 0.2\}\);
- \(\lambda_q \in \{0, 0.1, 0.5, 1, 2, 5\}\).

#### Optional learned field

After the explicit field passes, train a small scalar network:

\[
E_\phi(x,q)\approx E_{\mathrm{explicit}}(x\mid q).
\]

The field is obtained from the scalar:

\[
F_\phi(x,q)=-\nabla_x E_\phi(x,q).
\]

Training loss:

\[
\mathcal{L}
=
\alpha_E\lVert E_\phi-E_{\mathrm{explicit}}\rVert_2^2
+
\alpha_G
\left(
1-\cos(
\nabla_xE_\phi,
\nabla_xE_{\mathrm{explicit}}
)
\right).
\]

A scalar model is preferred to a directly predicted vector field because it is conservative by construction. The explicit field remains the oracle for debugging and evaluation.

#### Field contract

```python
class EnergyField(Protocol):
    def energy(
        self,
        state: LatentState,
        query: LatentState,
        context: FieldContext,
    ) -> Tensor: ...

    def gradient(
        self,
        state: LatentState,
        query: LatentState,
        context: FieldContext,
    ) -> Tensor: ...
```

### 5.3 Component 3 — Latent optimizer

#### Responsibility

Move the initial query state toward a lower-energy semantic state under an explicit compute budget.

#### Initialization

\[
x_0=q.
\]

Optional perturbed or multi-particle starts are ablations.

#### Reference update

\[
\tilde{x}_{t+1}
=
x_t-\eta_t\nabla_xE(x_t\mid q),
\qquad
x_{t+1}
=
\frac{\tilde{x}_{t+1}}
{\lVert\tilde{x}_{t+1}\rVert_2}.
\]

#### Required solvers

- projected gradient descent;
- momentum;
- directional mean shift;
- no-optimization control.

Optional after core completion:

- Adam;
- L-BFGS;
- Langevin noise;
- multi-start particles.

#### Stopping

Terminate when the first condition is met:

- maximum field evaluations;
- energy improvement below tolerance for three steps;
- state movement below tolerance for three steps;
- non-finite value;
- explicit cancellation.

Every termination includes a machine-readable reason.

#### Trace

Store per step:

- state hash;
- energy;
- gradient norm;
- step size;
- cosine distance from query;
- nearest evidence IDs;
- active candidate count;
- elapsed milliseconds.

The full state vector may be stored for research runs but can be omitted from compact reports.

#### Optimizer contract

```python
class LatentOptimizer(Protocol):
    def optimize(
        self,
        initial: LatentState,
        query: LatentState,
        field: EnergyField,
        context: FieldContext,
        budget: OptimizationBudget,
    ) -> OptimizationResult: ...
```

### 5.4 Component 4 — Grounded decoder

#### Responsibility

Turn the final latent state and resolved source payloads into a human-readable result without doing hidden retrieval or repairing a failed state.

#### Mandatory decoder

The deterministic decoder returns:

```json
{
  "answer": "Evidence-oriented natural-language report",
  "evidence": [
    {
      "chunk_id": "doc-17::chunk-004",
      "quote": "Exact excerpt",
      "score": 0.84
    }
  ],
  "unresolved_conflicts": [],
  "optimization": {
    "steps": 14,
    "termination": "stable_state",
    "initial_energy": -3.2,
    "final_energy": -5.1
  }
}
```

The answer may:

- restate the query;
- list the most relevant evidence;
- group semantically related evidence;
- report whether multiple viewpoints were recovered;
- say that the evidence is insufficient.

It may not:

- infer an unsupported causal or logical conclusion;
- resolve a contradiction from similarity alone;
- cite a chunk that was not in the evidence bundle;
- silently call another retriever;
- use gold labels.

#### Optional local language decoder

A quantized local instruction model of at most 1.5B parameters may rewrite the deterministic evidence report. It receives only:

- the query;
- selected exact evidence;
- scores;
- explicit formatting instructions.

It does not receive:

- the full corpus;
- benchmark labels;
- hidden expected answers;
- the optimization dataset.

Its output is accepted only if every citation resolves and every factual sentence is entailed by or directly quoted from the evidence under the chosen verifier.

#### Decoder contract

```python
class Decoder(Protocol):
    def decode(
        self,
        query_text: str,
        evidence: EvidenceBundle,
        trace: OptimizationSummary,
    ) -> DecodedAnswer: ...
```

## 6. End-to-end data contracts

Canonical artifacts:

| Artifact | Contents | Mutable? |
| --- | --- | --- |
| `CorpusManifest` | document IDs, hashes, licenses and chunking config | Versioned |
| `TopologyArtifact` | normalized vectors, payload pointers and encoder identity | Immutable |
| `FieldConfig` | candidate policy, kernel, temperatures and anchor | Immutable per run |
| `QueryCase` | query, relevant evidence IDs and evaluation tags | Immutable |
| `OptimizationTrace` | state trajectory and field metrics | Append-only |
| `EvidenceBundle` | exact resolved chunks and scores | Immutable |
| `DecodedAnswer` | answer, citations and unresolved status | Immutable |
| `RunRecord` | config, seeds, revision, timing, memory and metrics | Append-only |

Every artifact includes a schema version.

## 7. Datasets

### 7.1 Controlled synthetic-semantic suite

This is the mandatory scientific dataset because it gives exact evidence labels.

#### S1 — Paraphrase islands

- 100–1,000 concepts;
- 5–20 paraphrases per concept;
- lexical distractors sharing surface words;
- unrelated controls.

Tests local geometry, cluster recovery and robustness to lexical overlap.

#### S2 — Rare intent versus dominant topic

- one relevant cluster with 5–20 chunks;
- one irrelevant but broadly similar cluster with 100–2,000 chunks;
- query closer to the relevant cluster;
- imbalance ratios from 1:1 to 1:100.

Tests query anchoring and catastrophic drift into the largest mode.

#### S3 — Multi-aspect evidence

Each query requires recovery of two or three semantic aspects. No single chunk covers every aspect. Relevant chunks form a coherent neighborhood only when considered as a set.

Tests evidence-set coverage. It must be compared with classical pseudo-relevance feedback and diversity reranking.

#### S4 — Contradictory evidence

Create paired claims and negations with source and stance labels retained only for evaluation and deterministic reporting.

Tests whether the system retrieves both sides and refuses to treat semantic closeness as agreement.

#### S5 — Semantic chains

Create sequences where adjacent chunks share one concept but endpoints have little lexical overlap.

This is a navigation test, not a reasoning test. Success means discovering a semantic route or endpoint under a declared objective; it does not mean deriving an implication.

### 7.2 External evaluation

#### SciFact subset

Use the public [SciFact](https://aclanthology.org/2020.emnlp-main.609/) corpus and claims for evidence retrieval. Gold support/refute labels are evaluation-only.

Required metrics:

- evidence Recall@5 and Recall@10;
- nDCG@10;
- evidence-set precision;
- support-and-refute coverage;
- unsupported decoder statement rate.

#### BEIR-compatible retrieval

Use the BEIR evaluation conventions for the selected subset. BM25 or TF-IDF, frozen dense retrieval and any reranking baseline must share the same corpus and query split.

### 7.3 Repository qualitative corpus

Compile the LTM documentation itself and demonstrate:

- a query trajectory;
- evidence before and after optimization;
- a final grounded report.

This is a demo only and must never be counted as quantitative evidence.

## 8. Baselines

The POC is invalid without all mandatory baselines.

| Baseline | Purpose |
| --- | --- |
| BM25 or TF-IDF | Strong lexical retrieval control |
| Dense cosine kNN | Direct use of the frozen semantic topology |
| Dense kNN plus diversity reranking | Tests whether evidence coverage needs optimization |
| Rocchio/pseudo-relevance feedback | Classical iterative query refinement |
| Directional mean shift | Classical mode-seeking equivalent |
| Query-weighted centroid | Simple one-step field approximation |
| No-optimization LTM | Same pipeline with \(x_f=q\) |
| Explicit field | Inspectable reference |
| Distilled field | Tests compression of the reference field |

Phase 1 succeeds architecturally only if optimization provides a quality–cost trade-off not dominated by these simpler methods.

## 9. Experiment matrix

### P1-E0 — Reproducibility and schemas

Verify:

- same seed produces identical synthetic corpus and query hashes;
- artifact schemas round-trip;
- corpus and encoder revision are recorded;
- no training/evaluation overlap;
- every result links to exact configuration.

Pass: all checks are deterministic on CPU and MPS.

### P1-E1 — Embedding topology sanity

Measure:

- paraphrase Recall@k;
- lexical-distractor rejection;
- cluster silhouette;
- embedding norm;
- duplicate and collision rate;
- performance by query type.

Pass:

- Recall@10 at least 0.85 on S1;
- paraphrases rank at least 10 points above lexical distractors;
- no test query is present verbatim in the corpus.

Failing E1 rejects the chosen surrogate encoder, not LTM.

### P1-E2 — Field correctness

For 100 random states and queries:

- compare analytic gradient with PyTorch autograd;
- compare both with centered finite differences;
- verify tangent projection on the unit sphere;
- verify energy is finite;
- verify identical inputs return identical outputs.

Pass:

- median relative gradient error below \(10^{-4}\);
- 99th percentile below \(10^{-3}\);
- projected gradient dot state magnitude below \(10^{-5}\).

### P1-E3 — Optimizer correctness

Run known two-dimensional and spherical toy fields before semantic data.

Pass:

- at least 99% of stable projected-gradient steps do not increase energy beyond tolerance;
- every run terminates within budget;
- optimizer reaches the known basin on at least 95% of well-separated starts;
- non-finite values return a failure record.

### P1-E4 — Query-anchor sweep

Use S2 across:

- imbalance 1:1, 1:5, 1:20 and 1:100;
- candidate size 32–2,048;
- all declared \(\tau_f\) and \(\lambda_q\);
- five seeds.

Primary metric: relevant-cluster arrival.

Pass:

- at least one predeclared parameter region achieves 90% arrival through 1:20 imbalance;
- query drift remains below the declared maximum;
- the no-anchor failure boundary is documented.

Parameters are selected using validation cases only and then frozen.

### P1-E5 — Single-evidence retrieval preservation

On S1 and SciFact:

- compare initial dense kNN with evidence resolved from the optimized state;
- measure Recall@5, Recall@10, MRR and nDCG.

Pass:

- optimized explicit field loses no more than two absolute Recall@10 points from dense kNN.

This is a safety gate, not the source of expected improvement.

### P1-E6 — Multi-evidence improvement

On S3:

- measure aspect coverage;
- evidence precision/recall;
- set nDCG;
- redundancy;
- field evaluations and latency.

Compare every mandatory baseline.

Phase 1 decisive pass:

- explicit-field optimization improves mean aspect coverage by at least five absolute points over the best non-field baseline;
- 95% bootstrap confidence interval excludes zero;
- evidence precision loses no more than three points;
- improvement reproduces across four of five seeds.

If mean shift or Rocchio matches the result at lower cost, record Phase 1 as mechanically successful but architecturally non-novel.

### P1-E7 — Contradiction preservation

On S4 and the annotated SciFact subset:

- retrieve both supporting and refuting evidence;
- measure stance-pair coverage;
- test whether the decoder labels the conflict unresolved;
- ensure no similarity score is interpreted as truth.

Pass:

- at least 90% of cases with both sides in the candidate set preserve both in the evidence bundle;
- deterministic decoder never silently resolves a labeled conflict;
- unsupported-claim rate is zero.

### P1-E8 — Semantic-chain navigation

On S5:

- evaluate endpoint discovery;
- record intermediate nearest chunks;
- compare fixed-candidate and dynamically refreshed candidates;
- compare with graph-free multi-hop retrieval and iterative query expansion.

Report this separately from reasoning. A positive result supports latent navigation only.

### P1-E9 — Decoder leakage

Give the decoder:

- correct evidence;
- shuffled evidence;
- evidence from another query;
- an empty bundle;
- a corrupted optimization summary.

Pass:

- correct citations resolve 100%;
- empty or irrelevant evidence produces an unresolved answer;
- corrupted traces do not change factual content;
- query-only accuracy stays at chance on label-balanced synthetic cases.

### P1-E10 — Neural field distillation

Only after P1-E2–E6 pass.

Sweep:

- 50K, 250K, 1M and 2M parameters;
- 25K–250K training states;
- latent dimensions 64, 128 and native encoder dimension;
- energy-only versus energy-plus-gradient loss.

Pass:

- held-out gradient cosine at least 0.90;
- attractor agreement at least 90%;
- evidence Recall@10 within five points of explicit field;
- multi-evidence coverage within five points;
- no more than 2× optimizer steps.

If it fails, Phase 1 may retain the explicit field and defer compression.

### P1-E11 — Scaling simulation

Use average chunk length 200 tokens:

| Chunks | Token-equivalent storage |
| ---: | ---: |
| 5,000 | 1M |
| 25,000 | 5M |
| 50,000 | 10M |
| 100,000 | 20M |

Two modes:

1. **Functional mode:** genuinely encode a smaller corpus and measure quality.
2. **Storage mode:** generate schema-valid vectors and payload sizes to measure memory, candidate search and field cost.

Storage mode does not establish semantic quality at 20M tokens.

Measure:

- compile time;
- embedding bytes;
- payload bytes;
- candidate-search latency;
- field latency by active \(M\);
- peak memory;
- decoder latency;
- quality versus candidate budget.

Pass:

- 100K 384-dimensional float32 vectors and metadata remain below the 12 GB hard ceiling;
- field evaluation cost is approximately determined by active \(M\);
- fixed \(M\) retains at least 95% of full-candidate quality on the selected workload.

### P1-E12 — End-to-end demonstration

Starting from raw documents:

1. compile corpus;
2. encode an unseen query;
3. activate candidates;
4. construct field;
5. optimize state;
6. resolve evidence;
7. decode;
8. emit answer, citations and trace.

Pass:

- command completes without manual intervention;
- every answer citation resolves to exact source text;
- repeated run is deterministic under the same seed;
- the trace shows initial and final evidence;
- the result declares limitations and unresolved conflicts.

## 10. Metrics

### Semantic topology

- Recall@k;
- MRR;
- nDCG@k;
- cluster purity and silhouette;
- hard-negative rejection;
- embedding throughput.

### Field and optimizer

- energy decrease;
- gradient error;
- convergence rate;
- state drift from query;
- basin or attractor agreement;
- bad-attractor rate;
- field evaluations;
- optimizer steps and latency.

### Evidence

- evidence precision and recall;
- multi-aspect coverage;
- redundancy;
- contradiction-pair coverage;
- provenance completeness.

### Decoder

- citation precision and recall;
- unsupported statement rate;
- unresolved-case accuracy;
- leakage accuracy under corrupted evidence.

### System

- compile time;
- peak resident memory;
- index and payload size;
- cold and warm request latency;
- active candidates;
- tokens encoded;
- tokens passed to optional decoder.

## 11. Presets and resource budgets

### Smoke

- 100 concepts;
- 1,000 chunks;
- 20 queries;
- one seed;
- explicit field only;
- maximum 16 optimizer steps;
- target under 60 seconds after embeddings are cached.

### Standard

- 1,000 concepts;
- 10,000–25,000 chunks;
- at least 500 queries;
- five seeds;
- explicit field plus required baselines;
- target under 20 minutes per seed after embeddings are cached;
- peak memory target below 8 GB.

### Extended

- up to 100,000 chunks;
- optional SciFact;
- optional distilled field;
- optional local language decoder;
- overnight execution allowed;
- hard peak-memory ceiling 12 GB.

Any result must name its preset.

## 12. Tech stack

Compatibility ranges for the implementation plan:

- Python `>=3.11,<3.13`;
- NumPy `>=2,<3`;
- SciPy `>=1.13,<2`;
- PyTorch `>=2.3,<3`;
- sentence-transformers `>=3,<6`;
- scikit-learn `>=1.5,<2`;
- Pydantic `>=2,<3`;
- pandas `>=2,<3`;
- Matplotlib `>=3.8,<4`;
- pytest `>=8,<9`.

Exact versions and the semantic-model revision are pinned after the implementation compatibility smoke test. Core retrieval uses NumPy or scikit-learn so Phase 1 does not depend on FAISS support on macOS.

## 13. Commands

Proposed commands; they become executable acceptance criteria during implementation:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m pytest
python -m pytest tests/unit
python -m pytest tests/integration

python -m ltm_phase1.cli compile \
  --config configs/phase1/smoke.yaml

python -m ltm_phase1.cli run \
  --experiment P1-E6 \
  --preset smoke \
  --seed 0

python -m ltm_phase1.cli suite \
  --suite phase1-core \
  --preset standard \
  --seeds 0,1,2,3,4

python -m ltm_phase1.cli report \
  --input results/phase1 \
  --output results/phase1/report
```

No command downloads a model or dataset implicitly. Downloads require a separate explicit preparation command and cached artifact manifest.

## 14. Project structure

```text
src/ltm_phase1/
  cli.py
  config.py
  schemas.py
  corpus/
    chunking.py
    manifests.py
    payload_store.py
  topology/
    base.py
    semantic.py
    index.py
  field/
    base.py
    explicit.py
    distilled.py
  optimizer/
    projected_gradient.py
    mean_shift.py
    result.py
  decoder/
    base.py
    deterministic.py
    local_language.py
  verify/
    citations.py
    grounding.py
  baselines/
    lexical.py
    dense.py
    rocchio.py
    diversity.py
  data/
    synthetic.py
    scifact.py
  experiments/
    registry.py
    runner.py
    metrics.py
    report.py
configs/phase1/
tests/
  unit/
  integration/
  regression/
results/phase1/
docs/phases/
```

Generated results and downloaded checkpoints must not be committed unless explicitly approved.

## 15. Code style

Use typed, side-effect-light components with explicit immutable configuration.

```python
@dataclass(frozen=True)
class OptimizationBudget:
    max_field_evaluations: int
    min_energy_delta: float
    min_state_delta: float


def optimize_query(
    *,
    query: LatentState,
    context: FieldContext,
    field: EnergyField,
    optimizer: LatentOptimizer,
    budget: OptimizationBudget,
) -> OptimizationResult:
    """Return a bounded, fully traced latent optimization result."""
    return optimizer.optimize(
        initial=query,
        query=query,
        field=field,
        context=context,
        budget=budget,
    )
```

Conventions:

- `snake_case` functions and files;
- `PascalCase` types;
- type annotations on public functions;
- immutable configs and result objects where practical;
- no global model loading;
- no hidden network calls;
- no unrecorded fallback behavior;
- numerical tolerances defined in config, not scattered literals.

## 16. Testing strategy

### Unit tests

- chunk boundaries and hashes;
- vector normalization;
- cosine retrieval;
- energy values on hand-computed fixtures;
- analytic/autograd/finite-difference gradient agreement;
- spherical projection;
- optimizer stopping reasons;
- evidence resolution;
- citation verification.

### Property tests

- document-order permutation does not change results;
- duplicate chunks change density only when duplicate weighting is enabled;
- increasing anchor weight cannot increase allowed query drift in controlled fixtures;
- irrelevant candidates with zero weight do not change energy;
- final evidence always exists in the compiled manifest;
- empty evidence cannot produce a factual deterministic answer;
- identical config and seed reproduce the same trace within device tolerance.

### Integration tests

- raw corpus to decoded output;
- CPU and MPS agreement within tolerance;
- explicit field with every optimizer;
- corrupted-evidence decoder behavior;
- result-report generation.

### Regression tests

Keep tiny golden corpora and expected metric intervals. Do not store exact floating-point trajectories across hardware; compare energies, rankings and final evidence within declared tolerance.

### Coverage

- 90% line coverage target for schemas, energy functions, optimizer stopping and citation verifier;
- no global coverage target for plotting or optional model adapters;
- a passing coverage number cannot replace scientific acceptance tests.

## 17. Boundaries

### Always

- preserve exact source text and provenance;
- pin corpus, model and configuration identities in every result;
- run direct retrieval and classical refinement baselines;
- separate validation and test queries;
- record failures and non-convergence;
- enforce optimizer budgets;
- verify citations before accepting decoder output;
- call semantic navigation “semantic navigation,” not reasoning.

### Ask first

- add a paid or hosted model;
- change the frozen embedding engine after seeing test results;
- add a vector database or large dependency;
- raise the 12 GB memory ceiling;
- use external private data;
- make the local language decoder mandatory;
- change a success threshold after results exist.

### Never

- train on test queries;
- use gold evidence or stance labels during inference;
- silently remove failed seeds;
- compare only with weak retrieval baselines;
- report storage simulation as 20M-token semantic performance;
- let the decoder retrieve additional evidence;
- claim that low energy means truth;
- claim that Phase 1 validates native reasoning topology.

## 18. Success criteria

### Mechanical POC

Achieved when:

- P1-E0 through P1-E5 pass;
- the raw-document-to-decoded-output flow runs locally;
- every result is reproducible and grounded;
- all four component interfaces exist independently.

Estimated meaning: the complete architecture can be assembled around a known topology.

### Strong Phase 1 POC

Achieved when:

- mechanical POC passes;
- P1-E6 shows a statistically supported multi-evidence gain over the strongest mandatory non-field baseline;
- P1-E7 and P1-E9 pass;
- the full P1-E12 demo succeeds;
- latency and memory remain inside the standard budget.

Estimated meaning: latent field optimization provides a real semantic-navigation benefit, not just a more complicated nearest-neighbor lookup.

### Extended Phase 1 POC

Achieved when:

- strong Phase 1 passes;
- P1-E10 field distillation passes;
- P1-E11 demonstrates bounded active-field work in storage simulation;
- optional local language decoding preserves grounding.

Estimated meaning: the field has a plausible compression and sparse-scaling path worth carrying into the native reasoning-topology phase.

## 19. Failure interpretations

| Result | Interpretation |
| --- | --- |
| Embedding sanity fails | Replace or adapt the surrogate encoder; says little about the rest of LTM. |
| Field gradients fail | Implementation or mathematical formulation is wrong. Stop. |
| Optimizer converges but retrieval worsens | Landscape or anchor is unsuitable. |
| Direct kNN dominates every task | Phase 1 reduces to ordinary semantic retrieval. |
| Rocchio or mean shift dominates | The mechanism works but is classical query refinement, not yet an LTM advantage. |
| Multi-evidence improves but contradictions merge | Add explicit structure in Phase 2; semantic topology is insufficient. |
| Explicit field works but distillation fails | Keep explicit/modular field or redesign compression. |
| Decoder succeeds with corrupted evidence | Dataset leakage or decoder reasoning invalidates the result. |
| Fixed candidate budget loses quality as corpus grows | Sparse activation hypothesis is unsupported for this workload. |

Negative results remain valuable because the component boundaries identify what failed.

## 20. Promotion to Phase 2

Proceed to native reasoning topology when:

1. the mechanical POC passes;
2. the strong POC either passes or produces a clearly understood classical baseline result;
3. field and optimizer interfaces are stable;
4. decoder grounding and leakage tests pass;
5. the final report states exactly which behavior depends on semantic geometry;
6. no unresolved numerical correctness issue remains.

Phase 2 then replaces:

```text
Frozen semantic encoder + semantic corpus topology
```

with:

```text
Reasoning-topology encoder + typed instantiated topology
```

The generic `EnergyField`, `LatentOptimizer`, trace, evidence and decoder contracts should remain. Any required interface break must be documented as evidence that Phase 1 did not fully isolate the topology dependency.

## 21. Open questions for review

These do not block specification review but must be resolved in the implementation plan:

1. Freeze `all-MiniLM-L6-v2` as the sole core encoder, or use a different compact local model?
2. Is the optional local language decoder part of the Phase 1 completion definition or only a demonstration?
3. Should SciFact be mandatory for the strong POC or remain an external validation?
4. What maximum wall-clock duration is acceptable for the extended 100K-chunk run?
5. Should neural field distillation be required before Phase 2, or may explicit fields carry forward?
