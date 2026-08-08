# G11 — Safe Conversation-Memory Lifecycle

## Hypothesis

Can a copy-on-write session overlay retain structured conversational context,
references, corrections, preferences, scoped conflicts and episode provenance
while leaving immutable base knowledge untouched and never elevating assistant
output into evidence?

## Frozen experiment

- Standard-library Python and SQLite only; no language model, embeddings,
  latent optimization or network.
- Development: eight deterministic twelve-turn conversations (`seed 1739`).
- Locked: 32 fresh deterministic twelve-turn conversations (`seed 20260812`).
- Every conversation writes a structured user event transactionally, creates a
  non-evidential assistant event, uses indexed overlay queries, restarts once,
  folds and reopens an episode, deletes a claim and clears the session.
- The runtime owns only public structured turns. An independent full-history
  oracle owns expected active state, answer, references, preferences,
  conflicts, provenance and post-clear behavior.

## Storage contract

The immutable `base_claims` database is separately hashed. Session SQLite
holds raw events, append-only operations, claims, references, preferences,
conflicts, assistant events, episode summaries, tombstones, caches and a
generation counter. Corrections set the old claim's ending turn. Clearing
increments the generation, so old overlay state can remain auditable but is
inaccessible to ordinary queries. Episode summaries are indexes with exact
provenance links, never evidence by themselves.

Assistant events have `independent_evidence=false` and authority `0.25`.
Removing the original claim must leave ordinary retrieval unable to recover it;
the deliberately unsafe assistant-as-evidence control demonstrates the attack
that this rule prevents.

## Gates

Every controlled oracle agreement, correction, preference, scope, conflict,
provenance, restart, deletion, clearing and base-hash gate is `1.00`; assistant
self-contamination and cross-session leakage are `0`; ordinary queries never
scan the transcript and p95 rows read is at most 24. Runtime must be below 30
seconds and peak RSS below 256 MB. Any violation fails mechanically.

## Boundary

A pass establishes only this small structured session-memory lifecycle. It
does not establish raw-language compilation, Qwen decoding, integrated product
quality, persistence at production scale or 100M-token reliability.
