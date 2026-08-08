# G2.4 — Atom-Vector Topology Compiler Report

## Result

**G2.4-r1 — sentence-core failure: atom grounding or role binding is inadequate.**

This is a locked, 4,000-case sentence-core run using the staged MiniLM atom-slot model. It tests neither the specified stored-content atom matching nor the specified cross-sentence linker; those parts were not implemented in r1. Therefore this result is not a full G2.4 classification or an authorization to replace the failed compiler boundary.

## Locked measurements

| Metric | Value |
| --- | ---: |
| accepted | 2844 |
| accepted exact precision | 0.24648382559774965 |
| accepted safe coverage | 0.2190625 |
| all case exactness | 0.17525 |
| cases | 4000 |
| disposition accuracy | 0.911 |
| relation accuracy | 0.4065625 |
| silent invalid insertions | 0 |

The numerical result fails the intended compiler gates by a wide margin: accepted exact precision is 24.65% against 99%, and safe accepted coverage is 21.91% against 85%. The constrained G1 assembler prevented syntactically invalid structures from entering topology, but 2,143 of 2,844 accepted outputs were semantically wrong under exact topology comparison. This means safety filtering exists, but the learnt grounding and role-binding machinery is not reliable enough to authorize an atom-vector compiler.

## Boundary

Accepted output is assembled only after G1 registry validation. Invalid output is quarantined rather than partially inserted.
