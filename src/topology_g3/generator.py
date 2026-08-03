from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path

from .schemas import PromptMention, PromptSignature, TopologyAddress, canonical_hash

CATEGORIES = ("canonical", "alias", "near_name", "paraphrase", "scope", "temporal", "episode", "multiple", "ambiguous", "unsupported")
RELATIONS = ("implies", "conjoins", "requires", "excludes", "equals", "before", "after", "supersedes", "supports", "opposes", "prefers", "refers_to", "scoped_to", "fictional_rule", "causes_hypothetically", "uncertainty", "assistant_derived_from", "derived_from", "fact", "claim")

def _norm(text: str) -> str: return " ".join(text.lower().replace("-", " ").split())

def build_topology(seed: int, count: int = 10_000) -> tuple[TopologyAddress, ...]:
    prefix = f"{seed:x}"
    scopes = tuple(f"scope-{prefix}-{i:02d}" for i in range(20)); episodes = tuple(f"episode-{prefix}-{i:02d}" for i in range(50))
    entities: list[TopologyAddress] = []
    for i in range(1000):
        name = f"{prefix}-entity-{i:04d}"; alias = f"{prefix}-alias-{i:04d}"
        if i < 200: alias = f"{prefix}-shared-{i % 100:03d}"
        entities.append(TopologyAddress(f"entity:{name}", f"entity:{name}", "entity", name, (alias,), None, None, scopes[i % 20], None, None, episodes[i % 50], "agent" if i % 2 else "object", (f"source:{i}",)))
    values = list(entities)
    for relation in RELATIONS:
        name = f"predicate-{relation}"
        values.append(TopologyAddress(f"000predicate:{relation}", f"predicate:{relation}", "predicate", name, (), name, relation, "global", None, None, None, None, (f"source:predicate:{relation}",)))
    for i in range(count - len(values)):
        entity = entities[i % len(entities)]; relation = RELATIONS[i % len(RELATIONS)]
        name = f"{prefix}-{relation}-{i:05d}"; scope = entity.scope_id if i % 5 else scopes[(i + 1) % 20]
        valid_from = None if i % 7 else 10; valid_to = None if i % 7 else 90
        values.append(TopologyAddress(f"addr:{name}", f"obj:{name}", "constraint" if i % 20 == 0 else "claim", name, (), f"predicate-{relation}", relation, scope, valid_from, valid_to, entity.episode_id, entity.entity_type, (f"source:{i+1000}", entity.address_id)))
    return tuple(values)

def _signature(prompt_id: str, entity: TopologyAddress | None, category: str, relation: str, index: int) -> PromptSignature:
    if entity is None:
        return PromptSignature(prompt_id, "question", (), ("unregistered predicate",), (), (), (), None, None, "unknown", "asserted", (), "abstain")
    text = entity.canonical_name if category != "alias" else entity.aliases[0]
    if category == "near_name": text = entity.canonical_name.replace("-", " ")
    start = 0
    mention = PromptMention(text, _norm(text), "entity", start, len(text))
    scopes = (entity.scope_id,) if category == "scope" else ()
    valid_at = 50 if category == "temporal" else None
    episodes = (entity.episode_id,) if category == "episode" and entity.episode_id else ()
    return PromptSignature(prompt_id, "question", (mention,), (f"predicate-{relation}",), (relation,), (), scopes, valid_at, None, "positive", "asserted", episodes, "clarify")

def build_prompts(topology: tuple[TopologyAddress, ...], seed: int, prompts: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed); entities = [x for x in topology if x.object_kind == "entity"]; runtime: list[dict] = []; gold: list[dict] = []
    for index in range(prompts):
        category = CATEGORIES[index % len(CATEGORIES)]; entity = None if category == "unsupported" else entities[(index * 17) % len(entities)]
        if category == "ambiguous": entity = entities[index % 100]
        relation = RELATIONS[index % len(RELATIONS)]; pid = f"prompt-{seed}-{index:03d}"; sig = _signature(pid, entity, category, relation, index)
        text = "What applies to " + (sig.entity_mentions[0].text if sig.entity_mentions else "the unknown object") + "?"
        if category == "ambiguous": text = f"What applies to {entity.aliases[0]}?"; sig = PromptSignature(pid, sig.goal_kind, (PromptMention(entity.aliases[0], _norm(entity.aliases[0]), "entity", 16, 16+len(entity.aliases[0])),), sig.predicate_phrases, sig.relation_hints, (), (), None, None, "positive", "asserted", (), "clarify")
        runtime.append({"prompt_id": pid, "text": text, "category": category, "signature": asdict(sig)})
        required_entity = () if entity is None else (entity.address_id,)
        # Ambiguous shared aliases deliberately permit a set of scope-distinct entity candidates.
        options = tuple(x.address_id for x in entities if entity and x.aliases and x.aliases[0] == entity.aliases[0]) if category == "ambiguous" else ()
        matches = tuple(x.address_id for x in topology if entity is not None and x.object_kind == "predicate" and x.relation_type == relation)
        gold.append({"prompt_id": pid, "required_entity_addresses": required_entity, "required_predicate_addresses": matches, "required_scope_id": entity.scope_id if entity and category == "scope" else None, "required_temporal_addresses": matches if category == "temporal" else (), "required_episode_addresses": required_entity if category == "episode" else (), "required_constraint_addresses": (), "required_exception_addresses": (), "acceptable_ambiguity_sets": (options,) if options else (), "resolvable": category not in ("ambiguous", "unsupported")})
    rng.shuffle(runtime); return runtime, gold

def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(json.dumps(x, sort_keys=True) for x in rows) + "\n")

def read_jsonl(path: Path) -> list[dict]: return [json.loads(x) for x in path.read_text().splitlines() if x]

def topology_manifest(topology: tuple[TopologyAddress, ...]) -> dict:
    rows = [asdict(x) for x in topology]; return {"addresses": len(rows), "topology_hash": canonical_hash(rows)}
