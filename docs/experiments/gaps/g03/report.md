# G3 — Prompt-to-Topology Addressing Report

## Classification

**G3-A — PASS**

G3 tested gold-validated topology plus structured prompt signatures. It does not change the failed G2/G2.1 compiler classifications.

## Executive conclusion

When the topology is correct and the prompt has already been converted into a
correct structured signature, LTM can locate the relevant starting topology
region reliably without scanning the complete store. Across the locked
10,000-address topology, the resolver found every registered required entity,
predicate, scope, time, and conversation address, retained ambiguity safely,
and abstained on unsupported prompts. The median request considered two
candidates and inspected approximately `0.02%` of the topology postings.

This supports the topology-minimap mechanism: known structure and typed indexes
can tell request execution where to begin. It does not prove that raw language
can be converted into the required signature. The supplementary text parser
found simple entities but reached only `0.100` predicate recall, and frozen
MiniLM supplied no measurable advantage on this opaque synthetic topology.

The bounded conclusion is:

```text
Correct structured prompt → correct starting topology region: demonstrated
Raw conversational prompt → complete structured signature: not demonstrated
Starting addresses → complete answer-changing active frontier: not yet tested
```

G4 is authorized using G3-generated addresses over gold-validated topology.
End-to-end product use remains blocked on repairing the G2 compiler boundary.

## Full resolver

| Metric | Result |
| --- | ---: |
| ambiguity recall | 1 |
| complete scans | 0 |
| conversation reference accuracy | 1 |
| exact exception recall | 1 |
| hard constraint recall | 1 |
| incorrect confident resolutions | 0 |
| median candidate set | 2 |
| median fraction inspected | 0.0002 |
| p95 candidate set | 3 |
| predicate recall | 1 |
| scope accuracy | 1 |
| starting entity recall | 1 |
| temporal accuracy | 1 |
| unsupported abstention | 1 |

Locked runtime: `3.176 s`; peak RSS: `734.83 MB`.

## Controls

| Method | Entity recall | Predicate recall | Median candidates |
| --- | ---: | ---: | ---: |
| full | 1.000 | 1.000 | 2 |
| lexical | 1.000 | 1.000 | 2 |
| semantic | 0.000 | 0.100 | 0 |
| text | 1.000 | 0.100 | 1 |

## G3-Text diagnostic

**`G3-TEXT-NOT-DEMONSTRATED`**

The text-only parser recovered the simple entity phrase in this constrained
prompt family, but it did not recover the predicate, scope, time, or episode
fields required for complete addressing. It therefore achieved entity recall
`1.000` but predicate recall `0.100`. This is intentionally not used for the
G3-Core classification and confirms that a repaired G2-style compiler remains
necessary for end-to-end prompts.

The semantic-only control also did not solve the opaque-address corpus. Frozen
MiniLM was loaded offline and used only to propose candidates; it could not
authorize an address and provided no advantage over exact typed indexes here.
G2 and G2.1 remain failed upstream compiler experiments.
