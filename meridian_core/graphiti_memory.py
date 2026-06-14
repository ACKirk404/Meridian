"""Graphiti advisory memory sidecar for Meridian.

This module keeps Graphiti behind a Meridian-owned boundary. Echo and Atlas
remain the authoritative deterministic surfaces; Graphiti receives only safe
summaries/excerpts and returns advisory context hits with source references.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from importlib import import_module
from typing import Any, Protocol, Sequence

from .atlas import AtlasHit
from .echo import MemoryRecord


GRAPHITI_CORE_VERSION = "0.29.2"
DEFAULT_GRAPHITI_BACKEND = "neo4j"
DEFAULT_GROUP_PREFIX = "meridian"
MAX_EPISODE_CHARS = 4000
MAX_QUERY_CHARS = 500
MAX_HITS = 10


class GraphitiMode(Enum):
    """Runtime posture for the Graphiti sidecar."""

    DISABLED = "disabled"
    ADVISORY = "advisory"


class GraphitiBackend(Enum):
    """Supported Graphiti graph backends for Meridian wiring."""

    NEO4J = "neo4j"
    FALKORDB = "falkordb"
    NEPTUNE = "neptune"


class GraphitiSourceKind(Enum):
    """Meridian source surfaces allowed to feed Graphiti."""

    ECHO_SUMMARY = "echo_summary"
    ATLAS_HIT = "atlas_hit"
    GOAL_LINEAGE = "goal_lineage"
    GATE_OUTCOME = "gate_outcome"


class GraphitiSidecarStatus(Enum):
    """Lifecycle status for sidecar operations."""

    DISABLED = "disabled"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True)
class GraphitiSourceRef:
    """Stable provenance handle for content mirrored into Graphiti."""

    kind: GraphitiSourceKind
    ref: str
    project: str
    summary: str

    def __post_init__(self) -> None:
        _require_safe_text(self.ref, "ref", max_chars=240)
        _require_safe_text(self.project, "project", max_chars=80)
        _require_safe_text(self.summary, "summary", max_chars=500)


@dataclass(frozen=True)
class GraphitiEpisode:
    """Safe, bounded episode sent to Graphiti for graph extraction."""

    episode_id: str
    group_id: str
    name: str
    body: str
    source_description: str
    reference_time: datetime
    source_ref: GraphitiSourceRef
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_safe_text(self.episode_id, "episode_id", max_chars=160)
        _require_safe_text(self.group_id, "group_id", max_chars=160)
        _require_safe_text(self.name, "name", max_chars=240)
        _require_safe_text(self.body, "body", max_chars=MAX_EPISODE_CHARS)
        _require_safe_text(self.source_description, "source_description", max_chars=240)
        _require_aware_datetime(self.reference_time, "reference_time")
        for key, value in self.metadata:
            _require_safe_text(key, "metadata key", max_chars=80)
            _require_safe_text(value, "metadata value", max_chars=500)


@dataclass(frozen=True)
class GraphitiAdvisoryHit:
    """Graphiti recall result after Meridian safety projection."""

    source_ref: GraphitiSourceRef
    fact: str
    reason: str
    score: float
    advisory: bool = True

    def __post_init__(self) -> None:
        _require_safe_text(self.fact, "fact", max_chars=1000)
        _require_safe_text(self.reason, "reason", max_chars=240)
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}")
        if self.advisory is not True:
            raise ValueError("Graphiti hits must remain advisory")


@dataclass(frozen=True)
class GraphitiSidecarConfig:
    """Configuration for optional Graphiti sidecar use."""

    mode: GraphitiMode = GraphitiMode.DISABLED
    backend: GraphitiBackend = GraphitiBackend.NEO4J
    package: str = "graphiti-core"
    package_version: str = GRAPHITI_CORE_VERSION
    group_prefix: str = DEFAULT_GROUP_PREFIX
    graph_group_id: str | None = None
    max_episode_chars: int = MAX_EPISODE_CHARS
    max_hits: int = MAX_HITS

    def __post_init__(self) -> None:
        _require_safe_text(self.package, "package", max_chars=80)
        _require_safe_text(self.package_version, "package_version", max_chars=40)
        _require_safe_text(self.group_prefix, "group_prefix", max_chars=80)
        if self.graph_group_id is not None:
            _require_safe_text(self.graph_group_id, "graph_group_id", max_chars=160)
            if self.graph_group_id != _graphiti_safe_id(self.graph_group_id):
                raise ValueError("graph_group_id must contain only letters, numbers, dashes, or underscores")
        if self.max_episode_chars <= 0 or self.max_episode_chars > MAX_EPISODE_CHARS:
            raise ValueError("max_episode_chars must be between 1 and MAX_EPISODE_CHARS")
        if self.max_hits <= 0 or self.max_hits > MAX_HITS:
            raise ValueError("max_hits must be between 1 and MAX_HITS")

    @property
    def enabled(self) -> bool:
        """Whether Graphiti may be queried or written."""

        return self.mode is GraphitiMode.ADVISORY


@dataclass(frozen=True)
class GraphitiSidecarReport:
    """Result of a sidecar readiness or ingest operation."""

    status: GraphitiSidecarStatus
    message: str
    episodes: tuple[GraphitiEpisode, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_safe_text(self.message, "message", max_chars=500)
        for warning in self.warnings:
            _require_safe_text(warning, "warning", max_chars=500)


class GraphitiClientProtocol(Protocol):
    """Subset of Graphiti's async API used by Meridian."""

    async def add_episode(
        self,
        *,
        name: str,
        episode_body: str,
        source_description: str,
        reference_time: datetime,
        group_id: str | None = None,
        uuid: str | None = None,
    ) -> Any:
        """Add a safe episode to the context graph."""

    async def search(
        self,
        query: str,
        group_ids: list[str] | None = None,
        num_results: int = MAX_HITS,
    ) -> Sequence[Any]:
        """Search the advisory context graph."""


