# G1 — Executable Conversational Topology Report

## Result

**Classification: G1-A**

This deterministic schema experiment tested a fresh 80-fixture locked suite after an
independent 80-fixture development run. It used only Python's standard library
and SQLite. It did not use a language model, embeddings, latent optimization or
a decoder.

## Locked measurements

| Check | Result |
| --- | ---: |
| Valid fixture acceptance | 32/32 |
| Invalid fixture rejection | 48/48 |
| Canonical round trips | 32/32 |
| Exact operator checks | 32/32 |
| Valid verifier checks | 32/32 |
| Adversarial verifier rejections | 32/32 |
| Version-1 migration checks | 16/16 |
| Field contracts | PASS |
| Replay hash equals stored hash | True |
| Reverse-order hash equals stored hash | True |
| Runtime | 0.1261 s |
| Peak RSS | 28.16 MB |

## Conclusion boundary

The registered initial conversational topology is a stable executable internal language under this controlled schema test. G2, natural-language topology compilation, is authorized.

This result does not establish unrestricted-language compilation, prompt
addressing, active-frontier coverage, latent optimization, decoder quality or
100M-context scaling.
