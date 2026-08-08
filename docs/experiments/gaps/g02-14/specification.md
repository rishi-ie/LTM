# G2.14 — Margin-Gated Conversational Compiler

## Purpose

G2.14 isolates the remaining G2.13 safety failure. It keeps the frozen
G2.13 one-pass conversational predictions unchanged and adds only a bounded
G2.4-style candidate resolver plus a monotonic confidence and ambiguity gate.

The tested boundary is:

```text
supplied semantic spans + controlled conversational turn + public metadata
→ frozen G2.13 prediction
→ typed candidates (at most 16)
→ confidence, margin and compatibility checks
→ accept / clarification_required / quarantine
```

Only an accepted result may authorize a conversation-memory mutation. A
clarification records a neutral audit event and a quarantine performs no
active-memory mutation. G2.14 does not test raw span extraction, deep
reasoning relations, or unrestricted conversation.

## Frozen inputs and policy

- Checkpoint: `workspaces/topology-g2-13-r1/kernel-checkpoint.pt`.
- MiniLM and G2.13 source hashes are checked before evaluation.
- Candidate resolution filters session, scope, episode, validity, deletion,
  supersession and object type before scoring.
- The resolver visits no more than 16 public candidates and never scans the
  transcript or complete field.
- Acceptance is monotonic: the wrapper may downgrade a model decision, never
  upgrade an abstention.

Calibration uses a fresh 2,400-case suite. Locked evaluation uses a fresh
4,800-case suite and immutable prediction artifacts. Thresholds are selected
only for zero incorrect accepted predictions.

## Gates

The mandatory compiler gates are zero incorrect accepted predictions,
accepted precision of 1.0, safe coverage of at least 0.95, all-case exactness
of at least 0.95, act/action/context pre-gating quality of at least 0.97,
perfect ambiguity recall, perfect unique-reference precision, no cross-session
targets, and no invalid or partial commits. The conditional lifecycle panel
must preserve the independent G11 oracle exactly.

