# Repository Layout Convention

The normative architecture is
[LTM-ARCH-1.1](../architecture/architecture-lock-v1.md). Experiment ownership,
classification, and paths are indexed in the
[experiment registry](../experiments/registry.json); physical directories are
not reorganized to make the naming visually uniform.

Every experiment has one stable identifier and five matching locations:

```text
src/topology_g8/                       Python package
tests/topology_g8/                     focused tests
configs/topology-g8.json               frozen configuration
docs/experiments/gaps/g08/             specification and permanent report
workspaces/topology-g8/                 ignored generated artifacts
```

The product foundation has a separate stable location:

```text
src/ltm/                                 canonical product contracts/codecs
tests/ltm/                               product-foundation tests
configs/ltm-v1.json                      product topology/field policy
workspaces/ltm-v1-foundation/            ignored audit and codec artifacts
```

MICRO-LTM studies use the existing `micro_ltm*` naming family. Historical
package names such as `micro_ltm2` and `topology_g21` remain unchanged for
compatibility.

Latent-inference studies use the explicit I-series family:

```text
src/ltm_inference_i31/
tests/ltm_inference_i31/
configs/ltm-inference-i3-1.json
docs/experiments/inference/i03-1/
workspaces/ltm-inference-i3-1-r1/
```

Development-only studies must say so in their configuration, report, index,
and ledger entry. They may not be described as locked passes.

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

Historical experiment packages are evidence, not product runtime formats. Do
not move, rename, or rewrite their locked reports, source packages, tests,
configurations, or workspaces during product-foundation work. CNTG-1-R2 and
MICRO-LTM-2 are documented legacy report-only studies and do not require
retrospective specifications.

## Local environments and generated catalogs

`.venv` is the only supported repository environment and must use Python 3.11.
`.venv-g101` is an ignored historical G10.1 environment. Models, environments,
checkpoints, evaluator data, and every experiment workspace remain ignored.

Repository audits write local catalogs to
`workspaces/_repository-catalog/`. They catalog existing workspaces in place;
they never move, delete, or hash all bulk artifacts.
