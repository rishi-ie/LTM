# L5 — Compiled Multi-Hypothesis Latent Field Equilibrium

Status: implementation present; authoritative execution and measured classification pending.

Experiment identifier: `L5`

Profile revision: `ltm-equilibrium-field/1`

Compiler revision: `l5-controlled-compiler/1`

Authoritative configuration: [configs/ltm-limit-l5.json](../../../../configs/ltm-limit-l5.json)

Authoritative workspace: `workspaces/ltm-limit-l5-r1/`

Historical I3, I3.1, L1, L2, L3, and L4 artifacts remain immutable.

## 1. Question and claim boundary

L5 asks:

> Can controlled source bodies and a controlled prompt be placed in one shared
> coordinate system, then resolved through bounded multi-mode field relaxation
> so that source-normalized support, opposition, conjunction, scope, ambiguity,
> and unknown states produce independently certifiable outputs?

The intended mechanism is:

```text
controlled source items                         controlled prompt
         |                                              |
         +------ one shared semantic coordinate --------+
                                |
                   exact phase/context records
                                |
                  query-independent minimap/index
                                |
             bounded, dynamically reopened frontier
                                |
          simultaneous positive/negative latent modes
                                |
          projected energy-nonincreasing relaxation
                                |
          convergence and coverage certification
                                |
        independent source-support reconstruction
                                |
              strict authorized realization
```

L5 deliberately tests equilibrium over a compiled field, not learned sequential
proof-action selection. Its primary supplied-input suite contains one-to-sixteen
body dependencies, conjunctions, competing outcomes, signed contradictions,
scope isolation, and unsupported cases in controlled abstract and mathematical
domains.

The exact phase/context field law is deterministic. L5 trains only the shared
source/prompt coordinate and compatibility kernel. A high exact-result score is
not evidence that latent geometry caused the result unless the full system also
beats the no-learned-compatibility, fixed-state/zero-geometry, and deterministic
random-geometry controls by the frozen causal margins. This distinction is a
mandatory classification boundary, not an optional diagnostic.

Only a measured `L5-A` may support this bounded conclusion:

> For the controlled L5 source grammar and supplied compiled semantic fixtures,
> a shared coordinate compiler plus a bounded multi-mode field can recover
> source-backed candidate states, preserve supported alternatives and balanced
> contradictions, abstain when support or coverage is insufficient, and expose
> only independently certified outputs.

It does **not** establish:

- unrestricted natural-language compilation;
- arbitrary mathematical theorem proving;
- exact factual authorization from vector similarity;
- unlimited dependency depth;
- constant request cost independent of field size or query difficulty;
- unrestricted or linguistically diverse raw-text-to-final-answer evaluation;
- natural-language decoder quality;
- production persistence, serving, or replacement of G6/G9.

## 2. The three evidence tracks

L5 keeps three claim tracks separate. Their metrics must never be merged under
the label “compiler accuracy.”

| Track | Runtime input | What it measures | What it cannot establish |
|---|---|---|---|
| A — Raw controlled compiler | Controlled source or prompt text plus public context metadata | Exact controlled parsing, one-pass coordinate construction, fail-closed rejection, source/prompt coordinate alignment | Equilibrium correctness or unrestricted language |
| B — Supplied-input equilibrium | Already compiled `PublicFieldCase` fixtures | Minimap retrieval, source-normalized field dynamics, multi-mode equilibrium, verification, and strict realization | Raw compiler quality |
| C — Locked raw end to end | Raw controlled bodies and prompt compiled and atomically written into a field | The full compiler, writer, optimizer, verifier, and decoder chain on 600 controlled dependencies, unknowns, balanced contradictions, and alternatives | Unrestricted language, branching proof discovery, or broad joint-field behavior |

### 2.1 Track A — Raw controlled compiler

Track A is an independent compiler panel. It uses raw controlled strings and
separate public/gold files. The compiler receives no expected semantic keys,
alignment group, route, answer, or evaluator path.

It measures:

```text
accepted semantic precision
safe coverage
exact parsed-content agreement
shared-coordinate retrieval recall@8
incorrect accepted compilations
exactly one encoder call per item
```

### 2.2 Track B — Supplied-input equilibrium

Track B is the authoritative equilibrium panel. Its field bodies, prompt
influences, context, and deterministic 128D fixture positions are already
compiled. The evaluator-owned expected outcome is stored separately.

The fixture check named `supplied_input_contract` means only that the supplied
numeric/exact input satisfies the declared public contract. It is not raw
compiler accuracy. The two central metrics are:

```text
optimizer_conditional_on_supplied
end_to_end_from_supplied
```

The second includes the runtime optimizer, support certificates, and strict
decoder authorization, but still begins from supplied compiled fixtures.

The focused `experiment.py` harness produces these three rates with Wilson
intervals. The authoritative lifecycle persists an independently rescored
aggregate with answerable, unsupported, oracle-optimum, energy, coverage,
convergence, frontier, certificate, domain, dependency, and exact-depth metrics
in `locked-results.json`.

