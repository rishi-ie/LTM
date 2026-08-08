# G2.10 Draft — Behavioral Topology Coordinate Compiler

Expanded design appendix: [full design](full-design.md).

## Status

The representation, dataset, learned supplied-atom kernel, exact FieldIR/G1/
numeric handoff and development evaluator were implemented in
`workspaces/topology-g2-10-r4/`. The development kernel failed its registered
coverage and topology-recovery gates, so freeze, raw-span training, locked
generation and locked evaluation were refused. See [the measured report](report.md).

This does not change the provisional G2.5 engineering decision or any
historical G2 classification.

## Objective

Test whether natural language can be compiled more reliably when the learned
target is the observable behavior of an executable topology factor rather than
an arbitrary relation-label embedding.

The representation must make these properties intrinsic:

- directed roles differ because swapping them changes field behavior;
- symmetric roles are explicitly invariant and are not scored as directional;
- inverse surface forms normalize to one canonical factor;
- relations with similar residuals remain distinct through typed output
  channels;
- every accepted continuous proposal projects to exactly one legal FieldIR/G1
  factor;
- ambiguity produces abstention rather than a nearest-label insertion.

Success means that the topology target itself is lossless, behaviorally
separable, and suitable for a semantic embedder. It does not by itself mean
that unrestricted natural language can be compiled reliably.

## Assumptions

1. G1 and FieldIR remain the persistent executable authority.
2. Learned coordinates provide proposals, routing evidence, and field
   parameters; they do not independently authorize topology insertion.
3. Content identity, source spans, and provenance remain outside the
   behavioral signature and are attached exactly during projection.
4. The first kernel receives gold content atoms and tests only topology-family,
   mode, port binding, direction, and context recovery.
5. The initial topology contains five canonical binary factor families. Higher
   arity, identity, reference, quantification, and document composition are
   later stages.

## Central representation

A compiled statement is a typed factor:

\[
f=(A,\Psi,\mathcal P,M,\kappa,w,\pi),
\]

where:

- \(A\) is the set of persistent content atoms used by the factor;
- \(\Psi\) is a registered executable behavioral operator;
- \(\mathcal P\) is exact typed port-to-atom incidence;
- \(M\) declares which state channels each port may read or write;
- \(\kappa\) contains scope/time applicability, modality routing, and polarity
  transformation;
- \(w\) contains confidence, authority, and soft-strength parameters;
- \(\pi\) contains exact source provenance.

The persistent topology is:

\[
\mathcal T=(A,F,I,\Theta,\Sigma,\nu),
\]

where \(I\) is discrete incidence, \(\Theta\) is continuous field state and
parameters, \(\Sigma\) is the registered factor schema, and \(\nu\) is the
topology version.

The invariant is:

> Connectivity and authorization are discrete and exact. Behavior and semantic
> placement are continuous and learnable.

## Shared field state

Each atom address \(a_i\) exposes a typed state block:

\[
z_i=(y_i,e_i^+,e_i^-,u_i,\ell_i,t_i,m_i^t).
\]

| Variable | Range | Meaning |
| --- | --- | --- |
| \(y_i\) | \([0,1]\) | proposition, event, or state activation |
| \(e_i^+\) | \([0,1]\) | accumulated supporting evidence |
| \(e_i^-\) | \([0,1]\) | accumulated opposing evidence |
| \(u_i\) | \([0,1]\) | explicit epistemic uncertainty |
| \(\ell_i\) | \([0,1]\) | live/current applicability; zero means inactive or superseded |
| \(t_i\) | \([0,1]\) | normalized temporal coordinate when known |
| \(m_i^t\) | \(\{0,1\}\) | whether \(t_i\) is known and applicable |

Factor execution also exposes typed result channels:

\[
o_f=(\Delta y,\Delta e^+,\Delta e^-,\Delta u,\Delta\ell,
q_{\mathrm{derive}},q_{\mathrm{obligation}},q_{\mathrm{conflict}},
q_{\mathrm{temporal}},q_{\mathrm{supersession}}).
\]

