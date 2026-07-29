# LTM Phased Research Roadmap

**Status:** Phase 1, 1.1 and 1.2 experiments complete; later phases provisional.  
**Last updated:** 2026-07-29

## Why the work is phased

LTM combines several claims that can fail independently. Building the intended reasoning topology immediately would make it difficult to determine whether a failure came from representation, field construction, optimization, decoding or scale.

The program therefore replaces one uncertain component at a time with a known implementation and preserves explicit interfaces between components.

## Phase 0 — Foundation

**Status:** Complete enough to begin Phase 1.

Outputs:

- canonical architecture;
- literature map;
- first-principles experiment catalog;
- explicit limits on context, cost and frontier-model claims.

Phase 0 establishes the research question. It does not provide experimental evidence.

## Phase 1 — Semantic-topology surrogate POC

**Status:** Complete. Pipeline mechanics passed; semantic objective Result B.

A frozen semantic embedding engine temporarily replaces the native reasoning topology. The complete four-component runtime is still built:

1. semantic topology surrogate;
2. latent dynamic field;
3. latent optimizer;
4. grounded decoder.

The purpose is to establish that:

- corpus data can induce an inspectable query-conditioned field;
- latent states can be optimized through that field;
- the final state can select useful exact evidence;
- a decoder can produce a grounded output;
- interfaces allow the topology implementation to be replaced later.

Phase 1 does **not** establish logical or causal reasoning. Its canonical
specification is [Phase 1: Minimal Semantic-Field POC](../phases/phase-1/specification.md).
Broader experiments are retained in the
[Phase 1 Experimental Appendix](../phases/phase-1/experimental-appendix.md).

The ordered build sequence, pinned model revisions and verification
checkpoints are defined in the
[Phase 1 implementation record](../phases/phase-1/implementation.md).

Phase 1's complete surrogate pipeline passed. Its semantic optimizer produced
Result B. Phase 1.1 multi-state diversification also produced Result B. Phase
1.2's whole-corpus equilibrium produced E-B: it was numerically valid and
computationally bounded, but it did not improve over the weighted barycenter
or retrieval gates. These comparisons reject the tested semantic objectives,
not the unimplemented native reasoning topology.

## Phase 2 — Native reasoning topology

**Status:** Next falsifiable research gate; not yet implemented.

Replace semantic similarity as the primary structure with typed reasoning objects:

- premises and consequences;
- dependencies;
- causes;
- conflicts;
- goals;
- hard and soft constraints;
- provenance and uncertainty.

Phase 2 first tests explicit topologies and explicit energies on synthetic, exactly verifiable rule worlds. It should reuse the Phase 1 optimizer, trace format, verifier boundary and decoder contract wherever possible.

Exit condition:

> Native topology plus iterative optimization generalizes to unseen relation compositions or proof depths and beats retrieval and non-iterative neural baselines.

## Phase 3 — Topology compiler and multi-domain integration

**Status:** Provisional.

Add the offline pipeline:

```text
Raw data
    ↓
LLM-assisted structured extraction
    ↓
Reasoning Intermediate Representation
    ↓
Deterministic validation
    ↓
Domain-configured topology compilation
```

This phase evaluates extraction fidelity, JSON-configurable domain reuse, incremental updates, contradictions and topology-version migration.

Exit condition:

> At least two materially different domains can be compiled through a shared intermediate representation without hiding domain logic in the decoder.

## Phase 4 — Modular persistence and 10–20M-token scaling

**Status:** Provisional.

Introduce:

- sharded topology and field modules;
- prompt-conditioned routing;
- hot, warm and cold storage;
- adaptive activation;
- SSD-streamed experiments;
- exact external payload storage.

Exit condition:

> A 10–20M-token-equivalent store remains useful while ordinary single-domain requests activate a bounded subset of modules and preserve evidence fidelity.

This phase tests practical scaling, not literal unlimited context or constant worst-case work.

## Phase 5 — Product and economics

**Status:** Provisional.

Build the user-facing persistent reasoning workspace:

- ingestion and update workflows;
- conversational interface;
- domain configuration management;
- evidence and verification reports;
- latency and cost tiers;
- security, observability and recovery.

Exit condition:

> The system beats a strong LLM-plus-RAG baseline on a selected production workload at an acceptable quality, reliability and cost frontier.

## Promotion rule

Each phase requires:

1. a reviewed specification;
2. reproducible experiments;
3. comparison with the strongest relevant simpler baseline;
4. documented negative results;
5. a written decision to proceed, redesign or stop.

Later phases must not be used to explain away a failed earlier mechanism. In particular, model scale should not substitute for demonstrating that the Phase 1 field and optimizer work as claimed.
