# I2 Dynamic-Field Mechanism Audit

**Status:** post-hoc conservative audit, 2026-08-06  
**Question:** do the implemented I1, I2, I2.1, and I2.2 artifacts prove the I2 specification’s claim that a prompt is globally influenced by an anonymous, multiscale latent field through learned energy dynamics?

## Verdict

**No. The current artifacts prove a useful deterministic traversal demonstration, not the full I2 theory.**

I2.2’s reported locked metrics are real outputs of its frozen code: 1.0000 answerable terminal exactness and accepted precision over 4,000 prompts on a 100,000-body synthetic field, with 0 incorrect accepted candidates. But the implementation does not meet several material conditions of the original I2 specification:

- Its evaluator loads public prompts and evaluator gold in one Python process. The inference function is passed public rows only, but access denial is not enforced by a separate runtime boundary.
- Its update is not projected gradient optimization of a learned field energy. It selects the best matching source body and assigns the movable state to that body’s observed outcome representation.
- Its minimap is a deterministic median-split vector tree. It has no learned cell summaries, global summary forces, frontier value learning, or simultaneous minimap energy contribution.
- Its generated field is a regular 64-step successor chain. Vectors include an explicit normalized state coordinate and factorized state basis; one body’s outcome is intentionally exactly the next body’s source.

Therefore I2.2 supports only this narrow, mechanically demonstrated statement:

> In a regular synthetic observed-transition field, an aligned vector state can select the next source-compatible body through a global deterministic vector tree, be replaced by that observed body’s outcome vector, and repeat until no next source exists.

It does **not** yet prove relation-free multihop inference, learned latent optimization, global all-data influence in the I2 sense, evaluator-isolated safety, arbitrary question answering, raw-language compilation, or replacement of G6/G9.

## Evidence matrix

| Claim | Current evidence | Conservative status | Reason |
| --- | --- | --- | --- |
| A single Mumbrane representation can preserve the registered exact and vector contracts. | [LTM-R2](../experiments/representation/r02/report.md) | Supported for its controlled paired-oracle representation suite. | This concerns representation preservation, not latent inference. |
| Canonical FieldIR can drive G3–G10.1 without semantic loss. | [LTM-I1](../experiments/integration/i01/report.md) | Supported for its controlled integration suite. | It does not validate a learned relation-free field law. |
| A local relation-free energy model composes multi-hop bodies. | [I1](../experiments/inference/i01/report.md) | Rejected by its own locked result. | I1 reached zero locked accepted coverage/exactness. |
| Original I2 learned useful local anonymous transitions. | [I2](../experiments/inference/i02/report.md) | Rejected by its development gate. | It had a learned-query/raw-body coordinate mismatch and did not reach locked execution. |
| An aligned state can traverse observed bodies with direct identity addressing. | [I2.1](../experiments/inference/i02-1/report.md) | Demonstrated as a controlled traversal. | It uses stable identity-addressed retrieval, so it is not global content routing. |
| A current vector can select a different global vector-tree leaf with no identity-to-leaf lookup in `frontier`. | [I2.2 historical report](../experiments/inference/i02-2/report.md) and source | Demonstrated as a code-path property. | `GlobalTreeField.frontier` deletes/ignores identity routing and descends by current vector. |
| I2.2 demonstrates the full I2 latent field law and integrity boundary. | I2.2 source audit | **Not established.** | No true gradient energy law, no learned minimap summaries, regular chain data, and no process-isolated evaluator. |
| Controlled conversational Mumbrane writes can be safely gated from supplied spans. | [G2.14](../experiments/gaps/g02-14/report.md) | Supported for its own supplied-span conversation boundary. | It is not a reasoning or latent-inference result. |

## Code-level findings

### What I2.2 really does

1. The field creates a binary median-split tree over frozen learned source vectors.
2. The current state descends that tree to one leaf; up to 64 bodies in that leaf are scored by source-vector dot product.
3. The best source-compatible body is selected only when its dot product exceeds 0.99999.
4. The new state is normalized from current state plus outcome minus source, which algebraically is the selected observed outcome state.
5. The next tree leaf is opened from that outcome state. Completion occurs when no next source has the 0.99999 match.

That is a deterministic content-addressed successor walk. It is a valid engineering sanity check for coordinate alignment and vector-tree routing, but it is not the profile-defined eight-step/32-step energy minimization with candidate activations that I2 specified.