### 2.3 Track C — Locked raw-chain end to end

The atomic writer maps accepted compiler outputs into exact phase-0/phase-1
occurrence rows and `EquilibriumBody` records. The implemented lifecycle checks:

- compiler-to-writer round trips over a bounded development sample;
- one real two-body raw compiler → writer → optimizer → verifier development
  chain;
- that an unaccepted compiler output cannot enter the active field;
- that the writer creates no factual operation;
- a fresh 600-case locked raw panel containing 75% answerable linear chains at
  depths 1–16 and 25% unknown, balanced-conflict, and alternative cases.

Every locked raw-chain case starts with lexical controlled source strings and a
controlled prompt. Runtime compiles each item once, writes exact bodies, builds
the minimap/index, relaxes the field, reconstructs source support, and invokes
the strict decoder. Public identifiers and surface text are opaque and do not
encode family, disposition, depth, route, or terminal answer. Those fields
remain evaluator-only. Hidden scoring freezes the exact disposition,
semantic-key/polarity candidate set, and per-candidate certificate body count.

This is a real locked joint pipeline result, but its scope is narrow: the 600
cases are generated single-path chains, not the full contradiction,
alternatives, conjunction, malformed-input, or branching distribution. Track B
continues to supply the broader field-law coverage, and Track A continues to
supply the broader compiler rejection/precision panel. The report must publish
all three results rather than presenting Track C alone as unrestricted end to
end performance.

## 3. Fixed boundaries

- Local `all-MiniLM-L6-v2`; network access is disabled.
- One encoder call per raw compiler item.
- Encoder coordinates are geometry, never exact semantic authority.
- State dimension: 128.
- Maximum latent modes: 8.
- Maximum macro steps: 64.
- Inner projected updates per macro step: 4.
- Maximum bodies opened per step: 128.
- Maximum active units: 1,024.
- Maximum cumulative distinct bodies: 2,048.
- Minimap leaf size: 64 bodies.
- Minimap internal fan-out: 16.
- Maximum minimap prototypes/modes per cell: 8.
- Source mass cap: 8.0.
- CPU float32 with four PyTorch threads.
- Maximum new trainable parameters: 2,000,000.
- Maximum float32 inference weights: 8 MB.
- No network calls or factual field operations.
- Runtime receives no answers, expected dispositions, expected depth, required
  body IDs, route identifiers, proof objects, or evaluator paths.
- Stress and scale diagnostics cannot manufacture or erase the primary
  classification.

## 4. Repository, commands, and artifacts

Implementation locations:

```text
configs/ltm-limit-l5.json
src/ltm_limit_l5/
tests/ltm_limit_l5/
docs/experiments/limits/l05/
workspaces/ltm-limit-l5-r1/
```

Commands:

```bash
python -m ltm_limit_l5 model-check --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 dataset-build --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 compiler-develop --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 field-build --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 equilibrium-develop --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 calibrate --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 freeze --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 locked-suite-build --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 evaluate --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 stress-evaluate --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 scale-evaluate --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 intervene --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 controls --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 verify --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 report --workspace workspaces/ltm-limit-l5-r1
python -m ltm_limit_l5 resume --workspace workspaces/ltm-limit-l5-r1 --offline
python -m ltm_limit_l5 run-all --workspace workspaces/ltm-limit-l5-r1 --offline
```

`run-all` is fail-fast. It records only executed stages and never fabricates
later metrics after an earlier failure.

Expected workspace artifacts:

```text
model-check.json
dataset-manifest.json
compiler-development-results.json
field-results.json
development-results.json
calibration.json
selected-kernel.pt
frozen-manifest.json
locked-suite-manifest.json
locked/public/cases.jsonl
locked/evaluator-gold/gold.jsonl
locked/compiler-public/cases.jsonl
locked/compiler-evaluator-gold/gold.jsonl
locked/end-to-end-public/cases.jsonl
locked/end-to-end-evaluator-gold/gold.jsonl
locked-compiler-predictions.jsonl
locked-end-to-end-predictions.jsonl
locked-prediction-shards/
locked-runtime-access-audit.json
locked-results.json
stress-results.json
scale-results.json
intervention-results.json
controls.json
verification.json
report.json
report.md
execution-history.json
```

Completed locked predictions are immutable 256-case shards. A second locked
evaluation is refused. A source or evaluator correction after authoritative
generation requires a fresh workspace attempt rather than overwriting `r1`.

## 5. Public representation contracts

### 5.1 Field occurrences and bodies

`FieldMumbrane` is an exact occurrence record. It contains:

```text
unit and body identity
exact semantic key
vector-row reference
local and phase indexes
polarity and modality
scope, reality, and validity
stable identity and provenance
independent source key
```

`EquilibriumBody` connects one or more phase-0 occurrence IDs to one or more
phase-1 occurrence IDs. It retains base weight, authority, confidence, context,
source identity, provenance, and a deterministic body hash.

