# G2.3 — Hierarchical Sentence-to-Topology Compiler

G2.3 is the compatibility-preserving replacement for the failed G2.2 language boundary. It fully
fine-tunes the local `all-MiniLM-L6-v2`, retains a bounded lattice of typed spans, constructs only
G1-authorized relation candidates, reconciles them with a four-cycle local/global recurrent scorer,
and commits a complete sentence fragment atomically only after G1 validation.

The experiment uses 12,000/2,000/4,000 sentence cases and 6,000/1,000/2,000 link cases with split-
disjoint controlled language. It tests sentence extraction, topology construction, and bounded
cross-sentence linking. It does not establish arbitrary language ingestion, latent-field correctness,
natural-language decoding, or 100M-context reliability. G2, G2.1 and G2.2 remain historical results.

The authoritative output is the existing G1 `TopologyNode`, `RelationInstance` and
`TopologyOperation` contract. No G3–G15 source or result is modified.

Commands:

```bash
python -m topology_g23 model-check --workspace workspaces/topology-g2-3
python -m topology_g23 dataset-build --workspace workspaces/topology-g2-3
python -m topology_g23 diagnose --workspace workspaces/topology-g2-3
python -m topology_g23 develop --workspace workspaces/topology-g2-3
python -m topology_g23 freeze --workspace workspaces/topology-g2-3
python -m topology_g23 locked-suite-build --workspace workspaces/topology-g2-3
python -m topology_g23 evaluate --workspace workspaces/topology-g2-3 --offline
python -m topology_g23 report --workspace workspaces/topology-g2-3
python -m topology_g23 verify --workspace workspaces/topology-g2-3 --offline
python -m topology_g23 run-all --workspace workspaces/topology-g2-3 --offline
```

The locked operational gates are accepted exact precision ≥.99, safe sentence and link coverage
≥.85, all-case sentence and link exactness ≥.90, span F1 ≥.98, relation-role exactness ≥.99,
direction ≥.995, scope/time ≥.99, ambiguity/quarantine recall ≥.98, zero invalid insertions,
zero cross-session links, zero complete scans, deterministic replay, locked RSS <12 GB, runtime
<600 seconds and no network calls. A separate recurrent advantage requires five absolute sentence
points and three link points over a separately trained non-recurrent model.
