"""Tests for Echo memory harness domain slice."""

import pytest
from datetime import datetime, timezone, timedelta
from meridian_core.echo import (
    MemoryKind,
    MemorySource,
    MemoryRecord,
    MemoryQuery,
    MemoryHit,
    MemoryRepository,
)


@pytest.fixture
def repo():
    """Fresh repository for each test."""
    return MemoryRepository()


@pytest.fixture
def now():
    """Current UTC time."""
    return datetime.now(timezone.utc)


def test_memory_record_frozen(now):
    """MemoryRecord is immutable."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="test body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=("test",),
    )
    with pytest.raises(Exception):
        record.record_id = "r2"


def test_memory_query_frozen():
    """MemoryQuery is immutable."""
    query = MemoryQuery(project="meridian")
    with pytest.raises(Exception):
        query.project = "other"


def test_memory_hit_frozen(now):
    """MemoryHit is immutable."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="test body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    hit = MemoryHit(record=record, score=0.5, reason="test")
    with pytest.raises(Exception):
        hit.score = 0.8


def test_memory_kind_enum():
    """MemoryKind enum has all required values."""
    assert MemoryKind.DECISION.value == "decision"
    assert MemoryKind.FACT.value == "fact"
    assert MemoryKind.PLAN.value == "plan"
    assert MemoryKind.GATE_OUTCOME.value == "gate_outcome"
    assert MemoryKind.STANDING_INSTRUCTION.value == "standing_instruction"
    assert MemoryKind.NOTE.value == "note"


def test_memory_source_enum():
    """MemorySource enum has all required values."""
    assert MemorySource.PRIME.value == "prime"
    assert MemorySource.SCOTT.value == "scott"
    assert MemorySource.REVIEW_CONSOLE.value == "review_console"
    assert MemorySource.WORKER.value == "worker"
    assert MemorySource.IMPORT.value == "import"


def test_memory_record_importance_validation(now):
    """MemoryRecord rejects invalid importance values."""
    with pytest.raises(ValueError, match="importance must be 1-5"):
        MemoryRecord(
            record_id="r1",
            project="meridian",
            kind=MemoryKind.DECISION,
            summary="test",
            body="test body",
            source=MemorySource.PRIME,
            created_at=now,
            importance=0,
            pinned=False,
            tags=(),
        )

    with pytest.raises(ValueError, match="importance must be 1-5"):
        MemoryRecord(
            record_id="r1",
            project="meridian",
            kind=MemoryKind.DECISION,
            summary="test",
            body="test body",
            source=MemorySource.PRIME,
            created_at=now,
            importance=6,
            pinned=False,
            tags=(),
        )


def test_memory_hit_score_validation(now):
    """MemoryHit rejects invalid score values."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="test body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )

    with pytest.raises(ValueError, match="score must be in"):
        MemoryHit(record=record, score=-0.1, reason="test")

    with pytest.raises(ValueError, match="score must be in"):
        MemoryHit(record=record, score=1.1, reason="test")


def test_add_then_query_single_hit(repo, now):
    """Add a record then query returns it as a single hit."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test decision",
        body="test body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=("test",),
    )
    repo.add(record)

    hits = repo.query(MemoryQuery(project="meridian"))
    assert len(hits) == 1
    assert hits[0].record.record_id == "r1"


def test_query_empty_repository(repo):
    """Empty repository returns empty results."""
    hits = repo.query(MemoryQuery(project="meridian"))
    assert hits == ()


