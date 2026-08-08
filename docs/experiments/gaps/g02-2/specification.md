# G2.2 — Sentence-Level Reasoning Compiler

## Decision question

Can a token-level sentence compiler turn controlled unseen language into valid, typed G1 topology
with **at least 99% accepted precision and 85% coverage**, then unite the resulting sentence fragments
through a sparse, type-safe cross-sentence linker?

G2.2 is the direct remediation experiment for G2 and G2.1. The historical G2 Qwen boundary failed to
produce reliable structured extraction. The historical G2.1 approach used one pooled 384-dimensional
embedding per whole sentence and reached only 80.8% exact topology agreement. This experiment keeps
MiniLM's token sequence, reasons over explicitly proposed spans and legal typed relations, and only then
adds sentence-to-topology links.

## Claim boundary

The experiment establishes only controlled-language compilation into the frozen G1 ontology. It does
not establish unrestricted text ingestion, a native latent field, latent optimization, natural-language
decoding, complete context coverage, or 100M-context reliability. G2 and G2.1 remain failed historical
experiments regardless of G2.2's eventual result.

An ambiguous, quarantined, low-confidence, low-margin, low-round-trip, or invalid output writes **no
partial topology delta**. Safety is therefore assessed on what becomes topology, not merely on a raw
model proposal.

## Pipeline

```text
document with exact offsets
→ deterministic sentence splitter
→ local MiniLM raw token states (384 dimensions)
→ multi-kind start/end span proposals (maximum 12)
→ registry-authorized relation + role candidates (maximum 48)
→ four-cycle typed recurrent HRM (128 dimensions)
→ confidence, margin, disposition, scope, time, and canonical round-trip gates
→ atomic G1 assembly and validation
→ at most 16 public topology-index candidates
→ typed recurrent linker
→ unified topology delta and deterministic field handoff
```

The compiler never predicts a free relation role and direction independently. It scores a candidate made
from a real `topology_g1.registry.REGISTRY` relation and its valid named role bindings. Direction is
derived from the selected relation. Thus an emitted relation cannot have a role vocabulary unknown to G1.

## Dataset and separation

| Track | Train | Development | Locked | Seed |
| --- | ---: | ---: | ---: | ---: |
| Sentence fragments | 12,000 | 2,000 | 4,000 | 1742 / 1743 / 20260815 |
| Cross-sentence links | 6,000 | 1,000 | 2,000 | 1742 / 1743 / 20260815 |

The sentence training set contains 7,200 atomic accepted cases, 2,400 accepted multi-clause cases,
1,200 genuine ambiguities, and 1,200 quarantined/no-relation cases. The linker contains balanced
coreference, rule/requirement, correction, scope, temporal, evidence, no-link, and ambiguity families.
The generator uses opaque fictional entities and split-disjoint entity names, predicates, scope labels,
sessions, grammar templates, relation cues, temporal expressions, and source IDs. Runtime JSON contains
only source text and public candidate metadata; evaluator gold, labels, template IDs, and topology hashes
are written separately.

## Models and controls

The pinned local encoder is `.models/all-MiniLM-L6-v2`. The implementation verifies the frozen SHA-256
hashes for `config.json`, `model.safetensors`, and `tokenizer.json`, uses offline local loading, truncates
at 128 wordpieces, and defaults to CPU. The configured machine budget warns at 16 GB RSS and aborts at
18 GB; locked G2.2 must finish below 12 GB and ten minutes.

Three methods are run from the same legal-candidate interface:

1. Frozen token encoder plus four-cycle typed HRM, with two HRM learning rates.
2. Last-two-layer MiniLM partial tuning plus the same HRM, with two paired learning rates.
3. A non-recurrent typed marked-span control.

The HRM holds token, span, relation, and sentence-hub states in 128 dimensions. Every cycle updates a
relation state from ordered span and role information, sends typed directed messages to span states,
updates the spans, then updates the sentence hub. The linker repeats this operation only across a bounded
public context candidate set. It filters session-incompatible candidates before scoring and has no API for
scanning the entire topology.

Training is deterministic CPU float32 with AdamW, gradient clipping at 1.0, sentence batch size 16,
link batch size 8, accumulation 4, at most 30 epochs, and patience 5. The loss combines start/end
multi-kind spans, scope/time/disposition metadata, registry-legal candidate choice, sparse link choice,
and a 0.25 counterfactual margin. The linker receives only a validated fragment and public typed index
records; it cannot invent a context object.

## Freeze and evaluation

`develop` builds train/development inputs, trains all candidates, selects calibration only from the
development set, and writes checkpoints. Calibration enumerates confidence `[.70,.95]`, margin
`[.10,.25]`, and round-trip thresholds `[.80,.95]`, selecting maximum coverage subject to 99% accepted
precision and no high-severity error.

`freeze` hashes G2.2 sources, configuration, local encoder, development result, selected checkpoints,
and calibration. It blocks development overwrite. `locked-suite-build` creates the fresh locked corpus
once. `evaluate` checks hashes, writes raw runtime predictions before score calculation, records every
method, refuses overwrite, and applies gates mechanically. `verify` repeats semantic inference and
requires prediction hashes to match; latency and RSS are intentionally excluded from byte-equality.

## Locked gates

G2.2 operationally passes only when all hold:

- accepted sentence exact precision ≥ .99 and safe coverage ≥ .85;
- link exact precision ≥ .99 and safe coverage ≥ .85;
- all-case exact ≥ .90; span F1 ≥ .98; span-offset accuracy ≥ .99;
- relation macro F1 ≥ .98; relation-plus-role exact ≥ .99; direction ≥ .995;
- scope/time ≥ .99; ambiguity and quarantine recall ≥ .98;
- zero silent invalid insertions, high-severity polarity errors, cross-session links, and complete scans;
- deterministic replay, runtime < 600 seconds, RSS < 12 GB, and zero network calls.

The HRM advantage is separately assessed against the non-recurrent control. It requires at least five
absolute points in all-case topology exactness and three points in link exactness; this research comparison
does not waive any operational gate.

## Classification

- `G2.2-O-PASS / G2.2-H-PASS`: operational gates and recurrent advantage both pass.
- `G2.2-O-PASS / G2.2-H-NOT-DEMONSTRATED`: usable controlled compiler, but recurrence adds no measured value.
- `G2.2-C-FROZEN-REPRESENTATION-INSUFFICIENT`: operational gates fail.
- `G2.2-D-SHORTCUT`: aggregate score is high but counterfactual, scope, time, or linking safety fails.
- `G2.2-E-ASSEMBLY-FAILURE`: predictions are sound but G1 assembly loses validity/provenance.
- `G2.2-F-INTEGRITY-FAILURE`: leakage, nondeterminism, altered frozen artifact, invalid insertion, or full scan.
- `G2.2-COMPUTE`: correctness passes but the resource envelope fails.

The machine-readable configuration is [`topology-g2-2.json`](../../../../configs/topology-g2-2.json).
This document is a specification, not evidence of success, until a frozen locked result exists.