No G1 relation name, named premise/conclusion role, route index, proof depth, or
expected answer is required by the L5 runtime representation. Phase membership
and exact semantic keys are still explicit data semantics; “relation-free” does
not mean that the field is an anonymous bag of vectors.

### 5.2 Prompt field

`CompiledPromptField` contains:

- an immutable 128D anchor;
- one or more `PromptInfluenceRecord` rows;
- exact semantic keys and public context;
- compiler confidence and provenance;
- `accept`, `clarification_required`, or `quarantine` disposition;
- exactly one recorded encoder call.

The prompt is a query condition. It is not source evidence and is never written
as a factual field operation.

### 5.3 Runtime state

The optimizer exposes:

```text
MinimapCell
LatentModeState
EquilibriumStep
FrontierSnapshot
EquilibriumCandidate
SupportCertificate
FieldEquilibriumResult
```

`FieldEquilibriumResult.factual_operations` is always empty. The result is a
soft, source-backed candidate state until an independent verifier reconstructs
its support.

### 5.4 Forbidden public fields

The public fixture schema rejects these names recursively:

```text
answer_id
answer_candidates
expected_disposition
expected_depth
required_body_ids
route_identifier
proof
evaluator_path
```

Public and evaluator data are generated into separate files and consumed by
separate runtime and scoring paths.

## 6. Controlled shared-coordinate compiler

### 6.1 Accepted input forms

The implemented compiler accepts a narrow grammar.

Abstract source body:

```text
when INPUT [and INPUT ...] then OUTCOME [and OUTCOME ...]
```

Abstract prompt:

```text
given INPUT [and INPUT ...], what follows?
```

Controlled formal mathematics is parsed through the existing L3 proposition
parser into exact source and goal expressions. Open-ended math text that needs
goal discovery is rejected.

### 6.2 Exact and learned responsibilities

The parser deterministically supplies:

```text
content kind
exact input semantic keys
exact outcome semantic keys
formal expressions when present
polarity, modality, scope, reality, time, provenance, and source hash
```

The local MiniLM and learned projection supply only a normalized shared
coordinate. Each compiler item makes exactly one encoder call. The coordinate
cannot create an input, outcome, polarity, context value, provenance link, or
field body.

Low compiler confidence, malformed syntax, source/prompt form mismatch,
open-ended goal discovery, or forbidden runtime metadata produces
`clarification_required`. The compiler candidate contains no factual operation.

### 6.3 Compiler dataset

The raw compiler generator creates split-disjoint lexical atoms and paired body
and prompt forms. Invalid cases include malformed syntax, missing content, and
forbidden answer/route metadata. The public file contains only source and mode;
expected keys and alignment groups remain evaluator-only.

Configured counts:

| Split/use | Items |
|---|---:|
| Training compiler items | 48,000 |
| Development compiler items | 12,000 |
| Locked compiler items | 16,000 |

The development and locked compiler gates are independent of supplied fixture
metrics.

## 7. Atomic field writer

The writer accepts only compiler outputs with:

```text
disposition = accept
parsed complete body
nonempty inputs and outcomes
no failure code
no factual operation
unique source transaction hash
```

For each accepted source, it writes:

- exact phase-0 input occurrences;
- exact phase-1 outcome occurrences;
- one source-owned vector row;
- a context- and provenance-bound `EquilibriumBody`;
- stable identities and hashes.

The vector row is shared geometry for that source item. It cannot invent the
body boundary or exact phase membership. Any invalid source rejects the atomic
assembly. Duplicate compiled source transactions are refused.

## 8. Field, minimap, and source normalization

### 8.1 Deterministic minimap

The field is partitioned into deterministic leaf and internal cells. Each cell
stores bounded prototypes, transition summaries, positive/negative source mass,
context keys, radius, uncertainty, membership count, and a summary hash.

The minimap is built from field bodies, not from a query-specific answer list.
It may summarize member geometry and source mass. It may not store transitive
closure, a route, expected answer, or evaluator labels.

In the primary supplied-fixture suite, each case owns a small generated field.
This isolates equilibrium correctness but is not evidence of retrieval from one
large universal store. The scale panel separately constructs one shared indexed
field with relevant and distracting bodies.

### 8.2 Indexed frontier

At every macro step, the index filters and scores applicable bodies using:

```text
reality compatibility
scope compatibility
validity at request time
active semantic keys
current latent position
already-applied bodies
configured body budget
```

The frontier may reopen as a latent mode activates new semantic keys. Request
execution is bounded by both per-step and cumulative-body limits. Budget or
coverage exhaustion yields `incomplete_frontier`; it never forces a best-effort
candidate.

### 8.3 Source-normalized mass

Exact duplicates are grouped by independent source and exact body signature.
Repeating one source cannot multiply its authority. Independent sources may
accumulate support up to the configured source-mass cap. Positive and negative
mass remain separate.

This normalization is exact bookkeeping, not learned similarity. The raw
duplicate control must produce zero semantic changes.

## 9. Learned compatibility kernel