def sidecar_readiness(config: GraphitiSidecarConfig) -> GraphitiSidecarReport:
    """Return the sidecar posture without importing Graphiti or touching network."""

    if not config.enabled:
        return GraphitiSidecarReport(
            status=GraphitiSidecarStatus.DISABLED,
            message="Graphiti sidecar disabled; Echo and Atlas remain authoritative.",
        )
    return GraphitiSidecarReport(
        status=GraphitiSidecarStatus.READY,
        message=(
            f"Graphiti sidecar configured as advisory using "
            f"{config.package}=={config.package_version} on {config.backend.value}."
        ),
    )


def graphiti_available() -> bool:
    """Return whether graphiti-core can be imported in this environment."""

    try:
        import_module("graphiti_core")
    except Exception:
        return False
    return True


def create_graphiti_client(
    *,
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str | None = None,
    **kwargs: Any,
) -> GraphitiClientProtocol:
    """Create a real Graphiti client when the optional package is installed."""

    try:
        graphiti_module = import_module("graphiti_core")
    except Exception as exc:
        raise RuntimeError(
            "Graphiti sidecar requires the optional dependency: "
            "install meridian-core[graphiti]."
        ) from exc

    graphiti_class = getattr(graphiti_module, "Graphiti", None)
    if graphiti_class is None:
        graphiti_module = import_module("graphiti_core.graphiti")
        graphiti_class = getattr(graphiti_module, "Graphiti")

    if database:
        driver_module = import_module("graphiti_core.driver.neo4j_driver")
        neo4j_driver_class = getattr(driver_module, "Neo4jDriver")
        graph_driver = neo4j_driver_class(uri=uri, user=user, password=password, database=database)
        return graphiti_class(graph_driver=graph_driver, **kwargs)

    return graphiti_class(uri=uri, user=user, password=password, **kwargs)


def episode_from_memory_record(
    record: MemoryRecord,
    *,
    config: GraphitiSidecarConfig | None = None,
) -> GraphitiEpisode:
    """Project an Echo record into a safe Graphiti episode.

    Only ``MemoryRecord.summary`` is mirrored. ``MemoryRecord.body`` remains
    Echo-owned and is never copied into Graphiti by this function.
    """

    effective_config = config or GraphitiSidecarConfig()
    group_id = _group_id(effective_config, record.project)
    summary = _truncate(record.summary, effective_config.max_episode_chars)
    source_ref = GraphitiSourceRef(
        kind=GraphitiSourceKind.ECHO_SUMMARY,
        ref=f"echo://{record.project}/{record.record_id}",
        project=record.project,
        summary=summary,
    )
    metadata = (
        ("memory_kind", record.kind.value),
        ("memory_source", record.source.value),
        ("importance", str(record.importance)),
        ("pinned", str(record.pinned).lower()),
    )
    if record.superseded_by:
        metadata += (("superseded_by", record.superseded_by),)

    return GraphitiEpisode(
        episode_id=f"echo-{record.project}-{record.record_id}",
        group_id=group_id,
        name=f"Echo memory: {summary}",
        body=summary,
        source_description="Meridian Echo summary",
        reference_time=_normalize_datetime(record.created_at),
        source_ref=source_ref,
        metadata=metadata,
    )


def episode_from_atlas_hit(
    hit: AtlasHit,
    *,
    project: str,
    config: GraphitiSidecarConfig | None = None,
) -> GraphitiEpisode:
    """Project an Atlas hit into a safe Graphiti episode.

    Only the Atlas title/excerpt surface is mirrored. Whole files are never
    read here and Atlas remains the authority for file/doc retrieval.
    """

    effective_config = config or GraphitiSidecarConfig()
    group_id = _group_id(effective_config, project)
    text = hit.excerpt or hit.title
    body = _truncate(text, effective_config.max_episode_chars)
    source_ref = GraphitiSourceRef(
        kind=GraphitiSourceKind.ATLAS_HIT,
        ref=hit.path,
        project=project,
        summary=hit.title,
    )
    return GraphitiEpisode(
        episode_id=f"atlas-{project}-{_stable_ref(hit.path)}",
        group_id=group_id,
        name=f"Atlas hit: {hit.title}",
        body=body,
        source_description=f"Meridian Atlas {hit.source.value} hit",
        reference_time=datetime.now(timezone.utc),
        source_ref=source_ref,
        metadata=(
            ("atlas_source", hit.source.value),
            ("atlas_reason", hit.reason),
            ("atlas_score", f"{hit.score:.3f}"),
        ),
    )


