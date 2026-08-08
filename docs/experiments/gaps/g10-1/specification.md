# G10.1 — Strict FieldIR Surface Realization

G10.1 tests only whether a frozen compact language model can rank grammatical
surface realizations of a complete verified answer meaning representation.
Content selection, reasoning, retrieval, conflict resolution and inference are
out of scope. The grammar enumerates semantically valid candidates first; the
FLAN-T5-small model scores candidates and never generates unrestricted text.

The locked suite contains 256 fresh bundles, balanced across the eight G10
categories and the four registered styles. Every candidate must pass the
existing independent G10 validator before it is scored.

The primary pass requires 100% authorized-claim precision and recall, 100%
required-disclosure and disposition accuracy, zero unsupported or changed
claims, zero realization fallback, deterministic replay, and the existing
runtime/RSS limits. Human naturalness is deliberately not scored.
