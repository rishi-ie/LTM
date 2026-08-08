# L5 — Compiled Multi-Hypothesis Latent Field Equilibrium

Status: **PENDING AUTHORITATIVE EXECUTION**

No measured classification is authorized by this tracked report yet.

Specification: [L5 specification](specification.md)

Configuration: [configs/ltm-limit-l5.json](../../../../configs/ltm-limit-l5.json)

Authoritative workspace: `workspaces/ltm-limit-l5-r1/`

This file is the permanent report template. The lifecycle-generated workspace
`report.md` is only a stage summary. Values may be copied here only after the
workspace artifacts, raw prediction shards, evaluator outputs, controls,
interventions, replay, and resource logs have been audited. `Pending` is not a
zero and must never be treated as a measured failure or success.

## 1. Result at a glance

| Item | Measured result |
|---|---|
| Mechanical classification | **Pending** |
| Raw controlled compiler track | **Pending** |
| Supplied-input equilibrium track | **Pending** |
| Locked raw-chain end-to-end track | **Pending** |
| Accepted verified precision | **Pending** |
| Incorrect accepted compilations | **Pending** |
| Incorrect accepted candidates | **Pending** |
| Safe coverage | **Pending** |
| All-case exactness | **Pending** |
| Dependency 9–16 exactness | **Pending** |
| Contradiction/multi-hypothesis result | **Pending** |
| Learned-geometry causal mechanism gate | **Pending** |
| Causal controls | **Pending** |
| Independent verification | **Pending** |
| Stress annotation | **Pending** |
| Scale result | **Pending** |
| First failed boundary | **Pending** |

Plain-language conclusion: **Pending measured evidence.**

## 2. Evidence ledger

| Artifact | Required state | Audit result |
|---|---|---|
| `model-check.json` | pass | Pending |
| `dataset-manifest.json` | pass | Pending |
| `compiler-development-results.json` | pass | Pending |
| `field-results.json` | pass | Pending |
| `development-results.json` | pass | Pending |
| `calibration.json` | pass | Pending |
| `frozen-manifest.json` | hash-valid | Pending |
| `locked-suite-manifest.json` | hash-valid | Pending |
| `locked-runtime-access-audit.json` | separate runtime PID; all gold-path probes denied | Pending |
| `locked-results.json` | measured once | Pending |
| `stress-results.json` | integrity-valid | Pending |
| `scale-results.json` | pass | Pending |
| `intervention-results.json` | pass | Pending |
| `controls.json` | pass | Pending |
| `verification.json` | pass | Pending |
| Prediction shard hashes | immutable and complete | Pending |
| Execution history | complete | Pending |

Authoritative source/config/checkpoint hashes: **Pending**

Selected-kernel training audit (exactly 600 shared-coordinate/compiler-
alignment steps; no separate field-law training): **Pending**

Locked-suite generation timestamp and attempt: **Pending**

Scientific audit author/date: **Pending**

## 3. Track A — Raw controlled compiler

This section reports only raw controlled source/prompt compilation. It must not
contain scores derived from supplied `PublicFieldCase` fixtures.

| Metric | Gate | Result | Wilson 95% CI where applicable |
|---|---:|---:|---:|
| Locked compiler items | 16,000 configured | Pending | — |
| Accepted semantic precision | `1.00` | Pending | Pending |
| Safe coverage | `>=0.95` | Pending | Pending |
| Exact content agreement | `>=0.99` | Pending | Pending |
| Shared-coordinate recall@8 | `>=0.99` | Pending | Pending |
| Incorrect accepted compilations | `0` | Pending | — |
| One encoder call per item | `1.00` | Pending | — |

Failure-code distribution: **Pending**

Malformed/forbidden input behavior: **Pending**

Split-disjointness and leakage audit: **Pending**

## 4. Track B — Supplied-input equilibrium

These cases begin from already compiled field and prompt fixtures. The rows
below must retain the exact scientific labels.

| Metric | Gate | Result | Wilson 95% CI |
|---|---:|---:|---:|
| Primary locked queries | 8,000 configured | Pending | — |
| `supplied_input_contract` | `1.00` integrity | Pending | Pending |
| `optimizer_conditional_on_supplied` | reported separately | Pending | Pending |
| `end_to_end_from_supplied` | `>=0.88` all-case boundary | Pending | Pending |
| Accepted verified precision | `1.00` | Pending | Pending |
| Incorrect accepted candidates | `0` | Pending | — |
| Safe coverage | `>=0.90` | Pending | Pending |
| Answerable exactness | `>=0.90` | Pending | Pending |
| Corpus/oracle agreement | `1.00` | Pending | Pending |

`supplied_input_contract` is **not** raw compiler accuracy.

