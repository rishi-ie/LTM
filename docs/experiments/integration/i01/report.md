# LTM-I1 — Canonical FieldIR v2 Integration Validation

This report validates the registered numeric FieldIR v2 contract against the existing G3–G10.1 interfaces. The representation suite uses evaluator-generated or confirmed topology; it does not claim raw-language compilation.

Classification: **LTM-I1-A — CANONICAL INTEGRATION PASS**

## Locked results

| Metric | Value |
| --- | ---: |
| address agreement | 1.0 |
| artifact agreement | 1.0 |
| cases | 512 |
| coverage agreement | 1.0 |
| decoder agreement | 1.0 |
| failures | 0 |
| frontier agreement | 1.0 |
| g9 agreement | 1.0 |
| hard agreement | 1.0 |
| projection agreement | 1.0 |
| semantic agreement | 1.0 |
| soft agreement | 1.0 |
| vector rows read | 192 |

## G2.5 supplied-atom diagnostic

The frozen G2.5 checkpoint emitted 239 handoffs from 360 supplied-atom cases. 192 were correct under the G2.5 evaluator gold, and all 192 correct handoffs converted into FieldIR v2 successfully (conditional conversion precision 1.000). This is not a raw-language compilation result.

Measured locked runtime: 34.524s; peak RSS: 1126.2MB; semantic replay: True.
The registered corruption suite contained 128 attacks (eight per family); all 128 were rejected with their declared primary code.

The canonical path is: numeric FieldIR v2 → packed reload → G3/G4/G5 views → G6 exact state → G7 quadratic soft state → unchanged G9 verifier → strict G10.1 realization.

G2.5 is diagnostic only. Its supplied-atom kernel is not treated as a raw sentence compiler, and its known relation accuracy does not alter this representation verdict.

A pass authorizes the representation-backed integration step and a later compiled-topology rerun. It does not establish unrestricted language compilation, optimal learned geometry, free-form naturalness, ontology completeness, production serving, or G15.
