# LTM v1 Mumbrane Semantic Topology

> Normative contract: [LTM-ARCH-1.2](architecture-lock-v1.md).

This is the normative representation architecture for the first LTM build.
LTM-R2 authorizes **Mumbrane IR v1** as the canonical future compiler target.
The existing `ltm-field/2` implementation remains the verified execution and
persistence bridge until the isolated Mumbrane codec is promoted into
`src/ltm/`.

## One universal semantic form

The active latent dynamic field is a typed numeric program, not text, one
averaged embedding, or a collection of profile-specific record formats.
It is transformer-independent: transformer hidden state, attention state,
logits, and pretrained weights are not semantic authority in this substrate.
Every compiled semantic object is represented by the same unit structure:

```text
MumbraneUnit
+ zero or more named MumbranePorts
+ zero or more exact MumbraneCoordinates
+ an optional MumbraneVectorBundle
```

Entities, claims, observations, events, relations, goals, sources, contexts,
identities, regions, constraints and certificate references all use that form.
Their numeric class and semantic codes distinguish meaning; sparse ports bind
one unit to another through named roles.

## The nine Mumbranes

Every unit has nine conceptual feature bands. A feature mask records which
bands carry meaningful data for that unit.

| Mumbrane | Contents | Authority |
| --- | --- | --- |
| Content | semantic kind, identity and scalar payload | exact |
| Operator | relation identity and hard/soft class | exact |
| Role | sparse named ports, ordinals and targets | exact |
| Context | polarity, modality, scope, time and applicability | exact |
| Provenance | source identity, spans, hashes and derivation links | exact |
| Geometry | content, operator, role, context and binding vectors | soft only |
| Identity | stable identity, aliases and supersession | exact |
| Region | address, membership and dependency indexes | routing |
| Integrity | revisions, hashes and validation state | authorization |

The representation is therefore universal without becoming anonymous. A unit
has one physical schema while its feature bands preserve typed semantics.

## Authority boundary

The exact substrate is:

```text
semantic codes
+ sparse named ports
+ exact coordinates and applicability
+ provenance and identity
+ integrity hashes
```

Vectors may route, retrieve, rank and modulate registered soft energy. They may
not create a unit, choose an operator, bind a role, change polarity or scope,
alter a hard conclusion, or authorize insertion. G1 remains the executable
ontology and validation contract for exact operators.

## Topology profiles

The semantic substrate does not hard-code one purpose. A signed, versioned
topology profile selects:

```text
active operators
+ exact laws
+ soft laws and objective weights
+ context and addressing policy
+ coverage and verification policy
+ realization and migration policy
```

Runtime consumes only compiled numeric profiles using frozen primitive opcodes;
profiles cannot execute arbitrary Python. The initial locked profiles are:

- reasoning;
- planning;
- evidence/science;
- conversation memory.

A profile changes how captured semantics are used, not what the source said.
Inactive operators have no influence.

## Configuration changes

Profile switching has three explicit tiers:

1. **Dynamics-only:** change weights, thresholds, priorities or region budgets.
   Reuse the substrate unchanged and update only the execution hash.
2. **Structural policy:** disable or narrow an operator, revise cardinality, or
   change hard/soft treatment. Revalidate only indexed affected units, preserve
   unaffected bytes and retain rollback state.
3. **Missing semantic:** the new purpose requires information the substrate did
   not capture. Return `SOURCE_RECOMPILATION_REQUIRED`; never invent a default.

This is the limit of “change the topology by changing the config.” A profile
can select and weight recorded meaning, but it cannot manufacture absent
meaning.

## Hash and archive boundaries

The representation separates four identities:

- **substrate semantic hash:** exact units, ports, coordinates, applicability,
  provenance and identity;
- **artifact hash:** substrate plus vector definitions, references and
  sidecars;
- **profile execution hash:** substrate plus compiled topology profile;
- **archive hash:** raw source, aliases and decoder-facing labels.

Changing a vector does not change exact semantic identity. Changing a profile
does not falsely change the underlying substrate. Source text stays outside
active numeric execution and is opened only at authorized ingestion, audit and
surface-realization boundaries.

## Execution bridge

The current verified runtime path is:

```text
Mumbrane IR v1 exact substrate
→ G1 semantic projection
→ FieldIR v2 packed execution view
→ G3 addressing and G4 frontier
→ G5 coverage
→ G6 exact reasoning OR L7 fixed-law acyclic equilibrium
→ G7 soft optimization and G8 reduction
→ G9 verification
→ G10.1 authorized realization
```

FieldIR v2 is a derived execution view in this architecture, not a second
factual topology. Until product promotion is complete, `src/ltm/` remains the
canonical implemented runtime and `src/ltm_r2/` remains the isolated validated
Mumbrane candidate.

In the L7 lane, exact ports define factor endpoints and exact context masks;
they do not procedurally activate an outcome. Prompt assumptions are clamped,
all other activations start at zero, and a fixed synchronous profile law
determines positive, negative and tension states. An independent solver and
exact path replay authorize the resulting candidate.

## Compiler target

The compiler must emit complete Mumbrane units with exact ports, coordinates,
provenance and identity plus optional geometry. It may propose alternatives,
but an atomic commit occurs only after G1 validation, profile compatibility,
hash verification and lossless projection. Ambiguous or incomplete input is
clarified or quarantined.

The compiler boundary is modular. G2.14 supplies the accepted conversational
route when semantic spans are provided; G2.5 remains the provisional reasoning
route. Both target the same Mumbrane/G1 contract. LTM-R2 validates that target
representation; it does not improve either compiler's measured language
accuracy or supply raw span extraction.

## Evidence boundary

LTM-R2 measured 1,024 evaluator-owned semantic bodies across four profiles,
with 4,096 exact-oracle agreements, 320 rejected corruptions and 128 direct
FieldIR/G3–G10.1 adapter executions. G11–G14 were not freshly rerun in LTM-R2;
their compatibility rests on exact G1 projection plus their existing locked
evidence.

This architecture therefore authorizes modular compiler work against Mumbrane
IR v1. It does not establish unrestricted-language compilation, universal
ontology coverage, decoder naturalness or production serving.

L7 additionally supplies controlled evidence that the same exact semantic
substrate can drive a zero-parameter fixed equilibrium through 20 body
applications in an acyclic 512-body field. Cyclic and scaled execution remain
unproven.
