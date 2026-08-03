# Latent Topology Models

This repository is a research platform for **Latent Topology Models (LTM)**.
It contains the canonical architecture, a falsifiable gap-experiment program,
compact reference implementations, and permanent bounded reports for completed
experiments.

## Start here

1. [Documentation index](docs/README.md)
2. [Canonical architecture](docs/architecture/overview.md)
3. [Remaining product gaps](docs/roadmap/remaining-gaps.md)
4. [Gap experiment program](docs/roadmap/experiment-program.md)
5. [Authoritative results ledger](docs/roadmap/results-ledger.md)

The current isolated progress is G1, G3, G4, G5, G6, and G7 passed; G2 and
G2.1 failed their registered compiler gates. G8 is the next authorized
controlled experiment. These results do not establish unrestricted-language
reasoning, frontier-model equivalence, or 100-million-token reliability.

## Repository layout

- `docs/` — architecture, roadmap, specifications, and bounded reports;
- `src/` — independent experiment packages with stable import names;
- `tests/` — tests matching each source package;
- `configs/` — one frozen configuration per experiment;
- `workspaces/` — ignored local suites, manifests, checkpoints, and raw runs.

See the [repository layout convention](docs/conventions/repository-layout.md)
before adding G8 or another experiment.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
git diff --check
```

Python package names and existing experiment commands remain unchanged.
Downloaded models, virtual environments, raw results, and workspaces are local
assets and are intentionally excluded from Git.
