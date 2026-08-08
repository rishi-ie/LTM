# Fresh LTM Architecture Viability Audit

Date: `2026-08-06`  
Audit revision: `ltm-a2/1`  
Method: fresh source/report inspection plus new evaluator-owned semantic-body
replays. No model was trained and no historical locked result was overwritten.

## Bottom line

**Controlled LTM v1: CONDITIONAL_GO.** The exact
topology, Mumbrane/FieldIR representation, profile execution, addressing,
hard/soft execution, verification, constrained realization, lifecycle and
storage components have credible controlled evidence.

**Unrestricted/full vision: PLAUSIBLE_BUT_UNPROVEN.**
The decisive unsolved boundary is safe raw reasoning-language compilation, not
the packed field representation. Product serving/isolation (G15) is also not
yet measured.

## Forecasts

These are engineering forecasts after the fresh audit, not pass metrics:

| Outcome | Forecast |
| --- | ---: |
| Exact representation and profile execution | 90% |
| Structured topology to verified answer | 90% |
| Controlled user-facing v1 with current compilers | 60% |
| Bounded-domain product after the writer and G15 | 65% |
| Robust general raw reasoning compiler with the current small encoder | 25% |
| Full general LTM vision with the current known architecture | 35% |

## Evidence inventory

| Area | Ledger state | Proven boundary | Evidence source |
| --- | --- | --- | --- |
| G1 | PASS | exact topology contract | report/ledger evidence |
| G2.5 | FAILED; PROVISIONALLY ADOPTED | reasoning compiler | replayed artifact available |
| G2.14 | NARROW PASS | supplied-span conversation gate | replayed artifact available |
| G3–G5 | PASS | addressing, frontier and coverage | report/ledger evidence |
| G6–G9 | PASS | exact/soft execution and verification | report/ledger evidence |
| G10.1 | PASS | strict authorized realization | report/ledger evidence |
| G11–G13 | PASS | lifecycle, storage and scale | report/ledger evidence |
| G14 | CONTROLLED PASS | structured composition only | report/ledger evidence |
| LTM-I1 | PASS | FieldIR v2 integration | replayed artifact available |
| LTM-R2 | PASS | Mumbrane representation | replayed artifact available |
| G15 | NOT RUN | serving and fault isolation | report/ledger evidence |

The G2 result must be read as two distinct routes: G2.14 passed its narrow
supplied-span conversational acceptance boundary, while G2.5 is a deliberately
adopted provisional reasoning baseline despite its failed reliability gate.
Neither result establishes unrestricted raw-language reasoning compilation.

## Fresh representation replay

Nine fresh semantic bodies were compiled into Mumbrane programs and executed
under reasoning, planning, evidence, and conversation profiles. Each result was
compared against the independent semantic-body oracle. This validates the
representation/configuration path, not natural-language extraction.

| Scenario | Active relations in generated body | Mumbrane units | All profile/oracle agreements |
| --- | --- | ---: | --- |
| preference replacement | prefers | 14 | True |
| correction and supersession | supersedes | 14 | True |
| ambiguous reference | refers_to | 14 | True |
| hard implication chain | implies, conjoins | 15 | True |
| evidence tension | supports, opposes, uncertainty | 16 | True |
| scope and temporal isolation | before, scoped_to | 15 | True |
| profile switch | requires, prefers | 15 | True |
| integrity boundary | excludes | 14 | True |
| indexed scale locality | derived_from, assistant_derived_from | 15 | True |

Overall replay agreement: `True`.

## What a prompt flow means in the present system

1. **“Prefer concise answers.”** A supplied semantic span is classified as a
   session preference, candidate-resolved, then safely committed only if every
   threshold and margin passes. The conversation profile may alter answer form;
   it cannot make a factual claim true.
2. **“Actually, Project A replaces Project B.”** The compiler must identify one
   active target. If it cannot, it asks for clarification; if it can, the exact
   `supersedes` port is stored, and a later request sees the revised item.
