# G2.10 — Behavioral Topology Coordinate Compiler

## Status

G2.10 is a new controlled language-compiler experiment. Its representation
kernel is implemented and passes its current separability check. The learned
MiniLM compiler, FieldIR handoff, frozen lifecycle, controls, and locked score
card are planned but not yet implemented or measured.

This document is the full design reference. The permanent experiment result,
when one exists, belongs in `report.md`; this document must not be read as a
claim that G2.10 has passed.

## Question

Can a semantic embedder compile unseen controlled language into a reliable G1
topology more effectively when it predicts the **behavior of an executable
factor** rather than an arbitrary relation-label vector?

Earlier G2 experiments generally asked a language representation to recover
relation names, named roles, direction, and context as partly independent
classification tasks. G2.10 makes those choices consequences of a topology
factor's observable dynamics:

```text
sentence + supplied content atoms
  -> learned behavioral coordinate + port scores + context/disposition
  -> nearest legal behavioral topology cell
  -> exact role incidence
  -> FieldIR validation
  -> G1 validation
  -> atomic accept, clarify, or quarantine
```

The language model is a proposer. It never writes to G1 directly.

## Boundary

G2.10 is deliberately narrow.

Included:

- one factor per sentence;
- exactly two supplied content atoms for accepted cases;
- nine canonical factor cells;
- controlled, split-disjoint language;
- positive-polarity acceptance only;
- asserted and conditional modality metadata;
- global and fictional scope metadata;
- exact FieldIR/G1 projection and abstention.

Excluded:

- span extraction;
- multi-factor sentence composition;
- identity resolution and memory matching;
- document composition, migration, and G3–G9 integration;
- negative-polarity factor execution;
- unrestricted language or production-readiness claims.

## Authority model

The persistent topology remains a typed factor graph:

\[
\mathcal T=(A,F,I,\Theta,\Sigma,\nu).
\]

- \(A\): persistent content atoms;
- \(F\): executable factors;
- \(I\): exact factor-port-to-atom incidence;
- \(\Theta\): continuous field parameters;
- \(\Sigma\): registered schema and legal compositions;
- \(\nu\): topology version.

An individual factor is:

\[
f=(A,\Psi,\mathcal P,M,\kappa,w,\pi).
\]

- \(\Psi\): registered behavior;
- \(\mathcal P\): ordered typed ports;
- \(M\): port/channel read-write permissions;
- \(\kappa\): applicability, scope, modality, and polarity context;
- \(w\): bounded factor strength;
- \(\pi\): exact provenance.

Dense vectors may route, rank, and record field geometry. They cannot create a
fact, select a relation, bind a role, or authorize insertion on their own.

## Atom state and port permissions

Each of two factor ports exposes six continuous state channels:

\[
z_i=(y_i,e_i^+,e_i^-,u_i,\ell_i,t_i).
\]

| Channel | Meaning |
| --- | --- |
| \(y\) | activation of a proposition, event, or state |
| \(e^+\) | accumulated supporting evidence |
| \(e^-\) | accumulated opposing evidence |
| \(u\) | explicit uncertainty |
| \(\ell\) | live/current applicability |
| \(t\) | normalized temporal coordinate |

The factor declares which of the 12 channels it can write. Runtime mutability
intersects this factor mask. Therefore an implication cannot reduce its premise
to satisfy an energy residual, a requirement cannot invent a prerequisite, and
a temporal factor cannot rewrite observed event time.

For a differentiable factor response:

\[
\Delta_f(s)=\Pi_{[0,1]}(s-0.25(M_f\odot M_s)\odot\nabla E_f(s))-s.
\]

Exact effects—derivation, obligation, conflict, temporal violation, and
supersession—remain separate typed output channels. Gradient movement is not
factual authorization.

## Canonical cells

G2.10 has nine canonical cells.

| Cell | G1 relation | Ports | Direction |
| --- | --- | --- | --- |
| `transfer.derive` | `implies` | premise, conclusion | directional |
| `transfer.oblige` | `requires` | dependent, prerequisite | directional |
| `evidence.support` | `supports` | evidence, claim | directional |
| `evidence.opposition` | `opposes` | evidence, claim | directional |
| `evidence.uncertainty` | `uncertainty` | source, claim | directional |
| `constraint.equal` | `equals` | left, right | symmetric |
| `constraint.exclude` | `excludes` | left, right | symmetric |
| `precedes` | `before` | first, second | directional |
| `replace` | `supersedes` | older, newer | directional |

