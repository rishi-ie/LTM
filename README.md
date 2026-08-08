# Latent Topology Models

This repository contains the research evidence and first product foundation for
**Latent Topology Models (LTM)**: an independent post-transformer energy-based
latent architecture with a persistent universal Mumbrane topology,
profile-configured satisfaction laws, exact typed reasoning, independent
verification, and authorized surface realization.

## Start here

1. [Documentation index](docs/README.md)
2. [Normative LTM-ARCH-1.2 lock](docs/architecture/architecture-lock-v1.md)
3. [Mother Architecture thesis](docs/architecture/mother-architecture.md)
4. [Component internals](docs/architecture/component-internals.md)
5. [Experiment-series evidence compendium](docs/experiments/series-summary.md)
6. [Experiment series registry](docs/experiments/README.md)
7. [Semantic topology representation](docs/architecture/semantic-topology.md)
8. [LTM v1 build plan](docs/roadmap/ltm-v1-build-plan.md)
9. [Authoritative results ledger](docs/roadmap/results-ledger.md)
10. [Parasite v0.1 persistent modular runtime](Parasite/README.md)
11. [Parasite-L8 policy-equilibrium experiment](Parasite-L8/README.md)

Current status: G1, G3–G9, G10.1, and G11–G13 pass on their registered
controlled boundaries. G2 is engineering-complete through a modular boundary:
G2.14 passes supplied-span conversational routing, while safety-gated G2.5
remains the provisional reasoning compiler. G14 is a controlled composition
pass with a raw-language product verdict of `NOT_READY`. G15 has not run. These
results do not establish unrestricted language reasoning, raw semantic
segmentation, fluent general decoding, or production readiness.

The latest capacity result is L1. The frozen I3.1 runtime completed 20/20
grounded formal and opaque traversal cases at every depth from 1 through 64,
with exact replay and no invalid accepted proofs. This is observed grounded
capacity—not arbitrary 64-hop mathematics. L2 now has a conservative arithmetic
compiler baseline, but no locked result. See the [L1 report](docs/experiments/limits/l01/report.md)
and [L2 development report](docs/experiments/limits/l02/report.md).

L3 later verified controlled exact compilation and indexed 45-step replay, but
its learned scorer was not causally necessary. L4 tested genuine branching
selection and stopped before lock: accepted proofs were exact, while answerable
success was 33.3% and proposal recall@16 was 27.4%. Learned branching proof
discovery remains open; see the [L4 report](docs/experiments/limits/l04/report.md).

L7 `r3` adds the latest controlled architecture result: a zero-parameter fixed
satisfaction law reached independently reproduced equilibria on 240 supplied-
formal prompts over a 512-body acyclic field, including contradictions,
conjunctions, scope and time, through 20 body applications. This does not yet
cover cyclic fields, scaling, 64-hop equilibrium or natural-language input;
see the [L7 report](docs/experiments/limits/l07/report.md).

The [LTM-R2 representation audit](docs/experiments/representation/r02/report.md)
authorizes Mumbrane IR v1 as the canonical future compiler target: one numeric
unit/port/coordinate form supports reasoning, planning, evidence and
conversation profiles. FieldIR v2 remains the implemented execution bridge
while Mumbrane IR is promoted from its isolated validated package.

## Repository layout

- `docs/` — architecture, audits, roadmap, specifications, and bounded reports;
- `src/ltm/` — the product-foundation numeric field contracts and adapters;
- `src/topology_*` and `src/micro_ltm*` — independent historical experiments;
- `tests/` — tests matching each source package;
- `configs/` — one frozen configuration per experiment;
- `Parasite/` — the persistent four-component prototype runtime and its tests;
- `Parasite-L8/` — isolated compiled-policy equilibrium experiment (state ignored);
- `workspaces/` — ignored local suites, manifests, checkpoints, and raw runs.

See the [repository layout convention](docs/conventions/repository-layout.md)
before adding G15 or another experiment.

## Development

The canonical environment is Python 3.11 in `.venv`. `.venv-g101` is retained
only as ignored historical state. Models, workspaces and both environments are
local assets and are not pushed.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements/py311-macos.lock
.venv/bin/python -m pip install -e .

.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m ltm verify --workspace workspaces/_repository-catalog --offline
git diff --check
```

Python package names and existing experiment commands remain unchanged.
Downloaded models, virtual environments, raw results, and workspaces are local
assets and are intentionally excluded from Git.

See the [push-readiness procedure](docs/conventions/push-readiness.md) before
staging. Repository consolidation never stages, commits, or pushes
automatically.