L5 trains a compact `EquilibriumKernel` over local MiniLM embeddings. Its
implemented role is shared source/prompt projection and compatibility scoring.
It is not a direct answer classifier. Projection gradients come only from the
coordinate-alignment loss; compatibility inputs are detached so the soft gate
cannot distort the compiler coordinate space.

The training data consists of prompt, relevant-body, and unrelated-body rows.
There is one and only one learned curriculum in L5:

| Stage | Optimizer steps |
|---|---:|
| Shared-coordinate/compiler alignment | 600 |

Common optimization settings:

```text
AdamW
learning rate:       3e-4
batch size:          64
weight decay:        0.01
gradient clipping:   1.0
checkpoint interval: 100
CPU threads:         4
```

There is no architecture or hyperparameter grid. The local model is loaded in
offline mode. Deterministic hash coordinates exist only as a focused test
control and cannot support an authoritative semantic claim.

There is no separately trained local-field, equilibrium, or composition
kernel. Exact body applicability, phase propagation, conjunction, context,
source normalization, candidate construction, and disposition implement the
frozen deterministic field law. Documentation and metrics must not describe
those deterministic stages as additional training.

The learned compatibility probability is mapped into the frozen multiplier
band `[0.75, 1.00]`. It modulates continuous geometry only. Exact source mass,
candidate confidence, polarity, ambiguity, applicability, and authorization are
computed without that multiplier. Therefore a low vector score cannot erase an
exact applicable body or select one of two equally source-supported branches.

## 10. Multi-mode latent equilibrium

### 10.1 Initialization

The normalized prompt anchor remains immutable. The runtime creates up to eight
movable modes. Positive and negative root source mass may initialize separate
polarity modes. Each mode tracks:

```text
128D semantic position
active semantic keys
unit activations
applied and supporting body IDs
independent supporting sources
provenance
support and opposition weights
polarity and confidence
```

### 10.2 Body activation and conjunction

A body becomes applicable only when every exact phase-0 semantic requirement is
active in the mode and its context is compatible. Conjunction therefore
requires all inputs; similarity alone cannot fill a missing input.

Applicable bodies add signed source-normalized authority and activate exact
phase-1 semantic keys. Alternative and opposing branches can remain in separate
modes rather than being averaged into one vector. Candidate confidence is
derived from exact source-normalized authority, not learned vector similarity.

### 10.3 Energy update

For each mode, the registered energy contains:

- an anchor penalty;
- attractive support terms;
- repulsive opposition terms.

Projected gradient updates normalize the state and use backtracking. An update
is accepted only when it does not increase energy. Every persisted trajectory
row records the actual aggregate energy of the accepted latent modes (the
maximum current mode energy). The runtime may not cosmetically clamp a later
record to an earlier scalar merely to make the trace appear monotonic. A real
increase above the frozen numerical tolerance fails execution and the
independent evaluator recomputes the monotonicity check from the persisted
trajectory.

The learned compatibility function changes only the attractive or repulsive
energy strength within the bounded multiplier band. Exact semantic activation,
source authority, context, candidate confidence, source identity, and
disposition remain deterministic.

### 10.4 Dynamic reopening and convergence

After each macro step, the field is queried again from every current mode. A
changed position or newly active semantic key can open a previously inactive
region. Duplicate modes are deterministically collapsed and the best eight are
retained.

Certification requires:

```text
residual <= frozen threshold
frontier stable
mode state stable
three consecutive stable steps
coverage bound >= frozen threshold
cumulative frontier budget not exhausted
```

### 10.5 Dispositions

```text
candidate
alternatives
ambiguous
unknown
incomplete_frontier
quarantine
```

A single candidate requires sufficient confidence and margin. Equally supported
compatible outcomes remain `alternatives`; opposing tied polarities remain
`ambiguous`; missing support returns `unknown`; uncertified convergence or
coverage returns `incomplete_frontier`.

## 11. Independent evaluation, verification, and decoder

### 11.1 Evaluator-owned oracle

The evaluator independently computes exact reachability from the supplied
prompt, requiring every conjunction input and exact context compatibility. It
normalizes support by independent source and body signature. It derives the
expected candidate set, polarity, support mass, disposition, and selected state
without importing the optimizer.

The oracle is used only after runtime output exists. Runtime helpers never
receive the evaluator-owned expected outcome.

Authoritative locked prediction runs execute in a separate process from
evaluator scoring. Before importing the runtime lifecycle, that process installs
a Python audit hook denying opens beneath each evaluator-gold root and performs
explicit denial probes. The resulting access audit records the runtime PID,
probe denials, and unexpected denials. This is controlled process separation
with Python audit-path enforcement; it is **not** an operating-system sandbox or
a general security boundary.

### 11.2 Runtime verifier

After convergence, the verifier reconstructs every candidate from its claimed
support bodies. It checks:

```text
body existence
complete exact input activation
context/reality/time applicability
candidate occurrence membership
independent source agreement
provenance agreement
certificate hash
```

For controlled mathematical rows it also parses the expressions and confirms
that each body step is one exact legal proposal under the existing formal
kernel. It does not trust the optimizer’s geometry as proof.

