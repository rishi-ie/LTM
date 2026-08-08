# Experiment and product configurations

`topology-g*.json` files are immutable historical experiment inputs. Their
names match the stable `topology_g*` import and command families, including
legacy spellings such as `topology_g21`, `topology_g210`, and `topology_g101`.

`ltm-v1.json` is the product-foundation configuration. It defines the numeric
FieldIR v2 schema, registered vector spaces, packing widths, and authority
boundary. It is not a replacement for any frozen experiment configuration.

`ltm-architecture-v1.json` is the machine-readable LTM-ARCH-1.1 decision
boundary. Its tracked hash manifest is stored beside the normative architecture
document. It does not replace any experiment configuration.

Generated suites, checkpoints, sidecars, and manifests remain under ignored
workspaces.

`ltm-inference-i*.json` files configure the isolated latent-inference studies.
They do not change the product runtime or historical G-series classifications.
I3.1 is explicitly `development-only`; its configuration does not authorize a
locked result.

`ltm-limit-l4.json` freezes the failed branching-proof development boundary.
It does not authorize locked or 45-hop stress claims because L4 stopped before
freeze.
