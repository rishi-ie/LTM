# G2.11 — Single-Pass Atomic Mumbrane Compiler

G2.11 tests whether one small MiniLM attention pass can expose granular atomic
Mumbrane coordinates that a deterministic composer converts into exact G1 and
universal Mumbrane topology.

The experiment is fail-fast: the G1-derived atomic basis must reconstruct every
registered relation and role before model training begins. The learned model
predicts only unary span, ordered-pair, participation and context coordinates;
it never directly predicts complete G1 relations or graph JSON.

The operational model is the pinned local `all-MiniLM-L6-v2`, with layers 1–4
frozen, layers 5–6 trainable, one encoder forward per sentence, CPU float32,
four threads and a maximum of 128 wordpieces. G1 exact topology remains
authoritative; vectors and residual state cannot authorize facts.

The nine existing Mumbranes are storage feature channels. The learned compiler
target is a granular atomic coordinate field. A deterministic composer creates
complete legal structures, validates them through G1 and commits an entire
sentence atomically or not at all.

The full staged commands and gates are defined in the experiment implementation
and configuration. A basis collision, unsafe accepted operation, or failed
kernel gate stops the experiment before full extraction and locked execution.
