# G2.14 — Margin-Gated Conversational Compiler Report

## Classification

**G2.14-A — SUPPLIED-SPAN CONVERSATIONAL COMPILER PASS**

## Authoritative execution

Corrected authoritative workspace: `workspaces/topology-g2-14-r3/` (ignored).
The initial `r1` locked artifacts and corrected `r2` lifecycle attempt are
preserved; no locked result was overwritten. The final `r3` run reused the
same frozen checkpoint and locked inputs and added the immutable control
summary.

### Calibration

The fresh 2,400-case calibration suite selected:

```text
head confidence:       0.50
head margin:           0.02
identity confidence:   0.70
identity margin:       0.05
```

Calibration had 2,000 accepted exact cases, 1.0000 accepted precision, 1.0000
safe coverage, 1.0000 ambiguity recall, and zero incorrect accepted outputs.

### Fresh locked compiler result

| Metric | Result | Gate | Outcome |
| --- | ---: | ---: | --- |
| Locked cases | `4,800` | `4,800` | PASS |
| Accepted turns | `4,005` | — | measured |
| Accepted exact turns | `4,005` | — | measured |
| Accepted precision | `1.0000` | `1.00` | PASS |
| Safe coverage | `0.9998` | `>=0.95` | PASS |
| All-case exactness | `0.9998` | `>=0.95` | PASS |
| Discourse-act macro-F1 | `0.9996` | `>=0.97` | PASS |
| Memory-action macro-F1 | `1.0000` | `>=0.97` | PASS |
| Context accuracy | `1.0000` | `>=0.97` | PASS |
| Unique-reference precision | `1.0000` | `1.00` | PASS |
| Unique-reference safe coverage | `1.0000` | `>=0.95` | PASS |
| Ambiguity recall | `1.0000` | `1.00` | PASS |
| Candidate recall@16 | `1.0000` | `1.00` | PASS |
| Cross-session targets | `0` | `0` | PASS |
| Incorrect accepted predictions | `0` | `0` | PASS |

The same frozen G2.13 model without the acceptance layer accepted 4,006 turns
and retained one incorrect accepted prediction. The joint gate removed that
mutation. The recorded confidence-only and candidate-margin controls also
remained safe on this fresh suite; the decisive safety evidence is the direct
ungated-versus-joint comparison and the explicit candidate filtering tests.

### Conditional G11 lifecycle panel

The independent structured G11 panel used 400 conversations (12 turns each)
and a separately generated oracle. All lifecycle comparisons were exact:

| Check | Result |
| --- | ---: |
| Context/reference agreement | `1.0000` |
| Preference persistence | `1.0000` |
| Correction supersession | `1.0000` |
| Fictional scope and conflict retention | `1.0000` |
| Provenance agreement | `1.0000` |
| Restart/replay equality | `1.0000` |
| Targeted-deletion residue | `0` |
| Post-clear session influence | `0` |
| Cross-session leaks | `0` |
| Ordinary transcript scans | `0` |
| p95 rows read | `3` |

This is a structured G11 compatibility check, not evidence that G2.14 can
extract raw spans or perform reasoning compilation.

## Boundary and conclusion

G2.14 closes the supplied-span conversational routing boundary: the frozen
G2.13 model can be wrapped by bounded typed resolution and a monotonic margin
gate so that accepted conversational mutations are exact on the fresh locked
suite. It does not replace G2.5 for reasoning, and it does not authorize raw
language segmentation, factual promotion of user assertions, unrestricted
conversation, or a production claim.