The `q` channels are typed exact-output, violation, or event magnitudes. They
are not collapsed into one scalar energy. This is necessary because two
relations may have the same residual surface while producing different
authorized effects.

Every factor has a deterministic applicability gate:

\[
g_f(\kappa,s) =
g_{\mathrm{scope}}g_{\mathrm{time}}.
\]

A closed gate yields zero field contribution and a typed applicability
diagnostic. Modality selects a registered execution route, such as asserted,
hypothetical, quoted, or queried. Polarity selects a registered signed atom or
negated operator transformation. Neither modality nor negative polarity may be
implemented by silently zeroing an otherwise applicable factor. Context is
resolved before factor behavior.

## Behavioral response

For state \(s\), a registered factor returns:

\[
R_f(s)=
\left(E_f(s),\nabla E_f(s),\Delta_f(s),o_f(s)\right),
\]

where \(E_f\) is the factor energy or residual, \(\Delta_f\) is one fixed
projected optimization step, and \(o_f\) contains the typed result channels.

The projected step uses one registered learning rate \(\eta\), the factor's
allowed-write mask \(M_f\), and the runtime state's mutability mask \(M_s\):

\[
\Delta_f(s)=
\Pi_{[0,1]}\left(s-\eta(M_f\odot M_s)\odot\nabla E_f(s)\right)-s.
\]

Observed and otherwise immutable variables have a zero runtime mutability
mask. For example, an implication may write the conclusion activation but may
never satisfy its residual by lowering an observed premise. A requirement may
emit an obligation but may not invent its missing prerequisite. Port/channel
read-write masks are therefore part of the topology, not optimizer metadata.

Discrete exact effects such as derivation, conflict creation, obligation, or
supersession are reported in \(o_f\); gradient movement never substitutes for
those effects.

## Deterministic probe bank

The probe bank is configuration, not generated training data. Its hash is
frozen before model training.

### Activation probes

For ordered ports \((p_0,p_1)\), use:

```text
(0.00, 0.00)
(0.00, 1.00)
(1.00, 0.00)
(1.00, 1.00)
(0.25, 0.75)
(0.75, 0.25)
```

All unmentioned state channels use the neutral state:

```text
e+ = 0, e- = 0, u = 0, live = 1, time-known = 0
```

### Evidence probes

Use source activation \(y_0\in\{0,1\}\) crossed with the target channel value
in \(\{0.2,0.8\}\). Run separate probes for target support, opposition, and
uncertainty. Non-target evidence channels remain zero.

### Temporal probes

With both time masks enabled, use:

```text
(t0, t1) = (0.00, 1.00)
(t0, t1) = (1.00, 0.00)
(t0, t1) = (0.50, 0.50)
(t0, t1) = (0.25, 0.75)
(t0, t1) = (0.75, 0.25)
```

Also run one probe with each time mask missing. Missing time must produce an
applicability or clarification diagnostic, not a guessed ordering.

### Lifecycle probes

For the ordered pair `(older, newer)`, cross:

```text
older-live in {0, 1}
newer-active in {0, 1}
```

### Context probes

Every operator is evaluated once with the applicability gate open and once for
each independently closed applicability gate: scope and time. Registered
modality routes and polarity transformations are evaluated as distinct
behavioral probes. This prevents the behavioral coordinate from treating
context as an unrelated classification head or treating negation as
non-applicability.

### Counterfactual probes

For every directional factor, repeat the complete applicable probe bank with
the two atom bindings swapped. For every symmetric factor, the swapped response
must be identical after canonical output permutation.

## Behavioral signature

For a legal operator \(\Psi_j\) and its canonical port schema, define:

\[
B_j=\operatorname{concat}_{s\in\mathcal Q}
\operatorname{encode}(R_{\Psi_j}(s)),
\]

where \(\mathcal Q\) is the frozen probe bank. Encoding uses fixed per-channel
scales and clipping bounds from configuration. The signature is not globally
L2-normalized because zero and absolute magnitude carry meaning.

