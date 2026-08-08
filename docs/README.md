# LTM Documentation

This is the canonical documentation index. The
[results ledger](roadmap/results-ledger.md) is the only cross-experiment status
authority.

## Architecture

- [Architecture index](architecture/README.md)
- [Normative LTM-ARCH-1.1 lock](architecture/architecture-lock-v1.md)
- [Mother Architecture thesis](architecture/mother-architecture.md)
- [Compiler, field, optimization, and decoder internals](architecture/component-internals.md)
- [Canonical LTM architecture](architecture/overview.md)
- [Mumbrane semantic topology and FieldIR execution bridge](architecture/semantic-topology.md)
- [Runtime pipeline](architecture/runtime-pipeline.md)
- [Evidence boundary](architecture/evidence-boundary.md)
- [Scaling laws and runtime metrics](architecture/scaling-laws.md)
- [LTM-R1 compatibility contract](architecture/fieldir-v1.md)

## Audits

- [LTM v1 foundation audit](audits/2026-08-05-ltm-v1-foundation-audit.md)
- [Fresh architecture viability audit](audits/2026-08-06-ltm-architecture-viability-audit.md)
- LTM-R1 vector-native representation audit: [specification](experiments/representation/r01/specification.md) · [report](experiments/representation/r01/report.md) — PASS
- LTM-R2 universal Mumbrane representation audit: [specification](experiments/representation/r02/specification.md) · [report](experiments/representation/r02/report.md) — PASS on evaluator-owned semantic bodies
- LTM-I1 canonical FieldIR v2 integration: [specification](experiments/integration/i01/specification.md) · [report](experiments/integration/i01/report.md) — PASS on confirmed/evaluator-generated topology

## Latent-inference studies

- I1 relation-free Mumbrane latent inference: [specification](experiments/inference/i01/specification.md) · [report](experiments/inference/i01/report.md) — `I1-B` body-representation failure; authoritative r5 run
- I2 multiscale minimap latent dynamic inference: [specification](experiments/inference/i02/specification.md) · [report](experiments/inference/i02/report.md) — `I2-C` local-transition failure; fail-fast at development gate
- I2.1 aligned transition and minimap navigation: [specification](experiments/inference/i02-1/specification.md) · [report](experiments/inference/i02-1/report.md) — controlled terminal-completion pass; not arbitrary reasoning
- I2.2 global content-addressed minimap navigation: [specification](experiments/inference/i02-2/specification.md) · [report](experiments/inference/i02-2/report.md) — historical traversal demonstration; post-hoc mechanism/integrity audit required
- I2 dynamic-field mechanism audit: [evidence audit](audits/2026-08-06-i2-dynamic-field-mechanism-audit.md) — post-hoc audit: current I2 evidence does not prove the full field-law claim
- I2.3 hermetic field-law hardening: [specification](experiments/inference/i02-3/specification.md) · [report](experiments/inference/i02-3/report.md) — summary-dependent development reaches 97.67% answerable exactness through attempted depths 1–64, but is blocked by 97.85% frontier recall and 37 false accepts; no frontier-LLM superiority claim
- I3 latent-guided formal mathematical hopping: [specification](experiments/inference/i03/specification.md) · [report](experiments/inference/i03/report.md) — development stopped at the causal-control boundary; exact proof replay works, but no locked classification was authorized
- I3.1 branching mathematical reality search: [specification](experiments/inference/i03-1/specification.md) · [report](experiments/inference/i03-1/report.md) — development implementation; body-backed content-index reopening and goal-conditioned branch scoring are causal; hierarchical minimap and remaining-cost mechanisms are not yet validated

## Limit studies

