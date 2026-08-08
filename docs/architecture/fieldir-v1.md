# FieldIR v1 Compatibility Contract

> Normative current architecture: [LTM-ARCH-1.1](architecture-lock-v1.md).

FieldIR v1 is the source-facing predecessor to the numeric `ltm-field/2`
program. The canonical product architecture is documented in
[semantic topology](semantic-topology.md). This file is retained so existing
experiment packages and reports remain readable.

FieldIR v1 is a typed, versioned factor program—not a sequence of text tokens
and not an anonymous embedding store. LTM v1 migrates its active records to
numeric FieldIR v2 while retaining v1 as an input/output compatibility layer.

```text
golden atoms + typed context + explicit role bindings
    + field parameters + vector references
    -> validated typed factor program
    -> exact G1 execution and optional G6/G7 lowering
```

## Authority boundary

Atoms and factors carry the executable meaning. Vectors provide semantic
routing, retrieval and ranking evidence only. A vector cannot create an atom,
choose a relation, bind a role, or authorize an insertion without a complete
G1-valid typed factor.

## Identity and artifacts

`GoldenAtom.atom_id` is immutable and independent of vector values. FieldIR
therefore has two hashes:

- the semantic digest covers atoms, factors, context and provenance but not
  vector artifacts;
- the artifact digest additionally covers vector spaces and sidecar references.

This permits re-embedding without changing the semantic program, while making
every execution artifact reproducible.

Dense vectors live in immutable content-addressed `LTMFV1` sidecars. A
`VectorRef` names its vector space, sidecar hash, row index and row hash. The
runtime verifies all four before it uses a vector.

## Execution bridge

FieldIR validates each factor against the pinned G1 registry and projects it
losslessly into G1 nodes and relations. G1 is the exact execution path for all
registered operators. G6/G7 lowering is capability-declared; a factor without
a complete lowerer produces a diagnostic and remains executable through G1.
