# Phase 1.3 — Semantic LTM versus Traditional RAG

## Purpose

This phase measures the semantic POC against reproducible retrieval baselines.
It does not test the unimplemented native reasoning topology. The same frozen
MiniLM encoder, four-item evidence budget, and (where used) FLAN-T5-small
decoder are used for every method so the comparison isolates evidence
selection and latent optimization.

## Methods

The benchmark includes Okapi BM25 (`k1=1.2`, `b=0.75`), dense cosine
retrieval, reciprocal-rank fusion of BM25 and dense rankings (`k=60`), the
existing single-state optimizer, multi-state optimization, exact semantic
equilibrium, hierarchical semantic equilibrium, and the unchanged prompt
state. Gold evidence is an oracle ceiling, not a deployable method.

BM25 uses Unicode word tokens, case folding, stable chunk-ID tie breaks, and
no query rewriting. Hybrid fusion receives the top 100 candidates from each
ranking and emits at most four unique chunks.

## Data and metrics

The runner accepts both the Phase 1.3 domain/case schema and the existing
scenario fixtures. A locked benchmark should contain controlled cases plus a
deterministic HotpotQA distractor subset. Evidence metrics are Recall@1/2/4,
Precision@4, MRR, and nDCG; answer metrics are optional and must use the same
decoder and bounded evidence bundle. Latency, field evaluations, energy
monotonicity, unit norms, provenance, and reproducibility are recorded.

## Command

```bash
python -m ltm_poc evaluate-rag \
  --workspace workspaces/e2e \
  --controlled-suite eval/phase-1.3/controlled-held-out.json \
  --hotpot-suite eval/phase-1.3/hotpotqa-300.json \
  --output results/phase-1.3
```

The current implementation writes one summary and Markdown report per supplied
suite. It never retunes on a held-out suite. Existing `ask`, Phase 1, Phase
1.1, and Phase 1.2 commands remain unchanged.

## Decision gate

The proposed quality win is at least five absolute Recall@4 points over hybrid
RAG on both suites with a paired bootstrap interval above zero, no material
precision or answer-grounding loss, zero numerical failures, and deterministic
repeat results. Failure to meet that gate is a valid result: it means semantic
optimization has not shown an advantage over traditional RAG, not that native
reasoning topology has been disproved.