- [Complete 51-experiment series summary](experiments/series-summary.md)
- L1 frozen multihop capacity: [specification](experiments/limits/l01/specification.md) · [report](experiments/limits/l01/report.md) — observed grounded formal and opaque traversal capacity through 64 hops; not arbitrary mathematics
- L2 controlled mathematical-language compilation: [specification](experiments/limits/l02/specification.md) · [report](experiments/limits/l02/report.md) — development-only
- L3 controlled mathematical ingestion and replay: [specification](experiments/limits/l03/specification.md) · [report](experiments/limits/l03/report.md) — controlled indexed 45-step evidence
- L4 unseen branching proof discovery: [specification](experiments/limits/l04/specification.md) · [report](experiments/limits/l04/report.md) — development gate failure
- L5 compiled multi-hypothesis equilibrium: [specification](experiments/limits/l05/specification.md) · [report](experiments/limits/l05/report.md) — pending authoritative execution; unclassified
- L6 causal learned-equilibrium attempt: [specification](experiments/limits/l06/specification.md) · [report](experiments/limits/l06/report.md) — development-only historical attempt
- L7 fixed-law mathematical equilibrium: [specification](experiments/limits/l07/specification.md) · [report](experiments/limits/l07/report.md) — `L7-A` controlled acyclic depth-20 pass
- [Machine-readable experiment registry](experiments/registry.json)
- [Human series index](experiments/README.md)

## Roadmap

- [Remaining gaps to a shipping LTM](roadmap/remaining-gaps.md)
- [Falsifiable experiment program](roadmap/experiment-program.md)
- [Cumulative results ledger](roadmap/results-ledger.md)
- [LTM v1 build plan](roadmap/ltm-v1-build-plan.md)

## Foundational experiment

- [CNTG-1-R2 report](experiments/cntg-1-r2/report.md)

## MICRO-LTM mechanism studies

- MICRO-LTM-1: [specification](experiments/micro-ltm/01/specification.md) · [report](experiments/micro-ltm/01/report.md)
- MICRO-LTM-2: [report](experiments/micro-ltm/02/report.md)
- MICRO-LTM-3: [specification](experiments/micro-ltm/03/specification.md) · [report](experiments/micro-ltm/03/report.md)

## Shipping-gap experiments