The evaluator independently reconstructs the confidence authorized by exact
source-normalized support. For support mass \(m\), the registered confidence is
\(1-\exp(-2m)\). Candidate keys, polarities, and finite confidence values must
match this reconstruction within the frozen tolerance. A structurally valid
certificate with a fabricated low or high confidence therefore fails.

### 11.3 Strict realization

The decoder receives only independently certified candidates and a surface
archive. It never sees evaluator gold or the complete hidden oracle state.

It emits a fixed, strict realization for:

```text
one verified candidate
multiple verified alternatives
balanced ambiguity
incomplete frontier
unknown
quarantine
```

Missing an authorized surface label quarantines the output. L5 measures claim
authorization and disposition, not stylistic language quality.

## 12. Datasets

### 12.1 Seeds

```text
training:       1940
development:    1941
calibration:    1942
locked:         20270610
stress:         20270611
scale:          20270612
interventions:  20270613
replay:         91767
```

### 12.2 Configured sizes

| Dataset or panel | Configured size |
|---|---:|
| Development field bodies | 24,000 |
| Locked field bodies | 100,000 |
| Scale field target | 1,000,000 |
| Training compiler items | 48,000 |
| Development compiler items | 12,000 |
| Locked compiler items | 16,000 |
| Primary locked equilibrium queries | 8,000 |
| Stress queries | 4,000 |
| Intervention cases | 1,000 |
| Decoder/scale query cases | 600 |

The configured 600 decoder cases also define the locked raw-chain end-to-end
panel and the maximum number of shared-field scale queries.

### 12.3 Supplied fixture families

The deterministic, lazy fixture generator covers ten families:

| Family | Required behavior |
|---|---|
| `one_body` | Complete one local body |
| `dependency_2_4` | Compose two to four separate bodies |
| `dependency_5_8` | Compose five to eight separate bodies |
| `dependency_9_16` | Compose nine to sixteen separate bodies |
| `conjunction` | Activate a body only when every input is present |
| `weighted_contradiction` | Select the independently stronger polarity while deduplicating one repeated source |
| `balanced_contradiction` | Preserve equally supported opposite polarities as ambiguity |
| `alternatives` | Preserve equally supported compatible outcomes |
| `scope_isolation` | Ignore higher-weight wrong-scope and wrong-reality bodies |
| `unknown` | Abstain when a decisive input/body is absent |

Cases alternate between controlled mathematics and opaque abstract realities.
The public side contains only the field, prompt, and deterministic vector table.
The expected family, depth, candidates, disposition, and support masses remain
evaluator-only.

### 12.4 Controlled mathematical fixtures

The mathematical domain uses exact, source-backed expression transformations
accepted by the existing formal kernel. The current generator emphasizes nested
additive-zero and multiplicative-one identity transformations. These are valid
multi-body formal transformations, but they are not broad mathematical proof
discovery and must not be reported as such.

### 12.5 Abstract realities

The abstract domain uses opaque semantic states within signed, isolated reality
keys. It measures transport, conjunction, support, opposition, ambiguity, and
context behavior without importing named reasoning operators.

### 12.6 Deterministic semantic positions

Every supplied fixture semantic key maps to a stable normalized 128D position
with a shared topic component and a smaller item component. These positions are
test fixtures suitable for the index and optimizer. They are not outputs from
the raw MiniLM compiler and must not be cited as compiler success.

## 13. Calibration

The configuration freezes bounded searches for:

```text
compiler confidence: 0.50–0.99 by 0.01
candidate confidence: 0.50–0.99 by 0.01
candidate margin:     0.02–0.30 by 0.02
minimum coverage:     0.90
convergence residual: 0.001
```

The implemented lifecycle records thresholds selected from the frozen
configuration after development gates. It does not tune on locked inputs.

## 14. Metrics and mandatory gates

### 14.1 Raw compiler gates

| Metric | Gate |
|---|---:|
| Accepted semantic precision | `1.00` |
| Safe coverage | `>=0.95` |
| Exact content agreement | `>=0.99` |
| Shared-coordinate recall@8 | `>=0.99` |
| Incorrect accepted compilations | `0` |
| Encoder calls | exactly one per item |

### 14.2 Local field-law gates

| Metric | Gate |
|---|---:|
| One-body completion | `>=0.97` |
| Force direction | `>=0.99` |
| Multi-input completeness | `>=0.95` |

The richer experiment harness reports local supplied-input results separately;
the lifecycle must not substitute them for Track A compiler gates. One-body and
multi-input scores are enforced on the locked supplied-field families. Force
direction is enforced through the later one-body reversal intervention.

### 14.3 Locked raw-chain end-to-end gates

| Metric | Gate |
|---|---:|
| Locked raw-chain cases | `600` configured |
| Accepted precision | `1.00` |
| Incorrect accepted predictions | `0` |
| Safe coverage | `>=0.90` |
| All-case exactness | `>=0.88` |
| One encoder pass per source/prompt item | `1.00` |
| Unknown/conflict/alternative agreement | `1.00` |
| Decoder authorization | required for a correct case |
| Candidate set and certificate body count | exact evaluator agreement |