The signature contains, in this order:

1. applicability and diagnostic channels;
2. port/channel read-write masks;
3. scalar energy;
4. gradients for affected state variables;
5. one-step projected state changes;
6. typed exact-output channels;
7. the same values under port-swap counterfactuals.

The artifact stores both a full-precision canonical signature and a quantized
comparison signature. Its identity is the hash of:

```text
schema version
operator implementation hash
probe-bank hash
channel-order hash
channel-scale hash
full-precision response bytes
```

## Five canonical factor families

### 1. Directed transfer

Canonical form:

```text
transfer(source, target, mode)
mode = derive | oblige
```

For `derive`, corresponding to G1 `implies`:

\[
E=\left[\max(0,y_{source}-y_{target})\right]^2.
\]

When the source is exactly active, the exact output authorizes a derivation of
the target. The field step may increase target activation but cannot itself
authorize that derivation.

The source activation is read-only. The target activation is writable when the
runtime state permits it.

For `oblige`, corresponding to G1 `requires`:

\[
E=\left[\max(0,y_{source}-y_{target})\right]^2.
\]

Here `source` is the dependent and `target` is the prerequisite. The mode emits
an obligation when the source is active and the target is inactive. It never
emits a derivation.

Both activation ports are read-only for `oblige`; optimization cannot satisfy
the requirement by inventing its prerequisite.

These modes intentionally share an energy law and are distinguished by their
typed result channel. A signature containing energy alone is invalid.

Port swap must change the signature for both modes.

### 2. Directed evidence

Canonical form:

```text
evidence(source, target, channel)
channel = support | opposition | uncertainty
```

For confidence-authority strength \(w\) and source activation \(y_s\), the
factor emits contribution \(d=wy_s\). The selected target channel composes it
with its current value using the registered bounded aggregator:

\[
e^{+\prime}_t=e^+_t\oplus d \quad\text{for support},
\]

\[
e^{-\prime}_t=e^-_t\oplus d \quad\text{for opposition},
\]

\[
u'_t=u_t\oplus d \quad\text{for uncertainty}.
\]

The first draft uses probabilistic union:

\[
x\oplus d=1-(1-x)(1-d).
\]

The three modes must differ through the destination channel even when their
scalar strengths are equal. Port swap must change the signature.

The source activation is read-only. Only the selected target evidence channel
is writable.

### 3. Symmetric constraint

Canonical form:

```text
constraint(member_a, member_b, mode)
mode = equal | exclude
```

For `equal`:

\[
E=(y_a-y_b)^2.
\]

For `exclude`:

\[
E=\left[\max(0,y_a+y_b-1)\right]^2.
\]

`exclude` emits a conflict when both members are exactly active. `equal` emits
no conflict and may authorize the registered equality propagation only after
exact validation.

Both members expose activation as a potentially writable channel, but the
runtime mutability mask keeps observations and accepted facts fixed. A hard
exclusion never erases fixed evidence to hide a conflict.

Both modes are invariant under port swap. The compiler canonicalizes incidence
by stable atom ID before FieldIR serialization. It must not be penalized for
choosing arbitrary `left` and `right` surface labels.

### 4. Ordered temporal

Canonical form:

```text
precedes(earlier, later)
```

With both time masks known:

\[
E=\left[\max(0,t_{earlier}-t_{later})\right]^2.
\]

A positive residual emits a temporal-violation channel. Equal coordinates are
permitted only when the source semantics allow non-strict ordering; strictness
is a future registered mode and is not inferred implicitly.

Temporal coordinates are read-only in the first kernel. The factor reports a
violation or ambiguity; it does not rewrite event time.

Surface `before(A,B)` becomes `precedes(A,B)`. Surface `after(A,B)` becomes
`precedes(B,A)`. `after` is therefore not a second learned operator.

Port swap must change the signature except on deliberately tied individual
probes; separation is evaluated over the complete probe bank.

### 5. Ordered state replacement

Canonical form:

```text
replace(older, newer)
```

When the newer claim is active:

\[
\ell'_{older}=\ell_{older}(1-y_{newer}).
\]

The exact output emits a supersession event connecting the newer claim to the
older claim. It does not delete provenance or historical state. An inactive
newer claim produces no lifecycle change.

The newer activation is read-only. Only the older claim's live channel is
writable.

Port swap must change the signature.

## Surface-to-canonical projection

The first registry projection is:

| Surface/G1 relation | Canonical family | Mode and ports |
| --- | --- | --- |
| `implies` | `transfer` | `derive(premise, conclusion)` |
| `requires` | `transfer` | `oblige(dependent, prerequisite)` |
| `supports` | `evidence` | `support(evidence, claim)` |
| `opposes` | `evidence` | `opposition(evidence, claim)` |
| `uncertainty` | `evidence` | `uncertainty(source, claim)` |
| `equals` | `constraint` | `equal(min_id, max_id)` |
| `excludes` | `constraint` | `exclude(min_id, max_id)` |
| `before` | `precedes` | `(first, second)` |
| `after` | `precedes` | `(second, first)` |
| `supersedes` | `replace` | `(older, newer)` |

Projection back to G1 uses the canonical registered representative. `after`
may be retained as source-form metadata but is serialized executably as the
equivalent canonical `before` incidence. This requires an explicit migration
decision before implementation because current G1 permits both identifiers.

## Embedder contract

Given text \(x\) and candidate content atoms, the embedder proposes:

\[
C(x)=(\hat B,\hat P,\hat\kappa,\hat w,c),
\]

where \(\hat B\) is a behavioral signature, \(\hat P\) is a distribution over
atom-to-port incidence, \(\hat\kappa\) is typed context, \(\hat w\) contains
bounded continuous strengths, and \(c\) is calibrated confidence.

The deterministic projector:

1. filters signatures by arity and atom types;
2. evaluates every legal family, mode, and port permutation;
3. finds the nearest signature under the registered channel-weighted distance;
4. requires both an absolute-distance threshold and a winner/runner-up margin;
5. validates context and continuous parameter ranges;
6. constructs one canonical factor;
7. round-trips it through FieldIR and G1 validation;
8. accepts atomically or abstains.

Nearest-neighbor choice without both thresholds is forbidden.

## Training objective

The initial model objective is:

\[
\mathcal L=
\lambda_B L_{behavior}
+\lambda_P L_{ports}
+\lambda_I L_{intervention}
+\lambda_K L_{context}
+\lambda_C L_{cycle}
+\lambda_A L_{abstention}.
\]

- `behavior` matches the complete canonical response signature.
- `ports` matches exact atom-to-port incidence, quotienting symmetric port
  permutations.
- `intervention` uses reversal and port-swap minimal pairs.
- `context` matches typed applicability gates.
- `cycle` requires predicted signature → canonical factor → executed signature
  to recover the same topology cell.
- `abstention` calibrates malformed, ambiguous, and out-of-registry language
  outside every acceptance region.

No loss directly rewards a surface relation name. Names are serialization
targets obtained only after behavioral projection.

## Representation gates

These gates must pass before any language model is trained:

1. Every registered canonical factor has a deterministic signature across
   repeated processes and machines within the configured numeric tolerance.
2. Every pair of semantically distinct factors has nonzero registered distance
   over the complete probe bank.
3. Every directional factor differs from its port-swapped form by at least the
   frozen separation margin.
4. Every symmetric factor matches its port-swapped form within tolerance.
5. `before(A,B)` and `after(B,A)` produce identical canonical factors and
   signatures.
6. `derive` and `oblige` remain distinguishable despite sharing an energy law.
7. Support, opposition, and uncertainty remain distinguishable at equal
   strength.
8. Every canonical factor round-trips exactly through FieldIR and G1.
9. No probe can reduce a read-only premise, source, newer claim, or temporal
   coordinate to satisfy a residual.
10. A perturbed signature between two acceptance cells is rejected when it
   fails distance or margin requirements.
11. Provenance and source identity never affect behavioral distance.