| Experiment | Specification | Report | Result |
| --- | --- | --- | --- |
| G1 | [Topology](experiments/gaps/g01/specification.md) | [Report](experiments/gaps/g01/report.md) | PASS |
| G2 | [Language compiler](experiments/gaps/g02/specification.md) | [Report](experiments/gaps/g02/report.md) | ENGINEERING COMPLETE — G2.14 supplied-span conversation pass plus provisional safety-gated G2.5 reasoning |
| G2.1 | [Reasoning embedder](experiments/gaps/g02-1/specification.md) | [Report](experiments/gaps/g02-1/report.md) | FAILED |
| G2.2 | [Sentence-level reasoning compiler](experiments/gaps/g02-2/specification.md) | [Report](experiments/gaps/g02-2/report.md) | FAILED — frozen representation insufficient |
| G2.3 | [Hierarchical sentence-to-topology compiler](experiments/gaps/g02-3/specification.md) | [Report](experiments/gaps/g02-3/report.md) | DEVELOPMENT ONLY — NO LOCKED CLASSIFICATION |
| G2.4-r1 | [Atom-vector topology language compiler](experiments/gaps/g02-4/specification.md) | [Report](experiments/gaps/g02-4/report.md) | SENTENCE-CORE FAILURE; linker/memory phase still open |
| G2.5 | [Typed atom coordinate compiler](experiments/gaps/g02-5/specification.md) | [Report](experiments/gaps/g02-5/report.md) | ADOPTED PROVISIONAL BASELINE — measured classification remains failed |
| G2.6 | [Dual-prototype atom-pair compiler](experiments/gaps/g02-6/specification.md) | [Report](experiments/gaps/g02-6/report.md) | FAILED — joint routing kernel failure |
| G2.7 | [Frozen semantic reasoning-atom compiler](experiments/gaps/g02-7/specification.md) | [Report](experiments/gaps/g02-7/report.md) | DEVELOPMENT GATE FAILED — locked run not authorized |
| G2.8 | [Versioned golden-atom topology compiler](experiments/gaps/g02-8/specification.md) | [Report](experiments/gaps/g02-8/report.md) | DEVELOPMENT GATE FAILED — topology kernel failure; locked run not authorized |
| G2.9 | [Post-attention golden-query compiler](experiments/gaps/g02-9/specification.md) | [Report](experiments/gaps/g02-9/report.md) | DEVELOPMENT GATE FAILED — comparator kernel failure; locked run not authorized |
| G2.10 | [Behavioral topology coordinate compiler](experiments/gaps/g02-10/specification.md) | [Report](experiments/gaps/g02-10/report.md) | DEVELOPMENT GATE FAILED — behavioral coordinate is separable but learned reconstruction coverage is insufficient; locked run not authorized |
| G2.11 | [Atomic attention-to-Mumbrane compiler](experiments/gaps/g02-11/specification.md) | [Report](experiments/gaps/g02-11/report.md) | `G2.11-B` — latest r3 kernel precision `0.9357`, safe coverage `0.7025`; extraction phase stopped |
| G2.12 | [Factorized atomic operator–role compiler](experiments/gaps/g02-12/specification.md) | [Report](experiments/gaps/g02-12/report.md) | `G2.12-B` — r3 gold-span kernel precision `0.5979`, safe coverage `0.6783`, severe accepted errors `1,158`; fail-fast stop |
| G2.13 | [Conversational Mumbrane compiler](experiments/gaps/g02-13/specification.md) | [Report](experiments/gaps/g02-13/report.md) | `G2.13-B` — act F1 `0.9992`, accepted precision `0.9425`, reference accuracy `0.9167`, 115 incorrect accepted predictions; fail-fast stop |
| G2.14 | [Margin-gated conversational compiler](experiments/gaps/g02-14/specification.md) | [Report](experiments/gaps/g02-14/report.md) | `G2.14-A` — supplied-span pass; accepted precision `1.0000`, safe coverage `0.9998`, zero incorrect accepted predictions |
| G3 | [Addressing](experiments/gaps/g03/specification.md) | [Report](experiments/gaps/g03/report.md) | PASS |
| G4 | [Active frontier](experiments/gaps/g04/specification.md) | [Report](experiments/gaps/g04/report.md) | PASS |
| G5 | [Coverage certificate](experiments/gaps/g05/specification.md) | [Report](experiments/gaps/g05/report.md) | PASS |
| G6 | [Relation engine](experiments/gaps/g06/specification.md) | [Report](experiments/gaps/g06/report.md) | PASS |
| G7 | [Structured optimizer](experiments/gaps/g07/specification.md) | [Report](experiments/gaps/g07/report.md) | PASS |
| G8 | [Memory-bounded batching](experiments/gaps/g08/specification.md) | [Report](experiments/gaps/g08/report.md) | PASS |
| G9 | [Independent verifier](experiments/gaps/g09/specification.md) | [Report](experiments/gaps/g09/report.md) | PASS |
| G10 | [Verified decoder](experiments/gaps/g10/specification.md) | [Report](experiments/gaps/g10/report.md) | PASS VIA G10.1; ORIGINAL RUN MODEL-LIMITED |
| G10.1 | [Strict FieldIR surface realization](experiments/gaps/g10-1/specification.md) | [Report](experiments/gaps/g10-1/report.md) | PASS |
| G11 | [Memory lifecycle](experiments/gaps/g11/specification.md) | [Report](experiments/gaps/g11/report.md) | PASS |
| G12 | [Persistent storage](experiments/gaps/g12/specification.md) | [Report](experiments/gaps/g12/report.md) | PASS |
| G13 | [1M-to-100M scale](experiments/gaps/g13/specification.md) | [Report](experiments/gaps/g13/report.md) | PASS (controlled) |
| G14 | [Unified benchmark](experiments/gaps/g14/specification.md) | [Report](experiments/gaps/g14/report.md) | CONTROLLED PASS / PRODUCT NOT READY |

## Integration validation

| Experiment | Specification | Report | Result |
| --- | --- | --- | --- |
| LTM-I1 | [Canonical FieldIR v2 integration](experiments/integration/i01/specification.md) | [Report](experiments/integration/i01/report.md) | `LTM-I1-A` — canonical representation path passes; G2.5 handoff remains diagnostic |

## Conventions

- [Repository layout and future experiment convention](conventions/repository-layout.md)
