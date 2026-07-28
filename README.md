# Latent Topology Models

Latent Topology Models (LTM) are a proposed reasoning and persistent-memory architecture designed to work alongside language models.

An LLM handles ambiguous language, broad interaction and presentation. LTM compiles user or domain knowledge into configurable reasoning topologies, induces differentiable latent fields from those topologies, and optimizes a latent state toward a verified solution.

> **Knowledge is compiled into persistent structure. Reasoning is latent optimization over an activated field. Language is the interface.**

## Intended product

An end user creates an LTM workspace, selects one or more domain configurations, and adds documents, code, rules, databases and other data. The system compiles that material into persistent topology modules. The user then interacts through a familiar chat interface and can ask the system to:

- answer questions using a 10–20 million-token knowledge collection;
- combine evidence across many sources;
- find contradictions, dependencies and causes;
- generate plans that satisfy explicit constraints;
- reason about a large codebase or project over time;
- update its knowledge without resending the full corpus;
- return answers with evidence, assumptions and verification results.

LTM is initially intended to be a specialized reasoning coprocessor, not a replacement for all language-model capabilities.

### Product distinction

| Conventional LLM system | Intended LTM system |
| --- | --- |
| Broad pretrained knowledge | User-owned, expandable domain knowledge |
| Corpus inserted or retrieved for each request | Corpus compiled into persistent topology modules |
| Reasoning performed primarily through token generation | Candidate solution found through latent optimization |
| Context is conversational and temporary | Knowledge persists and can be incrementally updated |
| Plausibility is often the final criterion | Constraints, provenance and verification are first-class |
| Cost depends strongly on active tokens and tools | Compute can be explicitly budgeted per request |

The relevant comparison is LTM versus an LLM combined with retrieval, tools, memory and an agent harness—not only a raw language model.

## System boundary

The user-facing system has four primary runtime components and one essential offline pipeline.

### Offline: topology compilation

```text
Raw data
    ↓
LLM-assisted structured extraction
    ↓
Reasoning Intermediate Representation (RIR)
    ↓
Deterministic validation and normalization
    ↓
Domain-configured topology encoder
    ↓
Instantiated topology and field modules
```

### Online: reasoning

```text
Prompt
    ↓
Prompt and goal encoder
    ↓
Relevant topology activation
    ↓
Query-conditioned latent dynamic field
    ↓
Latent optimization
    ↓
Verification
    ↓
Language decoder
    ↓
Answer, evidence and constraint report
```

## Core definitions

- **Template topology:** A domain configuration defining state types, relation meanings, constraints, energy terms and validators.
- **Instantiated topology:** The validated states, relationships and provenance compiled from a corpus.
- **Topology encoder/compiler:** The ingestion system that places validated knowledge into the configured topology.
- **Latent dynamic field:** A differentiable, prompt-conditioned energy or vector field induced by active topology modules.
- **Latent optimizer:** The procedure that evolves a latent reasoning state toward a low-energy candidate.
- **Verifier:** An independent check that distinguishes convergence from correctness.
- **Decoder:** A language or symbolic model that expresses an already selected and checked result.

## Reasoning primitives

Every domain specializes a shared reasoning vocabulary:

- states;
- premises and consequences;
- causes;
- constraints;
- dependencies;
- conflicts;
- evidence;
- goals;
- abstractions;
- uncertainty;
- provenance.

An optional dual-vector representation assigns each state an Origin vector and a Target vector, making directed transitions such as premise → consequence asymmetric.

## What “global satisfaction” means

LTM does not attempt to satisfy every stored statement. Real knowledge contains contradictions, outdated claims and irrelevant information.

The actual objective is:

> Find the state that best satisfies the prompt-relevant, reliability-weighted constraints while minimizing unresolved conflict and uncertainty.

\[
E(x\mid q)=
\sum_i w_i(q)E_i(x)
+\lambda_gE_{\mathrm{goal}}(x,q)
+\lambda_uE_{\mathrm{uncertainty}}(x)
\]

The weights \(w_i(q)\) depend on relevance, provenance, confidence, recency and domain applicability.

## Scaling position

“Practically unlimited context” means an expandable persistent knowledge store, initially targeting 10–20 million tokens. It does not mean exact simultaneous attention to unlimited information.

Total topology capacity may grow through sharded field modules, external payload storage or—in a long-term sparse design—trillions of total parameters. Per-request compute remains bounded only when the system activates or streams a limited subset of this capacity.

The defensible scaling claim is:

> LTM aims to expand total accessible knowledge while keeping average active inference bounded through prompt-conditioned routing, sparse field activation, caching and offline compilation.

Exact global questions may still require corpus-dependent work.

## Current status

**Stage:** Formal specification and POC design.

No LTM performance, cost, general-reasoning or scaling claim has been experimentally established. All scores, costs and probabilities in this repository are projections or research targets unless explicitly marked as measured.

### Planning estimates

These are subjective estimates, not experimental measurements:

| Outcome | Estimated probability |
| --- | ---: |
| Complete end-to-end POC | 90–95% |
| Useful domain topology compilation | 80–90% |
| Useful retrieval and field navigation | 70–90% |
| Useful bounded-domain reasoning | 60–75% |
| Handle 10–20M tokens of accessible knowledge | 70–85% |
| Useful specialized product | 50–65% |
| Broadly useful LLM reasoning coprocessor | 30–50% |
| Broad frontier-model equivalence | 10–20% |

The primary risks are teacher-extraction error, inadequate topology primitives, field-distillation loss, bad optimization attractors, sparse-routing misses, decoder leakage and failure to outperform strong RAG or solver baselines.

## Immediate objective

Build two experimental gates:

1. Demonstrate that a query-conditioned field can navigate a compiled semantic corpus.
2. Demonstrate that a configured reasoning topology can solve unseen, verifiable multi-step constraint problems.

The second gate determines whether LTM performs reasoning rather than compressed retrieval.

## Documentation

- [Canonical architecture](docs/architecture.md)
- [Inference and scaling](docs/inference-and-scaling.md)
- [POC and evaluation plan](docs/poc-and-evaluation.md)
- [Research abstract](docs/research-abstract.md)
