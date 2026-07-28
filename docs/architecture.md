# Canonical Architecture

## Architectural thesis

LTM separates five responsibilities:

1. language interpretation;
2. knowledge compilation;
3. persistent reasoning structure;
4. latent solution search;
5. output expression.

This separation is intended to let language models and topology models improve independently.

## Offline architecture

### 1. Domain topology configuration

A template topology defines what reasoning means in a domain. Configuration includes:

- state and entity types;
- valid relation types;
- relation directionality;
- hard and soft constraints;
- energy components and weights;
- deterministic validators;
- provenance rules;
- update and versioning rules;
- mappings to shared reasoning primitives.

JSON configures trusted implementations; it should not become an unrestricted executable language.

### 2. LLM-assisted reasoning extraction

A teacher or reasoning LLM converts raw data into a strict Reasoning Intermediate Representation (RIR). The system requests structured, source-grounded analysis rather than private or free-form chain-of-thought.

The teacher proposes:

- states and claims;
- premises and consequences;
- dependencies and causes;
- goals and constraints;
- conflicts;
- valid and invalid transitions;
- evidence spans;
- uncertainty.

Teacher output is untrusted input to the compiler.

### 3. Validation and normalization

A deterministic program:

- validates the RIR schema;
- checks source grounding;
- rejects unsupported relationships;
- normalizes identifiers and units;
- deduplicates equivalent states;
- checks type compatibility;
- records contradictions;
- preserves provenance;
- runs domain validators;
- versions topology changes.

Multiple extraction or verification passes may be used for difficult material.

### 4. Topology encoding

Validated states and relationships are embedded into an instantiated topology.

A candidate directed representation is:

\[
f_\theta(s)=(O_s,T_s)
\]

where:

- \(O_s\) represents the state as a premise, origin or causal source;
- \(T_s\) represents it as a consequence, target or resolved state.

A valid directed transition \(s_i\rightarrow s_j\) should score more strongly than its reverse:

\[
O_{s_i}\cdot T_{s_j}
>
O_{s_j}\cdot T_{s_i}
\]

This representation is a hypothesis to test, not a required permanent design.

### 5. Field compilation

The explicit topology induces an energy function or vector field. The first implementation should compute this field from explicit relations so behavior can be inspected.

Once validated, the explicit field may be distilled into neural modules:

\[
F_\phi(x,q)\approx-\nabla_xE_{\mathrm{explicit}}(x,q)
\]

Distillation reduces runtime cost but may lose detail. Exact source payloads should remain attached to topology nodes for fidelity and verification.

## Online architecture

### 1. Prompt encoding

The language interface maps a prompt into:

- an initial latent state \(x_0\);
- a goal representation \(g_q\);
- hard and soft request constraints;
- domain routing signals;
- required output form.

### 2. Topology activation

A router selects relevant field modules:

\[
A(q)=\{m_1,\ldots,m_k\}
\]

The active field is composed as:

\[
F(x,q)=\sum_{m\in A(q)}g_m(q)F_m(x,q)
\]

where \(g_m(q)\) controls module relevance. Sparse activation is essential to bounded inference.

### 3. Query-conditioned energy

The optimizer minimizes prompt-relevant inconsistency:

\[
E(x\mid q)=
\lambda_cE_{\mathrm{constraint}}
+\lambda_dE_{\mathrm{dependency}}
+\lambda_xE_{\mathrm{causal}}
+\lambda_rE_{\mathrm{conflict}}
+\lambda_gE_{\mathrm{goal}}
+\lambda_uE_{\mathrm{uncertainty}}
\]

Each term is conditioned by the active topology, prompt, provenance and applicability.

### 4. Latent optimization

A basic update is:

\[
x_{t+1}=x_t-\alpha\nabla_xE(x_t\mid q)
\]

Optional momentum, adaptive step sizes, Langevin noise, beam-like particles or discrete repair operations may help avoid poor local minima.

Stopping requires more than a small gradient. Conditions may include:

- low energy;
- small state change;
- satisfied hard constraints;
- stable evidence set;
- verifier acceptance;
- explicit timeout or compute budget.

### 5. Verification

Convergence is not correctness. The verifier checks:

- hard constraints;
- source support;
- dependency closure;
- contradictions;
- domain-specific validity;
- output completeness.

If verification fails, the system may repair the state, activate more topology modules, increase the reasoning budget or return an unresolved result.

### 6. Decoding

A small language model or symbolic decoder receives the final state, evidence and verifier report. It produces the requested language or structured artifact.

The decoder may improve clarity but may not claim evidence absent from the verified state.

## Knowledge representation modes

### Weights-only research mode

