# LTM v1 Runtime Pipeline

> Normative contract: [LTM-ARCH-1.1](architecture-lock-v1.md).

## Compilation

```text
raw source
→ immutable source event
→ supplied or separately extracted semantic spans
→ conversational turn: G2.14 bounded candidate resolution and margin gate
  OR reasoning input: safety-gated G2.5 candidate topology
→ source-span/scope/time/provenance validation
→ G1 relation validation
→ universal Mumbrane units, ports and coordinates
→ selected topology-profile compatibility
→ FieldIR v2 packed execution view
→ accepted, clarification-required, or quarantined
```

G2.14 conversational acceptance is authorized only for supplied-span controlled
turns. The reasoning path uses confirmation for high-impact or
direction-sensitive decisions because G2.5 recorded valid-but-reversed false
accepts. Downstream schema validation cannot detect every semantic reversal.

## Request execution

1. Compile the selected signed topology profile into frozen numeric opcodes.
2. Encode the prompt into goal, entities, predicates, scope, time, polarity,
   modality, conversation references and resource limits.
3. Resolve starting addresses from Mumbrane region and identity indexes.
4. Derive the read-only FieldIR v2 execution view for the selected factors.
5. Construct a bounded G4 frontier from exact ports and registered bridges.
6. Use G5 to open answer-changing factors and certify summarized regions.
7. Select the registered reasoning lane:
   - run G6 exact propagation/search for hard relations and branching proofs; or
   - for a validated bounded acyclic field, clamp the supplied-formal prompt
     and run L7 synchronous fixed-law satisfaction from a neutral state.
8. Run profile-defined G7 soft reconciliation over the immutable verified
   state, then use G8 order-independent reduction. In the L7 lane, retain both
   polarity channels and residual contradiction tension.
9. Verify profile, proof, provenance, hard state, residuals and coverage with
   G9.
10. Widen, request clarification, or abstain when verification fails.
11. Pass only the authorized bundle and archive labels to G10.1, then validate
   the resulting text.

The active frontier and FieldIR execution view are ephemeral. Objects keep
stable references back to the Mumbrane substrate; a request does not create a
second authoritative topology.

## Fixed-law equilibrium lane

```text
validated reality factors
+ immutable prompt clamps
→ zero non-prompt activations
→ synchronous factor and atom target updates
→ source-normalized positive/negative activation
→ explicit contradiction tension
→ convergence and objective certification
→ candidate discovery from activated outcomes
→ independent fixed-point and path replay
```

Exact identity, reality, scope and time may mask invalid factors. They may not
procedurally fire an outcome. This lane currently inherits L7's evidence
boundary: supplied formal inputs, acyclic graphs, 512 bodies and paths through
20 body applications.

## Memory lifecycle

The immutable base substrate and clearable session overlay have independent
versions, hashes, provenance and deletion semantics. Both use Mumbrane units.
User turns update the overlay transactionally. Assistant responses are
discourse events with zero independent evidential authority.

## Profile switching

- **Tier 1:** update the compiled profile and execution hash; rewrite no field
  rows.
- **Tier 2:** migrate only indexed affected units and retain rollback state.
- **Tier 3:** reopen the source archive and recompile because required semantics
  are absent. If source or provenance is unavailable, abstain.

## Product modes

- **Controlled mode:** accepted structured or confirmed compiler output.
- **Conversational mode:** G2.14-accepted supplied-span session events.
- **Preview mode:** show proposed topology and evidence before committing it.
- **Clarification mode:** retain multiple hypotheses without guessing.
- **Abstention mode:** return a safe unknown when coverage, provenance or
  semantic confidence is insufficient.
- **Exhaustive mode:** explicitly allow a full scan for diagnostics; it is not
  ordinary request behavior.