The raw evaluator reports exactness at every answerable depth from 1 through
16 and separately for unknowns, balanced conflicts, and alternatives. A case is
correct only when disposition, selected key, complete candidate key/polarity
set, per-candidate verified certificate body count, decoder authorization, and
empty factual-operation tuple all agree. The answerable cases are linear
controlled chains; this track does not replace the broader supplied-field
family metrics.

### 14.4 Primary supplied-input equilibrium gates

| Metric | Gate |
|---|---:|
| Accepted verified precision | `1.00` |
| Incorrect accepted candidates | `0` |
| Safe coverage | `>=0.90` |
| All-case exactness | `>=0.88` |
| Answerable exactness | `>=0.90` |
| Dependency 2–4 exactness | `>=0.95` |
| Dependency 5–8 exactness | `>=0.92` |
| Dependency 9–16 exactness | `>=0.85` |
| Conjunction exactness | `>=0.90` |
| Weighted contradiction | `>=0.95` |
| Ambiguity/unknown recall | `>=0.95` |
| Global optimum agreement | `>=0.95` |

The evaluator reports per-family, per-domain, exact-depth, and dependency-band
metrics plus explicit numerator/denominator counts. Wilson 95% intervals are
computed for focused controls and interventions and must accompany any small-
panel interpretation. The frozen gates use point estimates.

The current lifecycle’s `safe_coverage` numerator is the count of cases whose
entire result exactly verifies, divided by all cases. It is therefore
numerically identical to `all_case_exactness`; it is not a separate measure of
the fraction of safe abstentions plus correct accepted answers. The final report
must retain that operational definition or the evaluator must be revised before
freezing.

### 14.5 Dynamics, frontier, and authorization gates

```text
accepted energy increases:                  0
accepted-query convergence:                >=0.99
frontier stability:                         >=0.99
required-body frontier recall:              >=0.99
support-certificate safety:                 1.00
candidate-confidence oracle agreement:      1.00
decoder authorization agreement:            1.00
factual operations:                         0
runtime evaluator-gold reads:               0
```

### 14.6 Three reported rates

Every supplied-fixture result must publish these under their exact names:

```text
supplied_input_contract
optimizer_conditional_on_supplied
end_to_end_from_supplied
```

No report may rename `supplied_input_contract` to compiler correctness.

## 15. Controls and causal interventions

### 15.1 Paired controls

The same supplied cases are run through:

1. full multi-mode dynamic field;
2. no optimization;
3. single latent mode;
4. fixed initial frontier;
5. no context gating;
6. raw duplicate amplification;
7. no learned compatibility callback;
8. fixed latent state with zero geometry;
9. deterministic random geometry.

Required sensitivity:

| Effect | Gate |
|---|---:|
| Full minus no optimization | `>=0.25` |
| Full minus fixed frontier on deep cases | `>=0.20` |
| Multi-mode minus single-mode on conflicts | `>=0.20` |
| Context-gated minus no-context on scope cases | `>=0.20` |
| Semantic changes from same-source raw duplicates | `0` |
| Full minus no learned compatibility | `>=0.05` |
| Full minus fixed state/zero geometry | `>=0.05` |
| Full minus deterministic random geometry | `>=0.05` |
| Full-system latent-state movement rate | `>0` |
| Fixed-state control movement rate | `0` |

These controls are causal mechanism gates. High primary accuracy without the
required drops is a mechanism failure, not an L5 pass. The full path must
actually receive a learned compatibility callback. The random control is
deterministic so replay tests the same ablation rather than sampling noise.

Failure of any learned-geometry or movement gate mechanically yields
`L5-E — LATENT EQUILIBRIUM FAILURE`. `L5-A` is impossible when this mechanism
gate fails, even if exact phase propagation still produces correct candidates.

### 15.2 Interventions

The intervention panel measures:

```text
remove decisive terminal support
remove irrelevant out-of-context bodies
remove repeated copies from one source
remove one conjunction prompt input
reverse a one-body query from outcome back toward its source
```

Required behavior:

| Metric | Gate |
|---|---:|
| Relevant-removal response accuracy | `>=0.95` |
| Irrelevant-region invariance | `>=0.95` |
| Duplicate-source invariance | `>=0.95` |
| Conjunction-input sensitivity | `>=0.95` |
| Direction-reversal accuracy | `>=0.99` |

## 16. Stress and scale diagnostics

### 16.1 Dependency stress

The 4,000-case stress panel cycles through exact dependency counts 17–64 in both
domains. Its gates are annotations only:

```text
depth 17–32 exactness >=0.75
depth 33–64 exactness >=0.50
accepted precision =1.00
incorrect accepted candidates =0
```

When both aggregate depth bands pass, the report may add
`L5-17-64-AGGREGATE-STRESS-PASS`. Otherwise it reports
`L5-STRESS-BOUNDARY-MEASURED`. The annotation does not imply that depth 64
itself passed; the exact-depth table and deepest verified dependency remain
authoritative. Neither annotation changes the primary L5 classification. The
deepest successful generated dependency is not a claim of arbitrary
mathematical reasoning at that depth.

