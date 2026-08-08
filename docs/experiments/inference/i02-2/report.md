# I2.2 — Global Content-Addressed Minimap Navigation

## Classification

**`I2.2-A — GLOBAL CONTENT-ADDRESSED NAVIGATION PASS`**

I2.2 validates the remaining controlled I2 mechanism after I2.1: a moved
latent state can route through a hierarchy built over the complete field’s
learned source vectors without an identity-to-leaf lookup.

## Locked evidence

The locked field contained 100,000 observed bodies. The 4,000 public prompts
contained only a supplied initial Mumbrane, scope and fixed resource budget;
the evaluator retained terminal candidate, path and depth.

| Metric | Development | Locked |
| --- | ---: | ---: |
| Next-body recall@64 | 1.0000 | 1.0000 |
| Cross-leaf transition rate | 0.9941 | 1.0000 |
| Tree membership accounting | 1.0000 | 1.0000 |
| Terminal exactness, depth 1–64 | 1.0000 | 1.0000 |
| Accepted precision | 1.0000 | 1.0000 |
| Safe coverage | 0.9230 | 0.9230 |
| All-case exactness | 1.0000 | 1.0000 |
| Incorrect accepted candidates | 0 | 0 |
| Certified energy increases | 0 | 0 |

The remaining 7.7% started at a terminal state and correctly returned
`unknown`; they are included in all-case exactness rather than accepted.

## Controls and causal separation

| Control | Result |
| --- | ---: |
| Full global vector tree answerable exactness | 1.0000 |
| Fixed/no-movement all-case upper bound | 0.0117 |
| Deterministically wrong tree answerable exactness | 0.0000 |
| Remove the current global leaf | abstains |
| Identity-to-leaf route present | false |

The tree has no stored answer list, origin-to-terminal map, closure, relation
label, named role, or query-specific hint. Its leaves contain only body
membership; routing decisions use the current learned 128D source state and
frozen split thresholds. The outcome of one opened body becomes the next
content-addressable state, causing a new global leaf to open.

## Conclusion boundary

Together, I2.1 and I2.2 establish a controlled empirical result:

```text
fixed prompt anchor
→ global content-addressed minimap retrieval
→ unnamed observed transition displacement
→ new latent position
→ different relevant field region
→ source-backed terminal completion
```

This is strong evidence for the core dynamic-field mechanism under supplied
atomic Mumbranes. It is not a proof of unrestricted reasoning: the test has a
single terminal-completion objective, uses observed successor bodies, and does
not demonstrate arbitrary goal selection, unstored rules, natural-language
compilation, factual authorization, or decoder quality.

The result is consistent with research on learned dynamics from observations
([Kipf et al.](https://proceedings.mlr.press/v80/kipf18a.html)), hierarchical
memory with dynamic routing ([Huynh et al.](https://openreview.net/forum?id=ByxKo04tvr)),
learned routing over global similarity structure
([Baranchuk et al.](https://proceedings.mlr.press/v97/baranchuk19a.html)), and
bounded associative-memory retrieval
([Davydov et al.](https://openreview.net/forum?id=bNBMnQXRJU)). These papers
motivate the mechanism; I2.2 supplies only its own controlled evidence.

Authoritative workspace: `workspaces/ltm-inference-i22-r1/`.
