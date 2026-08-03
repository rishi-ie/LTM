# CNTG-1-R2 Conversational LTM Experiment Report

## Executive result

The controlled CNTG-1-R2 experiment is classified **CNTG-C**.

The complete middle of the architecture worked end to end when the system was
given a correctly structured fictional reasoning topology:

```text
conversation
→ typed topology and session overlay
→ active latent field
→ structured latent optimization
→ independent verification
→ authorized evidence bundle
→ conversational decoder
```

The optimizer solved the registered multi-step relation-composition cases, the
session field preserved conversational state, the verifier rejected invalid
states, and sparse field activation remained nearly flat as the compiled field
grew from 64 MB to 1 GB.

The experiment did **not** demonstrate a general conversational LTM. The
language-to-topology boundary remains the main bottleneck: Qwen directly
produced valid Turn IR for only 10% of turns, and deterministic recovery
handled the remaining controlled-language cases. The decoder was safe but
required deterministic fallback for 17.38% of responses. A 10 GB quality build
was therefore not authorized.

## What was tested

CNTG-1-R2 used a deterministic fictional reasoning distribution with:

- a 64 MB, 128 MB, 256 MB, 512 MB, and 1 GB corpus ladder;
- persistent facts, implications, multi-premise rules, corrections, scopes,
  conflicts, preferences, episodes, and provenance;
- 32 development conversations and 80 locked conversations;
- 20 turns per locked conversation, or 1,600 locked turns;
- unseen world names and held-out paraphrase families;
- a frozen 4-bit `Qwen/Qwen2.5-0.5B-Instruct` decoder and extractor;
- an eight-token latent-prefix adapter;
- offline locked evaluation after artifact freezing.

This was a controlled ontology experiment, not a general web benchmark. The
RAG number below is an internal control on this fictional distribution and
must not be interpreted as a general RAG comparison.

## Complete flow

1. A user turn is preserved as an immutable source event.
2. A model proposes a typed Turn IR containing claims, references, goals,
   corrections, preferences, scopes, and source spans.
3. Deterministic validation converts accepted IR into replayable topology
   operations. Invalid objects are recovered, clarified, or quarantined.
4. The session overlay receives the new claims, corrections, preferences, and
   low-authority assistant events.
5. The prompt activates relevant persistent factors, session factors, relation
   paths, conflicts, and exact exceptions.
6. A structured latent state is optimized under typed energy terms and hard
   constraints.
7. The independent verifier checks proof paths, direction, scope, temporal
   validity, provenance, conflicts, and authorization.
8. The decoder receives the verified textual bundle plus the latent prefix.
9. Generated claims are checked against the authorized bundle. Rejected text
   is replaced by a deterministic verified fallback.
10. Only the accepted response event is reinserted into the session, with low
    epistemic authority so it cannot authenticate itself.

## Method results

| Method | Overall | Composition | Context |
| --- | ---: | ---: | ---: |
| Full LTM | 100.0% | 100.0% | 100.0% |
| Exact symbolic control | 100.0% | 100.0% | 100.0% |
| Exhaustive field control | 100.0% | 100.0% | 100.0% |
| No optimization | 85.0% | 0.0% | 100.0% |
| No session field | 85.0% | 100.0% | 62.5% |
| Full-history Qwen | 45.3% | 61.3% | 19.4% |
| MiniLM-RAG plus Qwen | 7.2% | 1.2% | 13.1% |

The full system improved registered composition accuracy by 100 percentage
points over the no-optimization control. This shows that the structured
optimizer propagated support through typed relations; it was not merely
selecting the nearest text item.

## Component findings

### Reasoning topology

The typed topology supported facts, directed implications, multi-premise
rules, corrections, conflicts, fictional scopes, preferences, episodes,
references, and provenance. After deterministic recovery, topology operations,
claim tuples, scope, correction targeting, coreference, and provenance were
correct on the registered suite.

However, direct model extraction was the limiting result:

- Qwen-valid Turn IR rate: **10.0%**;
- deterministic recovery handled the other controlled turns;
- unrestricted natural-language topology extraction was not established.

After recovery and validation, the registered suite reported **100%** for
topology operations, claim tuples, coreference, correction targets, scope,
and provenance integrity.

Therefore the experiment proves that the downstream reasoning pipeline works
over a valid topology, not that a small model can reliably construct that
topology from arbitrary language.

### Latent dynamic field

The persistent field compiled topology objects into indexed factors, summaries,
session overlays, and exact exceptions. Ordinary requests activated a small
frontier instead of scanning the complete compiled corpus.

Cached and exhaustive conclusions agreed on all tested cases. The minimum
comparable cached/exhaustive state cosine was **0.998478**.

### Latent optimization

