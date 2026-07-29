# Spec: Phase 1 Minimal Semantic-Field POC

**Status:** Binding specification for review; implementation has not started.  
**Primary target:** 32 GB Apple Silicon MacBook Pro, M5 Pro.  
**Portability target:** CPU-only operation on ordinary 8 GB or larger machines for the smoke preset.  
**Last updated:** 2026-07-29

The ordered build sequence and pinned model revisions are defined in the
[Phase 1 implementation](implementation.md).

## 1. Exact objective

Build the smallest complete Latent Topology Model proof of concept that lets a user:

1. create a local workspace;
2. add their own textual data;
3. embed that data with a frozen semantic embedding engine;
4. use those embeddings to define a latent dynamic field;
5. enter a natural-language prompt as the initial latent state;
6. optimize that state through the field;
7. resolve the optimized final state back to exact user data;
8. decode the final state and its evidence into a natural-language answer.

All four components must exist independently:

1. semantic embedding topology;
2. latent dynamic field;
3. latent optimizer;
4. decoder.

The POC is local, minimal, inspectable and falsifiable. It is not a web application, production service or general reasoning model.

## 2. Binding end-user flow

```text
User files
    ↓
Load and normalize text
    ↓
Deterministic chunking
    ↓
Frozen compact embedding engine
    ↓
Normalized semantic states + exact payload store
    ↓
Corpus-induced latent dynamic field

User prompt
    ↓
Frozen prompt embedding = initial state x₀
    ↓
Activate a small relevant part of the field
    ↓
Bounded latent optimization
    ↓
Final latent state x*
    ↓
Resolve x* to exact source chunks
    ↓
Small grounded decoder
    ↓
Natural-language answer + citations + optimization trace
```

The final state is not converted directly from floating-point values into words. Decoding means:

```text
final vector
    → nearest exact payloads
    → bounded evidence bundle
    → compact language decoder
    → answer
```

This separation preserves provenance and lets the decoder remain small.

## 3. The Phase 1 hypothesis

### Core hypothesis

> User data embedded into a semantic latent space can induce a useful query-conditioned field, and a prompt state can be optimized through that field into a final state from which a grounded natural-language answer can be decoded.

### Mechanical hypothesis

The entire four-component flow can run correctly and reproducibly on local consumer hardware.

### Value hypothesis

The optimized final state retrieves a more coherent or complete evidence set than the unoptimized prompt embedding on at least one declared semantic-navigation task.

### Replacement hypothesis

If the field, optimizer and decoder work around a semantic topology, the semantic backend can later be replaced by a native reasoning topology through the same component boundaries.

Phase 1 does not prove the replacement will succeed. It proves that a replaceable boundary exists and establishes the behavior the reasoning topology must improve.

## 4. What “any data” means in Phase 1

Phase 1 supports arbitrary **user-supplied textual or text-convertible records**.

### Built-in formats

- `.txt`;
- `.md`;
- `.json`;
- `.jsonl`;
- `.csv`;
- source-code files treated as UTF-8 text;
- directories containing supported files.

### Loading rules

- UTF-8 is the canonical encoding;
- invalid files produce explicit errors;
- JSON objects are flattened into stable `key: value` text records;
- CSV rows become stable field-labelled text records;
- Markdown remains text; formatting markers may be retained;
- source files retain relative path and line-range metadata;
- hidden files are skipped by default;
- symbolic links are not followed by default;
- identical content hashes are deduplicated.

### Not included in the minimal core

- image OCR;
- audio transcription;
- video;
- proprietary binary formats;
- database connectors;
- web crawling;
- live cloud drives;
- multimodal embeddings.

Those formats can be supported later by converting them into the canonical text-record contract. They are ingestion adapters, not changes to the four-component architecture.

## 5. Binding constraints

### Minimality

- one embedding engine;
- one explicit field formulation;
- one primary optimizer;
- one compact language decoder plus deterministic fallback;
- one local payload format;
- one command-line interface;
- no server;
- no database;
- no vector database;
- no distributed execution;
- no paid API;
- no model training in the core POC;
- no neural field distillation in the core POC.

### Hardware

- no CUDA requirement;
- CPU operation must work;
- Apple MPS may accelerate embedding and decoding;
- smoke preset peak memory target below 4 GB;
- standard preset peak memory target below 8 GB;
- hard target-machine ceiling below 16 GB;
- the 32 GB M5 Pro must have substantial headroom.

