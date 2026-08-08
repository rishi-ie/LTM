# Parasite v0.1 — Persistent Modular LTM Runtime

Parasite is the persistent, modular runtime companion to LTM-ARCH-1.2. It has
four replaceable components—compiler, field, optimizer, and decoder—around a
small integrity kernel. Runtime data is stored under `var/` and is ignored.

Its field, optimizer, exact execution, and verifier are transformer-independent.
Any transformer used for compilation or realization is a replaceable,
non-authoritative adapter.

The supported v0.1 boundary is structured G1 input, supplied-formal acyclic
mathematical realities, and supplied-span controlled conversation. Raw language,
cyclic equilibrium, HTTP serving, and production concurrency are deferred.

```text
Compiler → Latent Dynamic Field → Latent Optimizer → Decoder
                       ↑
              Integrity kernel
```

The compiler is replaceable and accepts only three explicit kinds:
`topology_document`, `mathematical_reality`, and `conversation_turn`. Conversation
turns run through the actual frozen G2.13 checkpoint and G2.14 thresholds; callers
cannot submit a trusted gate result. Mathematical input is formal atoms and factors,
never mathematical prose.

The field writes Mumbrane IR v1 and FieldIR v2 into a staging generation, reloads
and cross-checks both representations, atomically renames the content-addressed
generation, and only then changes the SQLite active pointer. Tenant and reality
partitions use hashed directory names. Conversation occurrences live in scoped
SQLite session overlays and assistant output is permanently non-evidential at
authority `0.25`.

The optimizer exposes two explicitly selected lanes. `exact` projects FieldIR into
G6 and G7 and authorizes through G9. `fixed_equilibrium` has zero parameters and
uses synchronous L7 satisfaction sweeps with source-normalized noisy-OR,
conjunction, positive/negative channels, and explicit tension. A separate module
recomputes the acyclic fixed point and derivation certificate.

The decoder is structured and deterministic. An optional renderer receives only
the authorized bundle; if its returned claim inventory differs, Parasite falls
back to deterministic text.

```bash
.venv/bin/python -m pip install --no-build-isolation --no-deps -e ./Parasite
.venv/bin/python -m parasite init
.venv/bin/python -m parasite demo
```

Every accepted result is bound to tenant, reality, source, generation, and
verification hashes. A custom reality never changes another reality.

## State and refinement

Persistent state is ignored under `Parasite/var/`:

```text
catalog.sqlite
archive/<source-hash>/
fields/<tenant-hash>/<reality-hash>/<generation-hash>/
staging/
```

Refinement freezes inputs, changes one of the four components, runs its component
tests and both vertical slices, compares against `benchmarks/baseline-v0.1.json`,
and adopts only with no safety regression. v0.1 intentionally has no factory or
plugin framework; package boundaries and immutable contracts provide modularity.

## Verification

```bash
.venv/bin/python -m pytest -q Parasite/tests
.venv/bin/python -m ruff check Parasite
.venv/bin/python -m compileall -q Parasite/src Parasite/tests
.venv/bin/python -m parasite demo
```

## P1 acceptance check

The fresh bounded prototype check uses 72 opaque cases, a separate runtime
worker, an independent fixed-point oracle, and six causal controls. It does
not reuse the transparent baseline chain. Run it with:

```bash
.venv/bin/python Parasite/benchmarks/run_acceptance.py \
  --workspace Parasite/var/checks/parasite-p10 --offline
```

The completed local `r10` evidence is classified `PARASITE-P1-A`: compiler and
exact execution agreement `1.00`, equilibrium agreement `1.00`, depth-20
success `1.00`, zero incorrect accepted conclusions, zero decoder additions,
and approximately `313 ms` p95 equilibrium query time. This is bounded evidence
for supplied formal realities and supplied-span conversation; it is not a raw
language, cyclic-equilibrium, or production-serving result.
