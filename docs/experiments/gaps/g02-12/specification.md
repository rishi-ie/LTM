# G2.12 — Factorized Atomic Operator–Role Compiler

G2.12 tests whether a one-pass MiniLM state can be factorized into an operator
decision, G1-conditioned named-role assignments, an explicit forward/reverse
direction score, context, and a deterministic complete-graph commit.

The learned model never predicts G1 arity, legal node kinds, exact operators,
field operators, or hard/soft status. Those are derived from the G1 registry.
Accepted outputs must validate through G1 before any FieldIR or Mumbrane handoff.

The experiment is fail-fast. The gold-span kernel must satisfy the frozen
precision, coverage, role, direction, context, and zero-severe-error gates before
raw span extraction, identity, document composition, or downstream integration
is authorized. G2.5 remains the provisional compiler unless G2.12 passes
independently.

Runtime constraints are the pinned local `all-MiniLM-L6-v2`, one encoder pass per
sentence, CPU float32, four threads, layers 1–4 frozen, layers 5–6 trainable
after warm-up, no network, and no generative decoder. Historical G2.5 and
G2.11 artifacts remain immutable.

