# LTM Gap Experiment Results

## 1. Purpose

This is the cumulative result ledger for the falsifiable experiments defined in
[Simple Falsifiable Experiments for the Remaining LTM Gaps](experiment-program.md).

It records completed results, failed attempts, authorized next steps and the
exact limits of every conclusion. A gap is marked `PASS` only when every
mandatory gate in its registered experiment passes. Planned work and historical
evidence cannot be promoted into a gap pass.

## 2. Current status

| ID | Component | Status | Classification | Next consequence |
| --- | --- | --- | --- | --- |
| G1 | Executable conversational topology | **PASS** | `G1-A` | G2 is authorized |
| G2 | Natural-language topology compiler | **ENGINEERING COMPLETE — MODULAR/BOUNDED** | `G2.14 CONVERSATION PASS + G2.5 PROVISIONAL REASONING` | Build the controlled pipeline; raw segmentation and general reasoning compilation remain future modules behind the Mumbrane/G1 boundary |
| G2.1 | Frozen reasoning embedding kernel | **FAILED** | `G2.1-C / G2.1-R-NOT-DEMONSTRATED` | Frozen MiniLM representation is inadequate; test an end-to-end trained reasoning encoder |
| G2.2 | Sentence-level reasoning compiler | **FAILED** | `G2.2-C-FROZEN-REPRESENTATION-INSUFFICIENT / G2.2-H-NOT-DEMONSTRATED` | See G2.2 report; historical G2/G2.1 remain unchanged |
| G2.3 | Hierarchical sentence-to-topology compiler | Development only | No locked classification | Corrected evaluator audit retained; no authorization decision |
| G2.4-r1 | Atom-vector topology language compiler (sentence-core) | **G2.4-B — atom grounding or role-binding failure** | Accepted exact precision 24.65%; safe coverage 21.91%; all-case exactness 17.53%; relation accuracy 40.66%; 0 invalid G1 insertions | Locked 4,000-case sentence-core run. The unimplemented memory-match and cross-sentence linker portions remain open, so this is not an authorization to replace G2.3. |
| G2.5 | Typed atom coordinate compiler and latent-field handoff | **ADOPTED PROVISIONAL BASELINE** | Measured classification remains `G2.5-C — REPRESENTATION KERNEL FAILURE` | Project-owner engineering waiver: continue the modular full-pipeline build using G2.5's typed atom/FieldIR architecture. The locked evidence remains 81.75% exact recovery with 199 reversal false accepts, so this adoption is not an experimental pass and requires strict validation, abstention and later component replacement. |
| G2.6 | G1-constrained dual-prototype atom-pair compiler | **FAILED** | `G2.6-B — JOINT ROUTING KERNEL FAILURE` | Clean 3,600-case development kernel: operator macro F1 84.37%, named-role exactness 84.37%, complete exactness 84.37%, safe coverage 84.37%. Safety remained exact: 0 reversal false accepts, 0 invalid G1 insertions, 100% G1/FieldIR validity, and 100% polarity, modality, scope and disposition. Fail-fast stopped before locked generation, span extraction, identity and document composition. |
| G2.7 | Frozen semantic reasoning-atom coordinate compiler | **DEVELOPMENT GATE FAILED** | `G2.7-B — FROZEN REASONING-COORDINATE KERNEL FAILURE` | Clean 3,600-case development kernel using a byte-frozen MiniLM and a 309,546-parameter learned topology kernel: safe coverage 10.83%, accepted exact precision 18.01%, all-case exactness 28.64%, operator macro F1 12.22%, named-role exactness 10.83%, and disposition accuracy 68.08%. It used 1,200 optimization steps and 895.5 MB peak RSS. A prior cue-matching prototype was discarded as invalid for semantic compilation. The fail-fast gate refused freeze, locked evaluation, extraction, identity, and document composition. |
| G2.8 | Versioned golden-atom structured topology compiler | **DEVELOPMENT GATE FAILED** | `G2.8-B — TOPOLOGY KERNEL FAILURE` | Split-disjoint 7,200-case held-out gold-content kernel after 700 steps: accepted exact precision 58.76%, safe coverage 48.26%, all-case exactness 48.61%, operator macro F1 49.77%, named-role exactness 48.26%, disposition accuracy 75.71%. Safety plumbing held: 0 accepted reversal/polarity errors, 0 invalid G1 insertions, and 100% FieldIR/G1 round trips. The developmental kernel missed every accuracy/coverage gate, so freeze, locked evaluation, extraction, identity, migration, and G3–G9 integration were refused. |
| G2.9 | Post-attention golden-query topology compiler | **DEVELOPMENT GATE FAILED** | `G2.9-B — POST-ATTENTION GOLDEN-COMPARATOR FAILURE` | Completed 1,200-step development kernel: accepted precision 55.66%, safe coverage 52.40%, operator macro F1 55.11%, named-role exactness 52.40%, and operator recall@3 35.21%. Safety plumbing held with 0 accepted reversal/polarity errors, 0 invalid G1 insertions, and 100% G1/FieldIR round trips. Freeze and locked evaluation were refused. |
| G2.10 | Behavioral topology coordinate compiler | **DEVELOPMENT GATE FAILED** | `G2.10-B — BEHAVIORAL COMPILER DEVELOPMENT FAILURE` | The nine behavioral cells were mathematically separable (minimum pairwise RMS `0.095758`), and all accepted outputs passed G1, FieldIR and numeric-field validation. The 1,200-step supplied-atom development run reached 100% accepted precision but only 27.78% safe coverage, 27.78% cell/role/port accuracy and 42.22% all-case agreement. No reversal false accepts or invalid insertions occurred. The fail-fast rule refused freeze and locked evaluation. |
| G3 | Prompt-to-topology addressing | **PASS** | `G3-A` | Available to the safety-gated G2.5 integration pipeline |
| G4 | Prompt-conditioned active frontier | **PASS** | `G4-A` | Available to the safety-gated G2.5 integration pipeline |
| G5 | Coverage certificate and widening | **PASS** | `G5-A` | G6 is authorized over the controlled certified frontier |
| G6 | General typed relation engine | **PASS** | `G6-A` | G7 is authorized over the controlled typed relation engine |
| G7 | Structured latent optimizer | **PASS** | `G7-A` | G8 is authorized over the controlled G6 hard boundary |
| G8 | Memory-bounded batching | **PASS** | `G8-A` | G9 is authorized over the controlled batched G6/G7 field |
| G9 | Independent result verifier | **PASS** | `G9-A` | G10 is authorized on controlled verified bundles |
| G10 | Conversational decoder | **PASS VIA G10.1** | `G10.1-S-A — STRICT SURFACE REALIZATION PASS` | Strict structured-meaning-to-language decoder gap is closed; the original `G10-T-B` run remains a historical failed attempt |
| G10.1 | Strict FieldIR surface realization | **PASS** | `G10.1-S-A` | Frozen compact LM ranks validator-safe realizations; closes G10 at the strict language-decoder boundary |
| G11 | Conversation-memory lifecycle | **PASS** | `G11-A` | G12 is authorized on structured controlled inputs |
| G12 | Persistent storage and incremental compilation | **PASS** | `G12-A` | G13 is authorized on controlled topology storage |
| G13 | 1M-to-100M context scaling | **PASS** | `G13-A` | G14 is authorized on structured controlled inputs |
| G14 | Unified benchmark program | **CONTROLLED PASS / PRODUCT NOT READY** | `G14-C-A / G14-P-NOT-READY` | Proceed with the safety-gated G2.5 pipeline; unrestricted raw-language reliability and fluency remain product limitations |
| G15 | Product serving and isolation | Not run | — | Final operational gate |
| R1 | Pure latent-equilibrium research | Current registered experiment not run | — | Prior MICRO-LTM evidence remains insufficient |

Progress through the shipping-gap program:

```text
13 of 15 shipping gap experiments passed on their registered controlled boundaries
1 additional gap, G2, is closed by an explicit provisional engineering decision
1 of 15 shipping gap experiments remains: G15 has not run
```

This count does not imply that every gap has equal difficulty or risk.

### Current architecture foundation

The [LTM v1 foundation audit](../audits/2026-08-05-ltm-v1-foundation-audit.md)
adopts the hybrid numeric FieldIR v2 direction: vectors provide routing and
continuous geometry, while exact sparse G1 topology, context and provenance
remain authoritative. This is an architecture foundation decision, not a new
gap pass and not a reclassification of G2.5.

The implementation audit is complete: `LTM-V1-F-A — FOUNDATION READY`. The
canonical `src/ltm/` package, adapters, fixed-width numeric codec, source
archive boundary, documentation map and audit command are present; 153
repository tests, Ruff, compilation, diff checks and the repository audit pass.
The result authorizes the modular LTM build and G15 planning while preserving
all historical experiment classifications.

### Engineering adoption decision for G2