def build_ingest_plan(
    *,
    config: GraphitiSidecarConfig,
    memory_records: Sequence[MemoryRecord] = (),
    atlas_hits: Sequence[AtlasHit] = (),
    project: str = "meridian",
) -> GraphitiSidecarReport:
    """Build a safe, reviewable set of episodes for Graphiti ingestion."""

    if not config.enabled:
        return GraphitiSidecarReport(
            status=GraphitiSidecarStatus.DISABLED,
            message="Graphiti sidecar disabled; no episodes built.",
        )

    episodes: list[GraphitiEpisode] = []
    warnings: list[str] = []

    for record in memory_records:
        if record.superseded_by:
            warnings.append(f"Skipped superseded Echo record {record.record_id}.")
            continue
        episodes.append(episode_from_memory_record(record, config=config))

    for hit in atlas_hits:
        episodes.append(episode_from_atlas_hit(hit, project=project, config=config))

    return GraphitiSidecarReport(
        status=GraphitiSidecarStatus.READY,
        message=f"Built {len(episodes)} safe Graphiti episode(s).",
        episodes=tuple(episodes),
        warnings=tuple(warnings),
    )


async def ingest_episodes(
    client: GraphitiClientProtocol,
    episodes: Sequence[GraphitiEpisode],
) -> GraphitiSidecarReport:
    """Ingest already-projected episodes through a Graphiti-compatible client."""

    for episode in episodes:
        await client.add_episode(
            name=episode.name,
            episode_body=episode.body,
            source_description=episode.source_description,
            reference_time=episode.reference_time,
            group_id=episode.group_id,
        )
    return GraphitiSidecarReport(
        status=GraphitiSidecarStatus.READY,
        message=f"Ingested {len(episodes)} Graphiti episode(s).",
        episodes=tuple(episodes),
    )


async def search_advisory_context(
    client: GraphitiClientProtocol,
    *,
    query: str,
    project: str,
    config: GraphitiSidecarConfig,
) -> tuple[GraphitiAdvisoryHit, ...]:
    """Search Graphiti and project results into advisory Meridian hits."""

    if not config.enabled:
        return ()

    _require_safe_text(query, "query", max_chars=MAX_QUERY_CHARS)
    group_id = _group_id(config, project)
    raw_hits = await client.search(
        query=query,
        group_ids=[group_id],
        num_results=config.max_hits,
    )
    hits = tuple(
        _advisory_hit_from_raw(raw_hit, project=project)
        for raw_hit in raw_hits[: config.max_hits]
    )
    return hits


def _advisory_hit_from_raw(raw_hit: Any, *, project: str) -> GraphitiAdvisoryHit:
    fact = _extract_attr(raw_hit, "fact", default=str(raw_hit))
    score = _extract_score(raw_hit)
    edge_uuid = _extract_attr(raw_hit, "uuid", default=_stable_ref(fact))
    source_ref = GraphitiSourceRef(
        kind=GraphitiSourceKind.ECHO_SUMMARY,
        ref=f"graphiti://{project}/{edge_uuid}",
        project=project,
        summary=_truncate(fact, 500),
    )
    return GraphitiAdvisoryHit(
        source_ref=source_ref,
        fact=_truncate(fact, 1000),
        reason="graphiti advisory search",
        score=score,
    )


def _extract_attr(value: Any, attr: str, *, default: str) -> str:
    if isinstance(value, dict):
        return str(value.get(attr) or default)
    return str(getattr(value, attr, default) or default)


def _extract_score(value: Any) -> float:
    raw = 0.5
    if isinstance(value, dict):
        raw = value.get("score", value.get("rank", raw))
    else:
        raw = getattr(value, "score", getattr(value, "rank", raw))
    try:
        score = float(raw)
    except (TypeError, ValueError):
        return 0.5
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return score


def _group_id(config: GraphitiSidecarConfig, project: str) -> str:
    if config.graph_group_id:
        return config.graph_group_id
    return _graphiti_safe_id(f"{config.group_prefix}_{project}")


def _graphiti_safe_id(value: str) -> str:
    return _stable_ref(value).replace("-", "_")


def _stable_ref(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")
    return safe[:120] or "unknown"


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _require_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."


def _require_safe_text(value: str, field_name: str, *, max_chars: int) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > max_chars:
        raise ValueError(f"{field_name} exceeds {max_chars} characters")
    if any(ch in value for ch in ("\x00", "\r")):
        raise ValueError(f"{field_name} contains unsafe control characters")
