# Parasite-L8 — Compiled Reasoning-Policy Equilibrium

This is an isolated experiment instance. It does not modify `Parasite/`; it
hash-pins the existing Parasite source/configuration as a read-only dependency
and keeps all state under `Parasite-L8/var/`.

The implementation tests one narrow question: can a signed, structured
reasoning policy change the fixed-law latent equilibrium and the verified
conclusion when the mathematical field and formal query are unchanged?

This is provisional evidence for LTM's post-transformer core, not a claim that
the reduced probe establishes general transformer replacement.

The runtime has zero trainable parameters. Policies are limited to bounded
numeric opcodes (`source_multiplier`, `path_decay`, conjunction mode, source
class requirements, thresholds, margins, and disclosure flags). The optimizer
uses synchronous fixed-point updates; exact factor eligibility does not insert
an answer directly. The evaluator is a separate process and reimplements the
activation equations without importing the runtime optimizer.

Run the focused checks:

```bash
PYTHONPATH=Parasite-L8/src:Parasite/src:src .venv/bin/python -m pytest -q Parasite-L8/tests
PYTHONPATH=Parasite-L8/src:Parasite/src:src .venv/bin/python -m ruff check Parasite-L8/src Parasite-L8/tests Parasite-L8/benchmarks
```

Run a fresh reduced probe (a completed workspace is never overwritten):

```bash
PYTHONPATH=Parasite-L8/src:Parasite/src:src \
  .venv/bin/python -m parasite_l8 run-all \
  --workspace Parasite-L8/var/l8-r7
```

The first completed isolated run is `var/l8-r6`. Its report is a reduced
vertical probe, not the full 96-observation L8 suite from the design plan.
It measured 16 opaque depth observations, policy twins, one-sweep and no-
optimization controls, storage-order reversal, and a separate evaluator
process. The result is evidence for policy-conditioned behavior within this
small boundary; it does not establish raw-language compilation, cyclic fields,
unlimited depth, or production serving.
