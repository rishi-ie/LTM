# LTM Scaling Laws and Runtime Metrics

> This is non-normative background. The bounded current contract is
> [LTM-ARCH-1.2](architecture-lock-v1.md).

## 1. Purpose and claim boundary

LTM is positioned as a post-transformer energy-based latent architecture.
Scaling measurements therefore separate persistent field work, request-time
optimization, exact execution and verification from optional transformer
adapter cost at compilation or realization boundaries.

This document defines how a Latent Topology Model (LTM) reports size, storage,
compute, quality, and scaling behavior.

It is primarily a measurement specification. The equations are hypotheses or
reporting contracts until they are fitted to runs at multiple scales. The
controlled CNTG-1-R2 measurements are summarized in
[CNTG-1-R2 report](../experiments/cntg-1-r2/report.md); they should not be generalized beyond that fictional
distribution.

The central rule is:

> LTM size is multidimensional. Learned weights, compiled knowledge, topology
> structure, active inference work, storage bandwidth, and answer quality must
> be reported separately.

A single parameter count is insufficient because an LTM may have a relatively
small learned core and a very large mutable compiled latent field.

The architecture described here is the general topology with hierarchical
domain regions, typed bridges, nested event/reasoning capsules, latent
optimization, verification, and a bounded decoder.

## 2. The LTM size vector

Every release reports the persistent size vector:

\[
\mathbf S_{\mathrm{LTM}}=
(P_L,B_K,T_E,N_F,N_C,N_D,N_B,B_P).
\]

| Symbol | Name | Meaning |
| --- | --- | --- |
| \(P_L\) | Learned parameters | Encoder, field evaluator, controller, adapter, and decoder weights |
| \(B_K\) | Compiled knowledge state | Bytes used by compiled field, topology, factors, indexes, and summaries |
| \(T_E\) | Source token equivalent | Accepted source material represented by the topology |
| \(N_F\) | Typed factors | Executable relation, rule, constraint, conflict, and verifier-linked factors |
| \(N_C\) | Capsules | Event, episode, and reasoning capsules |
| \(N_D\) | Domain regions | Seeded, discovered, promoted, and provisional regions |
| \(N_B\) | Bridges | Cross-domain and cross-capsule bridge relations |
| \(B_P\) | Provenance bytes | Exact source, span, lineage, and version records |

### 2.1 Learned parameters

\[
P_L=
P_{\mathrm{compiler}}
+P_{\mathrm{placement}}
+P_{\mathrm{controller}}
+P_{\mathrm{field}}
+P_{\mathrm{adapter}}
+P_{\mathrm{decoder}}.
\]

This is the number most comparable to an LLM parameter count.

It excludes mutable facts, capsules, relations, topology edges, field
coefficients generated from user data, indexes, and provenance.

The report must include:

- parameter count by component;
- numeric precision;
- quantization format;
- resident versus streamed weights;
- training-only versus serving weights;
- decoder size;
- verifier code and data size separately.

### 2.2 Compiled knowledge state

`CKS` means **Compiled Knowledge State**:

```text
CKS = field coefficients
    + topology objects and relations
    + typed factors
    + domain and bridge indexes
    + folded capsule summaries
    + exact capsule interiors
    + caches and update journals
    + verifier artifacts
```

Report the breakdown, not only the total:

```text
Compiled field coefficients: 480 GB
Topology and factors:        610 GB
Capsule summaries/interiors: 420 GB
Indexes and summaries:       190 GB
Provenance:                  300 GB
Update and cache reserve:     80 GB
Total CKS:                  2.08 TB
```

CKS is not equivalent to a parameter count. A field value, relation edge,
source span, and verifier certificate have different semantics and storage
costs.

### 2.3 Source token equivalent

`T_E` means **Source Token Equivalent**. It records how much source material
has been accepted and represented, even when the compiled form is not text.

Report:

- ingested source tokens;
- accepted source tokens;
- compiled source token equivalent;
- exact recoverable source tokens;
- deduplicated proposition count;
- superseded proposition count;
- quarantined source tokens.