def test_query_unknown_project(repo, now):
    """Querying unknown project returns empty result, no exception."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="test body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(record)

    hits = repo.query(MemoryQuery(project="unknown"))
    assert hits == ()


def test_query_kind_filter(repo, now):
    """Kind filter excludes records of other kinds."""
    record1 = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="decision",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    record2 = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.FACT,
        summary="fact",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(record1)
    repo.add(record2)

    hits = repo.query(MemoryQuery(project="meridian", kinds=(MemoryKind.DECISION,)))
    assert len(hits) == 1
    assert hits[0].record.kind == MemoryKind.DECISION


def test_query_tag_filter(repo, now):
    """Tag filter excludes records missing the tag."""
    record1 = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=("scott", "urgent"),
    )
    record2 = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.FACT,
        summary="test",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=("other",),
    )
    repo.add(record1)
    repo.add(record2)

    hits = repo.query(MemoryQuery(project="meridian", tags=("scott",)))
    assert len(hits) == 1
    assert "scott" in hits[0].record.tags


def test_query_since_filter(repo, now):
    """Since filter excludes old records unless pinned."""
    old_record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="old",
        body="body",
        source=MemorySource.PRIME,
        created_at=now - timedelta(days=40),
        importance=3,
        pinned=False,
        tags=(),
    )
    new_record = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="new",
        body="body",
        source=MemorySource.PRIME,
        created_at=now - timedelta(days=5),
        importance=3,
        pinned=False,
        tags=(),
    )
    pinned_old = MemoryRecord(
        record_id="r3",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="pinned old",
        body="body",
        source=MemorySource.PRIME,
        created_at=now - timedelta(days=40),
        importance=3,
        pinned=True,
        tags=(),
    )
    repo.add(old_record)
    repo.add(new_record)
    repo.add(pinned_old)

    since = now - timedelta(days=30)
    hits = repo.query(MemoryQuery(project="meridian", since=since))

    record_ids = [h.record.record_id for h in hits]
    assert "r2" in record_ids  # new record included
    assert "r3" in record_ids  # pinned old included
    assert "r1" not in record_ids  # unpinned old excluded


def test_pinned_outranks_unpinned(repo, now):
    """Pinned record outranks unpinned with same importance and recency."""
    unpinned = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="unpinned",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    pinned = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="pinned",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=True,
        tags=(),
    )
    repo.add(unpinned)
    repo.add(pinned)

    hits = repo.query(MemoryQuery(project="meridian"))
    assert hits[0].record.record_id == "r2"
    assert hits[1].record.record_id == "r1"


def test_newer_outranks_older(repo, now):
    """Newer record outranks older with same pinning and importance."""
    old = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="old",
        body="body",
        source=MemorySource.PRIME,
        created_at=now - timedelta(days=10),
        importance=3,
        pinned=False,
        tags=(),
    )
    new = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="new",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(old)
    repo.add(new)

    hits = repo.query(MemoryQuery(project="meridian"))
    assert hits[0].record.record_id == "r2"
    assert hits[1].record.record_id == "r1"


def test_higher_importance_outranks(repo, now):
    """Higher importance outranks lower with same pinning and recency."""
    low = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="low",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=1,
        pinned=False,
        tags=(),
    )
    high = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="high",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=5,
        pinned=False,
        tags=(),
    )
    repo.add(low)
    repo.add(high)

    hits = repo.query(MemoryQuery(project="meridian"))
    assert hits[0].record.record_id == "r2"
    assert hits[1].record.record_id == "r1"


def test_score_in_valid_range(repo, now):
    """All scores are in [0.0, 1.0]."""
    records = [
        MemoryRecord(
            record_id=f"r{i}",
            project="meridian",
            kind=MemoryKind.DECISION,
            summary=f"record {i}",
            body="body",
            source=MemorySource.PRIME,
            created_at=now - timedelta(days=i),
            importance=i % 5 + 1,
            pinned=i % 2 == 0,
            tags=(),
        )
        for i in range(10)
    ]
    for record in records:
        repo.add(record)

    hits = repo.query(MemoryQuery(project="meridian"))
    for hit in hits:
        assert 0.0 <= hit.score <= 1.0


def test_deterministic_ranking(repo, now):
    """Two identical queries return identical hit order (determinism)."""
    records = [
        MemoryRecord(
            record_id=f"r{i}",
            project="meridian",
            kind=MemoryKind.DECISION,
            summary=f"record {i}",
            body="body",
            source=MemorySource.PRIME,
            created_at=now - timedelta(days=i),
            importance=3,
            pinned=False,
            tags=(),
        )
        for i in range(5)
    ]
    for record in records:
        repo.add(record)

    query = MemoryQuery(project="meridian")
    hits1 = repo.query(query)
    hits2 = repo.query(query)

    assert len(hits1) == len(hits2)
    for h1, h2 in zip(hits1, hits2):
        assert h1.record.record_id == h2.record.record_id
        assert abs(h1.score - h2.score) < 0.01  # Allow small floating-point variance from time passing


def test_superseded_excluded_by_default(repo, now):
    """Superseded records are excluded by default."""
    original = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="original",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(original)

    replacement = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="replacement",
        body="body",
        source=MemorySource.PRIME,
        created_at=now + timedelta(seconds=1),
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.supersede("r1", replacement)

    hits = repo.query(MemoryQuery(project="meridian"))
    assert len(hits) == 1
    assert hits[0].record.record_id == "r2"


def test_superseded_included_with_flag(repo, now):
    """include_superseded=True includes superseded records."""
    original = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="original",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(original)

    replacement = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="replacement",
        body="body",
        source=MemorySource.PRIME,
        created_at=now + timedelta(seconds=1),
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.supersede("r1", replacement)

    hits = repo.query(MemoryQuery(project="meridian", include_superseded=True))
    assert len(hits) == 2
    record_ids = {h.record.record_id for h in hits}
    assert "r1" in record_ids
    assert "r2" in record_ids


def test_supersede_returns_new_record(repo, now):
    """supersede() returns the new record and links the old one."""
    original = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="original",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(original)

    replacement = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="replacement",
        body="body",
        source=MemorySource.PRIME,
        created_at=now + timedelta(seconds=1),
        importance=3,
        pinned=False,
        tags=(),
    )
    result = repo.supersede("r1", replacement)

    assert result.record_id == "r2"

    old_record = repo.get("r1")
    assert old_record.superseded_by == "r2"


def test_limit_zero_returns_empty(repo, now):
    """limit=0 returns an empty tuple."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(record)

    hits = repo.query(MemoryQuery(project="meridian", limit=0))
    assert hits == ()


