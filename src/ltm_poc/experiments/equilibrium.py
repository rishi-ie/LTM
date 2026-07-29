"""Conservative whole-corpus semantic equilibrium field."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from ltm_poc.schemas import ChunkRecord


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("cannot normalize a non-finite or zero vector")
    return vector / norm


def _logsumexp(values: np.ndarray) -> float:
    maximum = float(np.max(values))
    return maximum + float(np.log(np.exp(values - maximum).sum()))


def _metadata_prior(metadata: dict[str, Any]) -> float:
    values = {
        "priority": float(metadata.get("priority", 1.0)),
        "confidence": float(metadata.get("confidence", 1.0)),
        "authority": float(metadata.get("authority", 1.0)),
        "recency": float(metadata.get("recency", 1.0)),
    }
    if not 0 <= values["priority"] <= 100:
        raise ValueError("priority must be in [0, 100]")
    for name in ("confidence", "authority", "recency"):
        if not 0 <= values[name] <= 1:
            raise ValueError(f"{name} must be in [0, 1]")
    return float(np.prod(list(values.values())))


@dataclass(frozen=True)
class EquilibriumConfig:
    query_anchor: float = 1.0
    average_weight: float = 1.0
    max_weight: float = 1.0
    beta: float = 10.0
    relevance_floor: float = 1e-4
    relevance_temperature: float = 0.05
    steps: int = 8
    hard_evaluations: int = 16
    learning_rate: float = 0.05
    backtracking_retries: int = 3
    state_tolerance: float = 1e-4
    energy_tolerance: float = 1e-8

    def __post_init__(self) -> None:
        if min(self.query_anchor, self.average_weight, self.max_weight) < 0:
            raise ValueError("energy weights must be non-negative")
        if self.beta <= 0 or self.relevance_temperature <= 0:
            raise ValueError("temperatures must be positive")
        if not 0 <= self.relevance_floor <= 1:
            raise ValueError("relevance floor must be in [0, 1]")
        if self.steps < 1 or self.hard_evaluations < 2:
            raise ValueError("invalid optimization budget")


@dataclass
class HierarchyNode:
    node_id: int
    indices: np.ndarray
    mass: float
    weighted_sum: np.ndarray
    centroid: np.ndarray
    angular_radius: float
    max_prior: float
    children: tuple[int, ...] = ()

    @property
    def count(self) -> int:
        return int(len(self.indices))


@dataclass(frozen=True)
class FrontierElement:
    kind: str
    element_id: str
    vector: np.ndarray
    prior: float
    max_prior: float
    member_indices: tuple[int, ...]
    node_id: int | None = None


@dataclass(frozen=True)
class CompiledFrontier:
    query: np.ndarray
    elements: tuple[FrontierElement, ...]
    item_count: int
    exact_count: int
    aggregate_count: int

    def represented_indices(self) -> list[int]:
        return [index for element in self.elements for index in element.member_indices]


@dataclass
class SemanticFieldHierarchy:
    vectors: np.ndarray
    metadata: list[dict[str, Any]]
    priors: np.ndarray
    nodes: list[HierarchyNode]
    root_id: int
    branching_factor: int = 8
    leaf_size: int = 64

    @classmethod
    def build(
        cls,
        vectors: np.ndarray,
        metadata: Sequence[dict[str, Any]],
        branching_factor: int = 8,
        leaf_size: int = 64,
        max_iterations: int = 25,
        seed: int = 1729,
    ) -> "SemanticFieldHierarchy":
        vectors = np.asarray(vectors, dtype=np.float64)
        if vectors.ndim != 2 or vectors.shape[0] != len(metadata):
            raise ValueError("vectors and metadata must have matching rows")
        if len(vectors) == 0 or not np.allclose(
            np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5
        ):
            raise ValueError("hierarchy requires non-empty unit vectors")
        priors = np.asarray([_metadata_prior(dict(item)) for item in metadata])
        active = np.flatnonzero(priors > 0)
        if len(active) == 0:
            raise ValueError("at least one corpus item must have non-zero weight")
        hierarchy = cls(
            vectors=vectors,
            metadata=[dict(item) for item in metadata],
            priors=priors,
            nodes=[],
            root_id=0,
            branching_factor=branching_factor,
            leaf_size=leaf_size,
        )
        hierarchy.root_id = hierarchy._build_node(
            active, max_iterations=max_iterations, seed=seed
        )
        return hierarchy

    def _make_node(self, indices: np.ndarray) -> int:
        weights = self.priors[indices]
        weighted_sum = weights @ self.vectors[indices]
        centroid = _unit(weighted_sum)
        similarities = np.clip(self.vectors[indices] @ centroid, -1.0, 1.0)
        node = HierarchyNode(
            node_id=len(self.nodes),
            indices=np.asarray(sorted(indices.tolist()), dtype=np.int64),
            mass=float(weights.sum()),
            weighted_sum=np.asarray(weighted_sum, dtype=np.float64),
            centroid=centroid,
            angular_radius=float(np.max(np.arccos(similarities))),
            max_prior=float(weights.max()),
        )
        self.nodes.append(node)
        return node.node_id

    def _build_node(self, indices: np.ndarray, max_iterations: int, seed: int) -> int:
        node_id = self._make_node(indices)
        if len(indices) <= self.leaf_size:
            return node_id
        groups = self._spherical_kmeans(
            indices,
            min(self.branching_factor, len(indices)),
            max_iterations,
            seed + node_id,
        )
        if len(groups) <= 1:
            return node_id
        children = tuple(
            self._build_node(group, max_iterations, seed) for group in groups
        )
        self.nodes[node_id].children = children
        return node_id

    def _spherical_kmeans(
        self, indices: np.ndarray, clusters: int, iterations: int, seed: int
    ) -> list[np.ndarray]:
        data = self.vectors[indices]
        rng = np.random.default_rng(seed)
        first = int(rng.integers(len(indices)))
        chosen = [first]
        while len(chosen) < clusters:
            similarities = data @ data[chosen].T
            distance = 1.0 - np.max(similarities, axis=1)
            distance[chosen] = -1
            chosen.append(int(np.argmax(distance)))
        centroids = data[chosen].copy()
        labels = np.zeros(len(indices), dtype=np.int64)
        for _ in range(iterations):
            scores = data @ centroids.T
            new_labels = np.argmax(scores, axis=1)
            if np.array_equal(new_labels, labels) and _ > 0:
                break
            labels = new_labels
            for cluster in range(clusters):
                members = np.flatnonzero(labels == cluster)
                if len(members):
                    centroids[cluster] = _unit(
                        self.priors[indices[members]] @ data[members]
                    )
        groups = [
            np.asarray(sorted(indices[labels == cluster].tolist()), dtype=np.int64)
            for cluster in range(clusters)
            if np.any(labels == cluster)
        ]
        return sorted(groups, key=lambda group: int(group[0]))

    def _upper_bound(self, node: HierarchyNode, query: np.ndarray) -> float:
        angle = float(np.arccos(np.clip(query @ node.centroid, -1.0, 1.0)))
        return float(np.cos(max(0.0, angle - node.angular_radius)))

    def compile_frontier(
        self,
        query: np.ndarray,
        max_frontier: int = 256,
        max_exact: int = 128,
    ) -> CompiledFrontier:
        query = _unit(np.asarray(query, dtype=np.float64))
        frontier: list[tuple[str, int]] = [("node", self.root_id)]
        exact_count = 0
        while True:
            choices: list[tuple[float, int, str, int]] = []
            for position, (kind, identifier) in enumerate(frontier):
                if kind != "node":
                    continue
                node = self.nodes[identifier]
                added = len(node.children) if node.children else node.count
                new_exact = exact_count + (node.count if not node.children else 0)
                if len(frontier) - 1 + added > max_frontier or new_exact > max_exact:
                    continue
                choices.append(
                    (
                        -self._upper_bound(node, query),
                        node.node_id,
                        kind,
                        position,
                    )
                )
            if not choices:
                break
            _, node_id, _, position = min(choices)
            node = self.nodes[node_id]
            if node.children:
                replacement = [("node", child) for child in node.children]
            else:
                replacement = [("item", int(index)) for index in node.indices]
                exact_count += node.count
            frontier[position : position + 1] = replacement
        elements: list[FrontierElement] = []
        for kind, identifier in frontier:
            if kind == "item":
                elements.append(
                    FrontierElement(
                        kind="exact",
                        element_id=f"item:{identifier}",
                        vector=self.vectors[identifier],
                        prior=float(self.priors[identifier]),
                        max_prior=float(self.priors[identifier]),
                        member_indices=(identifier,),
                    )
                )
            else:
                node = self.nodes[identifier]
                elements.append(
                    FrontierElement(
                        kind="aggregate",
                        element_id=f"node:{identifier}",
                        vector=node.centroid,
                        prior=node.mass,
                        max_prior=node.max_prior,
                        member_indices=tuple(int(x) for x in node.indices),
                        node_id=identifier,
                    )
                )
        compiled = CompiledFrontier(
            query=query,
            elements=tuple(elements),
            item_count=self.nodes[self.root_id].count,
            exact_count=sum(item.kind == "exact" for item in elements),
            aggregate_count=sum(item.kind == "aggregate" for item in elements),
        )
        represented = compiled.represented_indices()
        if len(represented) != len(set(represented)) or set(represented) != set(
            self.nodes[self.root_id].indices.tolist()
        ):
            raise RuntimeError("frontier does not partition the active corpus")
        return compiled

    def exact_frontier(self, query: np.ndarray) -> CompiledFrontier:
        query = _unit(np.asarray(query, dtype=np.float64))
        active = self.nodes[self.root_id].indices
        return CompiledFrontier(
            query=query,
            elements=tuple(
                FrontierElement(
                    kind="exact",
                    element_id=f"item:{int(index)}",
                    vector=self.vectors[index],
                    prior=float(self.priors[index]),
                    max_prior=float(self.priors[index]),
                    member_indices=(int(index),),
                )
                for index in active
            ),
            item_count=len(active),
            exact_count=len(active),
            aggregate_count=0,
        )


@dataclass(frozen=True)
class EquilibriumField:
    frontier: CompiledFrontier
    config: EquilibriumConfig
    vectors: np.ndarray = field(init=False, repr=False)
    raw_weights: np.ndarray = field(init=False, repr=False)
    average_weights: np.ndarray = field(init=False, repr=False)
    relative_weights: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        vectors = np.asarray(
            [element.vector for element in self.frontier.elements], dtype=np.float64
        )
        average_priors = np.asarray(
            [element.prior for element in self.frontier.elements], dtype=np.float64
        )
        max_priors = np.asarray(
            [element.max_prior for element in self.frontier.elements],
            dtype=np.float64,
        )
        similarities = vectors @ self.frontier.query
        relevance = self.config.relevance_floor + (
            1.0 - self.config.relevance_floor
        ) * np.exp(
            np.clip(
                (similarities - 1.0) / self.config.relevance_temperature,
                -745,
                0,
            )
        )
        raw = average_priors * relevance
        max_raw = max_priors * relevance
        if (
            not np.isfinite(raw).all()
            or not np.isfinite(max_raw).all()
            or float(raw.sum()) <= 0
        ):
            raise ValueError("field weights must be finite and non-zero")
        object.__setattr__(self, "vectors", vectors)
        object.__setattr__(self, "raw_weights", raw)
        object.__setattr__(self, "average_weights", raw / raw.sum())
        object.__setattr__(self, "relative_weights", max_raw / max_raw.max())

    def energy_and_gradient(self, state: np.ndarray) -> tuple[float, np.ndarray]:
        state = np.asarray(state, dtype=np.float64)
        if state.shape != (self.vectors.shape[1],) or not np.isclose(
            np.linalg.norm(state), 1.0, atol=1e-6
        ):
            raise ValueError("field state must be a unit vector")
        residuals = 1.0 - self.vectors @ state
        logits = self.config.beta * self.relative_weights * residuals
        probabilities = np.exp(logits - _logsumexp(logits))
        energy = (
            self.config.query_anchor * (1.0 - float(state @ self.frontier.query))
            + self.config.average_weight * float(self.average_weights @ residuals)
            + self.config.max_weight / self.config.beta * _logsumexp(logits)
        )
        gradient = (
            -self.config.query_anchor * self.frontier.query
            - self.config.average_weight * (self.average_weights @ self.vectors)
            - self.config.max_weight
            * ((probabilities * self.relative_weights) @ self.vectors)
        )
        return float(energy), np.asarray(gradient, dtype=np.float64)

    def residuals(self, state: np.ndarray) -> np.ndarray:
        return 1.0 - self.vectors @ np.asarray(state, dtype=np.float64)

    def barycenter(self) -> np.ndarray:
        return _unit(
            self.config.query_anchor * self.frontier.query
            + self.config.average_weight * (self.average_weights @ self.vectors)
        )


@dataclass(frozen=True)
class EquilibriumStep:
    step: int
    field_evaluations: int
    energy: float
    gradient_norm: float
    query_cosine: float
    state_delta: float


@dataclass(frozen=True)
class EquilibriumResult:
    termination: str
    update_steps: int
    field_evaluations: int
    initial_energy: float
    final_energy: float
    final_state: list[float]
    trace: list[EquilibriumStep]
    frontier_statistics: dict[str, int]
    weights: list[float]
    residuals: list[float]
    evidence: list[dict[str, Any]]
    approximation_diagnostics: dict[str, Any]


def optimize_equilibrium(
    field: EquilibriumField,
    initial_state: np.ndarray | None = None,
) -> EquilibriumResult:
    state = _unit(
        field.frontier.query.copy()
        if initial_state is None
        else np.asarray(initial_state, dtype=np.float64)
    )
    energy, gradient = field.energy_and_gradient(state)
    initial_energy = energy
    evaluations = 1
    trace: list[EquilibriumStep] = []
    termination = "max_steps"
    for step in range(1, field.config.steps + 1):
        if evaluations >= field.config.hard_evaluations:
            termination = "hard_budget"
            break
        tangent = gradient - float(gradient @ state) * state
        learning_rate = field.config.learning_rate
        accepted = False
        for _ in range(field.config.backtracking_retries):
            candidate = _unit(state - learning_rate * tangent)
            candidate_energy, candidate_gradient = field.energy_and_gradient(candidate)
            evaluations += 1
            if candidate_energy <= energy + field.config.energy_tolerance:
                accepted = True
                break
            if evaluations >= field.config.hard_evaluations:
                break
            learning_rate *= 0.5
        if not accepted:
            termination = (
                "hard_budget"
                if evaluations >= field.config.hard_evaluations
                else "line_search"
            )
            break
        delta = float(np.linalg.norm(candidate - state))
        state, energy, gradient = candidate, candidate_energy, candidate_gradient
        trace.append(
            EquilibriumStep(
                step=step,
                field_evaluations=evaluations,
                energy=energy,
                gradient_norm=float(np.linalg.norm(tangent)),
                query_cosine=float(state @ field.frontier.query),
                state_delta=delta,
            )
        )
        if delta <= field.config.state_tolerance:
            termination = "converged_state"
            break
    return EquilibriumResult(
        termination=termination,
        update_steps=len(trace),
        field_evaluations=evaluations,
        initial_energy=initial_energy,
        final_energy=energy,
        final_state=state.tolist(),
        trace=trace,
        frontier_statistics={
            "items": field.frontier.item_count,
            "elements": len(field.frontier.elements),
            "exact": field.frontier.exact_count,
            "aggregate": field.frontier.aggregate_count,
        },
        weights=field.raw_weights.tolist(),
        residuals=field.residuals(state).tolist(),
        evidence=[],
        approximation_diagnostics={},
    )


def build_evidence_bundle(
    field: EquilibriumField,
    result: EquilibriumResult,
    chunks: Sequence[ChunkRecord],
    limit: int = 4,
) -> dict[str, Any]:
    """Return bounded exact evidence plus aggregate forces and residual tensions."""
    state = np.asarray(result.final_state)
    residuals = field.residuals(state)
    exact = [
        index
        for index, element in enumerate(field.frontier.elements)
        if element.kind == "exact"
    ]
    rankings = (
        sorted(
            exact,
            key=lambda i: (
                -float(field.raw_weights[i]),
                field.frontier.elements[i].element_id,
            ),
        ),
        sorted(
            exact,
            key=lambda i: (
                -float(field.relative_weights[i] * residuals[i]),
                field.frontier.elements[i].element_id,
            ),
        ),
        sorted(
            exact,
            key=lambda i: (
                -float(field.vectors[i] @ state),
                field.frontier.elements[i].element_id,
            ),
        ),
    )
    chosen: list[int] = []
    cursor = 0
    while len(chosen) < min(limit, len(exact)):
        ranking = rankings[cursor % len(rankings)]
        candidate = next((item for item in ranking if item not in chosen), None)
        if candidate is None:
            break
        chosen.append(candidate)
        cursor += 1
    evidence = []
    for rank, constraint_index in enumerate(chosen, start=1):
        corpus_index = field.frontier.elements[constraint_index].member_indices[0]
        chunk = chunks[corpus_index]
        evidence.append(
            {
                "rank": rank,
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                "text": chunk.text,
                "raw_weight": float(field.raw_weights[constraint_index]),
                "relative_weight": float(field.relative_weights[constraint_index]),
                "residual": float(residuals[constraint_index]),
                "weight_source": dict(chunk.metadata),
            }
        )
    aggregates = sorted(
        (
            {
                "element_id": element.element_id,
                "member_count": len(element.member_indices),
                "raw_weight": float(field.raw_weights[index]),
                "relative_weight": float(field.relative_weights[index]),
                "residual": float(residuals[index]),
            }
            for index, element in enumerate(field.frontier.elements)
            if element.kind == "aggregate"
        ),
        key=lambda item: (-item["raw_weight"], item["element_id"]),
    )[:4]
    tensions = [
        item
        for item in evidence
        if item["relative_weight"] >= 0.5 and item["residual"] >= 0.5
    ]
    return {
        "instruction": (
            "Describe the weighted semantic consensus, cite every factual statement, "
            "identify incompatible or weakly satisfied evidence, and never claim that "
            "every item was logically proven true."
        ),
        "evidence": evidence,
        "aggregate_regions": aggregates,
        "unresolved_tensions": tensions,
    }


def render_evidence_fallback(bundle: dict[str, Any]) -> str:
    """Render the decoder-safe evidence bundle without generative rewriting."""
    lines = [
        "Weighted semantic evidence (not a logical proof):",
        "",
        "| Chunk | Weight | Residual | Source |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in bundle["evidence"]:
        lines.append(
            f"| {item['chunk_id']} | {item['relative_weight']:.3f} | "
            f"{item['residual']:.3f} | {item['source_path']} |"
        )
    if bundle["unresolved_tensions"]:
        lines.extend(["", "Unresolved tension:"])
        lines.extend(
            f"- {item['chunk_id']} (residual {item['residual']:.3f})"
            for item in bundle["unresolved_tensions"]
        )
    return "\n".join(lines)