`100B-T_E` does not mean a 100-billion-token request context. It means that
roughly that much source material has been persistently compiled.

## 3. Topology structure metrics

The compiled state must also report counts and distributions:

| Metric | Meaning |
| --- | --- |
| `N_obj` | All entities, values, events, claims, rules, goals, and assignments |
| `N_rel` | All typed relation instances |
| `N_fact` | Constraint and factor instances |
| `N_cap` | Capsules, including nesting depth distribution |
| `N_dom` | Domain regions and subregions |
| `N_bridge` | Cross-domain and cross-capsule bridges |
| `N_axiom` | Domain-scoped hard axioms |
| `N_rule` | Reusable rule templates |
| `N_conflict` | Explicit contradiction groups |
| `N_proof` | Reusable proof or derivation structures |
| `D_cap,max` | Maximum capsule nesting depth |
| `d_rel,avg` | Average relation degree |
| `d_bridge,avg` | Average cross-domain bridge degree |
| `d_factor,avg` | Average number of state variables per factor |

These metrics reveal whether growth is producing useful structure or a dense,
unmanageable graph.

## 4. Active Inference Footprint

Persistent size does not determine request cost. Every request reports:

\[
\mathbf I_{\mathrm{request}}=
(D_A,F_A,C_O,B_A,K,d,L_\pi,H,IO,M_A,M_H).
\]

| Symbol | Name | Meaning |
| --- | --- | --- |
| \(D_A\) | Active domains | Domain regions contributing to the request |
| \(F_A\) | Active factors | Exact factors evaluated during optimization |
| \(C_O\) | Opened capsules | Capsules whose interiors were materialized |
| \(B_A\) | Active bridges | Cross-domain/capsule bridges traversed |
| \(K\) | Optimizer steps | Accepted or evaluated field updates |
| \(d\) | State width | Continuous and structured latent state size |
| \(L_\pi\) | Proof depth | Longest verified derivation path |
| \(H\) | Branch count | Active contradiction, hypothesis, or search branches |
| \(IO\) | Data movement | Bytes read from SSD, host memory, and accelerator memory |
| \(M_A\) | Accelerator memory | Peak accelerator or unified memory |
| \(M_H\) | Host memory | Peak host memory |

This vector is called the **Active Inference Footprint (AIF)**.

Example:

```text
AIF-O2:
  active domains: 4
  active factors: 3,840
  opened capsules: 11
  active bridges: 7
  optimizer steps: 18
  proof depth: 9
  branches: 3
  SSD reads: 720 MB
  peak accelerator memory: 31 GB
```

## 5. Standard workload profiles

Scaling numbers are meaningless unless the request workload is fixed.

### O1 — Light ordinary

```text
Maximum optimizer steps: 16
Maximum active factors: 1,024
Maximum opened capsules: 8
Maximum active bridges: 8
Maximum branches: 4
Maximum decoder output: 256 tokens
```

### O2 — Standard ordinary

This is the default comparison workload:

```text
Maximum optimizer steps: 32
Maximum active factors: 4,096
Maximum opened capsules: 64
Maximum active bridges: 32
Maximum branches: 16
Maximum decoder output: 512 tokens
```

### O3 — Deep ordinary

```text
Maximum optimizer steps: 128
Maximum active factors: 32,768
Maximum opened capsules: 512
Maximum active bridges: 256
Maximum branches: 64
Maximum decoder output: 2,048 tokens
```

### EX — Exhaustive

Exhaustive inference is request-budgeted rather than assigned one universal
profile:

```text
EX[K=1000,F=2M,C=50K,B=10K,timeout=300s]
```

An exhaustive result must report the actual closure explored, not merely the
requested budget.

## 6. Runtime envelope metrics

Every model publishes two hardware profiles.

### 6.1 Minimum Runtime Profile

The smallest tested machine that can execute the chosen workload, possibly with
high latency and low concurrency.

### 6.2 Effortless Runtime Profile

The recommended machine with at least 25–30% headroom, no swapping, sustained
operation, and the stated latency/concurrency target.

Define:

\[
\mathrm{ERP}=(M_A,M_H,S_D,B_D,C_{\mathrm{CPU}},L_{95},Q),
\]

where:

- \(M_A\): accelerator or unified memory;
- \(M_H\): host memory;
- \(S_D\): free SSD capacity;
- \(B_D\): sustained SSD bandwidth;
- \(C_{\mathrm{CPU}}\): recommended CPU cores;
- \(L_{95}\): p95 latency target;
- \(Q\): supported concurrency.

For unified-memory machines, use `U` instead of separate accelerator and host
memory.

Example:

```text
ERP-O2[A48-H64-S2.5T-B3-C16]@500ms×1
```

This means:

- 48 GB accelerator memory;
- 64 GB host memory;
- 2.5 TB free SSD;
- 3 GB/s sustained SSD bandwidth;
- 16 CPU cores;
- O2 workload;
- p95 latency under 500 ms;
- one concurrent request.

For a 32 GB Mac:

```text
ERP-O2[U32-S2.5T-B3-C12]@30m×1
```

The label makes the trade-off explicit: the model can run on the machine, but
the response may take much longer because the field is streamed sequentially.

## 7. Storage scaling laws

Let (N) represent compiled objects and let the separate structural counts be
(N_F,N_C,N_B). A basic storage model is:

\[
B_K(N)=B_0
+b_O N_O
+b_F N_F
+b_C N_C
+b_B N_B
+B_{\mathrm{indexes}}
+B_P.
\]

The expected asymptotic law is:

\[
B_K(N)=\Theta(N)
\]

when average factor degree and metadata size remain bounded.

Fit the empirical exponent:

\[
B_K(N)=aN^{\alpha_B}.
\]

Interpretation:

- \(\alpha_B\approx1\): expected linear storage;
- \(\alpha_B<1\): compression or deduplication is increasing;
- \(\alpha_B>1\): relations, indexes, or summaries are exploding.

Report both total bytes and bytes per accepted object:

\[
b_{\mathrm{object}}=B_K/N_O.
\]

## 8. Compilation scaling laws

Let (T_S) be source tokens and (N_F,N_C,N_B) be factors, capsules, and
bridges:

\[
C_{\mathrm{compile}}
\approx
aT_S+bN_O+cN_F+dN_C+eN_B+C_{\mathrm{validation}}.
\]

Measure:

- tokens per second through the small compiler model;
- RIR records per second;
- capsules per second;
- factors per second;
- relation-linking time;
- domain-discovery time;
- summary-compilation time;
- verifier-artifact generation time;
- peak compile memory;
- SSD write amplification.

The desired source-ingestion exponent is close to one. Entity resolution,
domain discovery, and bridge construction must be indexed to prevent hidden
quadratic behavior.

## 9. Incremental-update scaling

For (m) new validated objects in a topology containing (N) objects:

\[
C_{\mathrm{update}}=
O(m\log N)
+C_{\mathrm{link}}
+C_{\mathrm{affected\ summaries}}
+C_{\mathrm{verification}}.
\]

Measure:

- update latency by (m);
- number of field blocks rewritten;
- number of capsules resummarized;
- number of domains and bridges changed;
- number of unrelated answers that drift;
- update journal size;
- compaction frequency;
- background versus foreground work.

The key requirement is locality: adding one conversational episode should not
require rebuilding the complete field.

## 10. Addressing and sparse ordinary inference

Hierarchical addressing should be fitted as:

\[
C_{\mathrm{address}}(N)=a+b\log N+cN^{\alpha_A}.
\]

For ordinary requests, the desired (alpha_A) is near zero.

The request cost is:

\[
\begin{aligned}
C_{\mathrm{request}}={}&
C_{\mathrm{encode}}
C_{\mathrm{address}}(N)
C_{\mathrm{IO}}\\
&+K\,C_{\mathrm{field}}(F_A,d)
C_{\mathrm{capsule}}(C_O)
C_{\mathrm{bridge}}(B_A)\\
&+C_{\mathrm{verify}}(L_\pi,H)
C_{\mathrm{decode}}.
\end{aligned}
\]

