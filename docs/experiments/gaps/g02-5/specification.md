# G2.5 — Typed Atom Coordinate Compiler and Latent-Field Handoff

## Question and boundary

G2.5 tests whether a one-pass, fully fine-tuned local MiniLM can compile
unseen controlled language into the existing G1 ontology by separating four
mathematical spaces: 384D grounded content, 128D relation operators, 64D named
roles, and 64D typed context. Exact sparse `(relation, role, content atom)`
incidence is the authorization representation; a normalized 256D low-rank
binding contribution is continuous field geometry only.

The resulting field is a typed product state, never an anonymous semantic
vector. G1 remains authoritative for identities, scope, time, hard semantics
and provenance. No G2.5 vector is allowed to authorize a topology insertion
without a lossless G1 round trip and G1 registry validation.

This is a controlled language experiment over the existing 18 relation G1
registry. It cannot demonstrate arbitrary document understanding, internet
language ingestion, native latent decoding, G10 quality, or product readiness.

## Staged execution

```text
sentence → one MiniLM pass → all relation prototypes → role-conditioned atoms
→ four reconciliation cycles → bounded complete factor → G1 validation
→ persistent atom match → document field composition
```

The first stage is deliberately decisive. It supplies gold atom spans and
broad kinds while hiding relation, named-role, direction and context labels.
The kernel must pass a fresh 4,000-case locked suite before spending compute on
span extraction, persistent identity and document composition. A kernel miss
therefore refutes this registered mathematical representation rather than
being hidden by later complexity.

## Fixed safety properties

- Local pinned `.models/all-MiniLM-L6-v2`, CPU float32, four PyTorch threads,
  128 wordpieces and no network access.
- All 18 operators are scored before pruning. Role names and allowed kinds are
  derived from G1; no manually maintained schema is permitted.
- Alternatives survive all four reconciliation cycles. A graph factor is
  committed atomically or the whole sentence is clarified/quarantined.
- Runtime reads public sentence/atom input only; evaluator gold is a separate
  input phase. Locked outputs, shard hashes and checkpoint state are atomic.
- Checkpoints retain model/optimizer/RNG/batch position every 100 steps. The
  resume command validates completed work and continues only the first
  incomplete stage.
- The development process checkpoints and stops at 18 GB RSS. Locked results
  must remain below 12 GB, with an eight-hour total ceiling.

## Kernel gates

The locked kernel requires operator macro F1 and named-role exactness of at
least 0.995, exact direction/polarity, modality and scope/time of at least
0.995, complete G1 reconstruction at least 0.99, exact sparse-role and
field/G1 recovery, no reversal false accepts, and no invalid insertion. Failure
is `G2.5-C — REPRESENTATION KERNEL FAILURE`; no full compiler run is then
authorized.

The later compiler gates remain stricter: accepted exact precision at least
0.99, safe sentence coverage at least 0.85, no high-severity direction or
polarity error, and exact field/G1/document composition. Only every kernel and
full gate passing can produce `G2.5-A — CONTROLLED G2 PASS`.

## Commands

```bash
python -m topology_g25 model-check --workspace workspaces/topology-g2-5
python -m topology_g25 dataset-build --workspace workspaces/topology-g2-5
python -m topology_g25 kernel-develop --workspace workspaces/topology-g2-5
python -m topology_g25 kernel-freeze --workspace workspaces/topology-g2-5
python -m topology_g25 kernel-locked-suite-build --workspace workspaces/topology-g2-5
python -m topology_g25 kernel-evaluate --workspace workspaces/topology-g2-5 --offline
python -m topology_g25 verify --workspace workspaces/topology-g2-5 --offline
```

The configuration and frozen manifests are the executable authority. Historic
G2 through G2.4 workspaces and classifications remain unchanged.
