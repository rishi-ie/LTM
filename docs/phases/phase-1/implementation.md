# Phase 1 Minimal Semantic-Field POC — Implementation

**Status:** completed. The original implementation checklist has been
consolidated here because every listed build milestone is now represented by
code, tests, or canonical results.

Completed milestones:

- package, configuration, device inspection, and pinned local models;
- deterministic ingestion, chunking, embedding, and corpus storage;
- exact retrieval, semantic field construction, and bounded optimization;
- grounded decoding, fallback behavior, and query-run records;
- `init`, `ingest`, `ask`, `evaluate`, and model-management commands;
- unit, integration, integrity, offline-loading, and resource checks;
- fixed benchmark execution and result reporting.

The measured outcome is summarized in [results.md](results.md). Result B
describes the semantic optimizer comparison; the complete surrogate pipeline
itself passed mechanically.

**Plan status:** Ready for human review.  
**Source specification:** [Phase 1 Minimal Semantic-Field POC](specification.md)  
**Target:** 32 GB Apple Silicon M5 Pro MacBook Pro; CPU-only smoke support on 8 GB or larger machines.  
**Plan date:** 2026-07-29  
**Implementation status:** Not started.

## 1. Purpose of this document

This document converts the approved Phase 1 specification into an implementation sequence. It fixes model revisions, dependencies, file formats, numerical algorithms, device behavior, stage order and verification checkpoints.

An implementing model must not make new architectural decisions. If a necessary decision is missing, it must stop, document the ambiguity and request review.

## 2. Final implementation decisions

| Decision | Selected value |
| --- | --- |
| Interface | Local Python command-line application |
| Python | CPython 3.11 preferred; 3.12 supported |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding revision | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Embedding dimension | 384 |
| Embedding dtype | float32 |
| Chunk size | 128 embedding-tokenizer wordpieces |
| Chunk overlap | 24 wordpieces |
| Vector search | Exact normalized matrix–vector cosine |
| Vector storage | NumPy `.npy` |
| Payload storage | UTF-8 JSON Lines |
| Active field candidates | 128 |
| Field arithmetic | CPU float64 |
| Field | Explicit query-weighted directional log-density plus query anchor |
| Optimizer | Tangent-projected gradient descent with spherical retraction |
| Default update steps | 8 |
| Hard field-evaluation budget | 16 |
| Decoder | `google/flan-t5-small` |
| Decoder revision | `0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab` |
| Decoder dtype | float32 |
| Decoder generation | Greedy, deterministic, maximum 128 new tokens |
| Decoder evidence | Maximum 4 chunks, maximum 80 decoder tokens per excerpt |
| Failure-safe output | Deterministic extractive evidence report |
| Runtime network access | Forbidden |
| Model training | None |
| Database/server/UI | None |

## 3. Official model sources

### 3.1 Embedding model