def test_limit_exceeds_hard_cap(repo, now):
    """Limit larger than hard cap is truncated, not raised."""
    records = [
        MemoryRecord(
            record_id=f"r{i}",
            project="meridian",
            kind=MemoryKind.DECISION,
            summary=f"record {i}",
            body="body",
            source=MemorySource.PRIME,
            created_at=now,
            importance=3,
            pinned=False,
            tags=(),
        )
        for i in range(30)
    ]
    for record in records:
        repo.add(record)

    hits = repo.query(MemoryQuery(project="meridian", limit=100))
    assert len(hits) == MemoryRepository.HARD_LIMIT


def test_get_returns_record(repo, now):
    """get() returns the record if found."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(record)

    found = repo.get("r1")
    assert found is not None
    assert found.record_id == "r1"


def test_get_returns_none_if_not_found(repo):
    """get() returns None if record not found."""
    found = repo.get("nonexistent")
    assert found is None


def test_add_duplicate_raises(repo, now):
    """Adding a duplicate record ID raises an error."""
    record = MemoryRecord(
        record_id="r1",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="test",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )
    repo.add(record)

    with pytest.raises(ValueError, match="already exists"):
        repo.add(record)


def test_supersede_nonexistent_raises(repo, now):
    """supersede() on nonexistent record raises."""
    new_record = MemoryRecord(
        record_id="r2",
        project="meridian",
        kind=MemoryKind.DECISION,
        summary="new",
        body="body",
        source=MemorySource.PRIME,
        created_at=now,
        importance=3,
        pinned=False,
        tags=(),
    )

    with pytest.raises(ValueError, match="not found"):
        repo.supersede("nonexistent", new_record)
