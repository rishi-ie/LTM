# L1 — Frozen Multihop Reasoning Limit Characterization

## Measured result

The frozen I3.1 `r13` checkpoint completed every base case at depths 1–64 in
both panels (20 cases per depth and panel):

| Measure | Result |
| --- | ---: |
| Formal grounded-rewrite D95 | 64 |
| Formal grounded-rewrite D90 | 64 |
| Opaque traversal D95 | 64 |
| Opaque traversal D90 | 64 |
| Deepest independently replayed proof | 64 |
| Accepted-proof precision | 1.00 |
| Independent replay | 1.00 |
| Invalid accepted proofs | 0 |

At depth 64, formal p95 latency was approximately 92 ms. Opaque traversal
p95 latency was approximately 1.26 s on the four-way branching panel. The
over-budget boundary panel (65, 96 and 128 hops) abstained, and unknown cases
also abstained.

The field-size diagnostic preserved the verified answer at 16 hops for 46,
1,000, 10,000 and 50,000 bodies. Runtime increased from about 11 ms to
538 ms; this is a retrieval/index scaling measurement, not a new depth claim.
The frozen runtime applies the 64-body bound per frontier read. Because the
frontier is reopened, the cumulative union of distinct body IDs can be larger
(for example, 796 in the 50,000-body diagnostic); this is reported as search
effort and is not silently presented as a 64-total-body guarantee.

## Controls

On the stratified 10-case control panel, success was: full 1.00, no scorer
0.50, no goal 0.90, no heuristic 1.00, fixed frontier 0.00, no content index
0.60, and reduction preference 0.50. The fixed-frontier collapse and scorer/
index degradation show that the result depends on dynamic field retrieval and
learned search guidance. The reduction-preference variant is diagnostic only.

## Interpretation boundary

This is a valid capacity characterization of the frozen implementation, not a
claim of unrestricted theorem proving or general mathematical reasoning. The
formal panel is composed of source-backed, grounded instances of the frozen
standard identity families (alternating additive-zero and multiplicative-one
transitions). The opaque panel measures source-backed multihop transport. Both
therefore establish 64-hop grounded transition/traversal endurance, while
variable-schema algebra, broad axiom selection, and genuinely novel formal
proof composition remain unmeasured.

The headline L1 result is therefore:

> The current frozen architecture can independently verify bounded,
> source-backed chains through 64 hops. It does not yet justify saying that it
> can perform arbitrary 64-hop mathematics.

Artifacts: `workspaces/ltm-limit-l1-r1/locked-results.json`,
`controls.json`, `scale-results.json`, `boundary-results.json`,
`verification.json`, and `report.json`.