On `2026-08-05`, the project owner marked G2 engineering-complete using G2.5 as
the provisional compiler architecture, combined with strict downstream
validation, coverage checks, atomic insertion and abstention. This authorizes
the modular end-to-end pipeline using G2.5's typed content atoms, exact sparse
G1 bindings and continuous FieldIR handoff.

It does **not** rewrite the G2.5 measurements or mechanical classification.
G2.5 recovered `81.75%` of the locked gold-atom topologies against its `99%`
gate and produced `199` directional reversal false accepts. Therefore the
ledger distinguishes:

- **engineering completion:** yes, G2 is closed for current pipeline work and
  G2.5 is the selected baseline;
- **experimental pass:** no, the registered G2/G2.5 reliability gates were not
  met;
- **integration policy:** compiler output must remain validator-gated, atomic,
  provenance-preserving and able to abstain;
- **future architecture:** language grounding, operator routing, role binding,
  identity resolution and decoding remain replaceable modules.

On `2026-08-06`, G2.14 strengthened this engineering closure. The frozen G2.13
model plus typed bounded candidate resolution and a monotonic margin gate passed
the supplied-span conversational boundary with `1.0000` accepted precision,
`0.9998` safe coverage and zero incorrect accepted predictions. The current G2
architecture is therefore two-lane: G2.14 for supplied-span conversation and
safety-gated G2.5 for provisional reasoning. This does not convert G2.5 into an
experimental pass or claim raw semantic segmentation.

## 3. G1 — Executable conversational topology

### Registration

