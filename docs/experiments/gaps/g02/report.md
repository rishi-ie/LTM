# G2 — Natural-Language Topology Compiler Report

## Result

**Classification: `G2-B — MODEL INSUFFICIENT`**

G2 tested the pinned local `Qwen2.5-0.5B-Instruct-mlx-4bit` model as the only
semantic compiler for the executable G1 topology. The model received unseen,
controlled fictional language, a frozen JSON contract, bounded conversational
context, and one allowed model-generated repair. Deterministic code could
validate, normalize and reject output, but could not recover omitted meaning.

The model loaded with MLX/Metal, produced deterministic output and completed
the frozen 300-case locked suite offline. It did **not** extract the typed
semantic structure accurately enough to become the topology input boundary.

## Frozen evaluation

- Development cases: 300
- Locked cases: 300, generated only after development selection froze
- Prompt variants considered on development: 3; selected variant: 0
- Decoding: greedy, maximum 320 tokens; one constrained model repair
- Network during locked evaluation: disabled

## Locked measurements

| Measurement | Result | Required | Outcome |
| --- | ---: | ---: | --- |
| Claim tuple F1 | `0.000` | `>=0.95` | FAIL |
| Relation direction accuracy | `0.000` | `>=0.98` | FAIL |
| Named-role exact match | `0.000` | `>=0.98` | FAIL |
| Entity-link accuracy | `0.000` | `>=0.98` | FAIL |
| Coreference accuracy | `0.000` | `>=0.98` | FAIL |
| Correction-target accuracy | `0.000` | `>=0.99` | FAIL |
| Scope accuracy | `0.000` | `>=0.99` | FAIL |
| Temporal accuracy | `0.000` | `>=0.99` | FAIL |
| Source-span F1 | `1.000` | `>=0.99` | PASS |
| Provenance integrity | `0.153` | `1.000` | FAIL |
| Correct disposition | `0.207` | `>=0.98` | FAIL |
| Exact topology agreement | `0.000` | `>=0.98` | FAIL |
| Direct valid IR | `0.153` | `>=0.90` | FAIL |
| Final valid IR after one repair | `0.153` | `>=0.98` | FAIL |
| Clarification recall | `0.000` | `>=0.95` | FAIL |
| Quarantine recall | `0.767` | `>=0.95` | FAIL |
| Silent invalid topology insertions | `0` | `0` | PASS |
| Repair rate | `0.847` | informational | — |
| Locked runtime | `437.62 s` | `<600 s` | PASS |
| Peak RSS | `1153.63 MB` | `<8 GB` | PASS |

## Interpretation

The failure is semantic, not mechanical. The model commonly emitted a plausible
fact-shaped JSON object but omitted the required relation, misrepresented its
typed structure, or chose a wrong disposition. Strict validation prevented
those outputs from quietly becoming topology entries. The single repair did
not materially improve the valid-IR rate.

G1 remains valid: it executes correct topology objects. This experiment
rejects only this frozen 0.5B model/prompt compiler boundary. It does not prove
that topology compilation is impossible. **G3 is not authorized.**

The next experiment must evaluate a stronger structured-extraction model or
constrained decoding method while retaining strict validation and the ban on
deterministic semantic recovery.

## Historical identification

- `config.json`: `b045e57ea90b8f1b35f89f954b176a5c1faa02bd0af2c89bcec191239d66cef4`
- `tokenizer.json`: `a8506e7111b80c6d8635951a02eab0f4e1a8e4e5772da83846579e97b16f61bf`
- `model.safetensors`: `ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153`
- Locked-suite digest: `42b0a2f6e80030387b6d9bfa4bdc694ab6629da1c299df8a50cfcdd9caefa3d7`

Raw predictions, counterexamples and the frozen manifest remain locally in
the ignored `workspaces/topology-g2/` directory.
