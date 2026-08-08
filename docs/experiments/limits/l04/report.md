# L4 — Unseen Branching Mathematical Proof Discovery

Status: `L4-C — LOCAL PROPOSAL FAILURE (DEVELOPMENT STOP)`.

## Development result

L4 stopped at its mandatory pre-lock boundary. No frozen or locked suite was
generated, so this is a measured development failure rather than a locked
classification.

| Metric | Result |
| --- | ---: |
| Stratified pre-lock cases | `12` |
| Accepted proof precision | `1.0000` |
| Answerable success | `0.3333` |
| Correct proposal recall@16 | `0.2738` |
| Deepest independently replayed proof | `2` |
| Depth 2–4 success | `1.0000` |
| Depth 5–8 success | `0.0000` |
| Depth 9–12 success | `0.0000` |
| Branching-16 success | `0.0000` |
| Branching-32 success | `0.0000` |

## Causal controls

```json
{
  "full_minus_no_goal": 0.0,
  "full_minus_no_scorer": 0.0,
  "full_minus_no_value": -0.125,
  "full_minus_random": 0.0
}
```

The compact kernel safely abstained when it could not find a proof, but it did
not learn reliable goal-conditioned proposal ranking. Removing the scorer or
goal did not materially reduce deep success, and removing the value head
improved this panel. The first failure is therefore local proposal learning,
not exact verification, field persistence, or the decoder.

The valid L3 conclusion remains unchanged: indexed linear 45-hop proofs replay
exactly. L4 shows that this does not yet extend to learned branching proof
discovery. No 17–45-hop stress claim is issued because the primary development
boundary did not pass.
