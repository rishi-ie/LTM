# L4 — Unseen Branching Mathematical Proof Discovery

L4 tests whether a compact learned proposal/value kernel can causally improve
exact proof search over a fixed reusable axiom bank. Runtime receives supplied
formal ASTs only. It receives no expected depth, route, answer candidate,
required axiom/body identifier, proof certificate, template identifier or
evaluator path.

Two paired tracks use the same public cases and exact verifier. The frozen
I3.1 `r13` track is diagnostic. The newly trained L4 track is authoritative.
Every accepted proof is replayed outside the runtime process. The primary
claim covers evaluator-certified branching proofs through 16 primitive
applications. Depths 17–45 are a separate witness-length stress result.

## Executable mathematical contract

The historical 46-schema I3 inventory remains unchanged. L4 compiles a signed
39-schema executable subset. It excludes no-op, unbound-variable, synthetic
substitution, one-way implication and unsound modular rewrites. Reverse
directions that introduce an unbound variable are forbidden. Axiom audit,
type/sort validation and independent finite-domain checks must pass before any
dataset is generated.

For each state, exact code enumerates at most 128 legal applications before
the model ranks them. The model retains 16 proposals and a 16-state beam. It
cannot create a rewrite or authorize a conclusion. One hop is one primitive
schema application.

## Corpus and evidence boundary

Training, development and locked programs are split-disjoint. The axiom/body
bank is frozen before theorem generation and cannot contain query-specific
chains. Primary provable cases have independently certified shortest paths,
multiple legal choices and no direct source-to-goal body. Paired goals require
different first actions; detour cases require a temporary expression-size
increase. Stress cases report verified witness length without claiming global
shortest depth when exhaustive certification is unavailable.

The locked result requires 100% accepted-proof precision and replay, zero
incorrect accepted conclusions, at least 88% all-case exactness and the
depth/branching gates frozen in `configs/ltm-limit-l4.json`. It also requires
the full learned method to outperform no-scorer, no-goal, random and no-value
controls. A high score without causal control sensitivity is classified as a
mechanism failure.

## Commands

```bash
python -m ltm_limit_l4 model-check --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 axiom-audit --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 dataset-build --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 develop --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 calibrate --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 freeze --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 locked-suite-build --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 evaluate --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 stress-evaluate --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 field-evaluate --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 controls --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 attacks --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 audit --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 verify --workspace workspaces/ltm-limit-l4-r1 --offline
python -m ltm_limit_l4 report --workspace workspaces/ltm-limit-l4-r1
python -m ltm_limit_l4 run-all --workspace workspaces/ltm-limit-l4-r1 --offline
```

Completed locked shards and results are immutable. Any semantic correction
after locked generation requires a fresh attempt and fresh locked seed.
