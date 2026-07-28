# Inference, Scaling and Economics

## Scaling target

The initial practical target is 10–20 million tokens of persistent domain knowledge. A long-term architecture may contain trillions of total sharded parameters, but only a bounded subset should be active for ordinary requests.

The system does not claim literal unlimited context or exact \(O(1)\) reasoning. Its target is approximately bounded average active compute under a fixed workload distribution.

## Hierarchical storage

```text
Cold: object storage / SSD
    ↓
Warm: CPU memory / NVMe cache
    ↓
Hot: GPU-resident router and common modules
    ↓
Per-request active field
```

Recommended separation:

- **field weights:** compressed topological influence;
- **exact payload:** source facts, text and provenance;
- **router metadata:** module summaries and activation keys;
- **verifier data:** domain rules and deterministic constraints.

## Sparse modular inference

For total modules \(F_1,\ldots,F_N\), a prompt activates a bounded set:

\[
F_q(x)=\sum_{i\in A(q)}g_i(q)F_i(x),
\qquad |A(q)|=k
\]

If \(k\) remains approximately bounded while \(N\) grows, average field evaluation can remain approximately stable. Routing errors and cross-domain questions may require larger \(k\).

## Five-trillion-parameter thought experiment

Five trillion parameters require approximately:

| Precision | Raw weight storage |
| --- | ---: |
| 16-bit | 10 TB |
| 8-bit | 5 TB |
| 4-bit | 2.5 TB |

This capacity should be sharded. A plausible long-term design might contain:

- a small shared meta-topology;
- domain routers;
- many specialized field experts;
- exact external payload;
- 1–50B active field parameters for ordinary requests;
- a separate 3–70B decoder depending on quality tier.

Evaluating all 5T parameters at every optimization step would defeat the low-cost objective.

## SSD-streamed inference

A complete field can theoretically run on one high-memory GPU by streaming shards from SSD:

\[
\nabla E(x)=\sum_{m=1}^M\nabla E_m(x)
\]

For 2.5 TB of four-bit weights:

| Effective SSD-to-GPU bandwidth | One full pass |
| ---: | ---: |
| 10 GB/s | ~250 seconds |
| 25 GB/s | ~100 seconds |
| 50 GB/s | ~50 seconds |
| 100 GB/s | ~25 seconds |

Two optimization variants are possible:

- **Exact accumulated gradient:** Stream every shard, accumulate all forces, then update the latent state. Each optimizer step requires one full pass.
- **Streamed stochastic field optimization:** Update after each shard. This may converge in fewer full passes but is order-dependent and is not identical to global gradient descent.

Batching many query states lets one shard load serve many requests. This improves throughput cost, not individual latency.

## Recommended runtime

```text
GPU-resident global router and summary
        ↓
Select relevant topology modules
        ↓
Stream/cache those modules
        ↓
Assemble a local query-conditioned field
        ↓
Run most optimization steps locally
        ↓
Verify and decode
```

Complete topology scans should be rare, asynchronous and batched.

## Complexity statement

A more honest inference model is:

\[
C_{\mathrm{request}}=
C_{\mathrm{route}}+
T\cdot C_{\mathrm{active\ field}}+
C_{\mathrm{verify}}+
C_{\mathrm{decode}}+
C_{\mathrm{I/O}}
\]

where \(T\) is the number of optimizer steps.

The total corpus size affects module storage, routing quality, cache behavior, update cost and rare global queries even when ordinary active computation is bounded.

## Mature cost targets

Projected internal costs under high utilization:

| Mode | Active field | Optimization | Decoder | Target cost |
| --- | ---: | ---: | ---: | ---: |
| Lightweight | 1–5B | 16–48 steps | 3–7B | $0.003–$0.01 |
| Standard | 5–20B | 48–96 steps | 7–14B | $0.01–$0.05 |
| Multi-domain | 20–75B | 96–192 steps | 14–70B | $0.05–$0.50 |
| Deep/global | streamed or 100B+ | variable | 70B+ | $0.50–$5+ |

These are engineering targets, not measured costs. Fully loaded costs must include storage, replicas, networking, idle capacity, ingestion and operations.

## What must be measured

- latency distributions rather than averages only;
- active parameter count;
- optimizer steps to convergence;
- bytes read per request;
- cache hit rate;
- routing recall;
- decoder tokens;
- GPU seconds per request;
- accuracy as total storage grows;
- accuracy as active compute is capped;
- cost of incremental updates;
- cost and latency of global queries.
