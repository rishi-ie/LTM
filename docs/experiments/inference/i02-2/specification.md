# I2.2 — Global Content-Addressed Minimap Navigation

## Objective

I2.2 tests the remaining I2 mechanism after I2.1: can the next relevant body
be found through a hierarchy built over the full field’s **learned source
vectors**, with no stable-identity leaf lookup at runtime?

The scope remains terminal completion. A prompt anchors an observed initial
Mumbrane; each opened body exposes its unnamed outcome vector; the field moves
to that outcome and must route globally to the source vector of the next body.
The evaluator’s depth and final candidate remain hidden.

## Required difference from I2.1

I2.1 was allowed to use a stable Mumbrane identity to select the current leaf.
I2.2 forbids that route:

```text
allowed runtime inputs: learned current vector, scope/time, minimap cells
forbidden runtime inputs: current identity key, identity-to-leaf map,
                         answer list, path map, closure, relation/role labels
```

The hierarchy is rebuilt from the frozen learned source representations. In
the implemented `r1` experiment, a cell stores only a split dimension, split
threshold, member IDs, and hash. It does **not** yet use learned cell-summary
or outcome-summary vectors for routing. It may not store a terminal answer or
an origin-to-terminal mapping.

```text
root
→ binary median split on highest-variance learned source dimension
→ repeat until leaf has <=64 bodies
→ rank the leaf’s bodies by learned source compatibility
```

Because an opened body’s outcome representation is also the next body’s source
representation, a correct state movement must route to the appropriate global
leaf. Every body contributes to exactly one root-to-leaf membership path.

## Gates

| Stage | Gate |
| --- | --- |
| G0 tree accounting | every body has one leaf and one root path; no identity leaf map |
| G1 global retrieval | next-body recall@64 `>=0.99` from the full field |
| G2 update/rerouting | next leaf changes on cross-leaf transitions `>=0.95` |
| G3 terminal completion | depths 1–64 answerable exactness `>=0.90`, accepted precision `>=0.95`, coverage `>=0.85` |
| G4 controls | random tree and fixed-state controls each lose >=20 points; shuffled body vectors near chance |
| G5 interventions | remove decisive body / wrong scope abstain; irrelevant-leaf changes preserve the result |

Locked data must be split-disjoint in entity, body composition and full chains.
The 100,000-body locked field is retained. I2.2 does not make factual writes.

## Research basis

- [Baranchuk et al., *Learning to Route in Similarity Graphs* (ICML 2019)](https://proceedings.mlr.press/v97/baranchuk19a.html)
  motivates explicit tests that a learned/global routing representation avoids
  local minima rather than assuming nearest-neighbour access is enough.
- [Huynh et al., *Multigrid Neural Memory* (ICLR 2020)](https://openreview.net/forum?id=ByxKo04tvr)
  supports multiresolution memory with data-dependent routing as a scalable
  mechanism to test.
- [Davydov et al., *Retrieving k-Nearest Memories with Modern Hopfield
  Networks*](https://openreview.net/forum?id=bNBMnQXRJU) supports bounded
  differentiable/content-addressed memory access.
- [Lake and Baroni](https://proceedings.mlr.press/v80/lake18a.html) requires
  the held-out chain and control panels; retrieval success alone is not
  systematic generalization.

## Claim boundary

A pass would show global, hierarchical **content-addressed routing** in the
controlled observed-transition field. It would still not prove learned
multiscale summarization, arbitrary goal selection, unstored-rule inference,
raw-language compilation, or replacement of exact G6/G9 reasoning.
