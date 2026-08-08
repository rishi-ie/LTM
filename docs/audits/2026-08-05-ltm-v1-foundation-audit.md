# LTM v1 Foundation Audit

## Scope

This audit covers CNTG-1-R2, MICRO-LTM 1–3, G1, G2, G2.1–G2.10, G3–G14,
G10.1, and LTM-R1. It checks reports, frozen artifacts where present,
deterministic replays, repository layout, representation boundaries and
documentation consistency. It does not rerun model training or overwrite a
locked workspace.

## Repository baseline

- 153 repository tests pass after the foundation package was added (the
  historical suite remains unchanged; three tests cover the new numeric
  foundation and G2.5 handoff).
- All checked Markdown links resolved.
- Ruff, compilation and `git diff --check` pass.
- Historical source/test/config names remain unchanged.
- Models, virtual environments, caches and the 47 GB local workspace tree are
  ignored and retained locally.

## Authoritative conclusion

The structured architecture is supported on its registered controlled
boundaries. The canonical active representation should be numeric FieldIR v2:
vectors provide geometry and routing, while exact sparse G1 incidence,
contexts and provenance provide authority.

G2 is engineering-complete only by explicit provisional waiver. G2.5 remains
an experimental failure and must be gated by preview, confirmation,
clarification and abstention. G15 remains unrun.

## Result matrix

| Area | Status | Architectural consequence |
| --- | --- | --- |
| G1 | PASS | exact topology authority |
| G2.5 | provisional baseline; measured failure | compiler proposal only |
| G2.6–G2.10 | failed or development-only | historical alternatives |
| G3–G9 | controlled PASS | request execution components |
| G10.1 | strict PASS | constrained surface realization |
| G11–G13 | controlled PASS | lifecycle, storage and scale evidence |
| G14 | controlled PASS / product not ready | partial composition evidence |
| LTM-R1 | representation holds | v2 numeric target |
| G15 | not run | next operational gate |

## Integrity result

Permanent experiment reports are hash-tracked in the generated audit manifest.
The cleanup is accepted only if those hashes remain unchanged, all historical
replays are deterministic, and no generated artifact becomes tracked.

## Read-only replay audit

The existing locked workspaces were replayed without rewriting results. The
following registered controlled runs reproduced their semantic outputs and
classifications; latency and memory telemetry were treated as non-semantic:

| Runs | Replay result |
| --- | --- |
| G3–G5 | identical outputs and classifications |
| G6–G9 | identical outputs and classifications |
| G10.1 | strict realization replay passed |
| G11–G14 | identical lifecycle, storage, scale and composition outputs |
| LTM-R1 | 12/12 representation replays matched |

The failed or development-only G2 variants were not promoted by replay. Their
historical classifications remain the ledger authority. G15 has no run to
replay.

## Foundation result

**`LTM-V1-F-A — FOUNDATION READY`**

The canonical package is implemented and verified. `ltm.audit` reports zero
missing experiment contracts, zero broken Markdown links, zero tracked
generated artifacts, and all required local assets remain ignored. The numeric
FieldIR v2 codec enforces 64-byte factor rows and 24-byte binding rows, keeps
full SHA-256 semantic identities in symbol tables, separates source text into
an archive, and preserves G2.5 content, operator, role, binding and context
vector sidecars.

This result authorizes implementation of the modular LTM foundation and the
next registered gate, G15. It is not a new G2 pass, does not reclassify any
historical experiment, and does not claim unrestricted language compilation or
production readiness.
