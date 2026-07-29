# Evaluation Data

Evaluation fixtures are grouped by the phase that first treats them as
development or locked held-out data.

| Phase | Fixture | Use |
| --- | --- | --- |
| Phase 1 | `phase-1/development.json` | Inspected development suite |
| Phase 1.1 | `phase-1.1/held-out.json` | Locked multi-state evaluation |
| Phase 1.2 | `phase-1.2/development.json` | Manifest reusing inspected suites |
| Phase 1.2 | `phase-1.2/held-out.json` | Locked equilibrium evaluation |

Held-out suites must never select or tune configurations. Phase 1.2 writes its
selected development configuration before opening its held-out fixture.

`phase-1.2/generate_held_out.py` deterministically produced the checked-in
Phase 1.2 fixture. Evaluation reads the static JSON; it does not generate
documents, queries, or labels at runtime. Experiment outputs record model,
suite, and corpus hashes.
