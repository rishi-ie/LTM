# Push Readiness

This repository deliberately separates tracked architecture/code from local
research assets. Before a push, run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m ltm verify --workspace workspaces/_repository-catalog --offline
git diff --check
```

Then inspect `workspaces/_repository-catalog/push-readiness.json` and the full
`git diff`. The audit must show matching `LTM-ARCH-1.2` hashes, a valid
experiment registry, a clean Python 3.11 environment, no tracked generated
artifacts, and no broken documentation links.

Never stage or push `.models`, `.venv*`, `workspaces`, checkpoints, raw suites,
evaluator gold, or vector sidecars. Historical reports and classifications are
evidence records and must not be rewritten to simplify the current narrative.

Large local research artifacts are preserved outside the repository at
`/Users/rishi/work/ltm-archive/2026-08-08-pre-prototype/`. The archive is
manifest-backed and reversible; verify it with:

```bash
.venv/bin/python -m ltm archive-verify \
  --archive /Users/rishi/work/ltm-archive/2026-08-08-pre-prototype
```

It contains workspaces at or above 100 MiB, `.venv-g101`, and models not listed
in `.models/model-manifest.json`. The active repository retains small workspaces,
the canonical environment, MiniLM, FLAN, and all tracked source and evidence.
Use `archive-restore` for an explicit item restoration; no symlinks are made.

This procedure does not stage, commit, or push anything. Those actions remain
an explicit user review step.
