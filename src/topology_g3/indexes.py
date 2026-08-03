from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import asdict

import numpy as np

from .generator import _norm
from .schemas import TopologyAddress, canonical_hash


class Indexes:
    def __init__(self, addresses: tuple[TopologyAddress, ...]):
        self.addresses = {x.address_id: x for x in addresses}; self.canonical = defaultdict(list); self.alias = defaultdict(list); self.predicate = defaultdict(list); self.scope = defaultdict(list); self.episode = defaultdict(list)
        for x in addresses:
            self.canonical[_norm(x.canonical_name)].append(x.address_id)
            for alias in x.aliases: self.alias[_norm(alias)].append(x.address_id)
            # Predicate registry objects are starting addresses. Individual claims
            # are opened later by G4, not returned as hundreds of G3 candidates.
            if x.predicate and x.object_kind == "predicate": self.predicate[_norm(x.predicate)].append(x.address_id)
            self.scope[x.scope_id].append(x.address_id)
            if x.episode_id: self.episode[x.episode_id].append(x.address_id)
        for index in (self.canonical, self.alias, self.predicate, self.scope, self.episode):
            for value in index.values(): value.sort()
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        from topology_g21.encode import MODEL

        self._encoder = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
        self._semantic_keys = tuple(sorted(set(self.canonical) | set(self.alias) | set(self.predicate)))
        self._semantic_vectors = self._encoder.encode(
            list(self._semantic_keys), batch_size=128, normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False,
        ).astype(np.float32)

    def semantic_candidates(self, text: str, limit: int = 8) -> list[str]:
        vector = self._encoder.encode([text], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0]
        selected = np.argsort(-(self._semantic_vectors @ vector))[:limit]
        output: list[str] = []
        for position in selected:
            key = self._semantic_keys[int(position)]
            output.extend(self.canonical.get(key, ()))
            output.extend(self.alias.get(key, ()))
            output.extend(self.predicate.get(key, ()))
        return sorted(set(output))[:limit]
    def manifest(self) -> dict:
        payload = {"canonical": dict(self.canonical), "alias": dict(self.alias), "predicate": dict(self.predicate), "scope": dict(self.scope), "episode": dict(self.episode)}
        return {"topology_hash": canonical_hash([asdict(x) for x in self.addresses.values()]), "index_hash": canonical_hash(payload), "postings": sum(len(v) for group in payload.values() for v in group.values()), "indexes": 5}