### 16.2 Shared-field scale

The scale lifecycle materializes a 100,000-body indexed shared field and runs up
to 600 relevant queries. It verifies:

```text
exact result agreement
partition/cache hashes
no full-field scans
<=128 active bodies per step
<=2,048 cumulative distinct body reads
storage-order/index determinism
```

The configured one-million-body panel is represented by a deterministic lazy
distractor corpus commitment attached with `materialize_limit=0`. This tests
manifest/accounting and bounded-access compatibility; it does **not** mean that
one million bodies are simultaneously materialized or traversed during locked
runtime. The report must state materialized and committed body counts
separately.

## 17. Integrity and resource gates

```text
runtime answer/route/proof leakage:       0
runtime evaluator-gold reads:             0
runtime/evaluator process separation:     required
runtime evaluator-path audit denials:     every probe
unexpected evaluator-path denials:        0
network calls:                            0
factual field operations:                 0
incorrect accepted compilations:          0
incorrect accepted candidates:            0
deterministic replay:                      1.00
immutable locked shards:                  required
maximum new trainable parameters:         2,000,000
maximum float32 inference weights:        8 MB
development peak RSS:                    <12 GB
locked peak RSS:                          <8 GB
machine ceiling:                         <20 GB
maximum active experimental runtime:      <4 hours
```

The lifecycle verifies artifact hashes, public/gold separation, process-
separated runtime prediction, Python audit-path denial, no runtime gold reads,
prediction-shard hashes, zero full scans, controls, interventions, and
deterministic replay of representative supplied and raw cases. It records
wall-clock time and process peak RSS for compiler development, equilibrium
development, locked evaluation, scale execution, and the active `run-all`
command; resource claims remain unauthorized until those measured values exist
in the authoritative workspace.

## 18. Mechanical classification

The detailed evaluator precedence is:

1. `L5-G — INTEGRITY OR LEAKAGE FAILURE`
2. `L5-B — PROMPT OR SOURCE COMPILATION FAILURE`
3. `L5-C — SHARED COORDINATE OR LOCAL FIELD-LAW FAILURE`
4. `L5-D — MINIMAP OR DYNAMIC FRONTIER FAILURE`
5. `L5-E — LATENT EQUILIBRIUM FAILURE`
6. `L5-F — CONTRADICTION OR MULTI-HYPOTHESIS FAILURE`
7. `L5-H — VERIFICATION OR DECODER HANDOFF FAILURE`
8. `L5-S — SAFE BUT LOW COVERAGE`
9. `L5-COMPUTE`
10. `L5-A — COMPILED LATENT FIELD EQUILIBRIUM PASS`

The lifecycle report maps fail-fast stage failures to the nearest broad class.
The permanent measured report must retain the more specific evaluator boundary
when its artifacts are available instead of collapsing all equilibrium-family
failures into one generic label.

`L5-A` requires every compiler, equilibrium, causal, verification, integrity,
and resource boundary applicable to the authoritative run. A diagnostic stress
annotation cannot rescue a primary failure. In particular, a failed learned-
geometry mechanism gate takes precedence as `L5-E`; exact symbolic propagation
cannot substitute for the claimed latent-equilibrium mechanism.

## 19. Lifecycle and evaluator isolation

Authoritative order:

1. Verify Python 3.11, local model files, offline operation, and model hashes.
2. Validate deterministic generators and configured counts.
3. Train the single 600-step shared-coordinate/compiler-alignment kernel; the
   exact field law remains deterministic and untrained.
4. Evaluate the independent development compiler panel.
5. Build and hash development minimaps.
6. Evaluate supplied-input equilibrium and the development compiler/writer
   bridge.
7. Record the frozen thresholds.
8. Freeze source, configuration, checkpoint, generators, and development
   artifacts.
9. Generate public and evaluator locked inputs once.
10. Run raw compiler predictions from public compiler rows only.
11. Run raw-chain end-to-end predictions from opaque public source/prompt rows
    whose IDs and text reveal no family or disposition.
12. Run supplied-field predictions from public field rows only.
13. Write immutable 256-case supplied-field prediction shards and immutable
    compiler/raw-chain prediction files.
14. Start evaluator scoring only after all runtime predictions have been
    persisted by the guarded runtime process.
15. Run stress, shared-field scale, interventions, and causal controls.
16. Verify supplied-field and raw-chain deterministic replay and artifact
    hashes.
17. Generate a measured workspace report.
18. Audit the complete evidence before updating the tracked report.

The guarded runtime subprocess may read only public compiler rows, public field
cases, model/checkpoint files, configuration, and signed runtime code. A Python
audit hook denies evaluator-gold paths and produces an access-audit artifact.
The evaluator process may read expected outcomes only after predictions have
been persisted. This separation is not represented as an OS-level sandbox.

## 20. Required focused tests

Representation and leakage:

