"""Tests for the optional Graphiti advisory memory sidecar."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from meridian_core.atlas import AtlasHit, AtlasSource
from meridian_core.echo import MemoryKind, MemoryRecord, MemorySource
from meridian_core.graphiti_memory import (
    GRAPHITI_CORE_VERSION,
    GraphitiAdvisoryHit,
    GraphitiBackend,
    GraphitiMode,
    GraphitiSidecarConfig,
    GraphitiSidecarStatus,
    build_ingest_plan,
    create_graphiti_client,
    episode_from_atlas_hit,
    episode_from_memory_record,
    graphiti_available,
    ingest_episodes,
    search_advisory_context,
    sidecar_readiness,
)


def make_record(
    record_id: str = "decision-1",
    *,
    summary: str = "Use Atlas as deterministic retrieval authority",
    body: str = "Raw body must never enter Graphiti",
    superseded_by: str | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        record_id=record_id,
        project="meridian",
        kind=MemoryKind.DECISION,
        summary=summary,
        body=body,
        source=MemorySource.PRIME,
        created_at=datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc),
        importance=4,
        pinned=True,
        tags=("atlas", "retrieval"),
        superseded_by=superseded_by,
    )


def enabled_config() -> GraphitiSidecarConfig:
    return GraphitiSidecarConfig(mode=GraphitiMode.ADVISORY)


class FakeGraphitiClient:
    def __init__(self):
        self.added = []

    async def add_episode(
        self,
        *,
        name,
        episode_body,
        source_description,
        reference_time,
        group_id=None,
        uuid=None,
    ):
        self.added.append(
            {
                "name": name,
                "episode_body": episode_body,
                "source_description": source_description,
                "reference_time": reference_time,
                "group_id": group_id,
                "uuid": uuid,
            }
        )

    async def search(self, query, group_ids=None, num_results=10):
        return [
            {
                "uuid": "edge-1",
                "fact": "Atlas remains authoritative; Graphiti is advisory.",
                "score": 0.82,
            },
            {
                "uuid": "edge-2",
                "fact": "Echo bodies are not mirrored into Graphiti.",
                "score": 2.0,
            },
        ][:num_results]


def test_sidecar_disabled_by_default():
    config = GraphitiSidecarConfig()

    report = sidecar_readiness(config)

    assert config.enabled is False
    assert report.status is GraphitiSidecarStatus.DISABLED


def test_sidecar_ready_when_advisory():
    config = enabled_config()

    report = sidecar_readiness(config)

    assert config.enabled is True
    assert report.status is GraphitiSidecarStatus.READY
    assert GRAPHITI_CORE_VERSION in report.message
    assert GraphitiBackend.NEO4J.value in report.message


def test_graph_group_id_override_supports_aura_database_name():
    config = GraphitiSidecarConfig(
        mode=GraphitiMode.ADVISORY,
        graph_group_id="34d3d946",
    )

    episode = episode_from_memory_record(make_record(), config=config)

    assert episode.group_id == "34d3d946"


def test_graph_group_id_rejects_invalid_graphiti_characters():
    with pytest.raises(ValueError, match="graph_group_id"):
        GraphitiSidecarConfig(
            mode=GraphitiMode.ADVISORY,
            graph_group_id="meridian:meridian",
        )


def test_create_graphiti_client_reports_missing_optional_dependency():
    if graphiti_available():
        pytest.skip("graphiti-core is installed in this environment")

    with pytest.raises(RuntimeError, match="meridian-core\\[graphiti\\]"):
        create_graphiti_client()


def test_memory_record_projection_uses_summary_not_body():
    record = make_record()

    episode = episode_from_memory_record(record, config=enabled_config())

    assert episode.group_id == "meridian_meridian"
    assert episode.body == record.summary
    assert record.body not in episode.body
    assert episode.source_ref.ref == "echo://meridian/decision-1"
    assert ("pinned", "true") in episode.metadata


def test_memory_record_projection_normalizes_naive_datetime():
    record = MemoryRecord(
        record_id="naive",
        project="meridian",
        kind=MemoryKind.FACT,
        summary="Naive timestamp imported from old memory",
        body="not mirrored",
        source=MemorySource.IMPORT,
        created_at=datetime(2026, 6, 14, 12, 0),
        importance=3,
        pinned=False,
        tags=(),
    )

    episode = episode_from_memory_record(record, config=enabled_config())

    assert episode.reference_time.tzinfo is not None
    assert episode.reference_time.utcoffset() is not None


def test_atlas_hit_projection_uses_excerpt_and_preserves_source_ref():
    hit = AtlasHit(
        path="docs/atlas-retrieval-contract.md",
        title="Atlas Retrieval Contract",
        reason="required path",
        excerpt="Atlas is deterministic and FileMap-first.",
        source=AtlasSource.DOC,
        score=0.99,
    )

    episode = episode_from_atlas_hit(hit, project="meridian", config=enabled_config())

    assert episode.body == "Atlas is deterministic and FileMap-first."
    assert episode.source_ref.ref == "docs/atlas-retrieval-contract.md"
    assert ("atlas_source", "doc") in episode.metadata
    assert ("atlas_reason", "required path") in episode.metadata


def test_build_ingest_plan_is_disabled_without_advisory_mode():
    report = build_ingest_plan(
        config=GraphitiSidecarConfig(),
        memory_records=(make_record(),),
        project="meridian",
    )

    assert report.status is GraphitiSidecarStatus.DISABLED
    assert report.episodes == ()


def test_build_ingest_plan_skips_superseded_echo_records():
    active = make_record("active")
    old = make_record("old", superseded_by="active")

    report = build_ingest_plan(
        config=enabled_config(),
        memory_records=(old, active),
        project="meridian",
    )

    assert report.status is GraphitiSidecarStatus.READY
    assert [episode.source_ref.ref for episode in report.episodes] == [
        "echo://meridian/active"
    ]
    assert report.warnings == ("Skipped superseded Echo record old.",)


def test_ingest_episodes_calls_graphiti_client_with_safe_fields():
    client = FakeGraphitiClient()
    record = make_record()
    episode = episode_from_memory_record(record, config=enabled_config())

    report = asyncio.run(ingest_episodes(client, (episode,)))

    assert report.status is GraphitiSidecarStatus.READY
    assert len(client.added) == 1
    assert client.added[0]["episode_body"] == record.summary
    assert record.body not in client.added[0]["episode_body"]
    assert client.added[0]["group_id"] == "meridian_meridian"
    assert client.added[0]["uuid"] is None


def test_search_advisory_context_returns_bounded_advisory_hits():
    client = FakeGraphitiClient()

    hits = asyncio.run(
        search_advisory_context(
            client,
            query="What governs Atlas and Echo memory?",
            project="meridian",
            config=GraphitiSidecarConfig(mode=GraphitiMode.ADVISORY, max_hits=1),
        )
    )

    assert len(hits) == 1
    assert isinstance(hits[0], GraphitiAdvisoryHit)
    assert hits[0].advisory is True
    assert hits[0].score == 0.82
    assert hits[0].source_ref.ref == "graphiti://meridian/edge-1"


def test_search_advisory_context_disabled_returns_empty():
    client = FakeGraphitiClient()

    hits = asyncio.run(
        search_advisory_context(
            client,
            query="anything",
            project="meridian",
            config=GraphitiSidecarConfig(),
        )
    )

    assert hits == ()
    assert client.added == []


def test_advisory_hit_cannot_be_authoritative():
    with pytest.raises(ValueError, match="advisory"):
        GraphitiAdvisoryHit(
            source_ref=episode_from_memory_record(
                make_record(),
                config=enabled_config(),
            ).source_ref,
            fact="unsafe authority promotion",
            reason="test",
            score=0.5,
            advisory=False,
        )