All corpus influence is distilled into parameters. This offers bounded evaluation but risks blurred facts, difficult updates and poor provenance.

### Field plus exact payload

Relationships and global influence are compiled into field weights, while exact facts and source text remain attached to topology nodes. This is the recommended product architecture.

### Explicit topology mode

The field is calculated directly from stored states and relations. This is slower but transparent and is the preferred starting point for scientific validation.

## Topology compiler contract

The topology compiler translates arbitrary domain data into validated reasoning objects, places those objects into a configured topology and produces training material for the latent field. It is not merely a semantic embedding endpoint.

### Reasoning Intermediate Representation

The Reasoning Intermediate Representation is the stable contract between extraction, validation, topology encoding and field compilation.

A minimal record should contain:

```json
{
  "document_id": "source-123",
  "domain": "software_dependencies",
  "states": [],
  "premises": [],
  "goals": [],
  "constraints": [],
  "dependencies": [],
  "causal_edges": [],
  "conflicts": [],
  "valid_transitions": [],
  "invalid_transitions": [],
  "evidence": [],
  "uncertainties": [],
  "source_spans": []
}
```

Each relation must include provenance, confidence and the topology configuration version used to interpret it.

### Template topology

A conceptual domain configuration is:

```json
{
  "schema_version": "0.1",
  "domain": "software_dependencies",
  "state_types": [
    "package",
    "version",
    "requirement",
    "configuration"
  ],
  "relations": {
    "requires": {
      "directed": true,
      "energy": "dependency"
    },
    "conflicts_with": {
      "directed": false,
      "energy": "conflict"
    },
    "supports": {
      "directed": true,
      "energy": "evidence"
    }
  },
  "constraints": {
    "version_compatibility": {
      "weight": 1.0,
      "hard": true,
      "validator": "semver_validator"
    }
  },
  "optimization": {
    "goal_weight": 1.0,
    "conflict_weight": 2.0,
    "uncertainty_weight": 0.5
  }
}
```

Validators referenced by JSON are trusted, tested and versioned code.

### Extraction and validation

An LLM may identify candidate states, typed relations, source evidence, valid and invalid transitions, contradictions and missing premises. It must emit schema-constrained output. Free-form explanations may be retained for debugging but are not topology ground truth.

Validation layers include:

- JSON and schema validation;
- source-span entailment checks;
- domain type checking;
- unit and identifier normalization;
- deterministic constraint evaluation;
- duplicate detection;
- contradiction classification;
- confidence calibration;
- optional multi-model consensus;
- human review for high-impact changes.

The compiler preserves rejected candidates and rejection reasons for audit and future improvement.

### Training examples

Compilation produces:

- positive directed edges;
- reverse-direction negatives;
- incompatible-state negatives;
- dependency-completion examples;
- constraint-violation examples;
- evidence-support examples;
- abstraction mappings;
- query-goal-state triples.

A candidate directional loss is:

\[
\mathcal{L}_{\mathrm{dir}}=
-\log
\frac{\exp(O_s\cdot T_{s^+}/\tau)}
{\exp(O_s\cdot T_{s^+}/\tau)+
\sum_k\exp(O_s\cdot T_{s^-_k}/\tau)}
\]

Directional similarity alone is insufficient to establish reasoning. Training must also test constraints, provenance and contradictions.

### Incremental updates

An update should:

1. extract and validate only affected material;
2. locate related topology regions;
3. add a version rather than destructively overwrite;
4. identify newly created conflicts;
5. patch or retrain local field modules;
6. run retained-knowledge regressions;
7. promote the update after validation.

The system measures update latency, retained-answer accuracy, new-fact accuracy, conflict detection, topology drift and recompilation cost.

### Domain composition

Every domain maps specialized concepts to shared primitives. Cross-domain edges must be explicit.

```text
Software package dependency
        ↓ maps to
Shared dependency primitive
        ↑ maps from
Operational process prerequisite
```

This permits joint reasoning without forcing every domain into identical coordinates.

## Architectural invariants

- The prompt changes the field, not only the initial coordinate.
- Contradictions remain representable.
- New knowledge is versioned and localized where possible.
- The verifier is independent of optimizer convergence.
- Claims about fixed cost refer to active compute, not total system storage.
- Language quality and reasoning quality are evaluated separately.

## Primary failure modes

- teacher hallucination becomes durable topology structure;
- verbose reasoning traces are mistaken for ground truth;
- topology configuration encodes designer bias;
- equivalent entities fragment across modules;
- contradictions are averaged away;
- incremental updates destabilize unrelated regions;
- field distillation loses rare facts;
- domain mappings create false cross-domain analogies.