Failure stops the experiment and means the proposed topology is not a suitable
compiler target.

## Later language-kernel gates

After the representation passes, the gold-content language kernel retains the
existing safety boundary:

- accepted exact factor precision: at least `0.99`;
- safe coverage: at least `0.95` for the five-family controlled suite;
- exact canonical family and mode: at least `0.99`;
- exact directional port binding: at least `0.995`;
- symmetric binding modulo permutation: `1.00` on accepted cases;
- exact context applicability: at least `0.995`;
- reversal false accepts: `0`;
- invalid FieldIR or G1 insertions: `0`;
- behavioral cycle equality: `1.00` on accepted factors;
- provenance integrity: `1.00`.

Thresholds and data counts remain draft values until the representation test
establishes measured signature distances and noise scales.

## Controls

- relation-name classifier with the same encoder;
- G2.5 independent operator/role/context heads;
- behavioral signature without typed output channels;
- behavioral signature without swap interventions;
- projector without the winner/runner-up margin;
- randomized probe bank of equal size;
- context supplied through a separate classification head;
- surface `before` and `after` treated as independent operators.

## Testing strategy

The representation stage requires:

- unit tests for every energy, gradient, typed output, applicability gate,
  modality route, and polarity transformation;
- finite-difference checks for differentiable channels;
- metamorphic tests for swap invariance and directionality;
- exact canonicalization tests for inverse surface forms;
- property tests over bounded state grids;
- signature hash and serialization round trips;
- FieldIR/G1 projection and rejection tests;
- determinism tests across process restarts.

The language stage adds split-disjoint paraphrases, reversal minimal pairs,
ambiguous cases, and evaluator-only gold factors.

## Project structure

If this draft is approved, the experiment will use:

```text
src/topology_g210/                     implementation
tests/topology_g210/                   focused tests
configs/topology-g2-10.json            frozen probes, scales, and gates
docs/experiments/gaps/g02-10/          specification and eventual report
workspaces/topology-g2-10/             ignored generated artifacts
```

## Commands

The exact CLI is not yet authorized. The intended command boundary is:

```bash
PYTHONPATH=src python -m topology_g210 representation-check --workspace workspaces/topology-g2-10
PYTHONPATH=src python -m topology_g210 dataset-build --workspace workspaces/topology-g2-10
PYTHONPATH=src python -m topology_g210 develop --workspace workspaces/topology-g2-10
PYTHONPATH=src python -m topology_g210 freeze --workspace workspaces/topology-g2-10
PYTHONPATH=src python -m topology_g210 locked-suite-build --workspace workspaces/topology-g2-10
PYTHONPATH=src python -m topology_g210 evaluate --workspace workspaces/topology-g2-10 --offline
PYTHONPATH=src python -m topology_g210 verify --workspace workspaces/topology-g2-10 --offline
```

Repository verification remains:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
git diff --check
```

## Boundaries

- Always: derive topology coordinates from executable behavior; preserve exact
  incidence and provenance; validate atomically; retain abstention.
- Ask first: change G1 canonical relation identifiers; change FieldIR semantic
  hashes; add a factor family; change the frozen probe bank; add dependencies.
- Never: authorize insertion from vector distance alone; tune on locked data;
  collapse typed result channels into scalar energy; score symmetric factors as
  directional; silently guess missing temporal or contextual applicability.

## Open decisions before registration

1. Whether G1 `after` is migrated to canonical `before` incidence or retained
   as a lossless surface alias around the same behavioral operator.
2. Whether temporal order is strict or non-strict in the first kernel.
3. Whether evidence aggregation uses probabilistic union or an alternative
   registered bounded monoid.
4. The fixed projected-step learning rate, per-channel scales, clipping bounds,
   numeric dtype, and cross-machine tolerance.
5. Signature distance metric and the absolute and relative acceptance margins.
6. Whether confidence and authority belong in the predicted behavioral
   signature or remain separately calibrated scalar parameters.

Implementation must not begin until these decisions and the representation
gates are reviewed and frozen.
