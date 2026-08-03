# G2.1 — Frozen Reasoning Embedding Kernel Report

## Classification

**G2.1-C / G2.1-R-NOT-DEMONSTRATED**

This experiment used frozen local all-MiniLM-L6-v2 embeddings, supplied
proposition spans, a linear multi-head baseline and a nonlinear 128-dimensional
reasoning projection. It does not test clause extraction or general document
ingestion.

## Locked results

| Method | Relation accuracy | Relation macro F1 | Direction | Exact roles | Scope | Disposition | G1 topology agreement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Linear multi-head probe | 0.875 | 0.843 | 0.725 | 0.808 | 0.900 | 1.000 | 0.808 |
| Nonlinear 128D projection | — | 0.450 | 0.716 | 0.417 | 0.850 | — | 0.367 |

The linear probe was the development-selected operational candidate. It also
reached ambiguity recall `1.000`, quarantine recall `1.000`, and produced zero
silent invalid topology insertions. Classified locked inference took `0.067 s`
and peak RSS was `727.41 MB`.

## Gate interpretation

The operational requirement was exact G1 topology agreement of at least
`0.98`. The selected linear probe reached `0.808`, a shortfall of `0.172`, or
17.2 absolute percentage points. Approximately one in five locked structures
therefore had at least one incorrect relation, direction, role, or scope field.

The result is useful but not safe as an authoritative compiler. Correctly
compiled structures can be executed by G1. Incorrect structures would create
incorrect field factors, while rejected or missed structures would remove
potentially relevant constraints. Multi-relation reasoning can amplify this
upstream error.

The nonlinear projection was substantially worse than the linear probe. This
means the experiment did not demonstrate that its small learned projection
created a superior reasoning geometry from frozen MiniLM embeddings.

## What was demonstrated

- Frozen MiniLM embeddings expose meaningful signal for controlled relation
  classification.
- A cheap linear multi-head probe can reconstruct the complete registered G1
  structure on `80.8%` of the locked supplied-span cases.
- Ambiguous and quarantined cases were recognized in this controlled suite.
- Strict G1 validation prevented silent invalid insertions.
- The classified inference stage was computationally inexpensive.

## What was not demonstrated

- The required `98%` exact topology reliability.
- Natural-language clause or argument-span extraction.
- General document ingestion.
- A specialized nonlinear reasoning geometry advantage.
- Reliable integrated latent-field reasoning with compiler-generated topology.
- Large-context or 100-million-token reliability.

## Next experimental decision

The shipping dependency remains an end-to-end trained reasoning encoder with
calibrated abstention. G3 prompt addressing may nevertheless be tested as an
independent component by using gold-validated topology objects. Such a G3 run
must not be described as evidence that G2 or G2.1 passed.

## Boundary

An operational pass means a frozen semantic encoder plus a learned classifier
can compile supplied propositions into the registered controlled G1 relation
set. It does not establish natural-language clause extraction, unrestricted
topology compilation, latent optimization or large-context reliability.