If (K,F_A,C_O,B_A,d) remain bounded, active inference can remain nearly
constant as total storage grows.

This must be reported together with quality. Flat latency with severe quality
loss is not successful scaling.

## 11. Sequential batched full-field inference

When the compiled field is larger than memory, the runtime may process it in
sequential blocks.

Let:

- (S_F): total field size;
- (M_U): usable memory after the decoder, operating system, and working state;
- (S_{mathrm{block}}): actual block size;
- (B): number of sequential blocks;
- (K): number of full-field passes or optimizer sweeps.

The batch count is:

\[
B=\left\lceil\frac{S_F}{S_{\mathrm{block}}}\right\rceil,
\qquad S_{\mathrm{block}}<M_U.
\]

An ideal lower bound uses (M_U), but production execution must reserve
headroom:

\[
S_{\mathrm{block}}\leq0.70M_U.
\]

For a 2 TB field on a 32 GB machine:

\[
\frac{2\,\mathrm{TB}}{32\,\mathrm{GB}}\approx64
\]

ideal blocks. With only 20–24 GB safely usable, the practical count is closer
to 84–100 blocks.

If every optimizer step requires a full field pass:

\[
C_{\mathrm{full}}=O(KB),
\]

and approximate time is:

\[
T_{\mathrm{full}}
\approx
K\left(
\frac{S_F}{R_{\mathrm{storage}}}
+B\,T_{\mathrm{block\ overhead}}
\right).
\]

If the runtime performs one streaming pass to accumulate sufficient statistics
and then performs local optimization on the compressed result, the cost can be
closer to:

\[
T_{\mathrm{stream+local}}
\approx
\frac{S_F}{R_{\mathrm{storage}}}
+T_{\mathrm{global\ reduction}}
+T_{\mathrm{local\ optimization}}.
\]

This distinction is crucial. The response time is not “the field size times
32 GB.” It is determined by the number of passes, usable block size, storage
bandwidth, block overhead, reduction method, and decoder time.

Sequential execution makes a 2 TB field physically runnable on a 32 GB Mac,
but it does not make the request cheap or fast.

## 12. Capsule scaling laws

For capsules, report:

### 12.1 Capsule opening recall

\[
\mathrm{COR}@B=
\frac{\text{conclusion-changing capsules opened}}
{\text{all conclusion-changing capsules}}.
\]

### 12.2 Capsule opening precision

\[
\mathrm{COP}@B=
\frac{\text{opened capsules that affect the verified result}}
{\text{all opened capsules}}.
\]

### 12.3 Critical capsule miss rate

The percentage of requests where a capsule that could change the verified
answer remained folded.

This should be measured separately for O1, O2, O3, and exhaustive mode.

### 12.4 Folded-summary error

Compare folded and exact execution using:

- energy error;
- force error;
- final-state drift;
- influence-ranking overlap;
- verified-answer agreement;
- causal-path agreement;
- proof-path agreement.

### 12.5 Capsule compression ratio

\[
R_C=\frac{\text{exact capsule bytes}}
{\text{folded summary bytes}}.
\]

Always report (R_C) with answer disagreement and critical-miss rate.

## 13. Domain and bridge scaling

Domain organization must be measured as the corpus grows:

- multi-label domain precision, recall, and hierarchy-aware F1;
- calibration error of domain membership;
- unknown-domain detection rate;
- provisional-domain creation rate;
- incorrect-domain-promotion rate;
- domain fragmentation and merging;
- active domains per request;
- bridge precision and recall;
- false bridge activation rate;
- missed required bridge rate;
- bridge degree and connected-component growth.

Fit bridge growth:

\[
N_B(N)=aN^{\alpha_Br}.
\]

If \(\alpha_{Br}>1\), cross-domain relations are becoming a structural
bottleneck and require pruning, summarization, or stronger scope gates.

## 14. Reasoning-depth scaling

Let (h) be verified derivation depth. Fit success as:

\[
A(h)=A_0e^{-\lambda_hh}.
\]

This is a measurement model, not an assumption that reasoning must be
exponential.

Report:

- verified success at depths 1, 2, 4, 8, 16, and 32;
- intermediate-assignment accuracy;
- proof-path accuracy;
- branch count;
- verifier rejection rate;
- unsupported-equilibrium rate;
- ordinary versus exhaustive results.

Useful headline metrics:

- `RD90`: deepest path with at least 90% verified success;
- `RD50`: deepest path with at least 50% verified success;
- `BD50`: deepest cross-domain bridge path with at least 50% verified success;
- `CD50`: deepest capsule-opening chain with at least 50% verified success.

## 15. Field-quality and interference scaling

Measure quality as unrelated knowledge grows:

\[
\Delta Q(N)=Q(N+N_{\mathrm{irrelevant}})-Q(N).
\]

Important metrics:

- rare-fact retention;
- conclusion preservation;
- contradiction preservation;
- irrelevant-data drift;
- final-state drift;
- exact-versus-approximate energy error;
- exact-versus-approximate force error;
- active-factor recall;
- capsule-summary answer agreement;
- bridge-path preservation;
- update-induced unrelated-answer drift.

An LTM that stores more knowledge but loses rare facts or changes unrelated
answers is not scaling successfully.

## 16. Verification and coverage metrics

### 16.1 Verified Solution Rate

\[
\mathrm{VSR}=
\frac{\text{verified correct solutions}}
{\text{all evaluated requests}}.
\]

VSR is more important than raw decoder answer accuracy.

### 16.2 Unsupported equilibrium rate

\[
\mathrm{UER}=
\frac{\text{numerically converged candidates rejected by verification}}
{\text{numerically converged candidates}}.
\]

This measures whether field equilibrium corresponds to valid reasoning.

### 16.3 Coverage calibration

If the system reports 95% coverage, the declared coverage group should be
complete or correct approximately 95% of the time under the stated definition.

Report:

- open obligations;
- unexplored-domain influence bound;
- untraversed-bridge influence bound;
- unopened-capsule influence bound;
- pruned branch mass;
- cycle and fixed-point handling;
- verifier completeness;
- abstention rate.

## 17. Decoder scaling and faithfulness

Report:

- factual claim precision;
- verifier compliance;
- citation precision and recall;
- provenance correctness;
- contradiction disclosure;
- uncertainty calibration;
- event-order fidelity;
- causal-status fidelity;
- capsule narrative fidelity;
- unsupported-claim rate;
- decoder latency and output tokens.

Required ablations:

- correct latent state;
- zero latent state;
- shuffled latent state;
- incorrect capsule summaries;
- omitted proof path;
- conflicting verifier result;
- decoder-only answer without authorized evidence.

The decoder must not receive credit for reasoning performed by hidden decoder
generation.

## 18. Effective Persistent Context

Instead of claiming “unlimited context,” report:

\[
\mathrm{EPC}(\delta,L,Q)
\]

as the largest compiled source size for which:

- verified quality loss is at most \(\delta\);
- p95 latency is at most (L);
- concurrency is at least (Q);
- memory remains below the runtime envelope;
- critical capsule and bridge misses remain below their limits.

Example:

```text
EPC(2pp, 500ms, concurrency=1) = 100B-T_E
```

This means the topology retains its verified quality within two percentage
points over 100 billion source-token equivalents while meeting the stated
latency and concurrency target.

## 19. Cost and hardware metrics

Every scaling report includes:

- compilation cost per million source tokens;
- incremental update cost per thousand objects;
- monthly storage cost;
- p50, p95, and p99 latency;
- requests per second;
- accelerator-seconds per request;
- CPU-seconds per request;
- joules per request;
- SSD bytes read and written;
- peak accelerator memory;
- peak host memory;
- decoder tokens per request;
- verifier cost;
- total cost per O1, O2, O3, and exhaustive request.

LTM may be I/O-bound rather than FLOP-bound. Therefore FLOPs alone are not an
acceptable compute report.

## 20. Recommended public model label

Use this compact form:

```text
LTM-G1
1.3B-LP / 2TB-CKS / 100B-T_E
AIF-O2[D4-F4096-C64-B32-K32-H16-IO1.1G]
ERP-O2[A48-H64-S2.5T-B3-C16]@500ms×1
```

