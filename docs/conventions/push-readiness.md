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
`git diff`. The audit must show matching `LTM-ARCH-1.1` hashes, a valid
experiment registry, a clean Python 3.11 environment, no tracked generated
artifacts, and no broken documentation links.

Never stage or push `.models`, `.venv*`, `workspaces`, checkpoints, raw suites,
evaluator gold, or vector sidecars. Historical reports and classifications are
evidence records and must not be rewritten to simplify the current narrative.

This procedure does not stage, commit, or push anything. Those actions remain
an explicit user review step.