`after(A,B)` normalizes to `precedes(B,A)`. It is a surface realization, not a
second learned behavior. Equality and exclusion canonicalize their atom order
by stable atom ID because their topology behavior is symmetric.

## Factor dynamics

### Directed transfer

Both transfer cells use:

\[
E=[\max(0,y_{left}-y_{right})]^2.
\]

`derive` may write only the conclusion activation and emits a derivation
channel. `oblige` writes neither activation and instead emits an obligation
when its dependent is active without its prerequisite.

The shared energy law is intentional: the typed exact-output channel makes
implication and requirement distinct.

### Directed evidence

With source activation \(y_s\), strength \(w\), and selected target channel
\(x\):

\[
d=wy_s,\qquad E=d(1-x)^2.
\]

The factor can write only the chosen target channel. Persistent evidence uses
probabilistic union:

\[
x\oplus d=1-(1-x)(1-d).
\]

Support targets \(e^+\), opposition targets \(e^-\), and uncertainty targets
\(u\). Equal strength must still produce different behavioral coordinates.

### Symmetric constraints

\[
E_{equal}=(y_a-y_b)^2,
\]

\[
E_{exclude}=[\max(0,y_a+y_b-1)]^2.
\]

Both atom activations may be writable only when the runtime marks them mutable.
An exclusion also emits a typed conflict magnitude.

G1 equality has been changed to emit and verify both valid derivation
directions when equality holds. This prevents equality behavior from depending
on arbitrary atom ordering.

### Temporal precedence

\[
E_{precedes}=[\max(0,t_{first}-t_{second})]^2.
\]

Time channels are read-only. A violation is reported; event time is not
rewritten. The first experiment uses non-strict ordering, so equal coordinates
are allowed.

### State replacement

\[
E_{replace}=(\ell_{older}y_{newer})^2.
\]

Only the older live channel is writable. The exact supersession output records
that the newer claim displaces the older claim without deleting history or
provenance.

## Probe bank and behavioral signature

The topology cell is identified by executing it over a deterministic probe
bank, not by its relation name.

The bank contains 24 probes:

- six activation-pair probes;
- four evidence probes;
- seven temporal probes, including missing-time cases;
- four lifecycle probes;
- closed-scope, unsupported-modality, and negative-polarity probes.

Each probe is evaluated in canonical and swapped port order. A response stores:

```text
applicability and diagnostics       5 values
energy                               1 value
gradient                             12 values
projected state delta                12 values
typed exact outputs                  5 values
```

The static read and write masks contribute 24 values. Therefore:

\[
24 + (24\ \text{probes})\times(2\ \text{orders})\times35=1704.
\]

The current representation implementation rounds canonical values to eight
decimal places before hashing. The current measured minimum pairwise RMS
distance across the nine cells is `0.095758`, above the configured `0.001`
separability gate.

## Learned compiler

The planned learned compiler reuses the pinned local G2.9 MiniLM boundary:

- one token-state forward pass per sentence;
- embeddings and lower four layers frozen;
- upper two layers trainable;
- CPU-only, offline model loading;
- exact model-file hashes in every frozen manifest.

The head consumes masked sentence pooling and supplied span pooling. It emits:

```text
1704D behavioral signature proposal
3-way disposition logits
2-way scope logits
2-way modality logits
two ordered-port scores
```

The model has no unconstrained relation-name insertion head. Cell identity is
obtained only by distance to registered behavior signatures.

The training objective is:

\[
2L_{behavior}+L_{cycle}+L_{port}+L_{reversal}
+0.5L_{context}+L_{disposition}+L_{abstention}.
\]

- `behavior`: group-balanced Smooth-L1 over the behavioral coordinate;
- `cycle`: soft classification induced by distance to the nine legal cells;
- `port`: ordered atom-binding loss for directional cells;
- `reversal`: margin against the reversed binding;
- `context`: scope and modality prediction;
- `disposition`: accept, clarify, or quarantine;
- `abstention`: pushes quarantined inputs outside the legal cells and keeps
  ambiguous inputs below the acceptance margin.

## Deterministic projection

At runtime the projector:

1. accepts only public text and supplied atoms;
2. filters cells by G1-compatible atom kinds;
3. computes RMS distance from the predicted signature to every legal cell;
4. combines that distance with the two possible directional port scores;
5. canonicalizes symmetric bindings and `after`;
6. checks absolute distance, winner/runner-up margin, port confidence, and
   predicted disposition;
7. builds a FieldIR program and validates it against the current G1 registry;
8. returns a complete atomic handoff or no topology operations.

The development set calibrates the three acceptance thresholds on a frozen
`21 × 21 × 21` quantile grid. It selects maximum safe coverage subject to
`99%` accepted precision, zero reversal false accepts, and zero invalid
insertions. Locked data is never used in threshold calibration.

## Dataset

| Split | Accepted | Clarification | Quarantine | Total |
| --- | ---: | ---: | ---: | ---: |
| Train | 18,000 | 2,250 | 2,250 | 22,500 |
| Development | 3,600 | 450 | 450 | 4,500 |
| Locked | 3,600 | 450 | 450 | 4,500 |

Accepted examples are balanced across the nine cells. The planned generator
uses split-disjoint opaque atom names and paraphrase banks, matched reversal
pairs for directional cells, swapped symmetric forms, balanced `before` and
`after`, and global/fictional plus asserted/conditional contexts.

Runtime inputs contain only text, atom IDs, atom kinds, exact spans, and
provenance. Gold cell, ports, context, surface relation, and disposition are
stored under evaluator-only paths. Runtime loaders reject paths containing
`gold`.

## Lifecycle

The completed CLI will provide:

```text
model-check -> representation-check -> dataset-build -> develop
  -> freeze -> locked-suite-build -> evaluate -> verify -> report
```

`run-all` follows that sequence and stops at the first failed gate. Every
stage writes atomically, refuses overwrite, and records source/config/model/
registry/checkpoint hashes. A failed development gate prevents frozen or
locked-suite generation.

Resource envelope:

- four CPU threads;
- 18 GB development RSS limit;
- 12 GB locked RSS limit;
- fewer than ten million trainable parameters;
- eight-hour total active-time limit;
- checkpoints every 50 training steps.

## Scorecard

The candidate and controls report:

- accepted exact precision;
- safe coverage;
- all-case exactness;
- cell accuracy and macro F1;
- named-role exactness;
- directional port accuracy;
- symmetric binding accuracy modulo permutation;
- scope, modality, and disposition accuracy;
- reversal false accepts;
- invalid insertions;
- FieldIR/G1 round-trip rate;
- behavioral-cycle equality;
- provenance integrity;
- runtime, memory, and trainable parameter count.

Mandatory candidate gates are:

```text
accepted exact precision >= 0.99
safe coverage >= 0.95
canonical cell accuracy >= 0.99
directional port accuracy >= 0.995
symmetric binding accuracy = 1.00
accepted context accuracy >= 0.995
behavioral cycle equality = 1.00
FieldIR/G1 validity = 1.00
provenance integrity = 1.00
reversal false accepts = 0
invalid insertions = 0
```

Classifications:

```text
G2.10-R — BEHAVIORAL TOPOLOGY NOT SEPARABLE
G2.10-B — BEHAVIORAL COMPILER DEVELOPMENT FAILURE
G2.10-C — BEHAVIORAL COMPILER LOCKED FAILURE
G2.10-A — CONTROLLED BEHAVIORAL G2 PASS
```

## Controls

The final experiment will report three frozen-encoder readout controls:

1. a nine-label relation classifier;
2. an energy-only coordinate;
3. a non-counterfactual signature without reversal training.

It will also evaluate the candidate projector with its winner-margin check
disabled. These controls are diagnostic only; they cannot promote a failed
candidate to a pass.

## Current implementation inventory

Implemented now:

- nine-cell deterministic topology registry;
- 24-probe, 1704D signature construction;
- read/write dynamics and core symmetry tests;
- bidirectional G1 equality execution and verification;
- representation separability check;
- deterministic split generator and public/gold loader boundary;
- compact behavioral compiler head;
- basic deterministic projector and scorecard metric function.

Not yet implemented:

- MiniLM feature extraction and training loop;
- signature calibration and full projector threshold lifecycle;
- FieldIR vector-sidecar and atomic G1 handoff;
- frozen/locked lifecycle, controls, replay verification, and permanent report;
- full G2.10 scorecard.

Therefore the only measured G2.10 result at this time is representation
separability, not a language-compiler result.