### Corpus

- smoke: up to 1,000 chunks;
- standard: up to 10,000 chunks;
- extended diagnostic: up to 50,000 chunks;
- default chunk length: 128 embedding-tokenizer wordpieces;
- default overlap: 24 wordpieces;
- exact source payload is stored outside model weights.

The standard POC is not a 10–20M-token scaling demonstration. Scaling is tested only after the mechanism earns it.

### Inference

- default active candidates: 128;
- default optimization budget: eight steps;
- hard optimization budget: 16 steps;
- default decoded evidence: four chunks;
- decoder input budget: 512 tokens or the selected decoder’s lower hard limit;
- decoder output budget: 128 tokens;
- every budget is explicit in the result.

## 6. Research basis

The semantic surrogate is grounded in compact sentence-embedding research:

- [Sentence-BERT](https://aclanthology.org/D19-1410/) demonstrates efficient semantic sentence vectors that support cosine retrieval.
- [SimCSE](https://aclanthology.org/2021.emnlp-main.552/) studies alignment, uniformity and anisotropy in contrastive sentence embeddings.
- [MTEB](https://aclanthology.org/2023.eacl-main.148/) shows why embedding behavior must be evaluated across tasks rather than assumed from one score.

The field and optimizer are grounded in density-mode and energy-based inference:

- [Mean Shift](https://doi.org/10.1109/34.1000236) relates iterative updates to modes of a kernel density estimate.
- [Directional Mean Shift](https://www.jmlr.org/papers/v22/20-1194.html) studies mode seeking on the unit hypersphere used by normalized embeddings.
- [A Tutorial on Energy-Based Learning](https://yann.lecun.org/exdb/publis/pdf/lecun-06.pdf) defines inference through minimization of a scalar compatibility energy.
- [Universal Hopfield Networks](https://proceedings.mlr.press/v162/millidge22a.html) gives a general similarity–separation–projection view of associative memory.

The payload and decoder split follows the distinction between parametric generation and explicit non-parametric memory in [Retrieval-Augmented Generation](https://papers.neurips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html).

These citations support the ingredients. They do not establish that the complete Phase 1 flow is better than ordinary retrieval.

## 7. Component 1 — Semantic embedding topology

### Responsibility

Turn user data and prompts into a shared compact latent space.

### Selected default

Use one frozen compact Sentence-Transformers model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Expected properties:

- approximately 22 million parameters;
- 384-dimensional output;
- small enough for CPU and Apple Silicon;
- suitable for sentence and short-passage similarity;
- no fine-tuning required.

The exact model revision is pinned before implementation. Changing the model after evaluation requires a documented ablation.

### Why this is minimal enough

The embedding model is much smaller than a language model and is loaded once. For 10,000 chunks:

\[
10{,}000\times384\times4
\approx15.4\text{ MB}
\]

of raw float32 vector storage.

### Corpus artifact

```json
{
  "schema_version": "1",
  "workspace_id": "research-notes",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_revision": "pinned-revision",
  "dimension": 384,
  "chunk_count": 842,
  "vectors_file": "vectors.npy",
  "payload_file": "chunks.jsonl",
  "manifest_hash": "sha256:..."
}
```

### Chunk record

```json
{
  "chunk_id": "paper.md::0007",
  "source_path": "paper.md",
  "source_span": {
    "start": 1450,
    "end": 2381
  },
  "text": "Exact source text...",
  "content_hash": "sha256:...",
  "token_count": 191
}
```

### Embedding rules

For chunk \(c_i\):

\[
z_i
=
\frac{f(c_i)}{\lVert f(c_i)\rVert_2}.
\]

For prompt \(p\):

\[
q
=
\frac{f(p)}{\lVert f(p)\rVert_2}.
\]

The initial latent state is:

\[
x_0=q.
\]

### Component contract

```python
class SemanticTopology:
    def ingest(self, records: Sequence[TextRecord]) -> CorpusArtifact: ...
    def encode_prompt(self, prompt: str) -> LatentState: ...
    def nearest(self, state: LatentState, limit: int) -> EvidenceBundle: ...
```

## 8. Component 2 — Latent dynamic field

### Responsibility

Represent the influence of the user’s embedded data as a query-conditioned scalar energy.

The field is not stored as a dense grid. It is an energy function induced by the corpus embeddings and evaluated only where the optimizer visits.

### Activation

Before optimization:

1. compute cosine similarity between \(q\) and all corpus embeddings;
2. take the top 128 candidates;
3. freeze that candidate set for the request;
4. build the request field from those candidates.

Exact cosine search is sufficient for at most 50,000 chunks and removes the need for a vector database.

### Reference energy

For normalized state \(x\), query \(q\), and active vectors \(z_i\):

\[
E(x\mid q)
=
-\log
\sum_{i\in C(q)}
a_i(q)
\exp\left(\frac{x^\top z_i}{\tau_f}\right)
+
\lambda_q(1-x^\top q).
\]

Query relevance weights:

\[
a_i(q)
=
\frac{
\exp(q^\top z_i/\tau_q)
}{
\sum_{j\in C(q)}
\exp(q^\top z_j/\tau_q)
}.
\]

Minimal defaults:

```yaml
active_candidates: 128
query_temperature: 0.05
field_temperature: 0.10
query_anchor: 1.0
```

The implementation uses stable log-sum-exp operations.

### Why the query anchor is mandatory

Without \(\lambda_q(1-x^\top q)\), the state may move toward the densest corpus topic even when it is unrelated to the user’s exact intent. The anchor makes the field prompt-conditioned rather than a global clustering operation.

### Component contract

```python
class LatentDynamicField:
    def energy(self, state: LatentState) -> float: ...
    def gradient(self, state: LatentState) -> LatentVector: ...
```

### No learned field yet

Phase 1 does not train a neural approximation of the field. The analytic field is:

- smaller;
- easier to inspect;
- reproducible;
- directly tied to the user’s data;
- easier to falsify.

Field distillation is deferred until the explicit mechanism shows value.

## 9. Component 3 — Latent optimization

### Responsibility

Move the prompt’s initial state \(x_0\) through the user-data field to a final state \(x^\*\).

### Primary optimizer

Projected gradient descent:

\[
\tilde{x}_{t+1}
=
x_t-\eta\nabla_xE(x_t\mid q),
\]

\[
x_{t+1}
=
\frac{\tilde{x}_{t+1}}
{\lVert\tilde{x}_{t+1}\rVert_2}.
\]

Minimal defaults:

```yaml
optimizer: projected_gradient
learning_rate: 0.05
max_steps: 8
minimum_energy_change: 0.0001
minimum_state_change: 0.0001
patience: 2
```

### Stopping

Stop when the first condition is met:

- eight default steps completed;
- energy changes less than tolerance for two consecutive steps;
- state changes less than tolerance for two consecutive steps;
- gradient or state becomes non-finite;
- hard limit of 16 field evaluations is reached.

### Trace record

```json
{
  "step": 4,
  "energy": -7.241,
  "gradient_norm": 0.083,
  "query_cosine": 0.947,
  "state_delta": 0.004,
  "nearest_chunk_ids": [
    "notes.md::0012",
    "paper.md::0007"
  ]
}
```

### Required controls

- `steps=0`: direct retrieval from \(x_0\);
- projected gradient descent;
- directional mean-shift baseline.

No Adam, L-BFGS, Langevin dynamics, particles or beam search in the minimal POC.

### Component contract

```python
class LatentOptimizer:
    def optimize(
        self,
        *,
        initial_state: LatentState,
        field: LatentDynamicField,
        budget: OptimizationBudget,
    ) -> OptimizationResult: ...
```

## 10. Component 4 — Decoder

### Responsibility

Decode the optimized final state into grounded natural language.

### Decoding pipeline

```text
x*
    ↓ exact nearest-neighbour resolution
top four user-data chunks
    ↓ evidence formatting and truncation
compact text decoder
    ↓
answer with source references
```

### Selected compact decoder

The default language decoder candidate is:

```text
google/flan-t5-small
```

Expected properties:

- approximately 80 million parameters;
- small enough for CPU inference;
- much smaller than general-purpose chat models;
- capable of instruction-conditioned text generation;
- suitable for a short bounded evidence context.

The exact revision is pinned in the implementation plan. If its answer quality is unusable, replacement requires a documented decoder-only ablation.

### Decoder input

```text
Question:
{user_prompt}

Use only the evidence below.
If it is insufficient, say "The available data is insufficient."
Cite sources using [1], [2], and so on.

Evidence:
[1] {source_path}: {excerpt}
[2] {source_path}: {excerpt}
[3] {source_path}: {excerpt}
[4] {source_path}: {excerpt}
```

### Decoder output

```json
{
  "answer": "The user data indicates ... [1] ... [2].",
  "sources": [
    {
      "citation": "[1]",
      "chunk_id": "notes.md::0012"
    }
  ],
  "decoder": "google/flan-t5-small",
  "used_fallback": false
}
```

### Deterministic fallback

If the decoder:

- fails;
- emits no valid citation;
- exceeds its budget;
- produces invalid output;

the system returns:

```text
The optimized state selected the following relevant source passages:

[1] ...
[2] ...

A supported synthesized answer could not be produced.
```

This fallback still completes the four-component flow and prevents a language-model failure from hiding field behavior.

### Decoder constraints

- receives only the prompt and final-state evidence;
- cannot search the corpus;
- cannot see benchmark labels;
- cannot see expected answers;
- cannot change the final latent state;
- maximum four evidence chunks;
- maximum 512 input tokens unless the pinned model requires less;
- maximum 128 generated tokens;
- every citation must resolve.

### Component contract

```python
class Decoder:
    def decode(
        self,
        *,
        prompt: str,
        final_state: LatentState,
        evidence: EvidenceBundle,
    ) -> DecodedAnswer: ...
```

## 11. Minimal workspace

```text
my-workspace/
  workspace.json
  corpus/
    manifest.json
    chunks.jsonl
    vectors.npy
  queries/
    runs.jsonl
```

No SQLite database is required. Files are append-only or atomically replaced.

### Workspace configuration

```json
{
  "schema_version": "1",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "decoder_model": "google/flan-t5-small",
  "chunk_tokens": 128,
  "chunk_overlap": 24,
  "active_candidates": 128,
  "optimization_steps": 8,
  "evidence_limit": 4
}
```

## 12. Minimal user commands

Proposed executable contract:

```bash
python -m ltm_poc init ./my-workspace

python -m ltm_poc ingest \
  ./my-workspace \
  ./my-data

python -m ltm_poc ask \
  ./my-workspace \
  "What does my data say about the central hypothesis?"

python -m ltm_poc ask \
  ./my-workspace \
  "Find the most relevant connected evidence." \
  --show-trace

python -m ltm_poc evaluate \
  --preset smoke
```

### `init`

- creates directories;
- writes default configuration;
- records model names;
- does not download models silently.

### `ingest`

- recursively loads supported files;
- reports unsupported files;
- chunks records;
- embeds new or changed chunks;
- stores normalized vectors and exact payloads;
- writes a manifest;
- prints document, chunk, token, time and memory counts.

### `ask`

- encodes the prompt;
- records initial nearest evidence;
- activates the field;
- optimizes the prompt state;
- records final nearest evidence;
- decodes the final state;
- prints answer, sources and optional trace.

### `evaluate`

- runs the frozen test corpus;
- compares zero-step retrieval, gradient optimization and mean shift;
- produces a JSON and Markdown report;
- never changes success thresholds.

## 13. Project structure

```text
src/ltm_poc/
  __main__.py
  cli.py
  config.py
  schemas.py
  ingest.py
  chunk.py
  embed.py
  store.py
  field.py
  optimize.py
  decode.py
  evaluate.py
tests/
  fixtures/
  test_ingest.py
  test_embed.py
  test_field.py
  test_optimize.py
  test_decode.py
  test_end_to_end.py
configs/
  smoke.json
  standard.json
docs/phases/
```

The core implementation stays small enough to understand without a framework.

## 14. Tech stack

Minimal compatibility ranges:

- Python `>=3.11,<3.13`;
- NumPy `>=2,<3`;
- PyTorch `>=2.3,<3`;
- Transformers `>=4.40,<6`;
- sentence-transformers `>=3,<6`;
- Pydantic `>=2,<3`;
- pytest `>=8,<9`.

No SciPy, pandas, FAISS, vector database, web framework or experiment server is required for the core.

Exact working versions are pinned after a clean compatibility installation on the target Mac.

## 15. Code style

```python
def answer_prompt(
    *,
    workspace: Workspace,
    prompt: str,
) -> QueryResult:
    query = workspace.topology.encode_prompt(prompt)
    initial_evidence = workspace.topology.nearest(query, limit=4)
    field = workspace.build_field(query, active_candidates=128)
    optimization = workspace.optimizer.optimize(
        initial_state=query,
        field=field,
        budget=OptimizationBudget(max_steps=8),
    )
    final_evidence = workspace.topology.nearest(
        optimization.final_state,
        limit=4,
    )
    answer = workspace.decoder.decode(
        prompt=prompt,
        final_state=optimization.final_state,
        evidence=final_evidence,
    )
    return QueryResult(
        initial_evidence=initial_evidence,
        optimization=optimization,
        final_evidence=final_evidence,
        answer=answer,
    )
```

Rules:

- typed public functions;
- immutable configurations;
- explicit inputs and outputs;
- no global model objects;
- no hidden network access;
- no silent fallback;
- no premature abstraction beyond the four component boundaries;
- numerical constants live in configuration.

## 16. Minimal experiment suite

### P1-M0 — Data ingestion

Inputs:

- one text file;
- one Markdown file;
- one JSON file;
- one CSV file;
- one small source-code directory.

Pass:

- every supported record is represented;
- source path and span survive;
- duplicates are removed;
- re-ingestion without changes does not recompute embeddings;
- unsupported files are reported.

### P1-M1 — Field mathematics

For fixed synthetic vectors:

- compare autograd with finite-difference gradients;
- verify finite energy;
- verify normalized states;
- verify stable log-sum-exp;
- test empty corpus and empty activation errors.

Pass:

- median relative gradient error below \(10^{-4}\);
- no non-finite output for valid input;
- malformed input fails clearly.

### P1-M2 — Optimization

For controlled semantic clusters:

- start at \(x_0=q\);
- run zero-step control;
- run eight projected-gradient steps;
- record energy and state;
- compare with directional mean shift.

Pass:

- at least 95% of valid runs lower energy;
- all runs terminate within 16 evaluations;
- repeated CPU runs reproduce the same final evidence;
- MPS and CPU evidence ranking agree on at least 99% of smoke queries.

### P1-M3 — Semantic value test

Dataset:

- 500–2,000 generated chunks;
- 50 concepts;
- paraphrases;
- lexical distractors;
- rare relevant clusters;
- multi-evidence queries;
- held-out prompt wording.

Compare:

- direct cosine retrieval from \(x_0\);
- directional mean shift;
- optimized final state \(x^\*\).

Metrics:

- Recall@4;
- evidence precision;
- concept coverage;
- change in selected evidence;
- latency.

Strong pass:

- optimized state improves multi-evidence concept coverage by at least five absolute percentage points over direct retrieval;
- it does not lose more than five points of evidence precision;
- it is not dominated by directional mean shift on both quality and latency.

Mechanical-only result:

- the flow works but optimized evidence does not improve.

### P1-M4 — Decoder dependency

Run the decoder with:

- final-state evidence;
- initial-state evidence;
- shuffled irrelevant evidence;
- empty evidence.

Pass:

- all citations resolve;
- irrelevant or empty evidence yields an insufficient-data response or deterministic fallback;
- changing evidence changes the answer;
- the decoder cannot access chunks outside its input.

### P1-M5 — End-to-end user flow

Use a previously unseen local directory.

Pass:

- `init`, `ingest`, and `ask` complete without source changes;
- answer is natural language;
- answer includes valid sources or explicit insufficiency;
- output shows initial and final energy;
- output shows whether evidence changed;
- all four components can be individually disabled or inspected for testing.

### P1-M6 — Hardware budget

Measure on the 32 GB target Mac:

- fresh model load;
- ingestion of 1,000 and 10,000 chunks;
- warm query latency;
- peak memory;
- vector and payload storage.

Pass:

- smoke peak memory below 4 GB;
- standard peak memory below 8 GB;
- warm standard query target below five seconds;
- no process requires GPU acceleration;
- no query exceeds 16 field evaluations.

Latency is a target, not permission to weaken correctness.

## 17. What determines whether Phase 1 works

### Result A — Strong success

All of the following:

- complete user flow works;
- energy and gradients are numerically correct;
- optimizer is stable;
- final evidence measurably improves on the declared semantic task;
- decoder depends on final-state evidence;
- hardware budgets pass.

Conclusion:

> The four-component architecture works with a semantic topology, and field-based latent optimization provides useful behavior worth testing with a native reasoning topology.

### Result B — Mechanical success only

The flow works, but direct cosine retrieval or mean shift matches or beats the optimizer.

Conclusion:

> The architecture can be assembled, but the proposed latent optimization has not yet demonstrated an advantage. Do not assume that replacing embeddings with a reasoning topology will fix it; first inspect the field objective.

### Result C — Decoder-only success

Natural-language output looks useful, but it does not depend on the optimized final state.

Conclusion:

> The decoder is doing the useful work. The LTM hypothesis is not supported.

### Result D — Mechanical failure

The field is numerically unstable, optimization fails to converge, provenance is lost or the flow cannot run within budget.

Conclusion:

> Phase 1 fails. Do not build the reasoning topology yet.

## 18. Decision about building the reasoning topology

Proceed to native reasoning topology only if:

1. Result A is achieved, or a narrowly documented variant shows the same evidence;
2. optimizer behavior is reproducible;
3. decoder leakage tests pass;
4. direct retrieval is not sufficient for the tested behavior;
5. failures involving direction, contradiction or constraints can specifically be attributed to semantic geometry.

Do not proceed merely because:

- the answer sounds fluent;
- energy decreases;
- the final state is different;
- the system retrieves relevant passages;
- the architecture is theoretically interesting.

Those facts can all occur without reasoning.

## 19. Deferred until after Phase 1

The following are explicitly excluded from the minimal implementation:

- neural field distillation;
- native reasoning topology;
- LLM-assisted topology extraction;
- multiple embedding engines;
- learned routing;
- ANN/vector databases;
- 10–20M-token functional evaluation;
- SSD streaming;
- multi-domain topology configuration;
- GUI or web service;
- user authentication;
- cloud deployment;
- paid frontier-model decoder;
- multimodal ingestion;
- model training.

The broader experiments remain documented in the
[Phase 1 Experimental Appendix](experimental-appendix.md).

## 20. Testing strategy

### Unit

- loaders;
- chunk boundaries;
- hashes and deduplication;
- vector normalization;
- exact retrieval;
- energy and gradients;
- projection;
- optimizer stopping;
- evidence truncation;
- citation resolution.

### Integration

- directory ingestion;
- persisted workspace reload;
- prompt-to-final-state flow;
- final-state-to-decoder flow;
- CPU/MPS agreement;
- decoder fallback.

### Regression

- fixed tiny corpus;
- fixed prompts;
- initial evidence IDs;
- final evidence IDs;
- metric intervals;
- schema compatibility.

### Scientific

- frozen success thresholds;
- held-out queries;
- direct-retrieval and mean-shift controls;
- report every seed;
- no best-seed selection;
- explicit separation of mechanical and strong success.

## 21. Boundaries

### Always

- operate locally after explicit model download;
- preserve exact payloads and provenance;
- show initial and final evidence during evaluation;
- record every optimization step;
- enforce budgets;
- compare with zero-step retrieval;
- provide deterministic decoder fallback;
- call the result semantic navigation, not reasoning.

### Ask first

- change either frozen model;
- add a dependency;
- support a new file extractor;
- increase corpus or memory limits;
- add another optimizer;
- change the energy function;
- alter a success threshold after experiments begin.

### Never

- use gold evidence during inference;
- hide failed queries;
- let the decoder search the corpus;
- infer truth from embedding similarity;
- claim that energy decrease means correctness;
- report natural-language fluency as proof of latent optimization;
- claim Phase 1 validates the future reasoning topology.

## 22. Implementation acceptance checklist

- [ ] User can initialize a workspace.
- [ ] User can ingest a directory of supported data.
- [ ] Corpus vectors and payloads persist locally.
- [ ] User can submit an arbitrary text prompt.
- [ ] Prompt becomes \(x_0\).
- [ ] User-data field is instantiated.
- [ ] Optimizer produces \(x^\*\) within budget.
- [ ] Initial and final evidence are recorded.
- [ ] Final state is decoded into natural language.
- [ ] Citations resolve or fallback is used.
- [ ] Direct retrieval and mean shift are evaluated.
- [ ] P1-M0 through P1-M6 produce a report.
- [ ] Peak memory and latency are recorded.
- [ ] Result is classified as A, B, C or D.

## 23. Open question

One choice remains for approval before the implementation plan:

> Should `google/flan-t5-small` be the required natural-language decoder, or should the deterministic grounded decoder be the only required decoder and the language model remain optional?

The recommended choice is to require FLAN-T5-small with deterministic fallback. That implements the intended natural-language flow while keeping the system small and preserving a failure-safe path.
