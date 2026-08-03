# G1 — Executable Conversational Topology

G1 is the first shipping-gap experiment. It tests whether the registered LTM
conversational topology can represent, validate, execute, persist, verify,
migrate and replay its typed structures without changing their meaning.

It uses 160 deterministic fixtures split equally between development and locked
evaluation. It contains no language model, embedding model, latent optimizer,
decoder or network dependency.

Run the experiment with:

```bash
python -m topology_g1 run-all --workspace workspaces/topology-g1
```

`G1-A` requires every valid fixture to succeed, every invalid fixture to be
rejected, deterministic canonical/replay hashes, independent verifier
rejection of fabricated derivations, finite satisfied/violated field contracts,
successful v1-to-v2 migration, less than ten seconds runtime and less than 200
MB peak RSS.

The full implementation contract and result boundary are recorded in
[experiment program](../../../roadmap/experiment-program.md). Passing G1 authorizes G2,
natural-language topology compilation; it does not establish compiler quality,
prompt addressing, latent reasoning or product readiness.