3. **“Does A imply B?”** A reasoning compiler would have to ground `A`, `B`,
   operator `implies`, named roles and scope before G6 can derive anything.
   This is the presently weak boundary: G2.5 has not demonstrated it safely
   from arbitrary raw text.
4. **“Evidence E supports C, but F opposes C.”** Exact ports preserve the two
   evidence factors. G6 never turns the soft geometry into a hard fact; G7
   reconciles the confidence and G9 must disclose tension before G10.1 realizes
   only authorized claims.
5. **Changing a profile from reasoning to planning.** The same Mumbrane units
   remain stored. A new compiled profile changes active operators and soft
   objectives; it changes the execution hash, not the semantic substrate hash.
   If the new purpose needs missing information, the contract requires source
   recompilation rather than inventing a default.

## Critical findings

- **G2.14_HANDOFF — BOUNDARY_GAP:** G2.14 proves its supplied-span acceptance gate and structured G11 lifecycle compatibility; it does not independently prove the advertised G1/FieldIR/Mumbrane assembly handoff.
- **G2.5_REASONING_LIMIT — UNRESOLVED:** G2.5 is an engineering baseline, not an experimental compiler pass: 81.75% locked recovery and 199 reversal false accepts remain the limiting evidence.
- **G15_SERVING_LIMIT — UNTESTED:** Product serving, fault isolation and multi-tenant operational behavior have no measured result.

The first finding is especially consequential for implementation planning: G2.14
can be used as a conservative conversational routing/authorization module, but
not yet cited as an end-to-end compiler-to-Mumbrane handoff. That adapter must
be implemented and independently tested before it becomes an active runtime
writer.

## Research grounding

- [Koh et al. (2020), Concept Bottleneck Models](https://proceedings.mlr.press/v119/koh20a.html) — auditable intermediate representation; not raw-language reliability.
- [Smolensky (1990), Tensor Product Variable Binding](https://www.sciencedirect.com/science/article/pii/000437029090007M) — separate role/filler structure is mathematically motivated.
- [Geifman and El-Yaniv (2017), Selective Classification](https://papers.nips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html) — confidence/coverage abstention trade-off.
- [Bach et al. (2017), Hinge-Loss Markov Random Fields](https://jmlr.org/beta/papers/v18/15-631.html) — structured soft constraints and continuous optimization.
- [Schlichtkrull et al. (2018), Relational Graph Convolutional Networks](https://2019.eswc-conferences.org/wp-content/uploads/2018/02/ESWC2018_paper_4.pdf) — relation-specific message passing.
- [Rae et al. (2016), Scaling Memory-Augmented Neural Networks](https://papers.nips.cc/paper/2016/hash/2030e7d8a49f5e132b7c7d7bded7fe3e-Abstract.html) — sparse reads/writes can avoid full memory scans.
- [Green, Karvounarakis and Tannen (2007), Provenance Semirings](https://www.cs.ucdavis.edu/~green/papers/pods07.pdf) — lineage as first-class algebraic information.
- [Scholak et al. (2021), PICARD](https://aclanthology.org/2021.emnlp-main.779/) — incremental constraints can reject invalid decoded candidates.

These papers support individual design choices, not a proof of the architecture
as a whole. In particular, none establishes that a small encoder can reliably
compile unrestricted natural language into this ontology.

## Next engineering decision

Proceed with the controlled v1 integration only behind the existing exact,
atomic, verifier-gated boundary. Prioritize (1) a real supplied-span G2.14 to
G1/FieldIR/Mumbrane writer and integration test, (2) raw semantic span
segmentation as a separately measured module, (3) replacement of provisional
G2.5 reasoning compilation, and (4) G15 serving/isolation evaluation. Do not
claim a general raw-language reasoning compiler until that compiler passes a
fresh locked test at its intended boundary.
