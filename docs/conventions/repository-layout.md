# Repository Layout Convention

Every experiment has one stable identifier and five matching locations:

```text
src/topology_g8/                       Python package
tests/topology_g8/                     focused tests
configs/topology-g8.json               frozen configuration
docs/experiments/gaps/g08/             specification and permanent report
workspaces/topology-g8/                 ignored generated artifacts
```

MICRO-LTM studies use the existing `micro_ltm*` naming family. Historical
package names such as `micro_ltm2` and `topology_g21` remain unchanged for
compatibility.

## Required experiment documents

Before execution, the experiment directory contains `specification.md`. After
the locked run it also contains `report.md`. Specifications define hypotheses,
boundaries, interfaces, gates, seeds, controls, and commands. Reports contain
only measured results and bounded conclusions.

The cross-experiment classification is recorded once in
[`docs/roadmap/results-ledger.md`](../roadmap/results-ledger.md). Architecture
claims belong in the architecture documents, not in an individual report.

## Generated data

Raw suites, evaluator gold, checkpoints, model weights, field blocks, failed
runs, and manifests stay under ignored workspaces. They must not be committed.
Completed locked workspaces are immutable; a new attempt uses a new local
workspace name.

## Compatibility

Source-package names, module commands, and existing frozen configurations are
public research interfaces. Folder organization must not silently rename them.
Future experiments follow the G8 pattern above.
