# G12 — Persistent Block Store and Incremental Compilation

## Hypothesis

Can a one-million-object topology use immutable checksummed binary blocks,
SQLite lineage metadata and atomically published manifests to make local
updates, corrections and deletion safe without rebuilding unrelated regions?

## Frozen experiment

- Standard-library Python, SQLite, SHA-256, fixed binary records and `mmap`.
- Development: 10,000 objects in 100 regions; locked: 1,000,000 objects in
  1,000 regions.
- Each source yields ten local derived objects, allowing exact source-to-object
  lineage and deletion auditing.
- Locked operations: 32 insertions, 32 corrections, 32 deletions, 20 injected
  crashes and eight corruption attacks.
- 128 deterministic queries exercise normal, historical, corrected, deleted
  and provenance states.

## Contract

Region blocks are immutable and content-addressed. A change creates exactly one
replacement region block, its summary, its parent summary and a new manifest.
SQLite publishes the new version pointer only after those artifacts exist. Old
manifests therefore remain readable and an interrupted update exposes either
the complete old or complete new version.

Sources and lineage are append-only. A deletion leaves audit records but makes
all descendants inactive in the new block. Queries use SQLite location indexes,
then memory-map exactly one checksummed block; they never replay a transcript
or scan the full topology.

## Gates and boundary

G12 requires deterministic builds, exact clean-rebuild agreement, zero
unrelated-block rewrites, zero deleted descendants, complete old-or-new crash
recovery, zero accepted corruptions, indexed one-block queries and bounded
runtime, memory and disk use.

Passing proves this controlled one-million-object storage mechanism only. It
does not prove natural-language compilation, reasoning quality, decoding or
100M-token-equivalent context reliability.
