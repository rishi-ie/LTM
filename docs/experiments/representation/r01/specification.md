# LTM-R1 — Vector-Native Field Representation Compatibility Audit

LTM-R1 verifies a representation-only change: active field execution uses
numeric atom, factor, role-incidence, context, provenance and vector-reference
records. Existing semantic vectors are reused exactly. Source text is external
archive data for auditing and surface realization, never an input to core field
execution.

The audit is not a new gap experiment and does not alter G1–G14 results. It
requires identical semantic replay, no text reads during core execution, and no
increase in active bytes, peak RSS, or operation counts. G2 is compatibility
only: G2.5's recorded recovery and reversal failures remain unchanged.