The label communicates:

- learned model size;
- persistent field size;
- source capacity;
- active request work;
- recommended hardware;
- storage requirements;
- latency and concurrency target.

All values above are illustrative.

## 21. Scaling experiment protocol

Use geometrically increasing topology sizes, for example:

```text
10^3, 10^4, 10^5, 10^6, 10^7, 10^8 accepted objects
```

At each size, hold constant:

- topology version;
- encoder and decoder versions;
- numeric precision;
- relation and factor schemas;
- workload distribution;
- ordinary profile;
- quality evaluation suite;
- hardware and storage configuration.

For every size, record:

1. source and compiled bytes;
2. object, factor, domain, bridge, and capsule counts;
3. compiler time and peak memory;
4. incremental-update time;
5. p50/p95/p99 request latency;
6. active inference footprint;
7. SSD read/write volume;
8. accelerator and host memory;
9. verified solution rate;
10. reasoning depth metrics;
11. capsule and bridge misses;
12. decoder faithfulness;
13. cost and energy;
14. fitted scaling exponents with confidence intervals.

Run separate experiments for:

- irrelevant-data growth;
- relevant-data growth;
- capsule nesting growth;
- bridge-density growth;
- contradiction-density growth;
- reasoning-depth growth;
- concurrent requests;
- sequential full-field passes;
- sparse ordinary inference;
- exhaustive inference.

## 22. Recommended scaling gates

These are proposed gates for a mature implementation, not current results.

### Storage and compilation

- storage exponent between 0.95 and 1.10;
- full compilation exponent below 1.15;
- incremental updates touch less than 1% of the field for local changes;
- provenance completeness of 100% for accepted objects.

### Ordinary inference

- active-factor exponent at most 0.10;
- ordinary p95 latency exponent at most 0.10;
- no operating-system swapping;
- at least 25% memory headroom in ERP hardware;
- quality loss under 2 percentage points during 100x irrelevant-data growth.

### Capsules and bridges

- critical capsule miss rate below 1%;
- folded-summary conclusion agreement above 99%;
- bridge recall above 99% on required paths;
- inferred causal claims never silently promoted to verified facts.

### Reasoning and verification

- UER below 5% for ordinary verified tasks;
- coverage calibration error below 5 percentage points;
- no numerical failures;
- proof-path provenance completeness of 100%;
- decoder unsupported-claim rate below 1%.

The gates should be revised after the first controlled implementation results.

## 23. Reporting template

Every scaling run should produce a Markdown report containing:

```text
Topology ID and version:
Encoder, factor, optimizer, verifier, and decoder versions:
Source manifest hash:
Field manifest hash:
Hardware:
Storage device and sustained bandwidth:
Workload profile:

Persistent state:
  Learned parameters:
  Compiled knowledge bytes:
  Source token equivalent:
  Objects / factors / capsules / domains / bridges:

Request footprint:
  Active domains:
  Active factors:
  Opened capsules:
  Active bridges:
  Optimizer steps:
  Proof depth and branches:
  SSD I/O:
  Peak accelerator and host memory:

Quality:
  Verified Solution Rate:
  Unsupported Equilibrium Rate:
  RD50 / RD90 / BD50 / CD50:
  Critical capsule miss rate:
  Coverage calibration error:
  Decoder unsupported-claim rate:

Scaling fits:
  Storage exponent:
  Compile exponent:
  Active-factor exponent:
  Latency exponent:
  I/O exponent:
  Confidence intervals:

Runtime envelope:
  Minimum profile:
  Effortless profile:
  p50 / p95 / p99 latency:
  Concurrency:
  Cost per request:
```

## 24. Final rule

An LTM should never be described only as:

```text
“A 2 TB model”
```

It should be described as:

```text
learned core size
+ compiled knowledge size
+ source capacity
+ active inference footprint
+ hardware envelope
+ verified quality
+ measured scaling exponents.
```

That is the minimum information a user needs to know whether the model will
fit, how much it will cost, how long it will take, and whether its quality
survives as the persistent field grows.
