# G2 — Natural-Language Topology Compiler

G2 tests whether the pinned local Qwen 2.5 0.5B model can compile unseen
controlled natural language into the G1 executable topology while deterministic
validation prevents invalid or ambiguous output from silently entering storage.

The experiment contains 300 development and 300 locked cases. The model proposes
JSON only; one constrained model repair is allowed. The validation layer may
validate, normalize quotes, resolve exact aliases and map local IDs to G1 IDs,
but it may not add missing semantic content.

Run:

```bash
python -m topology_g2 run-all --workspace workspaces/topology-g2 --offline
```

The detailed registered protocol is in the [experiment program](../../../roadmap/experiment-program.md).
The permanent result is stored beside this specification as `report.md` and in the cumulative
[gap results ledger](../../../roadmap/results-ledger.md).
