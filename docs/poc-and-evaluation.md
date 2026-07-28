# Proof of Concept and Evaluation Plan

## Scientific objective

The POC must separate four claims:

1. continuous field navigation works;
2. configured topology compilation works;
3. optimization performs reasoning beyond retrieval;
4. sparse activation offers a useful quality–cost trade-off.

Success on one claim does not establish the others.

## Gate 1: Semantic field POC

### Pipeline

```text
Controlled corpus
    ↓
Frozen semantic encoder
    ↓
16–64D projection
    ↓
Explicit density/energy field
    ↓
Query-conditioned optimization
    ↓
Nearest exact payload
```

The objective must retain the query:

\[
E(x\mid q)=-U(x)+\lambda\lVert x-x_0\rVert^2
\]

Without query conditioning, states may collapse into the largest corpus cluster.

### Baselines

- exact cosine search;
- approximate nearest-neighbor search;
- standard RAG;
- mean shift or kernel density estimation;
- a non-optimized projected query.

### Metrics

- Recall@k and nDCG;
- answer accuracy;
- convergence rate;
- bad-attractor rate;
- latency;
- field evaluations;
- corpus-size scaling;
- information loss after field distillation.

Gate 1 validates field mechanics, not reasoning.

## Gate 2: Configured reasoning POC

Construct a controlled domain containing:

- typed facts;
- directed implications;
- dependencies;
- hard and soft constraints;
- conflicts;
- goals;
- confidence and provenance.

Example:

```text
A and B imply C
C implies D
D conflicts with E
Goal: satisfy D without activating E
```

Train on smaller graphs and test unseen compositions, longer paths, contradictions and topology updates.

### Baselines

- breadth-first or graph search;
- SAT/CSP solver;
- graph neural network;
- frontier LLM without retrieval;
- frontier LLM with strong RAG;
- LTM without field distillation;
- LTM with field distillation;
- LTM with and without verifier.

### Metrics

- verified solution rate;
- multi-hop accuracy by path length;
- invalid-equilibrium rate;
- constraint violation count;
- evidence precision and recall;
- contradiction detection;
- out-of-distribution generalization;
- update retention;
- latency and cost.

## Gate 3: 10–20M-token system evaluation

Create large-context variants of:

- multi-round coreference retrieval;
- graph traversal;
- multi-hop evidence synthesis;
- contradiction resolution;
- dependency closure;
- incremental knowledge updates.

Measure at 1M, 5M, 10M and 20M stored tokens while holding the per-request active budget fixed.

The frontier baseline must use a strong production-style retrieval system. Comparing LTM only with direct full-context prompting would overstate its advantage.

## Dated frontier reference

The following public values are a comparison reference as of **2026-07-28**, not LTM results.

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

Vendor results may use different harnesses and should be independently reproduced where possible.

## Projected LTM target ranges

These ranges are hypotheses for planning, not measured predictions.

| Evaluation | First credible POC | Mature domain LTM |
| --- | ---: | ---: |
| MRCR-style retrieval at 512K–1M | 65–85% | 85–95% |
| GraphWalks-style BFS at 1M | 70–88 F1 | 88–97 F1 |
| MRCR-style retrieval at 10M | 55–75% | 75–90% |
| MRCR-style retrieval at 20M | 50–70% | 70–88% |
| Evidence-grounded multi-hop QA | 55–75% | 75–90% |
| Configured constraint validity | 80–95% | 92–99% |
| Contradiction resolution with citations | 65–85% | 85–95% |

Standard broad-intelligence scores are expected to remain substantially below frontier models until LTM contains diverse mature topologies, capable tools and a strong decoder.

## Falsification criteria

The project should reconsider its central assumptions if:

- optimization does not improve over the initial state;
- field retrieval consistently underperforms ordinary ANN search without another advantage;
- low energy does not correlate with verified validity;
- unseen multi-hop accuracy collapses with path length;
- topology updates cause unacceptable forgetting;
- routing requires activation proportional to total corpus size;
- a graph or constraint solver dominates LTM on quality, cost and update behavior;
- the decoder performs most of the measured reasoning.

Negative results are scientifically useful if the experiments isolate which claim failed.
