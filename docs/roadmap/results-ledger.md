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
| G2 | Natural-language topology compiler | **FAILED** | `G2-B` | Blocks integrated G3; an isolated G3 test may use gold-validated topology |
| G2.1 | Frozen reasoning embedding kernel | **FAILED** | `G2.1-C / G2.1-R-NOT-DEMONSTRATED` | Frozen MiniLM representation is inadequate; test an end-to-end trained reasoning encoder |
| G3 | Prompt-to-topology addressing | **PASS** | `G3-A` | G4 is authorized over gold-validated topology; integrated use remains blocked on G2 |
| G4 | Prompt-conditioned active frontier | **PASS** | `G4-A` | G5 is authorized over the controlled gold topology; integrated use remains blocked on G2 |
| G5 | Coverage certificate and widening | **PASS** | `G5-A` | G6 is authorized over the controlled certified frontier; integrated use remains blocked on G2 |
| G6 | General typed relation engine | **PASS** | `G6-A` | G7 is authorized over the controlled typed relation engine |
| G7 | Structured latent optimizer | **PASS** | `G7-A` | G8 is authorized over the controlled G6 hard boundary |
| G8 | Memory-bounded batching | Not run | — | Awaiting stable field execution |
| G9 | Independent production verifier | Not run | — | G1 tested only the schema-level verifier contract |
| G10 | Conversational decoder | Not run | — | Awaiting verified result bundles |
| G11 | Conversation-memory lifecycle | Not run | — | Awaiting compiler and verifier integration |
| G12 | Persistent storage and incremental compilation | Not run | — | G1 tested only small SQLite persistence |
| G13 | 1M-to-100M context scaling | Not run | — | Blocked on correctness and coverage |
| G14 | Unified benchmark program | Not run | — | Blocked on integrated components |
| G15 | Product serving and isolation | Not run | — | Final operational gate |
| R1 | Pure latent-equilibrium research | Current registered experiment not run | — | Prior MICRO-LTM evidence remains insufficient |

Progress through the shipping-gap program:

```text
6 of 15 shipping gap experiments passed
9 of 15 shipping gap experiments remain; 2 compiler experiments have produced definitive failed results
```

This count does not imply that every gap has equal difficulty or risk.

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

## 12. Next experiment decision

G8 is the next authorized isolated experiment. It must determine whether the
now-correct controlled field execution can be batched and memory-bounded
without changing a verified result.

The product dependency remains a revised G2 compiler, preferably an end-to-end
trained reasoning encoder with calibrated abstention. G2 and G2.1 still block
integrated prompt-to-field execution from raw language.

## 13. Ledger update rules

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
