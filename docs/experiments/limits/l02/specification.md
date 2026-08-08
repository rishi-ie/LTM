# L2 — Controlled Mathematical-Language Reality Compiler

## Objective

L2 tests whether controlled English and mixed mathematical notation can be
compiled into exact, reality-scoped formal bodies and explicit source/goal
questions for the frozen I3.1 proof lane. Primary questions contain an explicit
target (`prove E = F`, `are E and F equivalent?`). Open-ended simplification and
solve prompts are recognized and safely abstained from; they are deferred to a
future goal-discovery experiment.

The authoritative compiler is a small local MiniLM structured compiler with a
grammar-constrained AST candidate layer. Known rules require an exact match to
the frozen registry. Custom rules require explicit confirmation before active
insertion. Every accepted proof is replayed independently; compiler output can
never directly authorize a factual conclusion.

## Boundaries

- English controlled mathematical prose and ASCII/Unicode notation only.
- Existing I3.1 expression vocabulary and registered 46-schema fragment.
- Arithmetic, order, modular, finite-set and propositional transformations.
- Primary proof depth 1–16; depths 17–64 are diagnostic endurance cases.
- No raw image parsing, unrestricted textbook mathematics, calculus, geometry,
  word-problem modeling, or automatic custom-axiom activation.
- I3.1 and L1 source, checkpoints, thresholds and reports remain immutable.

## Runtime flow

```text
source + signed reality metadata
→ one encoder pass
→ intent/spans/AST candidates
→ grammar, type, variable and direction checks
→ registry match or confirmation gate
→ exact MathematicalBody/Mumbrane transaction

explicit-target question
→ source and goal ASTs
→ frozen-compatible bounded proof search
→ process-isolated exact replay
→ authorized answer or abstention
```

Open-ended questions return `goal_discovery_required`; they do not enter proof
search. Source text remains archive-only during numeric execution.

## Commands

```bash
python -m ltm_limit_l2 model-check --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 grammar-build --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 dataset-build --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 develop --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 calibrate --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 freeze --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 locked-suite-build --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 evaluate --workspace workspaces/ltm-limit-l2-r1 --offline
python -m ltm_limit_l2 reality-evaluate --workspace workspaces/ltm-limit-l2-r1 --offline
python -m ltm_limit_l2 end-to-end-evaluate --workspace workspaces/ltm-limit-l2-r1 --offline
python -m ltm_limit_l2 verify --workspace workspaces/ltm-limit-l2-r1 --offline
python -m ltm_limit_l2 report --workspace workspaces/ltm-limit-l2-r1
python -m ltm_limit_l2 run-all --workspace workspaces/ltm-limit-l2-r1 --offline
```

## Acceptance gates

Accepted bodies and questions require precision `1.00`, zero incorrect active
insertions, zero variable/direction/reality errors, and exact replay of every
accepted proof. Minimum safe coverage is `0.95` for compiler outputs and `0.85`
for end-to-end compiled proof requests. The result is classified `L2-A` only
when representation, compiler, trust, proof, lifecycle, integrity and compute
gates all pass.

## Testing strategy

Tests cover canonical parsing, precedence, alpha-renaming, variable capture,
registry matching, direction policies, custom-rule confirmation, reality
isolation, atomic rollback, Mumbrane round trips, proof replay, open-ended
abstention, evaluator isolation, frozen-checkpoint protection and deterministic
replay. The locked suite is split-disjoint in surface forms, AST shapes,
symbols, realities and proof motifs.
