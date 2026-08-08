# G10 — Compact Verified Conversational Decoder

## Question and boundary

> Can the pinned frozen Qwen 0.5B render a bounded G9-authorized result bundle
> as a relevant conversational response without adding an unsupported claim?

G10 is deliberately a technical faithfulness test, not a naturalness audit or
a native latent-prefix experiment. Its complete path is:

```text
verified symbolic bundle + textual structured-state channel
→ frozen greedy Qwen 0.5B
→ controlled-vocabulary claim extraction
→ authorization check
→ one constrained repair
→ deterministic verified fallback
```

The decoder receives only the prompt, verifier status, authorized claim table,
short proof, conflict/uncertainty requirements, provenance labels, bounded
state channel and style instruction. It receives neither topology nor hidden
facts, evaluator answers, rejected claims or permission to reason further.

## Frozen execution

- Model: `.models/Qwen2.5-0.5B-Instruct-mlx-4bit`.
- Runtime: MLX `0.32.0` / MLX-LM `0.31.3`, local-only Metal execution.
- Decoding: greedy (`temperature=0`), maximum `64` output tokens.
- Training and soft prefixes: prohibited.
- Development / locked bundles: `24 / 64`.
- Locked seed: `20260811`; development seed: `1738`.
- Human naturalness: deliberately unmeasured.

The required SHA-256 values are pinned in the runtime package for
`config.json`, `tokenizer.json` and `model.safetensors`. A separate preflight
process must hash, load and repeat a short generation before any locked run;
if Metal is unavailable, the only allowed result is `BLOCKED-RUNTIME`.

## Bundle categories and safety rules

There are eight equally represented locked categories: direct answer, verified
explanation, correction, unresolved conflict, partial answer, unknown request,
style preference and fictional-scope disclosure. Every bundle contains one or
two opaque factual claims (or none for unknown), verified provenance and one of
`verified`, `verified_with_tension`, `partial` or `unknown`.

The deterministic validator normalizes the controlled vocabulary and rejects a
new fact, changed entity, opposite polarity, wrong scope, missing decisive
claim, undisclosed conflict, invalid certainty or assistant self-evidence. It
allows ordinary conversational glue. Exactly one model repair receives the
bundle, rejected text and error codes. A second rejection never reaches users:
the system emits a templated verified response instead.

Controls compare the full state channel with no-state and state-only panels,
first-generation-only acceptance and fallback. A 64-response deterministic
adversarial suite covers unsupported facts, polarity, entity, scope, conflict,
certainty, fictional/global and assistant-evidence attacks.

## Gates and interpretation

`G10-T-A` requires final authorized-claim precision `1.00`, recall at least
`0.95`, zero unsupported/opposite final claims, at least `0.98` final
disposition accuracy, conflict disclosure at least `0.95`, unknown abstention
at least `0.98`, preference adherence at least `0.95`, ordinary fallback below
`0.10`, all adversarial validator attacks rejected, deterministic replay,
runtime below ten minutes and RSS below 8 GB.

A technical pass would authorize only isolated conversation-memory work. It
would not establish human naturalness, raw-language compilation, a trained
latent decoder, end-to-end integration or 100M-context serving.