- all public fixture fields reject forbidden evaluator names;
- body occurrence ownership and phases are exact;
- vector indices, dimensions, and finite values validate;
- deterministic 128D fixture positions replay exactly;
- prompt and source hashes bind all public context;
- no runtime result contains factual operations.

Compiler and writer:

- exactly one encoder call per item;
- malformed, open-ended, and forbidden-metadata inputs clarify;
- source/prompt form mismatches clarify;
- exact content comes from the parser, not vectors;
- source and prompt share the learned coordinate space;
- unaccepted or incomplete compiler output cannot be written;
- duplicate source transactions fail atomically;
- writer phases, context, provenance, source identity, and hashes round-trip.

Field and optimization:

- every body belongs to deterministic minimap ancestry;
- no minimap contains closure or expected answers;
- scope, reality, and time gates fail closed;
- same-source duplicates do not add authority;
- independent sources can add bounded authority;
- the prompt anchor remains unchanged;
- at least one latent mode moves on answerable cases;
- every accepted update is energy-nonincreasing;
- persisted energy is the actual aggregate mode energy, not a cosmetic running
  minimum;
- conjunction requires all inputs;
- dynamic reopening reaches later bodies;
- balanced contradiction preserves opposing modes;
- compatible alternatives are not collapsed;
- uncertified coverage/convergence returns `incomplete_frontier`.

Verification and realization:

- the evaluator oracle does not import the optimizer;
- runtime support reconstruction rejects incomplete graphs;
- candidate confidence matches the evaluator's independent source-mass
  reconstruction;
- corrupt source, provenance, or body IDs fail;
- invalid formal math steps fail;
- an uncertified candidate cannot be realized;
- alternatives require at least two verified candidates;
- missing surface metadata quarantines;
- evaluator gold is inaccessible to runtime.
- runtime prediction and evaluator scoring use separate processes;
- the runtime audit hook denies every evaluator-path probe and reports no
  unexpected denial, without claiming OS sandboxing.

Lifecycle:

- freeze mismatch blocks execution;
- second locked evaluation is refused;
- prediction shards are immutable;
- interruption/replay preserves semantic results;
- scale access is bounded and performs no full scan;
- stress cannot change the primary classification;
- opaque Track-C public identifiers and text reveal no hidden family,
  disposition, depth, route, or answer;
- no-learned-compatibility, fixed-state/zero-geometry, and deterministic random-
  geometry controls each meet the required causal drop;
- the full system moves at least one latent state and the fixed-state control
  moves none;
- mechanism-gate failure makes `L5-A` impossible;
- tracked reports are not populated before measured artifacts exist.

Repository acceptance:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m ltm verify --workspace workspaces/_repository-catalog --offline
git diff --check
```

## 21. Evidence interpretation and known limitations

The following statements are mandatory in any L5 interpretation:

1. **Supplied fixtures are not compiler evidence.** Their exact semantic keys,
   phase records, and deterministic vectors already satisfy the input contract.
2. **The three locked tracks have different distributions.** Track A measures
   compiler parsing/rejection, Track B measures broad field behavior from
   supplied fixtures, and Track C measures 600 raw linear chains.
3. **The joint writer panel is narrow but real.** It estimates the implemented
   raw-to-answer path for generated controlled linear chains only, not the full
   conjunction/contradiction/branching family distribution.
4. **Controlled mathematics is narrow.** Identity transformations validate
   exact mathematical-body checking, not broad theorem discovery.
5. **Abstract dependencies measure field composition.** They do not show that a
   language compiler can discover arbitrary real-world causal or logical links.
6. **The primary fixture field is case-local.** Shared-store retrieval is tested
   separately in the scale panel.
7. **A lazy one-million-body commitment is not one million active bodies.** The
   report must disclose both values.
8. **Seventeen-to-sixty-four dependencies are stress diagnostics.** They cannot
   upgrade the one-to-sixteen primary claim.
9. **Multiple modes preserve alternatives; they do not prove global optimality
   for arbitrary nonlinear fields.** The claim is limited to the registered L5
   law and generator.
10. **The verifier, not the latent vector, authorizes output.** Vectors guide
    retrieval and soft movement only.
11. **The decoder is strict and symbolic.** Naturalness, explanation quality,
    and unrestricted response generation remain untested.
12. **Bounded execution is not unlimited influence.** Data outside the certified
    frontier affects only committed summaries until details are opened.
13. **The current locked `safe_coverage` field equals exactness by construction.**
    It must not be interpreted as an independent calibrated-abstention metric.
14. **Exact propagation is not evidence for learned latent causality.** L5-A
    requires the full learned geometry to outperform all three geometry-removal
    or replacement controls by at least 0.05, with state-movement checks.
15. **Process separation is bounded evidence, not a security sandbox.** The
    Python audit hook denies evaluator paths inside the runtime subprocess; it
    does not provide OS-level isolation from a hostile program.

Until the authoritative workspace is complete and independently audited, the
only valid statement is:

> L5 has an implemented experiment harness and frozen intended gates; it has no
> measured classification yet.
