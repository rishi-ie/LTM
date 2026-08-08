"""Shared-field aggregation, cache validation, and honest L5 scale diagnostics."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, replace

import numpy as np

from .dataset import PublicFieldCase, build_case
from .field import EquilibriumFieldIndex, build_minimap
from .optimizer import optimize
from .schemas import CompiledPromptField, EquilibriumBody, FieldEquilibriumResult, FieldMumbrane

SCALE_CORPUS_REVISION = "l5-query-independent-distractors/1"
MAX_MATERIALIZED_DISTRACTORS = 4_096


def _sha(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        if isinstance(value, np.ndarray):
            digest.update(np.asarray(value, dtype=np.float32).tobytes())
        else:
            digest.update(repr(value).encode())
    return digest.hexdigest()


def _reality(prompt: CompiledPromptField) -> str:
    values = {item.reality_key for item in prompt.influences}
    if len(values) != 1:
        raise ValueError("shared-field prompt must have one reality")
    return next(iter(values))


@dataclass(frozen=True, slots=True)
class PartitionManifest:
    reality_key: str
    case_ids: tuple[str, ...]
    body_count: int
    unit_count: int
    vector_row_count: int
    field_sha256: str
    minimap_sha256: str


@dataclass(frozen=True, slots=True)
class SharedFieldManifest:
    partition_manifests: tuple[PartitionManifest, ...]
    field_sha256: str
    minimap_sha256: str
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class FieldPartition:
    reality_key: str
    case_ids: tuple[str, ...]
    bodies: tuple[EquilibriumBody, ...]
    units: tuple[FieldMumbrane, ...]
    vectors: np.ndarray
    cells: tuple[object, ...]
    summaries: np.ndarray
    prompts: tuple[CompiledPromptField, ...]
    index: EquilibriumFieldIndex
    manifest: PartitionManifest


@dataclass(frozen=True, slots=True)
class SharedField:
    source_cases: tuple[PublicFieldCase, ...]
    partitions: tuple[FieldPartition, ...]
    case_partitions: tuple[tuple[str, str], ...]
    manifest: SharedFieldManifest

    def _partition_key(self, case_id: str) -> str:
        low, high = 0, len(self.case_partitions)
        while low < high:
            middle = (low + high) // 2
            key, value = self.case_partitions[middle]
            if key < case_id:
                low = middle + 1
            elif key > case_id:
                high = middle
            else:
                return value
        raise KeyError(f"unknown shared-field case: {case_id}")

    def partition_for(self, case_id: str) -> FieldPartition:
        key = self._partition_key(case_id)
        low, high = 0, len(self.partitions)
        while low < high:
            middle = (low + high) // 2
            partition = self.partitions[middle]
            if partition.reality_key < key:
                low = middle + 1
            elif partition.reality_key > key:
                high = middle
            else:
                return partition
        raise KeyError(f"missing shared-field partition: {key}")

    def index_for(self, case_id: str) -> EquilibriumFieldIndex:
        return self.partition_for(case_id).index

    def prompt(self, case_id: str) -> CompiledPromptField:
        prompts = self.partition_for(case_id).prompts
        low, high = 0, len(prompts)
        while low < high:
            middle = (low + high) // 2
            prompt = prompts[middle]
            if prompt.prompt_id < case_id:
                low = middle + 1
            elif prompt.prompt_id > case_id:
                high = middle
            else:
                return prompt
        raise KeyError(f"missing shared-field prompt: {case_id}")


@dataclass(frozen=True, slots=True)
class RebuildResult:
    field: SharedField
    affected_realities: tuple[str, ...]
    unaffected_partition_hash_equality: bool
    clean_rebuild_equality: bool | None


@dataclass(frozen=True, slots=True)
class LazyDistractorCorpus:
    body_count: int
    seed: int
    reality_key: str = "scale-distractor"
    scope_key: str = "global"
    revision: str = SCALE_CORPUS_REVISION

    def __post_init__(self) -> None:
        if self.body_count < 0:
            raise ValueError("distractor count must be non-negative")

    @property
    def corpus_sha256(self) -> str:
        # The frozen deterministic generator plus seed/count commits the complete lazy corpus.
        return _sha(self.revision, self.seed, self.body_count, self.reality_key, self.scope_key)

    def iter_cases(self, limit: int | None = None) -> Iterator[PublicFieldCase]:
        count = self.body_count if limit is None else min(self.body_count, max(0, limit))
        for index in range(count):
            case = build_case(
                index,
                self.seed,
                split="scale-distractor",
                family="one_body",
                domain="abstract",
            ).public
            yield replace(
                case,
                prompt=replace(
                    case.prompt,
                    influences=tuple(
                        replace(item, reality_key=self.reality_key, scope_key=self.scope_key)
                        for item in case.prompt.influences
                    ),
                ),
                units=tuple(
                    replace(item, reality_key=self.reality_key, scope_key=self.scope_key)
                    for item in case.units
                ),
                bodies=tuple(
                    replace(item, reality_key=self.reality_key, scope_key=self.scope_key)
                    for item in case.bodies
                ),
            )


@dataclass(frozen=True, slots=True)
class ScaleMetrics:
    requested_distractor_bodies: int
    materialized_distractor_bodies: int
    lazy_committed_distractor_bodies: int
    runtime_queryable_bodies: int
    partition_count: int
    corpus_sha256: str
    full_field_scans: int
    peak_materialization_batch: int


@dataclass(frozen=True, slots=True)
class ScaleOverlay:
    field: SharedField
    metrics: ScaleMetrics
    overlay_sha256: str

    def index_for(self, case_id: str) -> EquilibriumFieldIndex:
        return self.field.index_for(case_id)

    def prompt(self, case_id: str) -> CompiledPromptField:
        return self.field.prompt(case_id)


@dataclass(frozen=True, slots=True)
class SharedQueryObservation:
    result: FieldEquilibriumResult
    partition_body_count: int
    maximum_active_bodies: int
    cumulative_distinct_body_reads: int
    full_field_scans: int
    minimap_cells_scored: int
    body_records_read: int
    consumer_index_lookups: int


def _remapped_id(kind: str, case_id: str, original: str) -> str:
    return f"sf:{kind}:{_sha(case_id, original)[:24]}"


def _partition_manifest(
    reality_key: str,
    case_ids: tuple[str, ...],
    bodies: tuple[EquilibriumBody, ...],
    units: tuple[FieldMumbrane, ...],
    vectors: np.ndarray,
    cells: tuple[object, ...],
    summaries: np.ndarray,
) -> PartitionManifest:
    exact_rows = tuple(
        (
            item.unit_id,
            item.body_id,
            item.semantic_key,
            item.semantic_vector_ref,
            item.local_index,
            item.phase_index,
            item.polarity,
            item.modality,
            item.scope_key,
            item.reality_key,
            item.valid_from,
            item.valid_to,
            item.identity_key,
            item.provenance_id,
            item.independent_source_key,
        )
        for item in units
    )
    body_rows = tuple(asdict(item) for item in bodies)
    cell_rows = tuple(asdict(item) for item in cells)
    field_hash = _sha(reality_key, case_ids, exact_rows, body_rows, vectors)
    minimap_hash = _sha(cell_rows, summaries)
    return PartitionManifest(
        reality_key,
        case_ids,
        len(bodies),
        len(units),
        len(vectors),
        field_hash,
        minimap_hash,
    )


def _shared_manifest(partitions: tuple[FieldPartition, ...]) -> SharedFieldManifest:
    manifests = tuple(item.manifest for item in sorted(partitions, key=lambda item: item.reality_key))
    field_hash = _sha(tuple((item.reality_key, item.field_sha256) for item in manifests))
    minimap_hash = _sha(tuple((item.reality_key, item.minimap_sha256) for item in manifests))
    return SharedFieldManifest(manifests, field_hash, minimap_hash, _sha(field_hash, minimap_hash, manifests))


def _build_partition(cases: tuple[PublicFieldCase, ...]) -> FieldPartition:
    ordered = tuple(sorted(cases, key=lambda item: item.case_id))
    reality_key = _reality(ordered[0].prompt)
    if any(_reality(item.prompt) != reality_key for item in ordered):
        raise ValueError("partition mixes realities")

    vector_rows = {
        tuple(float(value) for value in row)
        for case in ordered
        for row in case.vector_table
    }
    sorted_rows = tuple(sorted(vector_rows, key=lambda row: (_sha(np.asarray(row, dtype=np.float32)), row)))
    vector_refs = {row: index for index, row in enumerate(sorted_rows)}
    vectors = np.asarray(sorted_rows, dtype=np.float32)
    all_units: list[FieldMumbrane] = []
    all_bodies: list[EquilibriumBody] = []
    prompts: list[CompiledPromptField] = []
    for case in ordered:
        unit_ids = {item.unit_id: _remapped_id("u", case.case_id, item.unit_id) for item in case.units}
        owner_ids = {
            item.body_id: _remapped_id("owner", case.case_id, item.body_id)
            for item in case.units
        }
        body_ids = {
            item.body_id: _remapped_id("b", case.case_id, item.body_id)
            for item in case.bodies
        }
        owner_ids.update(body_ids)
        remapped_units = tuple(
            replace(
                item,
                unit_id=unit_ids[item.unit_id],
                body_id=owner_ids[item.body_id],
                semantic_vector_ref=vector_refs[tuple(float(value) for value in case.vector_table[item.semantic_vector_ref])],
            )
            for item in case.units
        )
        all_units.extend(remapped_units)
        for body in case.bodies:
            payload = (
                body_ids[body.body_id],
                tuple(unit_ids[item] for item in body.input_unit_ids),
                tuple(unit_ids[item] for item in body.outcome_unit_ids),
                body.base_weight,
                body.authority,
                body.confidence,
                body.scope_key,
                body.reality_key,
                body.valid_from,
                body.valid_to,
                body.independent_source_key,
                body.provenance_ids,
            )
            all_bodies.append(
                replace(
                    body,
                    body_id=body_ids[body.body_id],
                    input_unit_ids=tuple(unit_ids[item] for item in body.input_unit_ids),
                    outcome_unit_ids=tuple(unit_ids[item] for item in body.outcome_unit_ids),
                    body_hash=_sha(payload),
                )
            )
        prompts.append(
            replace(
                case.prompt,
                influences=tuple(
                    replace(item, unit_id=unit_ids[item.unit_id])
                    for item in case.prompt.influences
                ),
            )
        )
    units = tuple(sorted(all_units, key=lambda item: item.unit_id))
    bodies = tuple(sorted(all_bodies, key=lambda item: item.body_id))
    prompts_tuple = tuple(sorted(prompts, key=lambda item: item.prompt_id))
    cells, summaries = build_minimap(bodies, units, vectors)
    index = EquilibriumFieldIndex(bodies, units, vectors, cells, summaries)
    case_ids = tuple(item.case_id for item in ordered)
    manifest = _partition_manifest(reality_key, case_ids, bodies, units, vectors, cells, summaries)
    return FieldPartition(reality_key, case_ids, bodies, units, vectors, cells, summaries, prompts_tuple, index, manifest)


def build_shared_field(cases: Iterable[PublicFieldCase]) -> SharedField:
    ordered = tuple(sorted(cases, key=lambda item: item.case_id))
    if not ordered or len({item.case_id for item in ordered}) != len(ordered):
        raise ValueError("shared field requires unique public cases")
    grouped: dict[str, list[PublicFieldCase]] = {}
    for case in ordered:
        grouped.setdefault(_reality(case.prompt), []).append(case)
    partitions = tuple(_build_partition(tuple(grouped[key])) for key in sorted(grouped))
    mapping = tuple(sorted((case.case_id, _reality(case.prompt)) for case in ordered))
    return SharedField(ordered, partitions, mapping, _shared_manifest(partitions))


def verify_cache(field: SharedField, expected: SharedFieldManifest | None = None) -> bool:
    current_parts = []
    for partition in field.partitions:
        fresh = _partition_manifest(
            partition.reality_key,
            partition.case_ids,
            partition.bodies,
            partition.units,
            partition.vectors,
            partition.cells,
            partition.summaries,
        )
        if fresh != partition.manifest:
            raise ValueError("STALE_MINIMAP_CACHE")
        current_parts.append(replace(partition, manifest=fresh))
    current = _shared_manifest(tuple(current_parts))
    if current != field.manifest or (expected is not None and current != expected):
        raise ValueError("STALE_MINIMAP_CACHE")
    return True


def incremental_rebuild(
    field: SharedField,
    additions: Iterable[PublicFieldCase],
    *,
    verify_clean: bool = True,
) -> RebuildResult:
    additions_tuple = tuple(additions)
    if not additions_tuple:
        return RebuildResult(field, (), True, True if verify_clean else None)
    existing_ids = {item.case_id for item in field.source_cases}
    if any(item.case_id in existing_ids for item in additions_tuple):
        raise ValueError("incremental rebuild cannot replace an existing case")
    affected = tuple(sorted({_reality(item.prompt) for item in additions_tuple}))
    combined = tuple(sorted(field.source_cases + additions_tuple, key=lambda item: item.case_id))
    cases_by_reality: dict[str, list[PublicFieldCase]] = {}
    for case in combined:
        cases_by_reality.setdefault(_reality(case.prompt), []).append(case)
    old = {item.reality_key: item for item in field.partitions}
    partitions = tuple(
        _build_partition(tuple(cases_by_reality[key])) if key in affected else old[key]
        for key in sorted(cases_by_reality)
    )
    mapping = tuple(sorted((case.case_id, _reality(case.prompt)) for case in combined))
    rebuilt = SharedField(combined, partitions, mapping, _shared_manifest(partitions))
    unaffected_equal = all(
        rebuilt_partition is old[key]
        for key, rebuilt_partition in ((item.reality_key, item) for item in partitions)
        if key not in affected
    )
    clean_equal = None
    if verify_clean:
        clean_equal = build_shared_field(combined).manifest == rebuilt.manifest
    return RebuildResult(rebuilt, affected, unaffected_equal, clean_equal)


def attach_distractors(
    field: SharedField,
    corpus: LazyDistractorCorpus,
    *,
    materialize_limit: int = 0,
) -> ScaleOverlay:
    if materialize_limit < 0:
        raise ValueError("materialize limit must be non-negative")
    if materialize_limit > MAX_MATERIALIZED_DISTRACTORS:
        raise ValueError("materialize limit exceeds the bounded-memory scale profile")
    additions = tuple(corpus.iter_cases(materialize_limit))
    rebuilt = incremental_rebuild(field, additions, verify_clean=False).field if additions else field
    materialized = sum(len(item.bodies) for item in additions)
    metrics = ScaleMetrics(
        corpus.body_count,
        materialized,
        corpus.body_count - materialized,
        sum(len(item.bodies) for item in rebuilt.partitions),
        len(rebuilt.partitions),
        corpus.corpus_sha256,
        0,
        materialized,
    )
    overlay_hash = _sha(rebuilt.manifest.manifest_sha256, corpus.corpus_sha256, materialized, corpus.body_count)
    return ScaleOverlay(rebuilt, metrics, overlay_hash)


def run_shared_query(
    field: SharedField | ScaleOverlay,
    case_id: str,
    **optimizer_options: object,
) -> SharedQueryObservation:
    shared = field.field if isinstance(field, ScaleOverlay) else field
    partition = shared.partition_for(case_id)
    before = partition.index.access_accounting()
    result = optimize(partition.index, shared.prompt(case_id), **optimizer_options)
    after = partition.index.access_accounting()
    active = max((len(item.body_ids) for item in result.frontiers), default=0)
    cumulative = len({body_id for item in result.frontiers for body_id in item.opened_body_ids})
    return SharedQueryObservation(
        result,
        len(partition.bodies),
        active,
        cumulative,
        after.full_field_scans - before.full_field_scans,
        after.minimap_cells_scored - before.minimap_cells_scored,
        after.body_records_read - before.body_records_read,
        after.consumer_index_lookups - before.consumer_index_lookups,
    )


__all__ = [
    "MAX_MATERIALIZED_DISTRACTORS",
    "LazyDistractorCorpus",
    "RebuildResult",
    "ScaleMetrics",
    "ScaleOverlay",
    "SharedField",
    "SharedFieldManifest",
    "SharedQueryObservation",
    "attach_distractors",
    "build_shared_field",
    "incremental_rebuild",
    "run_shared_query",
    "verify_cache",
]
