# G2.6 — G1-Constrained Dual-Prototype Atom-Pair Compiler

## Question

Can a small one-pass MiniLM compiler use G1-derived relation prototypes and
ordered atom-pair scoring to select a complete relation and named-role binding
on genuinely split-disjoint controlled language?

## Boundary

G2.6 is fail-fast. It first evaluates a gold-atom kernel, then authorizes span
extraction, persistent identity, and document composition only if the kernel
reaches the frozen 95%-level gates. The executed run stopped at the kernel
boundary. Historical G2 and G2.5 results remain unchanged.

## Contract

The runtime enumerates only G1 registry-valid relation/role assignments, scores
complete candidates jointly with ordered atom-pair interactions, and commits
only candidates that pass G1 and FieldIR validation. Dense vectors remain
advisory; sparse G1 incidence authorizes topology. Low confidence returns
clarification or quarantine, and a sentence is committed atomically or not at
all.

The development suite contained 3,600 split-disjoint cases: 2,520 accepted
cases (140 per registered G1 relation), 540 clarification cases, and 540
quarantine cases. It used separate entity vocabularies, relation constructions,
scopes, and predicates for development and locked data. Because the development
kernel failed, no locked suite was generated.

## Pass classification

`G2.6-A — CONTROLLED G2 PASS` requires the frozen gates in
[`topology-g2-6.json`](../../../../configs/topology-g2-6.json), deterministic
replay, FieldIR/G1 round-trip integrity, zero reversal or high-severity
polarity false accepts, and zero invalid insertions. The executed result is
`G2.6-B — JOINT ROUTING KERNEL FAILURE`.
