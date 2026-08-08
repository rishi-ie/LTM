# Tests

`tests/ltm/` covers the canonical numeric FieldIR v2 foundation and its source
archive/adapters. Every historical experiment keeps its matching
`tests/topology_g*` or `tests/micro_ltm*` directory unchanged.

Repository verification runs the complete suite; historical tests are not
silenced or reclassified by the product foundation.

`tests/ltm_inference_i*/` covers the isolated I-series mechanisms. Passing
these focused tests establishes implementation invariants only; experiment
classifications still come from frozen development and locked gates recorded
in the results ledger.

`tests/ltm_limit_l1/` verifies the frozen limit-characterization harness and
proof replay. It does not convert the I3.1 development prototype into a locked
product component.

`tests/ltm_limit_l4/` verifies the signed axiom boundary, leakage-resistant
public contracts, branching corpus, exact replay and replacement-budget kernel.
Passing these tests does not override L4's measured development failure.

`tests/ltm/` also owns repository-level checks for the architecture manifest,
experiment registry, ignored artifact boundaries, and canonical environment.