Locked lifecycle metric availability:

- The immutable supplied-field predictions are independently rescored for
  answerable and unsupported exactness, oracle optimum, energy, coverage,
  convergence, frontier recall, certificates, family, domain, dependency band,
  and exact depth.
- The lifecycle’s `safe_coverage` is computed from the same exact-result count
  as `all_case_exactness`; the two values are not independent.

## 5. Track C — Locked raw-chain end to end

| Metric/check | Gate | Measured result | Wilson 95% CI where applicable |
|---|---:|---:|---:|
| Locked raw-chain cases | `600` configured | Pending | — |
| Accepted precision | `1.00` | Pending | Pending |
| Incorrect accepted predictions | `0` | Pending | — |
| Safe coverage | `>=0.90` | Pending | Pending |
| All-case exactness | `>=0.88` | Pending | Pending |
| One encoder pass per item | `1.00` | Pending | — |
| Unknown/conflict/alternative agreement | `1.00` | Pending | Pending |
| Development compiler→writer round-trip | `1.00` | Pending | — |
| Development two-body complete chain | pass | Pending | — |
| Exact phase/context/provenance preservation | `1.00` | Pending | — |
| Factual operations | `0` | Pending | — |

### Raw-chain result by exact depth

| Depth | Cases | Exactness | Wilson 95% CI |
|---:|---:|---:|---:|
| 1 | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending |
| 3 | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending |
| 5 | Pending | Pending | Pending |
| 6 | Pending | Pending | Pending |
| 7 | Pending | Pending | Pending |
| 8 | Pending | Pending | Pending |
| 9 | Pending | Pending | Pending |
| 10 | Pending | Pending | Pending |
| 11 | Pending | Pending | Pending |
| 12 | Pending | Pending | Pending |
| 13 | Pending | Pending | Pending |
| 14 | Pending | Pending | Pending |
| 15 | Pending | Pending | Pending |
| 16 | Pending | Pending | Pending |

This is a genuine locked raw compiler→writer→optimizer→verifier→decoder panel,
but it contains generated linear chains. It does not cover the full supplied-
fixture conjunction, contradiction, alternatives, scope, and unknown families.
Its public identifiers and text must also audit as opaque: no family,
disposition, depth, route, or terminal answer may be recoverable from those
public fields.

## 6. Primary results by family

| Family | Gate | Cases | Exactness | Wilson 95% CI |
|---|---:|---:|---:|---:|
| One body | `>=0.97` | Pending | Pending | Pending |
| Dependency 2–4 | `>=0.95` | Pending | Pending | Pending |
| Dependency 5–8 | `>=0.92` | Pending | Pending | Pending |
| Dependency 9–16 | `>=0.85` | Pending | Pending | Pending |
| Conjunction | `>=0.90` | Pending | Pending | Pending |
| Weighted contradiction | `>=0.95` | Pending | Pending | Pending |
| Balanced contradiction | `>=0.95` ambiguity boundary | Pending | Pending | Pending |
| Alternatives | `>=0.95` ambiguity/unknown boundary | Pending | Pending | Pending |
| Scope isolation | reported | Pending | Pending | Pending |
| Unknown | `>=0.95` ambiguity/unknown boundary | Pending | Pending | Pending |

## 7. Domain and depth results

### Domain

| Domain | Cases | Exactness | Wilson 95% CI | Interpretation |
|---|---:|---:|---:|---|
| Controlled mathematics | Pending | Pending | Pending | Pending |
| Abstract signed realities | Pending | Pending | Pending | Pending |

The mathematics row covers the implemented controlled identity-transformation
fixture family. It must not be described as broad theorem proving.

Domain rows and Wilson intervals are not emitted by the current locked lifecycle
aggregate. Populate them only from an audited post-score over immutable locked
predictions; otherwise retain `Pending`.

### Exact dependency count

| Dependency count | Cases | Exactness | Wilson 95% CI |
|---:|---:|---:|---:|
| 1 | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending |
| 3 | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending |
| 5 | Pending | Pending | Pending |
| 6 | Pending | Pending | Pending |
| 7 | Pending | Pending | Pending |
| 8 | Pending | Pending | Pending |
| 9 | Pending | Pending | Pending |
| 10 | Pending | Pending | Pending |
| 11 | Pending | Pending | Pending |
| 12 | Pending | Pending | Pending |
| 13 | Pending | Pending | Pending |
| 14 | Pending | Pending | Pending |
| 15 | Pending | Pending | Pending |
| 16 | Pending | Pending | Pending |

## 8. Dynamics, frontier, certificates, and decoder