Optimization began from the prompt-conditioned structured state and applied
typed relation energies, branch handling, backtracking, and hard-constraint
checks. The run recorded:

- zero numerical failures;
- zero accepted energy increases;
- zero hard-constraint violations;
- 100% registered composition improvement over no optimization;
- agreement with exhaustive conclusions.

This is strong evidence for controlled relation propagation. It is not yet
evidence of broad reasoning, global optimality, or superiority to every
conventional symbolic solver.

### Independent verifier

The verifier independently checked premise availability, relation direction,
scope, correction and temporal status, proof continuity, provenance, conflict
disclosure, cache coverage, and assistant self-evidence. Registered adversarial
tests produced **zero false accepts**.

### Decoder

Final response authorization was strong:

- authorized-claim precision: **100%**;
- authorized-claim recall: **100%**;
- unsupported final claims: **0%**;
- conflict disclosure: passed;
- out-of-domain abstention: passed;
- preference adherence: passed.

The first generated answer was accepted in **82.63%** of cases. Deterministic
fallback was required in **17.38%**. Removing the latent prefix did not reduce
accuracy, so the experiment does not yet show that the latent prefix adds
unique reasoning information beyond the verified textual bundle. The human
naturalness audit was not scored before cleanup and remains pending. Complete
locked evaluation took approximately **1,300 seconds**; this exceeded the
earlier total-suite time envelope even though ordinary per-request field and
warm-response gates passed.

## Scaling measurements

The clean scaling run measured the controlled corpus ladder as follows:

| Measurement | Result |
| --- | ---: |
| Compilation exponent | 1.025 |
| Compiled-storage exponent | 0.998 |
| Field-latency exponent | -0.015 |
| Field evaluation p95 | approximately 0.44–0.47 ms |
| Session-update p95 | approximately 2.5–2.6 ms |
| Maximum ordinary field fraction read | 0.000441% |
| 1 GB compile time | approximately 9.6 s |
| 1 GB compiled field | approximately 928 MB |
| Projected 10 GB compiled field | approximately 9.28 GB |

These measurements support the engineering claim that bounded ordinary
activation can remain almost flat as persistent storage grows. They do not
prove constant worst-case inference. Global questions, routing misses,
cross-shard relations, and summary invalidation can still scale with the
corpus.

## What this experiment demonstrated

- typed conversational topology can represent registered reasoning objects;
- persistent and session topology can coexist;
- corrections, scopes, preferences, conflicts, and episodes can be retained;
- a compiled field can activate a bounded request frontier;
- structured latent optimization can propagate registered relations;
- an independent verifier can block invalid low-energy states;
- decoder claims can be bounded by verified evidence;
- assistant responses can be reinserted without self-authentication;
- cached inference can agree with exhaustive inference on the tested suite;
- field computation can remain nearly flat across the 64 MB–1 GB ladder.

## What this experiment did not demonstrate

- unrestricted natural-language topology compilation;
- broad domain or cross-domain generalization;
- general-world factual accuracy;
- causal reasoning beyond registered relations;
- superiority over Datalog, graph search, CSP, SAT, or SMT controls;
- frontier-model equivalence;
- quality preservation at 10 GB, 100 GB, or 2 TB;
- literal O(1) inference for arbitrary global questions;
- production reliability or commercial cost;
- a unique accuracy contribution from the latent soft prefix;
- human-rated conversational naturalness.

## Final classification

**CNTG-C — reasoning state works; decoder and topology boundary require more
work.**

The classification is not a claim that the architecture failed. It means the
controlled topology, field, optimizer, verifier, and safe decoder boundary
worked, while the learned language-to-topology compiler and decoder acceptance
rate did not meet the full conversational gate.

## Next experiment

The next work should freeze the field, optimizer, verifier, and authorization
boundary and focus on the topology compiler:

```text
Unrestricted paraphrase
→ staged topology encoder
→ validated Reasoning IR
→ gold-versus-predicted topology comparison
→ same field and optimizer
→ downstream reasoning comparison
```

The compiler must be tested on unseen domains, relation compositions,
corrections, scopes, conflicts, references, and ambiguous statements without
deterministic template recovery. The decisive metric is not only IR F1; it is
whether compiled-topology answers and proof paths remain close to answers from
the human-verified topology.

Do not begin a 10 GB quality build until this compiler gate passes.

## Historical identity

The experiment used the pinned Qwen revision:

```text
a5339a4131f135d0fdc6a5c8b5bbed2753bbe0f3
```

The locked public-suite hash began with `e1a9e82b5faa` and the evaluator-only
gold hash began with `719ca8b05e3a`. These identifiers are retained for
historical reference only. Raw runs, generated responses, hidden gold,
compiled fields, manifests, and audit files were intentionally removed from
the repository during cleanup.
