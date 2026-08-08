from __future__ import annotations

from .schemas import DecoderBundle

SYSTEM = """You are a verified conversational renderer. Do not reason beyond the supplied bundle. Answer in one or two sentences. Use only allowed factual claims, preserve names and polarity, disclose required conflict or uncertainty, and follow the requested style."""


def render(bundle: DecoderBundle, method: str = "full", repair_errors: tuple[str, ...] = ()) -> str:
    claims = "\n".join(f"- {item.entity} | {item.predicate} | {item.object} | {item.polarity} | {item.scope}" for item in bundle.authorized_claims) or "- none"
    proof, conflicts, assumptions, status = bundle.proof_summary, " | ".join(bundle.conflicts) or "none", " | ".join(bundle.assumptions) or "none", bundle.status
    state = f"confidence={bundle.state.confidence:.2f}; uncertainty={bundle.state.uncertainty:.2f}; tension={bundle.state.conflict_tension:.2f}; coverage={bundle.state.coverage:.2f}; act={bundle.state.response_act}; style={bundle.state.style}"
    if method == "no_state":
        state = "withheld"
    if method == "state_only":
        claims, proof, conflicts, assumptions, status = "- withheld", "withheld", "withheld", "withheld", "withheld"
    repair = f"\nThe previous answer was rejected for: {', '.join(repair_errors)}. Repair it using only the allowed claims." if repair_errors else ""
    return f"<|im_start|>system\n{SYSTEM}<|im_end|>\n<|im_start|>user\nPrompt: {bundle.prompt}\nVerifier status: {status}\nAllowed claims:\n{claims}\nProof: {proof}\nConflicts: {conflicts}\nAssumptions: {assumptions}\nState: {state}\n{repair}<|im_end|>\n<|im_start|>assistant\n"