| Metric | Gate | Result |
|---|---:|---:|
| Energy-nonincreasing accepted updates | `1.00` | Pending |
| Actual aggregate energy recorded without cosmetic clamp | `1.00` | Pending |
| Accepted-query convergence | `>=0.99` | Pending |
| Frontier stability | `>=0.99` | Pending |
| Required-body frontier recall | `>=0.99` | Pending |
| Coverage certification | `>=0.90` threshold | Pending |
| Support-certificate safety | `1.00` | Pending |
| Candidate-confidence oracle agreement | `1.00` | Pending |
| Independent proof/source replay | `1.00` | Pending |
| Decoder authorization agreement | `1.00` | Pending |
| Unauthorized realized candidates | `0` | Pending |
| Factual field mutations | `0` | Pending |

Dominant runtime failure codes: **Pending**

Representative successful trajectory: **Pending audited example**

Representative failed/abstained trajectory: **Pending audited example**

## 9. Causal controls

| Control comparison | Gate | Measured effect | Pass/fail |
|---|---:|---:|---:|
| Full minus no optimization | `>=0.25` | Pending | Pending |
| Full minus fixed frontier, deep cases | `>=0.20` | Pending | Pending |
| Multi-mode minus single-mode, conflict cases | `>=0.20` | Pending | Pending |
| Context gated minus no-context, scope cases | `>=0.20` | Pending | Pending |
| Same-source raw-duplicate semantic changes | `0` | Pending | Pending |
| Full minus no learned compatibility | `>=0.05` | Pending | Pending |
| Full minus fixed state/zero geometry | `>=0.05` | Pending | Pending |
| Full minus deterministic random geometry | `>=0.05` | Pending | Pending |
| Full-system latent-state movement rate | `>0` | Pending | Pending |
| Fixed-state control movement rate | `0` | Pending | Pending |

Control result interpretation: **Pending**

If primary accuracy passes but any required causal effect fails, the report must
classify the mechanism failure rather than claim latent-equilibrium evidence.
The three learned-geometry comparisons and both movement checks form one
mandatory mechanism gate. Failure of any member forces `L5-E`; `L5-A` is
impossible regardless of exact-result accuracy.

## 10. Interventions

| Intervention metric | Gate | Result | Wilson 95% CI |
|---|---:|---:|---:|
| Decisive-support removal response | `>=0.95` | Pending | Pending |
| Irrelevant-region invariance | `>=0.95` | Pending | Pending |
| Same-source duplicate invariance | `>=0.95` | Pending | Pending |
| Conjunction-input sensitivity | `>=0.95` | Pending | Pending |
| Direction-reversal accuracy | `>=0.99` | Pending | Pending |

Counterexamples: **Pending**

## 11. Stress diagnostic

Stress results do not alter the primary classification.

| Metric | Diagnostic boundary | Result |
|---|---:|---:|
| Stress queries | 4,000 configured | Pending |
| Depth 17–32 exactness | `>=0.75` | Pending |
| Depth 33–64 exactness | `>=0.50` | Pending |
| Accepted precision | `1.00` | Pending |
| Incorrect accepted candidates | `0` | Pending |
| Deepest successful generated dependency | reported | Pending |
| Annotation | `L5-17-64-AGGREGATE-STRESS-PASS` or boundary measured | Pending |

Per-depth stress table: **Pending**

This panel measures the generated L5 dependency mechanism, not arbitrary
64-step mathematical reasoning.

## 12. Scale diagnostic

| Metric | Required/result boundary | Measured result |
|---|---:|---:|
| Primary materialized bodies | `>=100,000` | Pending |
| Shared-field query cases | up to 600 | Pending |
| Shared-field exactness | `1.00` | Pending |
| Cache verification | pass | Pending |
| Maximum active bodies per step | `<=128` | Pending |
| Maximum cumulative distinct body reads | `<=2,048` | Pending |
| Full-field scans | `0` | Pending |
| Lazy distractor corpus commitment | 1,000,000 configured | Pending |
| Distractor bodies materialized at runtime | `0` in current diagnostic | Pending |

The final prose must distinguish materialized bodies from the lazy one-million-
body corpus commitment.

## 13. Integrity, replay, and resources

| Check | Gate | Result |
|---|---:|---:|
| Runtime evaluator-gold reads | `0` | Pending |
| Runtime/evaluator process IDs differ | required | Pending |
| Runtime evaluator-path denial probes | all denied | Pending |
| Unexpected runtime evaluator-path denials | `0` | Pending |
| Runtime answer/route/proof leakage | `0` | Pending |
| Network calls | `0` | Pending |
| Deterministic artifact replay | `1.00` | Pending |
| Prediction shard hashes | all match | Pending |
| Second locked evaluation | refused | Pending |
| New trainable parameters | `<=2,000,000` | Pending |
| Float32 inference weights | `<=8 MB` | Pending |
| Development peak RSS | `<12 GB` | Pending |
| Locked peak RSS | `<8 GB` | Pending |
| Machine peak RSS | `<20 GB` | Pending |
| Active experimental runtime | `<4 hours` | Pending |