### Why the synthetic suite is insufficient

The I2.1/I2.2 generator creates only successor bodies of the form state n to state n+1. The vector builder adds state n divided by 64 directly to vector coordinate zero and uses a deterministic basis for state n. An outcome is explicitly constructed to be the next body’s source. That makes exact chain walking expected once the aligned state space has been established.

The suite has no non-monotonic transition vocabulary, competing paths to differently requested goals, variable graph motifs, or evidence that the kernel learns a reusable transition law rather than follows observed exact vector keys. The original I2 requirement for learned transition sketches and multiscale summary influence is therefore untested.

### Integrity gap

`ltm_inference_i22.evaluate._load` reads `gold.jsonl` together with the public prompt rows, and `evaluate` computes inference and scoring in the same process. There is no file-system deny rule, subprocess boundary, capability object, or test that a runtime process cannot open evaluator gold. The inference signature itself receives no gold object, which is a positive API property, but it is weaker than evaluator isolation.

Historical I2.2 artifacts remain unchanged. This audit corrects their interpretation; it does not overwrite their measured metrics.

## Research context

Prior work makes the direction plausible but does not repair these gaps:

- [Kipf et al., *Neural Relational Inference* (ICML 2018)](https://proceedings.mlr.press/v80/kipf18a.html) learns latent interactions from observed dynamics; I2.2 does not yet demonstrate comparable learned interaction recovery.
- [Ramsauer et al., *Hopfield Networks Is All You Need* (ICLR 2021)](https://openreview.net/forum?id=tL89RnzIiCd) connects associative attention and energy-style retrieval, but does not show that a successor walk is multihop reasoning.
- [Huynh et al., *Multigrid Neural Memory* (ICLR 2020)](https://openreview.net/forum?id=ByxKo04tvr) motivates explicit multiresolution memory; I2.2 has a vector partition, not learned multiscale summaries.
- [Baranchuk et al., *Learning to Route in Similarity Graphs* (ICML 2019)](https://proceedings.mlr.press/v97/baranchuk19a.html) motivates evaluating global routing; I2.2 provides only a controlled vector-tree routing check.
- [Du et al., *Compositional Energy-Based Models* (ICML 2023)](https://proceedings.mlr.press/v202/du23a.html) makes compositional energy a testable hypothesis, while [Lake and Baroni, *Generalization without Systematicity* (ICML 2018)](https://proceedings.mlr.press/v80/lake18a.html) explains why regular-chain success cannot establish systematic generalization.

## Necessary next experiment: I2.3 hardening

I3 goal conditioning is premature. First, I2.3 must retest the existing no-goal claim under the original I2 integrity and mechanism boundaries:

1. **Hermetic evaluator separation:** runtime process receives only packed public field, profile, and public prompt; evaluator process owns gold. A denied gold-path/open attempt must fail.
2. **Real field law:** implement a bounded, differentiable energy containing prompt anchor, cell summary, opened-body transition, context, sparsity, and frontier terms. Accepted projected/backtracking updates must monotonically lower that energy.
3. **Learned multiscale summaries:** train shared summary and frontier-value functions; store only bounded summary statistics. Compare them to the deterministic vector tree with equal access budgets.
4. **Non-regular held-out graphs:** use shuffled opaque state labels, branching/merging motifs, reordered paths, conjunction-style multi-input transitions, unrelated distractors, scope/time conflicts, and nonmonotonic transitions. No numerical state coordinate or regular successor order may predict a terminal.
5. **Causal controls:** remove/reverse/negate/expire decisive bodies; perturb relevant and irrelevant remote regions; verify that only relevant changes affect the candidate.
6. **Mechanism gates:** require frontier recall, source-backed candidate provenance, energy descent, intervention accuracy, and full controls against nearest retrieval, fixed state, fixed frontier, static tree, and randomized summaries.

Only after I2.3 passes should I3 add a goal Mumbrane and test several questions from the same evidence. The [I3 proposal](../experiments/inference/i03/specification.md) must therefore be treated as downstream of I2.3, not as implementation-ready work.

## Conservative conclusion

The representation and downstream contracts remain promising, and I2.2 has identified a useful coordinate-alignment and content-addressed routing primitive. But the full I2 theory is **not proved**. A serious I2.3 engineering experiment—not a threshold tweak—is required before the architecture can claim learned, relation-free, multiscale latent inference.
