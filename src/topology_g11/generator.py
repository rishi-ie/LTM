from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .schemas import ConversationCase, ConversationEvent, SessionClaim

FAMILIES = (
    "context_reference",
    "correction",
    "preference",
    "fictional_conflict",
    "assistant_contamination",
    "isolation_clear",
    "compression_reopen",
    "restart_delete",
)


def stable_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:24]


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def claim(case: str, session: str, tag: str, subject: str, predicate: str, obj: str, polarity: str, scope: str, turn: int, event_id: str) -> SessionClaim:
    return SessionClaim(stable_id(case, "claim", tag, subject, predicate, obj, polarity, scope), session, subject, predicate, obj, polarity, scope, turn, None, event_id, (event_id,))


def event(case: str, session: str, turn: int, kind: str, episode: str, **payload: str) -> ConversationEvent:
    text = json.dumps(payload, sort_keys=True)
    return ConversationEvent(stable_id(case, "event", str(turn), kind, text), session, turn, "user", kind, tuple(sorted(payload.items())), source_hash(f"{case}:{turn}:{kind}:{text}"), episode)


def build_case(seed: int, number: int) -> ConversationCase:
    family = FAMILIES[number % len(FAMILIES)]
    case, session = f"g11-{seed:x}-{number:03d}", f"session-{seed:x}-{number:03d}"
    entity, first, corrected, base_obj = f"velin-{number + 101}", f"prism-{number + 301}", f"prism-{number + 501}", f"anchor-{number + 701}"
    episode = f"episode-{number % 3}"
    base_event = stable_id(case, "base-source")
    base = claim(case, "base", "base", f"archive-{number + 701}", "holds", base_obj, "positive", "global", 0, base_event)
    facts = event(case, session, 1, "fact", episode, subject=entity, predicate="holds", object=first, polarity="positive", scope="global", tag="first")
    first_claim = claim(case, session, "first", entity, "holds", first, "positive", "global", 1, facts.event_id)
    bind = event(case, session, 2, "bind_reference", episode, mention="it", entity=entity)
    query_ref = event(case, session, 3, "query", episode, subject="", predicate="holds", scope="global", query="reference")
    correction = event(case, session, 4, "correction", episode, old_claim_id=first_claim.claim_id, subject=entity, predicate="holds", object=corrected, polarity="positive", scope="global", tag="corrected")
    query_correction = event(case, session, 5, "query", episode, subject=entity, predicate="holds", scope="global", query="correction")
    preference = event(case, session, 6, "preference", episode, key="style", value="brief")
    query_preference = event(case, session, 7, "query", episode, subject=entity, predicate="holds", scope="global", query="preference")
    fictional = event(case, session, 8, "fact", episode, subject=entity, predicate="guards", object=f"gate-{number}", polarity="positive", scope=f"fiction-{number % 4}", tag="fictional")
    query_scope = event(case, session, 9, "query", episode, subject=entity, predicate="guards", scope="global", query="scope")
    conflict = event(case, session, 10, "conflict", episode, subject=entity, predicate="holds", scope="global")
    fold = event(case, session, 11, "fold_episode", episode, folded_episode=episode)
    query_episode = event(case, session, 12, "query", episode, subject=entity, predicate="holds", scope="global", query="episode", episode_reference=episode)
    return ConversationCase(case, family, session, base, (facts, bind, query_ref, correction, query_correction, preference, query_preference, fictional, query_scope, conflict, fold, query_episode))


def build(seed: int, count: int) -> list[ConversationCase]:
    return [build_case(seed, number) for number in range(count)]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, default=str, indent=2, sort_keys=True))
    temporary.replace(path)


def materialize(root: Path, cases: list[ConversationCase]) -> None:
    write_json(root / "conversations.json", [asdict(case) for case in cases])


def load(root: Path) -> list[ConversationCase]:
    rows = json.loads((root / "conversations.json").read_text())
    output = []
    for item in rows:
        base = SessionClaim(**item["base_claim"])
        events = tuple(ConversationEvent(**{**event_row, "payload": tuple(tuple(pair) for pair in event_row["payload"])}) for event_row in item["events"])
        output.append(ConversationCase(item["conversation_id"], item["family"], item["session_id"], base, events))
    return output