**Repository:** [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)  
**Pinned tree:** [`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41)  
**License:** Apache-2.0  
**Parameters:** 22,713,728 according to the Hugging Face safetensors metadata  
**Weight file:** `model.safetensors`, approximately 90.9 MB  
**Output:** 384-dimensional dense embeddings  
**Published behavior:** sentence and short-paragraph similarity, clustering and semantic search  
**Important limit:** the model card states that inputs beyond 256 wordpieces are truncated; it was fine-tuned with sequence length 128.

The implementation therefore chunks at 128 wordpieces rather than relying on truncation.

Load with:

```python
SentenceTransformer(
    model_name_or_path=str(local_model_path),
    device=device,
    trust_remote_code=False,
    local_files_only=True,
)
```

Encode with:

```python
model.encode(
    texts,
    batch_size=batch_size,
    convert_to_numpy=True,
    normalize_embeddings=True,
    precision="float32",
    show_progress_bar=False,
)
```

The official Sentence-Transformers API documents the `revision`, `local_files_only`, `device`, `precision` and `normalize_embeddings` controls in [`SentenceTransformer`](https://sbert.net/docs/package_reference/sentence_transformer/model.html).

### 3.2 Natural-language decoder

**Repository:** [`google/flan-t5-small`](https://huggingface.co/google/flan-t5-small)  
**Pinned tree:** [`0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab`](https://huggingface.co/google/flan-t5-small/tree/0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab)  
**License:** Apache-2.0  
**Parameters:** 77 million according to the model card  
**Weight file:** `model.safetensors`, approximately 308 MB  
**Architecture:** instruction-tuned T5 encoder–decoder  
**Role:** rewrite a bounded final-state evidence bundle into short natural language.

Load with:

```python
tokenizer = AutoTokenizer.from_pretrained(
    local_model_path,
    local_files_only=True,
    trust_remote_code=False,
)
model = AutoModelForSeq2SeqLM.from_pretrained(
    local_model_path,
    local_files_only=True,
    trust_remote_code=False,
    use_safetensors=True,
    torch_dtype=torch.float32,
)
model.eval()
model.to(device)
```

Generate with:

```python
with torch.inference_mode():
    output_ids = model.generate(
        **tokenized_prompt,
        max_new_tokens=128,
        do_sample=False,
        num_beams=1,
        use_cache=True,
    )
```

The official [FLAN-T5 model card](https://huggingface.co/google/flan-t5-small) documents `AutoTokenizer` and `AutoModelForSeq2SeqLM` loading, the Apache-2.0 license and model limitations. The decoder is not trusted as a factual verifier.

### 3.3 Why these two models

- Combined selected safetensor weights are approximately 399 MB.
- Neither requires CUDA.
- Both have standard PyTorch implementations.
- Both use permissive Apache-2.0 licensing.
- The embedder is small enough for repeated corpus batches.
- The decoder is small enough for bounded CPU generation.
- They separate semantic geometry from language expression.
- Larger models would make failures harder to attribute.

### 3.4 Model acquisition

Models are downloaded only through an explicit command:

```bash
python -m ltm_poc models download --model-dir ./.models
```

Use [`huggingface_hub.snapshot_download`](https://huggingface.co/docs/huggingface_hub/package_reference/file_download), which supports exact revisions plus allow/ignore patterns.

Embedding snapshot:

```python
snapshot_download(
    repo_id="sentence-transformers/all-MiniLM-L6-v2",
    revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    local_dir=model_dir / "all-MiniLM-L6-v2",
    allow_patterns=[
        "*.json",
        "*.txt",
        "*.safetensors",
        "1_Pooling/*",
        "modules.json",
        "README.md",
    ],
    ignore_patterns=[
        "*.bin",
        "*.h5",
        "*.ot",
        "*.msgpack",
        "onnx/*",
        "openvino/*",
    ],
)
```

Decoder snapshot:

```python
snapshot_download(
    repo_id="google/flan-t5-small",
    revision="0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab",
    local_dir=model_dir / "flan-t5-small",
    allow_patterns=[
        "*.json",
        "*.model",
        "*.safetensors",
        "README.md",
    ],
    ignore_patterns=[
        "*.bin",
        "*.h5",
        "*.msgpack",
    ],
)
```

After download:

1. verify required files exist;
2. calculate SHA-256 for every downloaded file;
3. write `.models/model-manifest.json`;
4. run one embedding and one decoder smoke inference;
5. prohibit network access during every other command.

Hugging Face recommends safetensors when available because it avoids pickle-based weight loading and loads safely and efficiently; see the official [model-loading documentation](https://huggingface.co/docs/transformers/en/models).

## 4. Minimal dependency set

### Runtime dependencies

```toml
dependencies = [
  "numpy>=2.0,<3",
  "pydantic>=2.7,<3",
  "torch>=2.3,<3",
  "transformers>=4.40,<5",
  "sentence-transformers>=3,<6",
  "sentencepiece>=0.2,<1",
  "safetensors>=0.4,<1",
  "huggingface-hub>=0.24,<2"
]
```

### Development dependencies

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8,<9",
  "pytest-cov>=5,<7",
  "ruff>=0.5,<1"
]
```

### Standard-library responsibilities

Use the standard library for:

- CLI: `argparse`;
- files: `pathlib`, `tempfile`, `os`;
- serialization: `json`, `csv`;
- hashing: `hashlib`;
- pattern matching: `fnmatch`;
- timing: `time.perf_counter`;
- memory measurement on macOS/Linux: `resource`;
- logging: `logging`;
- immutable records where Pydantic is unnecessary: `dataclasses`.

Do not add:

- Click or Typer;
- pandas;
- SciPy;
- FAISS;
- a vector database;
- a web framework;
- an experiment-tracking service;
- LangChain or LlamaIndex.

### Environment creation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip check
```

After the first compatible installation:

```bash
python -m pip freeze > artifacts/environment/pip-freeze.txt
python -m ltm_poc doctor --json > artifacts/environment/doctor.json
```

Do not commit the virtual environment or model weights.

## 5. Device and numerical policy

### Device selection

CLI option:

```text
--device auto | cpu | mps
```

`auto` selects:

1. `mps` when `torch.backends.mps.is_available()` is true;
2. otherwise `cpu`.

PyTorch documents the Apple Metal device through its official [MPS backend notes](https://docs.pytorch.org/docs/stable/notes/mps.html).

### Component placement

| Component | Device | Dtype |
| --- | --- | --- |
| Embedding model | selected `cpu` or `mps` | float32 |
| Stored embeddings | disk/CPU | float32 |
| Exact cosine search | CPU NumPy | float32 |
| Field | CPU PyTorch | float64 |
| Optimizer | CPU PyTorch | float64 |
| Decoder | selected `cpu` or `mps` | float32 |

The field is deliberately CPU float64 because only 128×384 values are active. This improves numerical testing and makes optimizer behavior independent of accelerator details.

### Determinism

At process start:

```python
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
```

Additional rules:

- embedding and decoder models call `.eval()`;
- decoder uses greedy generation;
- no dropout or sampling;
- vector-search ties sort by descending score, then ascending `chunk_id`;
- CPU is the reference result;
- MPS may differ numerically, but evidence ranking must meet the specified agreement threshold.

## 6. Repository layout after implementation

```text
pyproject.toml
README.md
.gitignore
src/
  ltm_poc/
    __init__.py
    __main__.py
    cli.py
    config.py
    schemas.py
    devices.py
    models.py
    ingest.py
    chunk.py
    embed.py
    store.py
    retrieve.py
    field.py
    optimize.py
    decode.py
    experiments/
      phase_1.py
tests/
  fixtures/
    inputs/
    semantic_cases.json
    tiny_vectors.npy
  test_config.py
  test_ingest.py
  test_chunk.py
  test_embed.py
  test_store.py
  test_retrieve.py
  test_field.py
  test_optimize.py
  test_decode.py
  experiments/
    test_phase_1.py
  test_end_to_end.py
configs/
  smoke.json
  standard.json
artifacts/
  environment/
docs/
  phases/
    phase-1/
      specification.md
      implementation.md
```

Generated and ignored:

```text
.venv/
.models/
.pytest_cache/
.ruff_cache/
results/
tmp/
*.egg-info/
__pycache__/
```

## 7. Canonical schemas

Implement these first in `schemas.py`. Do not replace field names without updating the specification and migration version.

### `WorkspaceConfig`

```python
class WorkspaceConfig(BaseModel):
    schema_version: Literal["1"] = "1"
    embedding_model_path: str
    embedding_model_id: str
    embedding_revision: str
    decoder_model_path: str
    decoder_model_id: str
    decoder_revision: str
    device: Literal["auto", "cpu", "mps"] = "auto"
    chunk_wordpieces: int = 128
    chunk_overlap_wordpieces: int = 24
    embedding_batch_size: int = 32
    active_candidates: int = 128
    evidence_limit: int = 4
    query_temperature: float = 0.05
    field_temperature: float = 0.10
    query_anchor: float = 1.0
    optimizer_learning_rate: float = 0.05
    optimizer_max_steps: int = 8
    optimizer_hard_evaluations: int = 16
    energy_tolerance: float = 1e-4
    state_tolerance: float = 1e-4
    convergence_patience: int = 2
    decoder_excerpt_tokens: int = 80
    decoder_input_tokens: int = 512
    decoder_output_tokens: int = 128
    seed: int = 1729
```

Validation:

- overlap must be smaller than chunk size;
- active candidates and evidence limit must be positive;
- evidence limit cannot exceed active candidates;
- max steps plus final evaluation cannot exceed hard evaluations;
- temperatures, anchor and learning rate must be positive;
- paths are resolved relative to `workspace.json`.

### `TextRecord`

```python
class TextRecord(BaseModel):
    record_id: str
    source_path: str
    source_kind: Literal["text", "markdown", "json", "jsonl", "csv", "source"]
    text: str
    metadata: dict[str, str | int | float | bool | None]
    content_hash: str
```

### `ChunkRecord`

```python
class ChunkRecord(BaseModel):
    chunk_id: str
    record_id: str
    source_path: str
    source_kind: str
    text: str
    char_start: int
    char_end: int
    token_start: int
    token_end: int
    token_count: int
    content_hash: str
    metadata: dict[str, str | int | float | bool | None]
```

### `CorpusManifest`

```python
class CorpusManifest(BaseModel):
    schema_version: Literal["1"] = "1"
    corpus_id: str
    created_at: str
    embedding_model_id: str
    embedding_revision: str
    dimension: Literal[384]
    dtype: Literal["float32"]
    document_count: int
    record_count: int
    chunk_count: int
    skipped_files: list[str]
    chunks_sha256: str
    vectors_sha256: str
    config_sha256: str
```

### Query and optimization schemas

```python
class EvidenceItem(BaseModel):
    rank: int
    chunk_id: str
    source_path: str
    score: float
    text: str


class OptimizationStep(BaseModel):
    step: int
    field_evaluations: int
    energy: float
    gradient_norm: float
    query_cosine: float
    state_delta: float
    nearest_chunk_ids: list[str]


class OptimizationResult(BaseModel):
    termination: Literal[
        "converged_energy",
        "converged_state",
        "max_steps",
        "hard_budget",
        "non_finite",
    ]
    update_steps: int
    field_evaluations: int
    initial_energy: float
    final_energy: float
    final_state: list[float]
    trace: list[OptimizationStep]


class DecodedAnswer(BaseModel):
    text: str
    citation_chunk_ids: list[str]
    decoder_model_id: str
    used_fallback: bool
    fallback_reason: str | None


class QueryRun(BaseModel):
    run_id: str
    prompt: str
    corpus_id: str
    started_at: str
    initial_evidence: list[EvidenceItem]
    optimization: OptimizationResult
    final_evidence: list[EvidenceItem]
    answer: DecodedAnswer
    timings_ms: dict[str, float]
    peak_rss_mb: float
```

## 8. File-format invariants

### Corpus storage

```text
workspace/
  workspace.json
  corpus/
    manifest.json
    chunks.jsonl
    vectors.npy
  queries/
    runs.jsonl
```

Invariants:

1. `vectors.npy` is shape `[chunk_count, 384]`.
2. Row `i` corresponds exactly to line `i` in `chunks.jsonl`.
3. All vectors are finite float32.
4. Every vector norm is within `1e-4` of 1.
5. `chunk_id` is unique.
6. `content_hash` is SHA-256 of canonical chunk text.
7. Manifest hashes are verified when a workspace opens.
8. A corrupt workspace fails closed; it is never silently rebuilt during `ask`.

### Atomic writes

For ingestion:

1. write `chunks.jsonl.new`, `vectors.npy.new` and `manifest.json.new` in the existing corpus directory;
2. validate the new files completely;
3. copy the current valid files to one `.previous/` backup;
4. replace `chunks.jsonl` and `vectors.npy` with `os.replace`;
5. replace `manifest.json` last so it is the commit marker;
6. reopen and validate the committed corpus;
7. restore `.previous/` if commit validation fails.

The Phase 1 CLI has no concurrent readers. Never write a new manifest before both data files are durable, and never leave a manifest intentionally pointing at partially written arrays.

### Query log

Append one compact JSON line per completed query. Do not write partial results. Full final states are included in Phase 1 for reproducibility; later versions may move them to separate binary traces.

## 9. Ingestion algorithm

Implement in `ingest.py`.

### Discovery

1. accept a file or directory;
2. resolve it without following symlinks;
3. recurse in lexicographic relative-path order;
4. skip hidden paths;
5. match supported suffixes case-insensitively;
6. record unsupported files in the manifest;
7. reject files larger than a configurable 10 MB default;
8. decode UTF-8 strictly.

### Supported source files

Text-like suffix list belongs in `config.py`:

```python
TEXT_SUFFIXES = {
    ".txt", ".md", ".rst",
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".c", ".h", ".cpp", ".hpp",
    ".html", ".css", ".yaml", ".yml", ".toml",
}
```

Structured loaders:

- `.json`: recursively flatten scalar leaves;
- `.jsonl`: parse one JSON value per non-empty line;
- `.csv`: parse with `csv.DictReader`.

### Canonical structured text

JSON leaf:

```text
path.to.field: value
```

JSON object record:

```text
field_a: value
field_b: value
```

CSV row:

```text
column_a: value
column_b: value
```

Sort JSON keys. Preserve CSV column order. Never call `repr()` on values because it can change across types and versions.

### Record IDs

```text
<relative-source-path>::<zero-padded-record-index>
```

Whole text files use record index `000000`.

### Deduplication

- record hash: SHA-256 of canonical UTF-8 text;
- chunk hash: SHA-256 of exact chunk UTF-8 text;
- identical chunk hashes share one stored vector;
- retain all source references in chunk metadata or a `duplicate_sources` list;
- evaluation counts the canonical chunk once.

## 10. Token-aware chunking algorithm

Implement in `chunk.py`.

Use the fast tokenizer shipped with the embedding model:

```python
encoded = tokenizer(
    text,
    add_special_tokens=False,
    return_offsets_mapping=True,
    truncation=False,
)
```

Algorithm:

1. obtain `input_ids` and character `offset_mapping`;
2. if zero tokens, skip the record;
3. create windows of 128 token IDs;
4. advance by `128 - 24 = 104` tokens;
5. derive `char_start` from the first token offset;
6. derive `char_end` from the final token offset;
7. extract `text[char_start:char_end]`;
8. validate re-tokenized chunk length is at most 128 wordpieces;
9. create stable chunk ID:

```text
<record_id>::chunk-<six-digit-window-index>
```

Special cases:

- ignore zero-length offsets;
- a single tokenizer token longer than normal is accepted;
- if offset mapping is unavailable, fail setup rather than switching algorithms;
- never decode token IDs to create payload text because decoding may alter whitespace.

Tests must cover Unicode, newlines, empty files, a 128-token boundary and overlap.

## 11. Embedding and persistence algorithm

Implement in `embed.py` and `store.py`.

### Batch embedding

1. select device through `devices.py`;
2. load local model once;
3. embed chunk texts in stable order;
4. default batch size 32;
5. on MPS out-of-memory, fail with a message suggesting `--embedding-batch-size 8`; do not silently change the batch;
6. request normalized float32 NumPy output;
7. validate shape and norms;
8. write C-contiguous float32 array.

### Incremental reuse

For an existing valid corpus:

1. build `content_hash → vector-row` mapping;
2. reuse vectors for unchanged chunk hashes;
3. embed only new hashes;
4. rebuild `chunks.jsonl` and `vectors.npy` in the new stable order;
5. report reused and newly embedded counts.

The embedding model ID and revision must match. If they differ, re-embed everything.

### Store reader

`CorpusStore.open()`:

1. validate manifest schema;
2. verify file hashes unless `--skip-hash-check` is explicitly used for profiling;
3. load chunk metadata;
4. memory-map vectors read-only;
5. validate row count and dimension;
6. expose exact retrieval.

Hash verification remains the default.

## 12. Exact retrieval algorithm

Implement in `retrieve.py`.

Given unit query/state vector \(x\) and unit corpus matrix \(Z\):

\[
s=Zx.
\]

Algorithm:

1. validate `x.shape == (384,)`;
2. cast to float32 and normalize again;
3. calculate scores using memory-mapped `vectors @ x`;
4. choose top \(k\) with `np.argpartition`;
5. fully sort selected indices by:
   - score descending;
   - `chunk_id` ascending for ties;
6. return copied evidence records.

For corpus size smaller than \(k\), return every chunk.

Tests:

- hand-computed vectors;
- tie stability;
- empty corpus error;
- non-finite state rejection;
- agreement with full `argsort`.

## 13. Latent dynamic field algorithm

Implement in `field.py`.

### Construction

Input:

- query \(q\);
- top 128 candidate vectors \(Z_C\);
- temperatures \(\tau_q,\tau_f\);
- anchor \(\lambda_q\).

Convert copies to CPU float64.

Precompute fixed log query weights:

\[
\ell_i
=
\frac{q^\top z_i}{\tau_q}
-
\operatorname{logsumexp}_j
\left(
\frac{q^\top z_j}{\tau_q}
\right).
\]

For state \(x\):

\[
E(x\mid q)
=
-
\operatorname{logsumexp}_i
\left(
\ell_i+\frac{x^\top z_i}{\tau_f}
\right)
+
\lambda_q(1-x^\top q).
\]

### API

```python
class LatentDynamicField:
    def energy(self, state: np.ndarray) -> float: ...
    def energy_and_gradient(
        self,
        state: np.ndarray,
    ) -> tuple[float, np.ndarray]: ...
```

Implementation:

1. clone state into a CPU float64 tensor with `requires_grad=True`;
2. compute energy with `torch.logsumexp`;
3. call `torch.autograd.grad`;
4. return finite NumPy values;
5. count one field evaluation.

### Gradient reference

Tests compare:

- PyTorch autograd;
- centered finite differences with \(h=10^{-6}\);
- at least 20 coordinates per case;
- 100 seeded cases.

Acceptance:

- median relative error below \(10^{-4}\);
- 99th percentile below \(10^{-3}\).

### Empty and invalid cases

Reject:

- zero candidates;
- non-finite candidates;
- non-unit query beyond tolerance;
- non-positive temperatures;
- negative anchor.

## 14. Latent optimizer algorithm

Implement in `optimize.py`.

### Tangent-projected update

For Euclidean gradient \(g_t\):

\[
g_t^\perp
=
g_t-(g_t^\top x_t)x_t.
\]

Update and retract:

\[
\tilde{x}_{t+1}
=
x_t-\eta g_t^\perp,
\qquad
x_{t+1}
=
\frac{\tilde{x}_{t+1}}
{\lVert\tilde{x}_{t+1}\rVert_2}.
\]

### Exact loop

1. normalize \(x_0=q\);
2. evaluate initial energy and gradient;
3. record step 0;
4. for at most eight updates:
   - project gradient to tangent space;
   - update using learning rate 0.05;
   - retract to unit sphere;
   - evaluate new energy and gradient;
   - resolve nearest four chunk IDs for trace;
   - record state delta and query cosine;
   - update convergence counters;
5. stop after two consecutive below-tolerance energy or state deltas;
6. stop before exceeding 16 total field evaluations;
7. return final state and termination reason.

Default eight updates use nine field evaluations including the initial state.

### Non-increasing guard

The primary algorithm uses fixed learning rate as specified. If a proposed step increases energy by more than `1e-10`:

1. reject the step;
2. halve the learning rate;
3. retry up to three times;
4. count every retry as a field evaluation;
5. if no step lowers energy, terminate as `converged_energy`.

This bounded backtracking is part of projected gradient descent, not a second optimizer.

### Mean-shift baseline

Implement a separate deterministic baseline:

\[
w_i(x)
=
\operatorname{softmax}
\left(
\ell_i+\frac{x^\top z_i}{\tau_f}
\right),
\]

\[
x_{t+1}
=
\operatorname{normalize}
\left(
\sum_iw_i(x_t)z_i+\beta q
\right).
\]

Choose \(\beta=\lambda_q\tau_f\) as the declared anchored baseline. Run the same maximum updates and evidence resolution.

Do not share result labels between gradient optimization and mean shift.

## 15. Decoder algorithm

Implement in `decode.py`.

### Evidence preparation

1. take final-state top four evidence items;
2. assign citations `[1]` through `[4]`;
3. tokenize each excerpt with the FLAN tokenizer;
4. truncate each excerpt to at most 80 tokens;
5. decode the truncated IDs back into decoder input text;
6. retain original exact text separately for displayed evidence;
7. assemble the fixed prompt;
8. ensure total input is at most 512 tokens;
9. if over budget, reduce excerpt limits evenly until it fits;
10. never remove the question or citation labels.

### Fixed instruction

```text
Answer the question using only the numbered evidence.
If the evidence is insufficient, answer exactly:
The available data is insufficient.
Add citations such as [1] after supported statements.

Question:
{prompt}

Evidence:
[1] Source: {path}
{excerpt}

...
```

### Generation

- greedy only;
- maximum 128 new tokens;
- no sampling;
- one return sequence;
- decoder model in evaluation mode;
- `torch.inference_mode()`.

### Citation validation

Use regex:

```python
r"\[(\d+)\]"
```

Valid generated answer:

- non-empty after stripping;
- every referenced integer is between 1 and evidence count;
- at least one citation, unless the answer is the exact insufficiency string;
- no unexpanded template braces;
- no control characters.

Otherwise use deterministic fallback.

### Deterministic fallback

Return:

```text
The optimized state selected these passages:

[1] {first exact excerpt}
[2] {second exact excerpt}

A supported synthesized answer could not be produced.
```

The fallback reason is recorded.

### Decoder leakage test

The decoder object receives no `CorpusStore`, retriever or field. Its constructor receives only local model paths and device. Its `decode` method receives prompt plus evidence. This makes hidden retrieval structurally impossible.

## 16. Evaluation corpus

Implement in `evaluate.py`; fixture definitions live in `tests/fixtures/semantic_cases.json`.

### Case schema

```json
{
  "case_id": "energy-storage-001",
  "documents": [
    {
      "id": "aurora-power",
      "text": "Project Aurora uses nickel battery cells."
    },
    {
      "id": "nickel-temperature",
      "text": "Nickel battery cells remain reliable in very cold storage."
    },
    {
      "id": "aurora-distractor",
      "text": "Aurora lights were photographed above a nickel mine."
    }
  ],
  "query": "What evidence explains Aurora's power choice for cold storage?",
  "gold_chunk_ids": [
    "aurora-power",
    "nickel-temperature"
  ],
  "gold_aspects": [
    "aurora-power-source",
    "cold-reliability"
  ]
}
```

### Dataset construction

Provide at least 50 hand-reviewed deterministic cases:

- 20 paraphrase cases;
- 10 lexical-distractor cases;
- 10 rare-cluster cases;
- 10 multi-evidence cases.

Each case includes:

- query not copied verbatim from a document;
- gold evidence IDs;
- aspect labels;
- at least two distractors.

No LLM generates evaluation data at runtime.

### Methods

Run:

1. zero-step direct cosine retrieval;
2. anchored directional mean shift;
3. projected-gradient field optimization.

Use the same:

- frozen embeddings;
- active candidate budget;
- evidence limit;
- query set.

### Metrics

For each method:

- Recall@4;
- evidence precision@4;
- aspect coverage;
- evidence-set change rate from direct retrieval;
- mean and p95 latency;
- field evaluations;
- failure count.

### Seeds

- smoke: seed `1729`;
- standard: `1729, 1730, 1731, 1732, 1733`.

If the fixture itself is static, seeds control tie perturbations and case ordering only; they must never alter gold labels.

### Classification

Report:

- Result A: strong success;
- Result B: mechanical success only;
- Result C: decoder-only success;
- Result D: mechanical failure.

Thresholds come only from the source specification.

## 17. CLI design

Implement with `argparse` in `cli.py`.

### Commands

```text
ltm-poc doctor
ltm-poc models download
ltm-poc init
ltm-poc ingest
ltm-poc ask
ltm-poc evaluate
```

The module entry point mirrors the console script:

```bash
python -m ltm_poc ...
```

### Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Success |
| 2 | CLI usage/configuration error |
| 3 | Missing or invalid model assets |
| 4 | Invalid/corrupt workspace |
| 5 | Ingestion failure |
| 6 | Query/optimization failure |
| 7 | Evaluation gate failure |
| 8 | Resource budget exceeded |

### Output

- human-readable output to stdout;
- errors to stderr;
- `--json` emits one JSON object to stdout and suppresses prose;
- logs never include full private document text;
- `--verbose` may include chunk IDs and timing, not unredacted corpus content.

## 18. Ordered implementation stages

The stages are sequential. Do not begin a stage until its checkpoint passes.

## Stage 0 — Scaffold and environment

### Goal

Create an installable empty package and deterministic test environment.

### Files

- `pyproject.toml`;
- `.gitignore`;
- `src/ltm_poc/__init__.py`;
- `src/ltm_poc/__main__.py`;
- `tests/test_import.py`.

### Work

1. declare package metadata and dependencies;
2. expose `ltm-poc = "ltm_poc.cli:main"` only after `cli.py` exists, or provide a minimal placeholder returning usage;
3. ignore generated directories;
4. install editable package;
5. verify imports.

### Checkpoint

```bash
python -m pip check
python -m pytest tests/test_import.py
python -m compileall -q src
```

Exit: clean installation and import.

## Stage 1 — Configuration, schemas and device detection

### Files

- `src/ltm_poc/config.py`;
- `src/ltm_poc/schemas.py`;
- `src/ltm_poc/devices.py`;
- `tests/test_config.py`.

### Work

1. implement canonical schemas;
2. implement config loading and relative-path resolution;
3. implement CPU/MPS selection;
4. implement seeding;
5. implement JSON-safe device report.

### Checkpoint

- invalid overlap rejected;
- missing model path rejected;
- `auto` always resolves;
- config JSON round-trips;
- no model is loaded.

## Stage 2 — Explicit model acquisition and smoke loading

### Files

- `src/ltm_poc/models.py`;
- `src/ltm_poc/cli.py`;
- `tests/test_models.py`.

### Work

1. implement pinned model catalog constants;
2. implement explicit snapshot download;
3. implement allow/ignore patterns;
4. write model manifest with file hashes;
5. implement local-only loaders;
6. implement `doctor`;
7. implement smoke embedding and decoder generation.

### Checkpoint

```bash
python -m ltm_poc models download --model-dir ./.models
python -m ltm_poc doctor --model-dir ./.models
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python -m ltm_poc doctor --model-dir ./.models
```

Exit: both models load and infer offline.

## Stage 3 — Ingestion and token-aware chunking

### Files

- `src/ltm_poc/ingest.py`;
- `src/ltm_poc/chunk.py`;
- `tests/test_ingest.py`;
- `tests/test_chunk.py`;
- `tests/fixtures/inputs/*`.

### Work

1. implement discovery;
2. implement text, JSON, JSONL and CSV loaders;
3. implement canonical record IDs and hashes;
4. implement tokenizer offset windows;
5. implement chunk deduplication;
6. report skipped files.

### Checkpoint

- all fixture formats load;
- Unicode spans resolve exactly;
- 128-token windows and 24-token overlap are correct;
- same input order yields identical chunk JSON;
- unsupported binary file is reported, not decoded.

## Stage 4 — Embeddings and corpus storage

### Files

- `src/ltm_poc/embed.py`;
- `src/ltm_poc/store.py`;
- `tests/test_embed.py`;
- `tests/test_store.py`.

### Work

1. implement batch embedding;
2. validate normalized 384D float32 output;
3. write atomic corpus artifacts;
4. validate manifests and hashes;
5. implement incremental vector reuse;
6. memory-map vectors.

### Checkpoint

- stored norms within tolerance;
- row/chunk correspondence exact;
- a corrupt hash prevents the corpus from opening;
- unchanged re-ingestion embeds zero chunks;
- changed record embeds only changed chunks.

## Stage 5 — Exact retrieval

### Files

- `src/ltm_poc/retrieve.py`;
- `tests/test_retrieve.py`;
- `tests/fixtures/tiny_vectors.npy`.

### Work

1. implement exact matrix cosine;
2. implement top-k and stable tie sorting;
3. return evidence payloads;
4. record scores as Python floats.

### Checkpoint

- matches hand calculation;
- matches full argsort;
- stable across repeated runs;
- rejects invalid state.

## Stage 6 — Latent dynamic field

### Files

- `src/ltm_poc/field.py`;
- `tests/test_field.py`.

### Work

1. implement query-weight precomputation;
2. implement stable scalar energy;
3. implement autograd gradient;
4. implement evaluation counter;
5. implement finite-difference tests.

### Checkpoint

- gradient thresholds pass;
- valid cases are finite;
- empty/invalid cases fail clearly;
- no corpus payload is needed during energy evaluation.

Do not proceed if Stage 6 fails.

## Stage 7 — Latent optimizer and mean-shift control

### Files

- `src/ltm_poc/optimize.py`;
- `tests/test_optimize.py`.

### Work

1. implement tangent projection;
2. implement spherical retraction;
3. implement bounded backtracking;
4. implement convergence counters;
5. implement trace;
6. implement mean-shift baseline.

### Checkpoint

- at least 95% controlled cases lower energy;
- unit norm preserved;
- no run exceeds 16 evaluations;
- known basin fixtures converge;
- termination reason always set.

## Stage 8 — Decoder and deterministic fallback

### Files

- `src/ltm_poc/decode.py`;
- `tests/test_decode.py`.

### Work

1. implement evidence token budgets;
2. implement fixed prompt;
3. implement local FLAN loading;
4. implement deterministic generation;
5. implement citation validation;
6. implement fallback.

### Checkpoint

- valid cited output accepted;
- missing/invalid citations fall back;
- empty evidence returns insufficiency/fallback;
- decoder has no corpus-store dependency;
- offline inference succeeds.

## Stage 9 — Workspace CLI and end-to-end query

### Files

- `src/ltm_poc/cli.py`;
- `src/ltm_poc/__main__.py`;
- `tests/test_end_to_end.py`.

### Work

1. implement `init`;
2. implement `ingest`;
3. implement `ask`;
4. persist query runs;
5. add `--show-trace`, `--json`, `--device`;
6. implement exit codes.

### Checkpoint

```bash
python -m ltm_poc init /tmp/ltm-poc-workspace \
  --model-dir ./.models
python -m ltm_poc ingest /tmp/ltm-poc-workspace \
  tests/fixtures/inputs
python -m ltm_poc ask /tmp/ltm-poc-workspace \
  "What does the data say?" \
  --show-trace
```

Exit: natural-language answer or explicit insufficiency with valid sources.

## Stage 10 — Scientific evaluation

### Files

- `src/ltm_poc/evaluate.py`;
- `src/ltm_poc/report.py`;
- `tests/test_evaluate.py`;
- `tests/fixtures/semantic_cases.json`.

### Work

1. author and review 50 cases;
2. implement three methods;
3. implement metrics;
4. implement five-seed standard run;
5. classify A/B/C/D;
6. write JSON and Markdown reports.

### Checkpoint

```bash
python -m ltm_poc evaluate \
  --preset smoke \
  --model-dir ./.models \
  --output results/phase1-smoke
```

No threshold may be changed after the first report.

## Stage 11 — Resource measurement and documentation

### Files

- `src/ltm_poc/report.py`;
- `README.md`;
- tests only if measurement helpers require them.

### Work

1. measure cold model load;
2. measure 1K and 10K chunk ingestion;
3. measure warm query p50/p95;
4. record peak RSS through `resource`;
5. document exact commands and known limitations;
6. save environment and model manifests.

### Checkpoint

- smoke below 4 GB;
- standard below 8 GB;
- target warm query below five seconds;
- report contains device, versions, revisions and hashes.

## Stage 12 — Final audit

### Work

1. run all tests on CPU;
2. run smoke tests on MPS;
3. run offline end-to-end flow;
4. run `ruff check` and `ruff format --check`;
5. run `pip check`;
6. verify no models/results are tracked;
7. verify every citation resolves;
8. compare implementation with source specification line by line.

### Final commands

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python -m pytest --cov=ltm_poc --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m compileall -q src
python -m pip check
git status --short
```

Exit: Phase 1 implementation candidate ready for experimental execution.

## 19. Dependency order

```text
Stage 0 scaffold
    ↓
Stage 1 schemas/config/device
    ↓
Stage 2 model assets
    ↓
Stage 3 ingestion/chunking
    ↓
Stage 4 embeddings/storage
    ↓
Stage 5 retrieval
    ↓
Stage 6 field
    ↓
Stage 7 optimizer
    ↓
Stage 8 decoder
    ↓
Stage 9 end-to-end CLI
    ↓
Stage 10 evaluation
    ↓
Stage 11 resources/docs
    ↓
Stage 12 audit
```

Stages 6 and 7 are the scientific core. Stage 8 must not begin early to avoid mistaking fluent decoder output for field success.

## 20. Checkpoint artifacts

| Stage | Required artifact |
| ---: | --- |
| 0 | import/test output |
| 1 | validated sample config and doctor device JSON |
| 2 | model manifest with exact revisions and hashes |
| 3 | canonical records and chunks fixture |
| 4 | valid mini corpus artifact |
| 5 | retrieval golden-result JSON |
| 6 | gradient comparison report |
| 7 | controlled optimizer trace |
| 8 | cited answer and fallback examples |
| 9 | complete persisted query run |
| 10 | Phase 1 JSON and Markdown evaluation reports |
| 11 | hardware/resource report |
| 12 | final audit log |

Do not commit generated model weights or large reports. Commit small golden fixtures and schemas.

## 21. Risk register

### Embedding truncation

Risk: chunks exceed the model’s useful sequence length.  
Control: tokenizer-aware 128-wordpiece windows with exact offsets.

### Semantic majority collapse

Risk: field moves toward a dense but irrelevant topic.  
Control: query weights, query anchor, active candidates and rare-cluster evaluation.

### Field equals classical mean shift

Risk: the LTM mechanism has no advantage.  
Control: mandatory anchored mean-shift baseline and Result B classification.

### Optimizer instability

Risk: fixed learning rate increases energy or produces NaNs.  
Control: float64 CPU field, tangent projection, bounded backtracking and hard budget.

### Decoder hallucination

Risk: FLAN produces unsupported language.  
Control: final-state evidence only, citation validation, small token budget and deterministic fallback.

### Decoder masks field failure

Risk: output sounds correct using query priors.  
Control: shuffled/empty evidence tests and Stage 8 after field/optimizer checkpoints.

### MPS incompatibility

Risk: an operation is unsupported or inconsistent.  
Control: CPU is mandatory reference; `--device cpu` always works; field never uses MPS.

### Hidden network access

Risk: `from_pretrained` downloads during normal use.  
Control: local paths, `local_files_only=True`, offline environment tests.

### Workspace corruption

Risk: vectors and payload rows become misaligned.  
Control: atomic writes, hashes, row-count checks and one backup.

### Evaluation leakage

Risk: thresholds or fixtures are adjusted after observing results.  
Control: commit fixtures and thresholds before standard evaluation.

## 22. Instructions for a small implementation model

An implementation model must follow this protocol:

1. Read the source specification.
2. Read only the current stage plus Sections 2, 5, 7 and 8 of this plan.
3. State the stage goal and files before editing.
4. Write the stage’s failing tests first.
5. Modify only the listed stage files unless a compile error requires an import-only change.
6. Keep each public function typed.
7. Use the exact schema and field names.
8. Run only the stage checkpoint tests first.
9. Run the full existing test suite before declaring the stage complete.
10. Record the checkpoint result.
11. Do not begin the next stage automatically.

The model must never:

- substitute another model checkpoint;
- add a framework;
- silently relax a test;
- introduce a database;
- implement optional appendix experiments;
- optimize performance before correctness;
- claim a scientific result from unit tests.

If a test reveals a conflict with this plan:

1. stop;
2. write the smallest reproducible failure;
3. identify the conflicting plan sections;
4. request a plan amendment;
5. do not invent a workaround.

## 23. Review gates

### Gate P — Plan approval

Human confirms:

- exact models and revisions;
- dependency set;
- 128/24 chunking;
- field equation;
- optimizer update;
- required FLAN decoder;
- stage order.

### Gate T — Task approval

After Plan approval, convert stages into session-sized checkbox tasks. Each task changes no more than approximately five files and has its own acceptance command.

### Gate I — Implementation approval

Begin code only after the task list is reviewed.

### Gate E — Experiment approval

Freeze fixtures, seeds and thresholds before running standard evaluation.

## 24. Definition of implementation complete

Implementation is complete when:

- all 12 stages pass;
- models load from pinned local safetensors;
- normal commands work with networking disabled;
- a user can initialize, ingest and query their own supported files;
- prompt state \(x_0\), final state \(x^\*\), energy and evidence are recorded;
- FLAN decoder produces cited output or deterministic fallback;
- direct retrieval, mean shift and latent optimization are compared;
- hardware report is produced;
- evaluation classifies the POC as A, B, C or D;
- no deferred feature has entered the core.

This completes the software implementation. It does not predetermine whether the scientific hypothesis passes.
