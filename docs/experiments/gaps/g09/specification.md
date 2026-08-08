# G9 — Independent Result Verifier

## Hypothesis

A separately implemented verifier can authorize only results whose sources,
proof, hard constraints, coverage certificate, provenance and registered soft
state all agree with the topology. Low reported energy or a plausible-looking
bundle is not evidence of correctness.

## Compact design

- 24 development and 48 locked valid/corrupted base-twin pairs.
- Every valid bundle contains a small typed topology, sources, proof, coverage
  certificate, soft state and provenance.
- Every corrupted twin changes exactly one safety-relevant property while
  retaining high confidence and a low reported energy.
- The verifier replays implications and conjunctions itself and solves the
  registered separable quadratic soft objective itself.
- It imports no G5–G8 engine, optimizer, certificate function or generator.

## Locked attacks

The locked set contains four examples each of reversed relations, missing
premises, fabricated conclusions, scope escape, superseded evidence, hidden
conflicts, missing hard factors, incomplete coverage, source-hash corruption,
assistant self-evidence, soft-state corruption and version mismatch.

## Decision rule

`G9-A` requires every valid result to receive its expected valid status, every
corruption to be rejected with its exact stable code, zero false accepts,
deterministic replay, runtime below ten seconds and peak RSS below 256 MB.

This experiment is intentionally isolated. It proves a small independent
authorization contract, not G5–G8 integration, language understanding,
decoder quality, production security or 100M-context reliability.