Environment and model hashes: **Pending**

Isolation note: the authoritative runtime is a separate process with a Python
audit hook that denies evaluator-gold paths. This is auditable process/path
separation, not an operating-system sandbox or a hostile-code security claim.

## 14. Mechanical classification

Classification precedence:

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

Applied classification: **Pending**

First failed gate: **Pending**

First dominant failure mechanism: **Pending**

Gate-completeness audit: **Pending.** A lifecycle-generated `L5-A` is not enough
by itself until every configured family, optimizer, integrity, and resource gate
listed in the specification has a measured artifact and has been applied.
The learned-geometry mechanism gate is part of this classification, not a
post-hoc annotation.

## 15. Authorized conclusion

If and only if every primary and causal gate passes, use this bounded statement:

> On the controlled L5 grammar and supplied compiled semantic fixtures, the
> shared-coordinate, multi-mode field recovered source-backed candidates and
> preserved supported alternatives and contradictions under bounded dynamic
> retrieval, with independently verified authorization and fail-closed unknown
> or incomplete states.

Measured authorization status: **Pending**

Do not add claims about unrestricted language, arbitrary mathematics, universal
depth, constant-time inference, or production readiness.

## 16. Known limitations retained after a pass

- Supplied fixtures do not measure raw compiler accuracy.
- The three locked tracks have different input distributions and must be
  reported separately.
- The 600-case joint raw pipeline is limited to generated controlled linear
  chains, unsupported conjunctions, balanced contradictions, and alternatives.
- Primary supplied fields are case-local; shared-field retrieval is a separate
  scale diagnostic.
- Controlled math uses narrow identity transformations.
- Abstract realities demonstrate the registered generated field law only.
- The one-million-body corpus is a lazy commitment, not one million active
  runtime bodies.
- Stress depth 17–64 is diagnostic.
- The strict decoder measures authorization, not naturalness.
- Exact verification remains the output authority.
- Current locked `safe_coverage` is numerically identical to all-case exactness,
  and remains a legacy exactness alias rather than an independent
  abstention/coverage statistic.
- Learned compatibility modulates continuous geometry only; exact source mass
  and candidate authority remain exact. If removing or randomizing that geometry
  leaves exactness unchanged, L5 must report `L5-E` rather than treating exact
  propagation as evidence for the latent-placement theory.
- The exact field law is deterministic. Only the shared-coordinate/compiler-
  alignment kernel is trained, for 600 optimizer steps.
- Candidate confidence is authorized only when it matches the evaluator's
  independent reconstruction from exact source-normalized support.
- Runtime/evaluator separation is enforced by Python audit paths, not an OS
  sandbox.

## 17. Permanent-report sign-off

The following must be completed before changing the status from pending:

- [ ] Source/config/checkpoint hashes match the frozen manifest.
- [ ] Public/evaluator files match the locked-suite manifest.
- [ ] Locked prediction shards are complete and immutable.
- [ ] Raw compiler predictions were scored only against evaluator-owned gold.
- [ ] Supplied-input metrics were not relabelled as compiler accuracy.
- [ ] Controls and interventions passed their causal gates.
- [ ] Full geometry beat no-learned, fixed-state/zero, and deterministic random
  geometry by at least 0.05, with full-state movement and zero fixed-state
  movement.
- [ ] No incorrect accepted compilation or candidate exists.
- [ ] Independent support/proof replay passed.
- [ ] Candidate confidence matched independent source-mass reconstruction.
- [ ] Persisted energy used actual aggregate mode energy with no cosmetic clamp.
- [ ] Runtime PID differed from evaluator PID and every evaluator-path probe was
  denied by the Python audit hook.
- [ ] Track-C public identifiers/text revealed no hidden family or disposition.
- [ ] Replay, network, full-scan, and resource gates passed.
- [ ] Stress and scale results are labelled diagnostic.
- [ ] Materialized and lazy-committed field sizes are stated separately.
- [ ] Counterexamples and failure-boundary counts were inspected.
- [ ] Mechanical classification was reproduced from raw artifacts.
- [ ] Every configured family, dynamics, frontier, authorization, causal, and
  resource gate was applied or explicitly classified incomplete.
- [ ] Repository tests, Ruff, compilation, link checks, and `git diff --check`
  passed.

Auditor: **Pending**

Audit date: **Pending**

Final report artifact hashes: **Pending**