- Experiment: [G1 specification](../experiments/gaps/g01/specification.md)
- Detailed gates: [G1 section in the gap experiment program](experiment-program.md#4-g1--executable-conversational-topology-schema)
- Authoritative report: [G1 locked report](../experiments/gaps/g01/report.md)
- Date completed: `2026-08-03`
- Implementation: `src/topology_g1/`
- Configuration: `configs/topology-g1.json`
- Tests: `tests/topology_g1/`

### Question

> Can the initial registered LTM conversational topology represent, store,
> execute, verify, migrate and replay its reasoning structures without changing
> their meaning?

### Experimental boundary

G1 used:

- Python standard library only;
- SQLite persistence;
- 160 deterministic fixtures;
- 80 development fixtures;
- one fresh 80-fixture locked suite;
- no language model;
- no semantic embedding;
- no latent optimizer;
- no natural-language decoder;
- no network access.

The locked suite contained 32 valid executable fixtures and 48 invalid or
adversarial fixtures.

### Locked results

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Valid fixture acceptance | `32/32` | `100%` | PASS |
| Invalid fixture rejection | `48/48` | `100%` | PASS |
| Canonical serialization round trips | `32/32` | `100%` | PASS |
| Exact operator checks | `32/32` | `100%` | PASS |
| Valid independent-verifier checks | `32/32` | `100%` | PASS |
| Fabricated derivation rejections | `32/32` | `100%` | PASS |
| Version-1-to-version-2 migrations | `16/16` | `100%` | PASS |
| Registered field contracts | Passed | All | PASS |
| SQLite reopen hash | Identical | Identical | PASS |
| Operation replay hash | Identical | Identical | PASS |
| Reverse insertion-order hash | Identical | Identical | PASS |
| Complete locked runtime | `0.1261 s` | `<10 s` | PASS |
| Peak RSS | `28.16 MB` | `<200 MB` | PASS |
| Full repository tests after implementation | `20 passed` | All | PASS |
| Ruff, compilation and diff checks | Passed | All | PASS |

### Mechanical classification

**`G1-A — PASS`**

Every mandatory G1 gate passed. G2, natural-language topology compilation, is
authorized.

### What G1 demonstrated

For the registered controlled ontology:

- node and relation structures have deterministic machine-readable contracts;
- relation direction and named argument roles survive serialization and
  persistence;
- scope, temporal applicability and provenance remain attached;
- implications, conjunctions, requirements, exclusions, equality, temporal
  relations, supersession, evidence messages, preferences, references, scopes,
  hypotheses, uncertainty and derivation links have executable contracts;
- satisfied and violated field cases produce their registered residual or typed
  obligation behavior;
- fabricated derivations can be rejected independently;
- saving, reopening and replaying the operation log reconstructs the same
  topology;
- physical insertion order does not alter the canonical topology hash;
- the registered minimal migration preserves semantic identity and provenance.

### What G1 did not demonstrate

G1 did not test:

- whether natural language can be compiled into the topology accurately;
- whether the ontology covers every kind of human or domain reasoning;
- prompt-to-topology address accuracy;
- active-frontier completeness;
- whole-field coverage certificates;
- differentiable latent reasoning;
- decoder faithfulness or naturalness;
- large persistent stores;
- 100-million-token-equivalent context;
- frontier-model benchmark performance.

Therefore the result supports this bounded statement:

> The registered initial conversational topology is coherent and executable
> enough to serve as the target representation for the G2 compiler experiment.

It does not support calling the complete LTM architecture solved.

### Development incident retained for transparency

An initial preflight run exposed three invalid-type fixtures that were accepted
because three relation roles were typed too broadly. The relation registry was
tightened, the failed local artifacts were retained in an ignored preflight
workspace, and the authoritative result was produced against a distinct fresh
locked fixture namespace. The final suite achieved `48/48` invalid rejection.

## 4. R1 historical evidence — not a current gap result

Earlier MICRO-LTM experiments investigated whether a differentiable latent
state itself could carry unseen conclusions. These experiments predate the
current R1 specification and do not count as an R1 pass.

The strict MICRO-LTM-3 result found:

- exact symbolic structured field: `100%`;
- differentiable optimizer plus query-agnostic compression: `49.86%`;
- failed causal state-swap behavior;
- classification: `MICRO-LTM-3-E`.

The earlier closure-only compression diagnostic reached `99.17%`, but exact
closure had already performed the reasoning. It therefore demonstrated
compression of a solved state, not latent-equilibrium reasoning.

Current R1 status remains:

> **Not passed. Pure latent equilibrium is not authorized as the shipping
> correctness path.**

The hybrid product continues to use exact typed relation propagation for
correctness and structured optimization for soft reconciliation.

Supporting reports:

- [MICRO-LTM-1 report](../experiments/micro-ltm/01/report.md)
- [MICRO-LTM-2 report](../experiments/micro-ltm/02/report.md)
- [MICRO-LTM-3 report](../experiments/micro-ltm/03/report.md)

## 5. G2 — Natural-language topology compiler

### Registration and locked result

- Experiment: [G2 specification](../experiments/gaps/g02/specification.md)
- Authoritative report: [G2 locked report](../experiments/gaps/g02/report.md)
- Date completed: `2026-08-03`
- Model: pinned local `Qwen2.5-0.5B-Instruct-mlx-4bit`, greedy MLX inference
- Evaluation: one frozen, offline 300-case locked suite

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Claim tuple F1 | `0.000` | `>=0.95` | FAIL |
| Relation direction accuracy | `0.000` | `>=0.98` | FAIL |
| Named-role exact match | `0.000` | `>=0.98` | FAIL |
| Coreference / correction / scope / temporal accuracy | `0.000` | `>=0.98/0.99` | FAIL |
| Correct disposition | `0.207` | `>=0.98` | FAIL |
| Exact topology agreement | `0.000` | `>=0.98` | FAIL |
| Direct valid IR | `0.153` | `>=0.90` | FAIL |
| Final valid IR after one repair | `0.153` | `>=0.98` | FAIL |
| Quarantine recall | `0.767` | `>=0.95` | FAIL |
| Silent invalid topology insertions | `0` | `0` | PASS |
| Locked runtime | `437.62 s` | `<600 s` | PASS |
| Peak RSS | `1153.63 MB` | `<8 GB` | PASS |

### Mechanical classification

**`G2-B — MODEL INSUFFICIENT`**

The pinned 0.5B Qwen model loaded, produced deterministic output and stayed
inside the compact compute envelope. However, it did not reliably express the
registered typed topology: it often produced an underspecified fact-like JSON
object in place of a directed relation, or failed strict validation. One model
repair did not materially improve valid IR. Strict validation prevented all
silent invalid topology insertions.

This is a decisive failure of the selected compiler boundary, not of G1 or of
typed topology compilation as a general idea. Integrated G3 remains blocked.
An isolated G3 component experiment may proceed with gold-validated topology.
The compiler still requires a stronger structured-extraction model or a
different trained reasoning encoder before end-to-end integration.

## 6. G2.1 — Frozen reasoning embedding kernel

### Registration and locked result

- Experiment: [G2.1 specification](../experiments/gaps/g02-1/specification.md)
- Authoritative report: [G2.1 locked report](../experiments/gaps/g02-1/report.md)
- Date completed: `2026-08-03`
- Encoder: frozen local `all-MiniLM-L6-v2`, 384-dimensional output
- Dataset: 2,000 training, 500 development and 1,000 locked cases

### Locked measurements

| Method | Relation macro F1 | Direction | Exact roles | G1 topology agreement |
| --- | ---: | ---: | ---: | ---: |
| Linear multi-head probe | `0.843` | `0.725` | `0.808` | `0.808` |
| Nonlinear 128D projection | `0.450` | `0.716` | `0.417` | `0.367` |

The selected operational candidate was the linear probe. It stayed well within
the compute limits (`0.07 s` classified inference; `727.41 MB` peak RSS), but
missed the required relation, direction, role, scope and topology thresholds.
The nonlinear projection did not establish a specialized reasoning-geometry
advantage.

Additional locked measurements for the selected linear probe were relation
accuracy `0.875`, scope accuracy `0.900`, disposition accuracy `1.000`,
ambiguity recall `1.000`, quarantine recall `1.000`, and zero silent invalid
topology insertions. Its exact G1 topology agreement was 17.2 absolute
percentage points below the `0.98` gate.

### Mechanical classification

**`G2.1-C — FROZEN REPRESENTATION INSUFFICIENT / G2.1-R-NOT-DEMONSTRATED`**

The frozen semantic representation held enough information for useful
controlled relation classification, but not enough for executable-topology
reliability. A small nonlinear projection did not repair this. The next
intervention is an end-to-end trained reasoning encoder, not additional
prompting or frozen-head tuning.

## 7. G3 — Prompt-to-topology addressing

### Registration and locked result

- Experiment: [G3 specification](../experiments/gaps/g03/specification.md)
- Authoritative report: [G3 locked report](../experiments/gaps/g03/report.md)
- Date completed: `2026-08-03`
- Boundary: gold-validated topology and evaluator-provided structured prompt
  signatures; this is an isolated addressing result.
- Locked topology: 10,000 addresses; locked suite: 400 prompts.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Starting-entity recall | `1.000` | `>=0.99` | PASS |
| Predicate recall | `1.000` | `>=0.98` | PASS |
| Scope / temporal / episode accuracy | `1.000` | `>=0.98/0.99` | PASS |
| Ambiguity recall / unsupported abstention | `1.000` | `>=0.99` | PASS |
| Incorrect confident resolutions | `0` | `0` | PASS |
| Median / p95 candidate set | `2 / 3` | `<=8 / <=24` | PASS |
| Median inspected fraction | `0.0002` | `<0.005` | PASS |
| Complete scans | `0` | `0` | PASS |
| Locked runtime / peak RSS | `3.18 s / 735 MB` | `<600 s / <2 GB` | PASS |

### Mechanical classification

**`G3-A — PASS`**

The resolver entered all required starting topology regions in this controlled
gold-topology setting while inspecting a bounded fraction of the store. It did
not make an unsafe confident selection. This authorizes G4 using predicted G3
addresses over gold-validated topology.

In plain terms, the topology-minimap mechanism worked: once the prompt's
entities, predicate, scope, time, and conversation references were already
structured correctly, typed indexes identified where request execution should
begin without searching the complete topology. The median request retained two
candidates and inspected approximately `0.02%` of topology postings.

This result does not repair G2 or G2.1. The natural-language compiler remains
an upstream product blocker; the supplementary G3-Text parser is only a
controlled-language diagnostic.

## 8. G4 — Prompt-conditioned active frontier

### Registration and locked result

- Experiment: [G4 specification](../experiments/gaps/g04/specification.md)
- Authoritative report: [G4 locked report](../experiments/gaps/g04/report.md)
- Date completed: `2026-08-03`
- Boundary: gold topology and gold starting addresses for G4-Core; controlled
  G3 signatures form a separate integration diagnostic.
- Locked topology: 100,000 factors; locked suite: 300 cases across six typed
  traversal families and proof depths one through six.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Required-factor recall | `1.000` | `>=0.99` | PASS |
| Exhaustive conclusion agreement | `1.000` | `>=0.98` | PASS |
| Hard-constraint / exact-exception recall | `1.000 / 1.000` | `1.00 / 1.00` | PASS |
| Session / bridge / conflict recall | `1.000 / 1.000 / 1.000` | `>=0.99` | PASS |
| Proof-path / decisive-provenance recall | `1.000 / 1.000` | `>=0.95 / >=0.99` | PASS |
| False resolved conclusions | `0` | `0` | PASS |
| Median / p95 opened fraction | `0.00007 / 0.00009` | `<0.01 / <0.02` | PASS |
| Budget exhaustion / complete scans | `0 / 0` | `<0.01 / 0` | PASS |
| Locked runtime / peak RSS | `56.55 s / 1,135 MB` | `<600 s / <2 GB` | PASS |

Controls were materially weaker in several important ways: frozen-MiniLM
semantic top-k recovered `0.352` of required factors and agreed with exhaustive
conclusions on `0.280`; forward-only traversal recovered `0.408` and agreed on
`0.533`; removing correction or safety indexes reduced conclusion agreement to
`0.833`. The reported locked runtime includes the semantic control.

The untyped-BFS control tied the typed frontier (`1.000` required-factor recall
and conclusion agreement) on this synthetic low-degree topology. Therefore G4
demonstrates that the typed frontier is correct and sparse on its registered
distribution, but does **not** yet demonstrate a typed-traversal advantage over
generic BFS. A future stress distribution with dense irrelevant branches is
needed for that comparative claim.

The actual frozen G3 resolver, supplied with controlled structured signatures,
reached starting-address agreement `1.000` with zero unsafe resolutions. This
diagnostic does not repair the failed language compiler.

### Mechanical classification

**`G4-A — PASS`**

Starting from correct addresses, typed backward and forward traversal recovered
the registered answer-changing factors and reproduced exhaustive conclusions
while opening a tiny fraction of the synthetic 100,000-factor topology. This
authorizes G5 in the same controlled gold-topology setting.

G4 does not establish that unopened regions are harmless. It records open
obligations and omissions but does not certify them or widen the frontier. It
also does not repair G2/G2.1, test latent optimization, or establish
100-million-token reliability.

## 9. G5 — Certified coverage, distant influence, and automatic widening

### Registration and locked result

- Experiment: [G5 specification](../experiments/gaps/g05/specification.md)
- Authoritative report: [G5 locked report](../experiments/gaps/g05/report.md)
- Date completed: `2026-08-03`
- Boundary: gold topology and starting addresses; deterministic region summaries
  and an additive 32-dimensional quadratic field only.
- Locked topology: 100,000 factors in 634 immutable regions; 240 base/twin
  pairs, or 480 requests.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Answer-changing omission detection | `1.000` | `1.00` | PASS |
| Material latent influence detection or incorporation | `1.000` | `>=0.99` | PASS |
| Hard / exception / correction / conflict / bridge recall | `1.000 / 1.000 / 1.000 / 1.000 / 1.000` | `1.00 / >=0.99` | PASS |
| Exhaustive conclusion agreement | `1.000` | `>=0.98` | PASS |
| False certified conclusions | `0` | `0` | PASS |
| Certified-bound containment | `1.000` | `1.00` | PASS |
| Maximum certified state error | `0.001406` | `<=0.02` | PASS |
| Mandatory abstention recall / unnecessary abstention | `1.000 / 0.000` | `1.00 / <0.01` | PASS |
| Harmless unnecessary widening | `0.000` | `<0.10` | PASS |
| Median / p95 opened fraction | `0.00080 / 0.00082` | `<0.005 / <0.015` | PASS |
| Complete scans / summary soundness violations | `0 / 0` | `0 / 0` | PASS |
| Locked runtime / peak RSS | `1.96 s / 515 MB` | `<600 s / <2 GB` | PASS |

The fixed G4 frontier reached only `0.744` final conclusion agreement on the
base/twin distribution. Forcing certification without widening produced `150`
false certificates; removing the exact safety channel produced `40`. The full
G5 path widened or used a summary when needed, abstained for each deliberately
uncertifiable region, and produced no false certificate.

### Mechanical classification

**`G5-A — PASS`**

For the registered typed topology and additive quadratic field law, a sparse
frontier can account for distant regions with conservative summaries, incorporate
small distant forces, open exact regions when their possible effect is material,
and abstain when no valid bound exists. This authorizes G6 in the same
controlled setting.

G5 does not show that arbitrary nonlinear fields have compact safe summaries,
does not repair G2/G2.1 natural-language compilation, and does not establish
full end-to-end or 100-million-token reliability.

## 10. G6 — General typed relation engine

- Experiment: [G6 specification](../experiments/gaps/g06/specification.md)
- Authoritative report: [G6 locked report](../experiments/gaps/g06/report.md)
- Date completed: `2026-08-03`
- Locked suite: `280` controlled typed programs across 14 relation families.

**`G6-A — PASS`**

The compact fixed-point engine matched the generator-owned oracle on atomic
and depth-one-to-six programs, generated replayable proofs, preserved the
registered hard/soft boundary, and completed within the compute gate. This
authorizes G7 on the controlled relation-engine boundary.

G6 uses perfect typed topology. It does not repair language compilation,
validate latent optimization, or establish general real-world reasoning.

## 11. G7 — Structured latent optimizer and soft reconciliation

### Registration and locked result

- Experiment: [G7 specification](../experiments/gaps/g07/specification.md)
- Authoritative report: [G7 locked report](../experiments/gaps/g07/report.md)
- Date completed: `2026-08-03`
- Locked suite: `240` deterministic cases across six soft-reconciliation
  families; hard truth was supplied by the frozen G6 relation engine.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| G6 exact conclusions preserved | `1.000` | `1.00` | PASS |
| Hard-constraint violations | `0` | `0` | PASS |
| Soft decision / conflict / reference accuracy | `1.000 / 1.000 / 1.000` | `>=.90 / >=.95 / >=.95` | PASS |
| Ambiguity / preference / uncertainty accuracy | `1.000 / 1.000 / 1.000` | `>=.95` | PASS |
| Improvement over neutral state | `100.0` points | `>=10` | PASS |
| Accepted energy increases | `0` | `0` | PASS |
| Oracle state / disposition agreement | `1.000 / 1.000` | `>=.99 / >=.99` | PASS |
| Numerical failures / provenance failures | `0 / 0` | `0 / 0` | PASS |
| Repeated result agreement | `1.000` | `1.00` | PASS |
| Locked runtime / peak RSS | `0.371 s / 44.84 MB` | `<60 s / <512 MB` | PASS |

### Mechanical classification

**`G7-A — PASS`**

On this registered controlled distribution, a projected structured optimizer
reconciled soft signals after G6 reasoning while preserving every hard G6
conclusion. It correctly retained conflict/reference alternatives inside the
decision margin, expressed uncertainty as abstention, and matched an
independently constructed quadratic oracle. The neutral, no-branch,
untyped-vector and weighted-average controls reached at most `0.500`
decision accuracy; neutral state reached `0.000`.

This does not establish that optimization derives logical truth, that the same
energy scales to unbounded numbers of branches, or that the system understands
raw language. G7 has a fixed typed input and uses G6 as its hard correctness
authority. It authorizes G8 only on this controlled boundary.

## 12. G8 — Memory-bounded batching and order-independent reduction

### Registration and locked result

- Experiment: [G8 specification](../experiments/gaps/g08/specification.md)
- Authoritative report: [G8 locked report](../experiments/gaps/g08/report.md)
- Date completed: `2026-08-03`
- Locked suite: `96` deterministic requests. Each selected `16` physical
  blocks of `256` factors from a `65,536`-factor field.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Hard conclusion and full hard state agreement | `1.000 / 1.000` | `1.00` | PASS |
| Branch/disposition/provenance agreement | `1.000` | `1.00` | PASS |
| Soft-state L2 / minimum cosine | `0 / 1.000000` | `<=1e-8 / >=.999999` | PASS |
| Maximum energy / residual error | `1.11e-16 / 0` | `<=1e-10` | PASS |
| Cross-order semantic agreement | `1.000` | `1.00` | PASS |
| Residency-cap violations / full materializations | `0 / 0` | `0 / 0` | PASS |
| Last-block / local-average / sequential control failures | `98.96% / 100% / 100%` | `>=20%` | PASS |
| Repeated-result agreement | `1.000` | `1.00` | PASS |
| Locked runtime / peak RSS | `7.51 s / 61.53 MB` | `<60 s / <512 MB` | PASS |

### Mechanical classification

**`G8-A — PASS`**

For this controlled G6/G7-compatible field, the system delivered the same
selected blocks at widths one, four and sixteen and in ascending, descending
and seeded-random orders. It then canonically combined exact hard factors and
soft quadratic contributions before one global update. Every one of the nine
executions per request matched the all-selected-block reference. By contrast,
averaging locally optimized states, keeping only the last block, and updating
sequentially failed frequently.

This establishes a narrow but important implementation rule: physical batching
can be a memory-management detail only when the logical union and soft
reduction are globally canonical. It does not prove generic asynchronous
optimization, missing-region coverage, language ingestion, decoder quality, or
100M-context performance.

## 13. Next experiment decision

## 13. G9 — Independent result verifier

### Registration and locked result

- Experiment: [G9 specification](../experiments/gaps/g09/specification.md)
- Authoritative report: [G9 locked report](../experiments/gaps/g09/report.md)
- Date completed: `2026-08-03`
- Locked suite: `48` valid typed result bundles plus `48` plausible
  single-corruption twins across twelve adversarial categories.

### Locked measurements

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Valid structural handling and status agreement | `1.000 / 1.000` | `1.00` | PASS |
| Corrupted-bundle rejection / false accepts | `1.000 / 0` | `1.00 / 0` | PASS |
| Primary rejection-code agreement | `1.000` | `1.00` | PASS |
| Proof, source/provenance and scope/time checks | `1.000 / 1.000 / 1.000` | `1.00` | PASS |
| Hard factor, conflict and coverage checks | `1.000 / 1.000 / 1.000` | `1.00` | PASS |
| Assistant-self-evidence and soft-state checks | `1.000 / 1.000` | `1.00` | PASS |
| Deterministic replay / independent imports | `1.000 / yes` | `1.00 / yes` | PASS |
| Locked runtime / peak RSS | `0.008 s / 26.50 MB` | `<10 s / <256 MB` | PASS |

### Mechanical classification

**`G9-A — PASS`**

On its self-contained controlled distribution, the G9 verifier independently
replayed hard proofs and the registered soft objective and rejected every
plausible corruption before authorizing a result. Hash-only, self-claimed-valid
and energy-threshold controls falsely accepted `91.67%`, `100%` and `100%` of
corrupted bundles respectively. Disabling coverage checks accepted every
coverage-corruption twin.

This proves a bounded result-authority mechanism, not integration with the
separate G5–G8 workspaces, unrestricted language, decoder safety, production
security or large-context operation.

## 14. G10 — Compact verified conversational decoder

### Historical locked result

- Experiment: [G10 specification](../experiments/gaps/g10/specification.md)
- Authoritative report: [G10 locked report](../experiments/gaps/g10/report.md)
- Locked suite: `64` verified opaque fictional bundles; controls: `32` no-state
  and `32` state-only generations; validator attacks: `64`.

| Measurement | Result |
| --- | ---: |
| adversarial cases | 64 |
| authorized claim precision | 1 |
| authorized claim recall | 1 |
| conflict disclosure | 1 |
| correct final disposition | 1 |
| direct generation acceptance | 0.28125 |
| fallback control acceptance | 1 |
| ood abstention | 1 |
| opposite polarity final claims | 0 |
| ordinary fallback rate | 0.67857143 |
| preference adherence | 1 |
| raw unsupported claims | 7 |
| rejected text exposed | 0 |
| repair recovery rate | 0 |
| unsupported final claims | 0 |
| validator adversarial rejection | 1 |

### Mechanical classification

**`G10-T-B — SAFE BUT MODEL-LIMITED`**

This is a bounded technical decoder result with deterministic authorization,
one repair attempt and verified fallback. Human naturalness, raw-language
compilation, native latent prefixes and production conversation memory remain
unmeasured. This failed attempt is retained for provenance; it is superseded for
the strict language-decoder gap decision by G10.1 below.

## 14.1 G10.1 — Strict FieldIR surface realization

### Locked result

- Experiment: [G10.1 specification](../experiments/gaps/g10-1/specification.md)
- Authoritative report: [G10.1 report](../experiments/gaps/g10-1/report.md)
- Locked suite: `256` fresh bundles; frozen FLAN-T5-small ranks only
  deterministic validator-safe candidates.

| Measurement | Result |
| --- | ---: |
| candidate validator acceptance | `1.00` |
| authorized claim precision / recall | `1.00 / 1.00` |
| correct disposition | `1.00` |
| unsupported final claims | `0` |
| rejected final text | `0` |
| realization fallback | `0.00` |
| runtime / peak RSS | `10.316 s / 704.0 MB` |

### Mechanical classification

**`G10.1-S-A — STRICT SURFACE REALIZATION PASS`**

G10.1 is strictly a language decoder boundary. It does not perform reasoning,
retrieval, content selection, conflict resolution or latent-state inference.
At this registered boundary, G10 is therefore **closed as PASS via G10.1**.
This conclusion requires the latent field to expose a complete verified
structured answer meaning representation; it does not claim direct decoding of
opaque latent vectors or unrestricted conversational generation.

## 15. G11 — Safe conversation-memory lifecycle

### Locked result

- Experiment: [G11 specification](../experiments/gaps/g11/specification.md)
- Authoritative report: [G11 locked report](../experiments/gaps/g11/report.md)
- Locked suite: `32` twelve-turn conversations (`384` turns), evaluated against
  an independent full-history oracle.

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Context, reference, correction and preference agreement | `1 / 1 / 1 / 1` | `1.00` | PASS |
| Scoped conflict, provenance, episode reopening and restart | `1 / 1 / 1 / 1` | `1.00` | PASS |
| Assistant self-contamination / cross-session leak | `0 / 0` | `0 / 0` | PASS |
| Targeted-deletion / post-clear residual influence | `0 / 0` | `0 / 0` | PASS |
| Base hash preservation / transcript scans | `1 / 0` | `1 / 0` | PASS |
| p95 rows read | `3` | `<=24` | PASS |
| Deterministic replay | `1` | `1.00` | PASS |
| Locked runtime / peak RSS | `0.4383 s / 26.50 MB` | `<30 s / <256 MB` | PASS |

### Mechanical classification

**`G11-A — PASS`**

On this controlled structured distribution, the overlay preserved lifecycle
state and provenance without mutating base knowledge. It did not treat prior
assistant messages as independent evidence; the unsafe control demonstrated
that promotion would contaminate retrieval. This authorizes isolated G12
persistence work only, not raw-language conversation, decoder quality,
integration with the failed G2 ingestion boundary, unrestricted decoding or
100M-context reliability.

## 16. G12 — Persistent storage and incremental compilation

### Locked result

- Experiment: [G12 specification](../experiments/gaps/g12/specification.md)
- Authoritative report: [G12 locked report](../experiments/gaps/g12/report.md)
- Locked store: `1,000,000` compact topology objects across `1,000`
  independently checksummed memory-mapped regions.

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Deterministic initial compile / clean replay | `1 / 1` | `1.00 / 1.00` | PASS |
| Local region and ancestor-summary updates | `1 / 1` | `1.00 / 1.00` | PASS |
| Unrelated blocks rewritten / deleted descendants | `0 / 0` | `0 / 0` | PASS |
| Provenance, reopen and crash atomicity | `1 / 1 / 1` | `1.00` | PASS |
| Accepted corruptions / mixed recoveries | `0 / 0` | `0 / 0` | PASS |
| Full scans / p95 block reads | `0 / 1` | `0 / <=1` | PASS |
| Store size / runtime / peak RSS | `223.16 MB / 15.156 s / 31.91 MB` | `<1 GB / <180 s / <512 MB` | PASS |

### Mechanical classification

**`G12-A — PASS`**

On the registered synthetic million-object topology, content-addressed binary
blocks, source-to-object lineage and atomic SQLite version publication supported
local insertions, corrections, deletion, reopening and crash recovery without
rewriting unrelated regions. This authorizes G13 controlled scaling work. It
does not establish raw-language compilation, semantic quality, decoder quality
or 100M-token-equivalent reliability.

## 17. Next experiment decision

The controlled benchmark path may continue to G14. The product dependency
remains a revised G2 compiler, preferably an end-to-end trained reasoning
encoder with calibrated abstention. G2 and G2.1 still block integrated
prompt-to-field execution from raw language.

## 17. G13 — 1M-to-100M context scaling

### Registration

- Experiment: [G13 specification](../experiments/gaps/g13/specification.md)
- Authoritative report: [G13 locked report](../experiments/gaps/g13/report.md)
- Authoritative workspace: `workspaces/topology-g13-r1/` (ignored)
- Locked source: `100,000,000` actual `uint32` token IDs.
- Locked compiled field: `25,000,000` fixed-width factors in `97,657` logical
  blocks and three physical S4 layouts.

### Locked result

| Measurement | Result | Gate | Outcome |
| --- | ---: | --- | --- |
| Required-factor recall | `1.0000` | `>=0.99` | PASS |
| Cross-scale conclusion agreement | `1.0000` | `>=0.98` | PASS |
| Independent hard-result replay | `4,000 / 4,000` | `1.00` | PASS |
| S4 identity/reverse/affine agreement | `1.0000` | `1.00` | PASS |
| Candidate full scans | `0` | `0` | PASS |
| Maximum opened factor fraction | `0.00000032` | `<0.001` | PASS |
| S4 warm p95 core latency | `0.106 ms` | `<3,000 ms` | PASS |
| Peak RSS / locked runtime | `146.84 MB / 3.99 s` | `<20 GB / <4 h` | PASS |
| True uncached mode / network calls | `F_NOCACHE / 0` | required / `0` | PASS |
| Deterministic verification | identical | `1.00` | PASS |

### Mechanical classification

**`G13-A — PASS`**

This run demonstrated that the registered controlled core contracts can retain
their typed conclusion while sparsely accessing a real disk-backed 100M-token,
25M-factor field. It used structured requests, actual fixed-width token and
factor storage, bounded block reads, summary-triggered widening, G6/G7 adapter
execution, batch-order checks, independent hard replay and session checks.

The result is deliberately narrower than a product claim. All query-relevant
factors occur in the common S1 prefix, while the extra S2–S4 field is
addressable persistent distractor content. It therefore does not demonstrate
raw-language ingestion over 100M tokens, arbitrary semantic far-field
influence, natural response quality, or integrated conversational reliability.
G2/G2.1 ingestion remains empirically below its registered gates; G2 is now
engineering-closed through the safety-gated G2.5 baseline. G10 is closed only at G10.1's strict
structured-meaning-to-language boundary; natural response quality remains
unmeasured.

## 18. G14 — Unified controlled benchmark and product gate

### Locked result

- Experiment: [G14 specification](../experiments/gaps/g14/specification.md)
- Authoritative report: [G14 locked report](../experiments/gaps/g14/report.md)
- Authoritative workspace: `workspaces/topology-g14-r5/` (ignored).
- Controlled suite: `50` locked twelve-turn conversations and `300`
  evaluator-separated structured requests.
- Public catalog: `500` LongMemEval records and `1,986` LoCoMo QA records,
  never exposed with their answers or evidence to the runtime process.

| Measurement | Result | Outcome |
| --- | ---: | --- |
| Controlled G3–G7/G9 conclusion accuracy | `1.000` | PASS |
| Required-factor recall | `1.000` | PASS |
| Bounded retrieval-control accuracy | `0.683` | Full-system advantage: `31.7` points |
| Bootstrap interval, full minus retrieval | `[0.263, 0.370]` | Positive lower bound |
| No exact propagation / no session / no coverage | `0.317 / 0.933 / 0.850` | Component-sensitive controls fail as expected |
| G9 fabricated hard-state rejection | `1.000` | PASS |
| Deterministic semantic replay / network calls | `1.000 / 0` | PASS |
| Peak RSS | `4,784.83 MB` | Below `20 GB` ceiling |
| Raw public benchmark input support | `0 / 2,486` | Not ready by design |

### Mechanical classification

**`G14-C-A — PASS`** for the controlled structured-composition boundary, and
**`G14-P-NOT-READY`** for a normal raw-language conversational product.

The controlled verdict shows that, once public structured facts and rules are
already correctly available, the selected G3 addressing, G4 traversal, G5
coverage widening, G6 hard execution, G7 reconciliation, and G9 verification
compose without an evaluator-label path. It does not repair G2/G2.1 ingestion,
does not establish unrestricted fluency beyond G10.1's strict surface-realizer
pass, and does not measure LongMemEval or LoCoMo answer quality. G8, G11, G12 and G13
remain valid upstream component evidence but were not re-executed as a single
per-request G14 path.

## 19. Ledger update rules

When a new experiment completes:

1. preserve its registration and frozen gates;
2. record development and locked suites separately;
3. retain failed attempts and counterexamples;
4. include exact metrics, runtime, memory and artifact hashes where available;
5. state the mechanical classification;
6. state what is newly authorized;
7. state what remains unproven;
8. update the summary table without rewriting older outcomes;
9. never mark a gap passed from an informal demo or development-only result;
10. link the authoritative detailed report.

## 20. G2.2 — Sentence-level reasoning compiler

- Experiment: [G2.2 specification](../experiments/gaps/g02-2/specification.md)
- Authoritative report: [G2.2 locked report](../experiments/gaps/g02-2/report.md)
- Mechanical classification: **`G2.2-C-FROZEN-REPRESENTATION-INSUFFICIENT / G2.2-H-NOT-DEMONSTRATED`**
- Accepted sentence exact precision / safe coverage: `0.0000` / `0.0000`.
- Link exact precision / safe coverage: `0.1020` / `0.1360`.
- Locked runtime / peak RSS: `58.958 s` / `967.7 MB`.

This is a controlled G1-ontology compiler result only. It does not revise the historical G2 or G2.1 result or establish raw-language product readiness.

## 21. LTM-R1 — Vector-native field representation compatibility audit

- Specification: [LTM-R1](../experiments/representation/r01/specification.md)
- Authoritative report: [LTM-R1 report](../experiments/representation/r01/report.md)
- Authoritative workspace: `workspaces/topology-field-r1/` (ignored)

### Measured result

| Measurement | Result | Outcome |
| --- | ---: | --- |
| G1 locked fixtures | `80` (`32` valid, `48` invalid) | PASS |
| G1 semantic agreement | `1.00` | PASS |
| Active execution without source text | `1.00` | PASS |
| Source-text mutation invariance | `1.00` | PASS |
| Role/context/vector mutation detection | `1.00` | PASS |
| G3–G14 deterministic semantic replays | `12 / 12` | PASS |
| G2.5 G1/FieldIR round trip | `1.00` | COMPATIBLE |
| Numeric active bytes / legacy serialized bytes | `26,688 / 69,544` | PASS |
| Existing/candidate factor-record width | `64 / 64 bytes` | PASS |
| Audit runtime / peak RSS | `32.872 s / 307.78 MB` | PASS |

### Mechanical classification

**`LTM-R1-A — REPRESENTATION HOLDS`**

The audit establishes that active FieldIR text can be replaced by numeric atom,
operator, exact role-incidence, context, provenance and vector-reference records
without changing the tested G1–G14 semantics or widening the existing fixed-width
field record. Text remains external at explicit ingestion, provenance-audit and
surface-realization boundaries; it is not active reasoning state.

This is a representation-isomorphism and compatibility result, not a rewrite of
every historical package. It does not improve G2.5's measured compiler accuracy,
change its historical failure classification, or establish unrestricted-language
understanding. G2.5 remains the adopted safety-gated compiler baseline.

## 22. LTM-I1 — Canonical FieldIR v2 integration validation

- Specification: [LTM-I1](../experiments/integration/i01/specification.md)
- Authoritative report: [LTM-I1 report](../experiments/integration/i01/report.md)
- Authoritative workspace: `workspaces/ltm-i1-r7/` (ignored; earlier r1–r6 workspaces retained as attempts).

### Locked result

| Measurement | Result | Outcome |
| --- | ---: | --- |
| Representation cases | `512` | PASS |
| G1 → FieldIR v2 → G1 semantic agreement | `1.000` | PASS |
| In-memory → packed/reloaded agreement | `1.000` | PASS |
| G3 address / G4 frontier / G5 coverage agreement | `1.000 / 1.000 / 1.000` | PASS |
| G6 hard conclusion/proof agreement | `1.000` | PASS |
| G7 optimizer/oracle agreement | `1.000` | PASS |
| G9 verification agreement | `1.000` | PASS |
| G10.1 strict realization agreement | `1.000` | PASS |
| Deterministic semantic replay | `1.000` | PASS |
| Runtime / peak RSS | `34.524 s / 1,126.2 MB` | PASS |
| Network calls / locked overwrite | `0 / refused by contract` | PASS |

### G2.5 conditional handoff

The frozen supplied-atom G2.5 diagnostic emitted `239` handoffs from `360`
cases; `192` were correct and all `192` converted to FieldIR v2 (`1.000`
conditional conversion precision). This is explicitly not a raw-language
compilation result and does not change G2.5's historical `G2.5-C` classification.

The registered attack suite contained `128` cases (eight per attack family),
and all `128` were rejected with their declared primary code.

### Mechanical classification

**`LTM-I1-A — CANONICAL INTEGRATION PASS`** for the confirmed/evaluator-generated
numeric representation boundary. This authorizes a compiled-topology rerun once
G2's compiler boundary is improved. It does not establish raw-language
compilation, learned semantic geometry, free-form decoder naturalness,
ontology completeness, production serving, or G15.

## 23. LTM-R2 — Universal Mumbrane representation and configurable-topology audit

- Specification: [LTM-R2](../experiments/representation/r02/specification.md)
- Authoritative report: [LTM-R2 report](../experiments/representation/r02/report.md)
- Authoritative workspace: `workspaces/ltm-r2-r3/` (ignored; `r1` is preliminary and `r2` is retained because the final report renderer changed before this fresh frozen run)

### Locked result

| Measurement | Result | Outcome |
| --- | ---: | --- |
| Semantic bodies / profile executions | `1,024 / 4,096` | PASS |
| Reasoning / planning / evidence / conversation oracle agreement | `1.000 / 1.000 / 1.000 / 1.000` | PASS |
| Packed-field reload equality | `1.000` | PASS |
| Tier-1 / Tier-2 / Tier-3 switch behavior | `1.000 / 1.000 / 1.000` | PASS |
| Real G1 → FieldIR v2 adapter panel | `128` cases, `1.000` agreement through G3–G7, G9 and G10.1 | PASS |
| G11–G14 compatibility boundary | Exact G1 projection `1.000`; historical lifecycle suites not rerun here | BOUNDED |
| Registered corruption rejection | `320 / 320` | PASS |
| Deterministic semantic replay | `1.000` | PASS |
| Active packed bytes / paired FieldIR v2 bytes | `0.139` ratio on representative direct adapter case | PASS |
| Runtime / peak RSS | `1.497 s / 184.7 MB` | PASS |
| Network calls | `0` | PASS |

### Mechanical classification

**`LTM-R2-A — UNIVERSAL MUMBRANE PASS`**

LTM-R2 establishes a canonical future compiler target: all evaluated semantic
items can use one Mumbrane unit/port/coordinate schema, while a signed
topology profile selects the field purpose and soft dynamics without changing
the underlying exact substrate. Tiered configuration changes are explicit:
dynamics-only changes reuse the field; structural changes select and migrate
affected units; missing semantics require source recompilation.

This is a representation and configuration result on evaluator-owned semantic
bodies. The representation audit directly executed G1–G10.1 adapters; G11–G14
remain supported here by exact projection plus their existing separate locked
evidence, not by a fresh lifecycle rerun. It does not close unrestricted G2
language compilation, establish a complete ontology, or upgrade the historical
G2.5 evidence.

## 24. G2.11 — Atomic attention-to-Mumbrane compiler

- Specification: [G2.11 specification](../experiments/gaps/g02-11/specification.md)
- Authoritative report: [G2.11 report](../experiments/gaps/g02-11/report.md)
- Authoritative workspace: `workspaces/topology-g2-11-r3/` (ignored; `r1` and `r2` retained as failed attempts)

### Locked kernel result

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Kernel cases | `3,600` | `3,600` | PASS |
| Accepted precision | `0.9357` | `>=0.98` | FAIL |
| Safe coverage | `0.7025` | `>=0.95` | FAIL |
| All-case exactness | `0.7025` | `>=0.90` | FAIL |
| Severe accepted relation errors | `149` | `0` | FAIL |
| Basis reconstruction | `1.000` | `1.000` | PASS |
| MiniLM deterministic preflight | `1.000` | `1.000` | PASS |

### Mechanical classification

**`G2.11-B — ATOMIC BASIS / KERNEL FAILURE`**

The G1-derived 181-feature atomic basis is deterministic and lossless. Adding an
explicit G1-derived operator coordinate improved precision from `0.8270` in `r2`
to `0.9357` in `r3`, but coverage fell to `0.7025` and 149 incorrect relations
were still accepted. The kernel therefore cannot proceed to span extraction or
document composition. G2.5 and LTM-R2 historical classifications remain
unchanged.

## 25. G2.12 — Factorized atomic operator–role compiler

- Specification: [G2.12 specification](../experiments/gaps/g02-12/specification.md)
- Authoritative report: [G2.12 report](../experiments/gaps/g02-12/report.md)
- Authoritative workspace: `workspaces/topology-g2-12-r3/` (ignored; r1 and r2 are retained as prior attempts)

### Locked kernel result

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Kernel cases | `3,600` | `3,600` | PASS |
| Accepted predictions | `2,880` | — | measured |
| Accepted exact predictions | `1,722` | — | measured |
| Accepted precision | `0.5979` | `>=0.95` | FAIL |
| Safe coverage | `0.6783` | `>=0.90` | FAIL |
| All-case topology exactness | `0.6783` | `>=0.90` | FAIL |
| Operator macro-F1 | `0.8439` | `>=0.95` | FAIL |
| Named-role/direction exactness | `0.5979` | `>=0.95 / >=0.995` | FAIL |
| Disposition accuracy | `0.9078` | `>=0.95` | FAIL |
| Severe accepted errors | `1,158` | `0` | FAIL |

### Mechanical classification

**`G2.12-B — FACTORIZED KERNEL FAILURE`**

G2.12 improved operator identification relative to its earlier attempts, but
the learned named-role and direction decisions were still unsafe. The frozen
gold-span kernel failed before raw span extraction, identity, document
composition, or downstream handoff. G2.5 remains the provisional compiler;
this result does not alter historical G2.5, G2.11, or LTM-R2 classifications.

## 26. G2.13 — Conversational Mumbrane compiler

- Specification: [G2.13 specification](../experiments/gaps/g02-13/specification.md)
- Authoritative report: [G2.13 report](../experiments/gaps/g02-13/report.md)
- Authoritative workspace: `workspaces/topology-g2-13-r1/` (ignored)

### Gold-span kernel result

| Measurement | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Kernel cases | `2,400` | `2,400` | PASS |
| Accepted precision | `0.9425` | `>=0.97` | FAIL |
| Safe coverage | `0.9146` | `>=0.95` | FAIL |
| Discourse-act macro-F1 | `0.9992` | `>=0.97` | PASS |
| Memory-action macro-F1 | `1.0000` | `>=0.97` | PASS |
| Reference accuracy | `0.9167` | `>=0.99` | FAIL |
| Context accuracy | `0.9996` | `>=0.97` | PASS |
| Disposition accuracy | `0.9167` | `>=0.97` | FAIL |
| Incorrect accepted predictions | `115` | `0` | FAIL |

### Mechanical classification

**`G2.13-B — CONVERSATIONAL KERNEL FAILURE`**

G2.13 confirms that conversational act and memory-action classification is much
more tractable than the full reasoning compiler. Reference resolution,
disposition, and safe abstention remain below the locked gates. The fail-fast
boundary stopped raw extraction, identity linking, lifecycle execution, and
downstream handoff. G11 remains the structured lifecycle authority and G2.5
remains the provisional compiler.

## 27. G2.14 — Margin-gated conversational compiler

- Specification: [G2.14 specification](../experiments/gaps/g02-14/specification.md)
- Authoritative report: [G2.14 report](../experiments/gaps/g02-14/report.md)
- Authoritative workspace: `workspaces/topology-g2-14-r3/` (ignored)

### Locked result

**`G2.14-A — SUPPLIED-SPAN CONVERSATIONAL COMPILER PASS`**

The frozen G2.13 one-pass predictions were evaluated on 4,800 fresh locked
cases with supplied semantic spans and at most 16 public candidates. The
G2.4-style typed resolver and monotonic confidence/margin gate accepted 4,005
cases with `1.0000` precision and `0` incorrect accepted predictions. Safe
coverage and all-case exactness were `0.9998`; ambiguity recall, unique-target
precision, candidate recall@16, and context accuracy were all `1.0000`. The
ungated frozen compiler accepted 4,006 cases and retained one false accept.

The conditional independent 400-conversation G11 panel was exact for context,
references, preferences, corrections, scope, conflict, provenance,
restart/replay, deletion and clearing, with zero cross-session leakage and
p95 three rows read. This closes only supplied-span conversational routing.
G2.5 remains the provisional reasoning compiler; raw span extraction and deep
reasoning remain outside the G2.14 claim.

## I1 — Relation-free Mumbrane latent inference

- Specification: [I1 specification](../experiments/inference/i01/specification.md)
- Authoritative report: [I1 report](../experiments/inference/i01/report.md)
- Authoritative workspace: `workspaces/ltm-inference-i1-r5/` (ignored)

### Locked result

**`I1-B — BODY REPRESENTATION FAILURE`**

The compact 15,457-parameter energy kernel was trained without relation or role
labels and evaluated on 8,000 locked queries over 50,000 bodies. Development
stored-body one-step exactness was `0.4648` (gate `>=0.90`), accepted precision
was `0.1312`, and depth-2/3/5/6 composition exactness was `0.0000`. Calibration
therefore abstained on every locked query: locked safe coverage was `0.0000`,
with no incorrect accepted operations. Energy increases were `0`, candidate
frontier recall was `1.00`, runtime was `5.98s`, and the integrity replay matched
16/16 predictions with no relation labels, closure, network calls or factual
commits. I1 does not authorize an I2 raw-data compiler; the field law must first
 be redesigned for stored-body completion and compositional state transfer.

## I2 — Multiscale minimap latent dynamic inference

- Specification: [I2 specification](../experiments/inference/i02/specification.md)
- Measured report: [I2 report](../experiments/inference/i02/report.md)
- Authoritative workspace: `workspaces/ltm-inference-i2-r1/` (ignored)

### Result

**`I2-C — LOCAL TRANSITION FAILURE`**

The supplied-Mumbrane multiscale implementation built the hierarchical field
successfully (48,000 training bodies, 24,000 development bodies and 100,000
locked bodies), but the learned anonymous transition kernel failed the first
development boundary. Across all 6,000 development queries it produced zero
accepted exact candidates, safe coverage `0.0000`, answerable exactness
`0.0000`, one-step exactness `0.0000`, and required-body frontier recall
`0.0005`. The checkpoint had 73,985 trainable parameters and runtime emitted
no relation labels, closure, candidate IDs or factual operations.

The locked continuation was not authorized after this fail-fast result; the
partial diagnostic was stopped before prediction shards were emitted. I2
therefore does not establish multiscale composition or reject the universal
Mumbrane representation. It identifies local anonymous transition learning
and frontier value estimation as the next engineering boundary. I1 and all
historical G2 results remain unchanged.

## I2.1 — Aligned transition and minimap navigation

- Specification: [I2.1 specification](../experiments/inference/i02-1/specification.md)
- Measured report: [I2.1 report](../experiments/inference/i02-1/report.md)
- Authoritative workspace: `workspaces/ltm-inference-i21-r2/` (ignored)

### Locked result

**`I2.1-A — ALIGNED TERMINAL-COMPLETION PASS`**

I2.1 repaired I2's runtime coordinate mismatch. The original learned-query to
raw-body score had same-body recall@64 `0.0020` in the 100,000-body locked
field; the shared learned coordinate score was `1.0000`. On 4,000 public
initial-Mumbrane prompts, terminal completion through hidden paths of one to
64 observed bodies achieved answerable exactness `1.0000`, accepted precision
`1.0000`, safe coverage `0.9230`, all-case exactness `1.0000`, zero incorrect
accepted candidates, zero certified energy increases and required-body frontier
recall `1.0000`.

Removing the decisive body or using the wrong scope produced abstention;
shuffling body membership reduced answerable exactness to `0.0000`; and a
no-movement control had only `0.0117` all-case upper-bound accuracy. This
supports aligned, source-backed terminal completion with bounded identity
addressing. It does not establish arbitrary question answering, unstored-rule
inference, global learned minimap descent, raw-language compilation or a
replacement for G6/G9.

## I2.2 — Global content-addressed minimap navigation

- Specification: [I2.2 specification](../experiments/inference/i02-2/specification.md)
- Measured report: [I2.2 report](../experiments/inference/i02-2/report.md)
- Authoritative workspace: `workspaces/ltm-inference-i22-r1/` (ignored)

### Locked result

**`I2.2-A — GLOBAL CONTENT-ADDRESSED NAVIGATION PASS`**

I2.2 removes I2.1's identity-to-leaf route. It builds a complete binary
minimap over frozen learned source vectors, and the moved outcome vector alone
selects the next leaf. On a 100,000-body locked field and 4,000 public
initial-Mumbrane prompts, next-body recall@64, tree membership accounting,
answerable terminal exactness through depths 1–64, accepted precision,
all-case exactness and cross-leaf transition rate were all `1.0000` except
development cross-leaf rate `0.9941`. Safe coverage was `0.9230`, with the
remaining terminal-start queries correctly returning `unknown`; there were no
incorrect accepted candidates or energy increases.

The no-movement control had only `0.0117` all-case upper-bound accuracy, a
deterministically wrong tree had `0.0000` answerable exactness, and removing
the selected leaf forced abstention. This supports bounded global
content-addressed terminal completion, not arbitrary goal selection,
unstored-rule inference, raw-language compilation, factual authorization or a
replacement for G6/G9.

### Post-hoc evidence-boundary correction (2026-08-06)

The frozen I2.2 report and its measured metrics remain historical artifacts,
but the later source audit found that it is a deterministic observed-successor
walk rather than the full I2 energy/minimap mechanism: it selects an exact
source-vector match in one global vector-tree leaf and replaces the state with
the selected body’s observed outcome vector. It does not implement learned
cell summaries, a gradient-optimized field law, or evaluator/runtime process
separation. Its regular successor-chain generator also exposes a numerical
state coordinate. Consequently, `I2.2-A` is evidence for the narrow traversal
code path only; it must not be used as evidence that the original I2 theory is
proved. See the [I2 mechanism audit](../audits/2026-08-06-i2-dynamic-field-mechanism-audit.md).

## I2.3 — Hermetic summary-dependent field inference

- Specification: [I2.3 specification](../experiments/inference/i02-3/specification.md)
- Development report: [I2.3 report](../experiments/inference/i02-3/report.md)
- Latest development workspace: `workspaces/ltm-inference-i23-r7/` (ignored)

### Development result — no locked classification

The learned-coordinate minimap is now causally active: zeroing cell summaries
changes `91.9%` of outputs. On 2,000 development prompts over 8,000 opaque
bodies, accepted precision is `0.9799`, safe coverage `0.9015`, all-case
exactness `0.9785`, answerable exactness `0.9767`, and required-body frontier
recall `0.9785`. There are 37 incorrect accepted candidates and zero accepted
energy increases. Calibration sufficient to remove every observed false accept
reduces safe coverage to `0.6855`.

The development gate failed and no frozen or locked result is authorized. The
tested maximum of 64 refers to supplied semantic-body transitions; it is not a
measurement of raw-language 64-hop reasoning and has not been paired against a
frontier LLM. I2.3 remains unclassified pending a richer bounded minimap,
perfect certified retrieval, causal graph controls, and a fresh locked run.

## I3 — Latent-guided formal mathematical hopping

- Specification: [I3 specification](../experiments/inference/i03/specification.md)
- Development report: [I3 report](../experiments/inference/i03/report.md)
- Latest development workspace: `workspaces/ltm-inference-i3-r1/` (ignored)

### Development result — stopped before freeze

I3 validated its exact formal rewrite kernel and independent proof replay on
the constrained development fragment: accepted proof precision and replay were
`1.0000`, incorrect accepted proofs were `0`, safe coverage was `0.9517`, and
required-axiom frontier recall was `0.9986`. It did not validate its proposed
latent mechanism. Removing the energy constraint increased control success
from `0.9767` to `0.9967`, and removing the goal reduced it only to `0.9567`.

No locked classification was issued. I3 is evidence for exact verified local
rewrite selection, not goal-conditioned latent proof-state movement.

## I3.1 — Branching mathematical reality search

- Specification: [I3.1 specification](../experiments/inference/i03-1/specification.md)
- Development report: [I3.1 report](../experiments/inference/i03-1/report.md)
- Latest development workspace: `workspaces/ltm-inference-i3-1-r13/` (ignored)

### Development result — no locked classification

On 600 held-out paired-goal branching problems covering generated depths 2–16,
the body-backed content-index method reached `1.0000` all-case exactness,
`1.0000` accepted-proof precision, zero incorrect accepted proofs, `1.0000`
independent replay, and `1.0000` required-body frontier recall. The causal
control panel measured: full `1.0000`, no goal `0.5050`, no learned action
scorer `0.0000`, fixed frontier `0.0000`, no remaining-cost head `1.0000`, and
hierarchical-minimap-only `0.0050`.

These controls support bounded content-addressed reopening, goal-conditioned
learned action ranking, exact proof construction, and independent replay. They
do not validate hierarchical minimap retrieval or the remaining-cost head. The
public staged corpus also exposes route-position cues, so the separate 17–64
hop result (`0.9600` exactness on 200 generated cases) is only a traversal
diagnostic. Freeze correctly remains blocked pending an opaque detour corpus,
causal global guidance, and a fresh locked run.

## L1 — Frozen multihop reasoning limit characterization

- Specification: [L1 specification](../experiments/limits/l01/specification.md)
- Measured report: [L1 report](../experiments/limits/l01/report.md)
- Authoritative workspace: `workspaces/ltm-limit-l1-r1/` (ignored)

**`L1-A — CURRENT CAPACITY CHARACTERIZED`**

The frozen I3.1 `r13` checkpoint completed all 20 cases at every depth from 1
through 64 in both its grounded formal-rewrite and opaque traversal panels.
Accepted-proof precision and independent replay were `1.0000`, incorrect
accepted proofs were zero, and unsupported or over-budget depth-65/96/128
cases abstained. The point-estimate formal and traversal D90/D95 values are 64.

This is observed grounded capacity, not arbitrary 64-hop mathematics. The
formal panel uses source-backed additive-zero and multiplicative-one
transformations, and 20/20 cases yield a Wilson lower bound of approximately
`0.8389`. Each frontier read is capped at 64 bodies, but cumulative distinct
reads can exceed that through reopening. L2 has a development baseline. L3
now has a separate controlled 50,000-body compiled-reality result; its narrow
claim and mechanism limitations are recorded below.

## L3 — Compiled 45-hop mathematical reality

The [L3 specification](../experiments/limits/l03/specification.md) defines an
exact controlled prose/notation compiler feeding the frozen I3.1 lane.

**`L3-A — COMPILED 45-HOP MATHEMATICAL REALITY PASS`**

The locked `r2` run reused byte-identical inputs created by incomplete `r1`
and evaluated a 50,000-body standard-mathematics field. The compiler achieved
`1.000` body precision, body coverage, AST equality, question precision and
question coverage. It solved and independently replayed `256 / 256` grounded
shortest-45-hop proofs and `128 / 128` eight-schema ring 45-step proof paths, with
zero invalid accepted proofs, `1.000` required-body recall and `1.000` safe
coverage in both answerable panels. The independent evaluator certified exactly
45 as the shortest path in every grounded case. All 128 unknown, missing-body,
wrong-reality and unregistered-body attacks failed closed.

The correct scope is **controlled exact compilation plus indexed verified
composition**. Dynamic reopening matters (`0.667` under a fixed initial
frontier) and the content index matters (`0.000` without it). On this mostly
linear corpus, removing the learned scorer, goal anchor or remaining-cost head
did not reduce success. The planned three-family mixed-axiom diagnostic was not
exercised. L3 therefore does not establish learned branching proof discovery,
raw-language mathematics, broad mixed-family composition, or arbitrary theorem
proving.

## L4 — Unseen branching mathematical proof discovery

The [L4 specification](../experiments/limits/l04/specification.md) removed L3's
query-specific route structure. It used supplied formal ASTs, a signed reusable
39-schema bank, exact proposal enumeration, a compact learned proposal/value
kernel and independent proof replay.

**`L4-C — LOCAL PROPOSAL FAILURE (DEVELOPMENT STOP)`**

The 12-case stratified pre-lock panel retained `1.0000` accepted-proof precision but
reached only `0.3333` answerable success and `0.2738` correct-proposal
recall@16. Depth 2–4 succeeded at `1.0000`; depth 5–8 and 9–12 were `0.0000`
on the stratified control sample, as were branching-16 and branching-32.
Full-minus-no-scorer and full-minus-no-goal gains were both `0.0`; removing the
value head improved success by `0.125`.

L4 therefore stopped before freeze, locked generation and the 17–45 stress
panel. This is negative evidence about learned proposal selection, not exact
verification: returned proofs replayed and weak cases abstained. L3's indexed
45-hop result remains valid, while learned goal-sensitive branching discovery
remains open.

## L5 — Compiled multi-hypothesis latent field equilibrium

The [L5 specification](../experiments/limits/l05/specification.md) defines a
compiled multi-hypothesis equilibrium experiment. Its implementation and
[tracked report](../experiments/limits/l05/report.md) exist, but the report
remains pending and no authoritative execution has produced a measured
classification. L5 is therefore **UNCLASSIFIED — pending authoritative
execution**. It is neither a pass nor a failure, and none of its development or
workspace-only observations authorize an architecture capability claim.

## LTM-A2 — Architecture evidence audit

The [full architecture audit](../audits/2026-08-06-ltm-architecture-viability-audit.md)
is an evidence audit rather than a new capability experiment. It keeps
compiler, representation, execution, verification and decoder claims within
their measured boundaries.

## LTM-ARCH-1.0 — Architecture lock

The normative [architecture lock](../architecture/architecture-lock-v1.md)
freezes the hybrid product direction at the `2026-08-07` evidence cutoff:
Mumbrane IR v1 is the semantic target, G1 is exact authority, FieldIR v2 is the
implemented execution bridge, G6/G7 separate hard and soft execution, and
G9/exact replay authorize results. G2.14 is the supplied-span conversation
lane; G2.5 remains provisional reasoning; I3.1/L1 remain a supplied-formula
research lane; L3 adds controlled exact compiler-to-proof evidence; L2 and G15
remain planned.

## L6 — Causal mathematical reality equilibrium

The [L6 specification](../experiments/limits/l06/specification.md) is the
next decisive boundary. Its isolated implementation currently contains the
reality/body/prompt contracts, minimap field, continuous factor activation,
source-backed smoke verifier and causal-control hooks. It has six focused tests
passing, but no authoritative locked result. The 25,000-body field, independent
high-precision equilibrium oracle, 8,000-query run and causal gates remain
pending. No L6 capability or pass is claimed.

## L7 — Fixed-law mathematical reality equilibrium

L7 supersedes L6 as the causal-equilibrium experiment without altering L6's
historical development artifacts. Its strengthened immutable `r3` run passed
as `L7-A` on 240 supplied formal prompts over a 512-body field in 27.34
seconds. It reached
100% exactness and accepted precision, zero incorrect accepted conclusions,
100% depth-20 results, 100% independent-equilibrium agreement, and all frozen
causal controls/interventions, including partial conjunction, expiry, rescope
and reality-move checks. This is controlled evidence for a fixed acyclic factor
law only; language, cyclic global optimization, minimap scaling and
unrestricted mathematics remain open.

## LTM-ARCH-1.1 — Architecture lock

The normative [architecture lock](../architecture/architecture-lock-v1.md)
now incorporates the controlled L7 result at the `2026-08-08` evidence
cutoff. It retains G6 verified exact execution and adds a separate fixed-law
lane for bounded supplied-formal acyclic fields: immutable prompt clamps,
neutral non-prompt state, synchronous source-normalized factor satisfaction,
explicit polarity/tension, candidate discovery, and independent fixed-point
plus path verification. Cyclic, scaled and 64-hop equilibrium remain open.
