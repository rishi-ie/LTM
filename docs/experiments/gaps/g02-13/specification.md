# G2.13 — Conversational Mumbrane Compiler

G2.13 tests the narrow language boundary needed for conversational memory:
one MiniLM pass identifies a discourse act, memory action, content spans,
references, corrections, preferences, scope, and safe disposition. Deep G1
reasoning is deliberately deferred.

Ordinary user assertions are session-scoped user-reported claim occurrences,
not verified facts. Preferences affect response form only. Ambiguous references
and corrections are retained without mutation. Assistant events are always
non-evidential. Accepted events must survive G1, FieldIR v2, Mumbrane, source
provenance, and G11 lifecycle validation atomically.

The experiment uses the pinned one-pass MiniLM boundary, split-separated
controlled conversational turns, a gold-span fail-fast kernel, bounded memory
candidate linking, and the existing G11 lifecycle oracle. A kernel failure
stops raw extraction, identity, lifecycle, and downstream stages. A pass closes
only controlled conversational compilation; it does not close reasoning G2 or
unrestricted language understanding.
