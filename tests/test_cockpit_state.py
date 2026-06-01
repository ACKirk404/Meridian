"""Tests for Prime cockpit snapshot/event domain model."""

from __future__ import annotations

import pytest

from meridian_core.cockpit_state import (
    CockpitStatus,
    EventSeverity,
    LaneCockpitStatus,
    LaneSummary,
    PrimeCockpitSnapshot,
    ProgressEvent,
    ProgressEventCategory,
    QueuePolicy,
    filter_events,
    lane_summary_counts,
    sort_lanes,
)


def _make_lane(
    lane_id: str,
    status: LaneCockpitStatus = LaneCockpitStatus.IDLE,
    attention: bool = False,
    role: str = "builder",
) -> LaneSummary:
    return LaneSummary(
        lane_id=lane_id,
        role=role,
        status=status,
        last_poll_at="2026-06-02T21:00:00",
        last_commit="abc1234",
        attention=attention,
    )


def _make_event(
    category: ProgressEventCategory = ProgressEventCategory.ROUTINE_PROGRESS,
    severity: EventSeverity = EventSeverity.INFO,
) -> ProgressEvent:
    return ProgressEvent(
        category=category,
        severity=severity,
        timestamp="2026-06-02T21:00:00",
        message="test event",
    )


def _make_snapshot(
    lanes: tuple[LaneSummary, ...] = (),
    events: tuple[ProgressEvent, ...] = (),
    review_gate_count: int = 0,
) -> PrimeCockpitSnapshot:
    return PrimeCockpitSnapshot(
        project="Meridian",
        bearing="V1 Bifrost",
        risk_tier="low",
        prime_status=CockpitStatus.ONLINE,
        queue_policy=QueuePolicy.ON,
        lanes=lanes,
        progress_events=events,
        review_gate_count=review_gate_count,
    )


class TestSortLanes:
    def test_attention_lanes_sort_first(self) -> None:
        no_attn = _make_lane("b1", LaneCockpitStatus.IDLE, attention=False)
        with_attn = _make_lane("b2", LaneCockpitStatus.IDLE, attention=True)
        result = sort_lanes([no_attn, with_attn])
        assert result[0].lane_id == "b2"

    def test_running_before_polling_before_idle_before_offline(self) -> None:
        offline = _make_lane("off", LaneCockpitStatus.OFFLINE)
        idle = _make_lane("idle", LaneCockpitStatus.IDLE)
        polling = _make_lane("poll", LaneCockpitStatus.POLLING)
        running = _make_lane("run", LaneCockpitStatus.RUNNING)
        result = sort_lanes([offline, idle, polling, running])
        assert [lane.lane_id for lane in result] == ["run", "poll", "idle", "off"]

    def test_attention_overrides_status_order(self) -> None:
        offline_attn = _make_lane("off-attn", LaneCockpitStatus.OFFLINE, attention=True)
        running_no_attn = _make_lane("run-no", LaneCockpitStatus.RUNNING, attention=False)
        result = sort_lanes([running_no_attn, offline_attn])
        assert result[0].lane_id == "off-attn"

    def test_blocked_after_idle_before_stale(self) -> None:
        stale = _make_lane("s", LaneCockpitStatus.STALE)
        blocked = _make_lane("b", LaneCockpitStatus.BLOCKED)
        idle = _make_lane("i", LaneCockpitStatus.IDLE)
        result = sort_lanes([stale, blocked, idle])
        assert [lane.lane_id for lane in result] == ["i", "b", "s"]

    def test_empty_returns_empty(self) -> None:
        assert sort_lanes([]) == []

    def test_returns_new_list_not_original(self) -> None:
        lanes = [_make_lane("b1"), _make_lane("b2")]
        result = sort_lanes(lanes)
        assert result is not lanes

    def test_attention_ties_broken_by_status(self) -> None:
        a_running = _make_lane("a-run", LaneCockpitStatus.RUNNING, attention=True)
        a_offline = _make_lane("a-off", LaneCockpitStatus.OFFLINE, attention=True)
        result = sort_lanes([a_offline, a_running])
        assert result[0].lane_id == "a-run"


class TestFilterEvents:
    def test_filter_by_category(self) -> None:
        e1 = _make_event(category=ProgressEventCategory.BLOCKER)
        e2 = _make_event(category=ProgressEventCategory.COMPLETION)
        snapshot = _make_snapshot(events=(e1, e2))
        result = filter_events(snapshot, category=ProgressEventCategory.BLOCKER)
        assert len(result) == 1
        assert result[0].category == ProgressEventCategory.BLOCKER

    def test_filter_by_severity(self) -> None:
        e1 = _make_event(severity=EventSeverity.ERROR)
        e2 = _make_event(severity=EventSeverity.INFO)
        snapshot = _make_snapshot(events=(e1, e2))
        result = filter_events(snapshot, severity=EventSeverity.ERROR)
        assert len(result) == 1
        assert result[0].severity == EventSeverity.ERROR

    def test_filter_by_both_category_and_severity(self) -> None:
        e1 = _make_event(ProgressEventCategory.BLOCKER, EventSeverity.ERROR)
        e2 = _make_event(ProgressEventCategory.BLOCKER, EventSeverity.INFO)
        e3 = _make_event(ProgressEventCategory.COMPLETION, EventSeverity.ERROR)
        snapshot = _make_snapshot(events=(e1, e2, e3))
        result = filter_events(snapshot, category=ProgressEventCategory.BLOCKER, severity=EventSeverity.ERROR)
        assert len(result) == 1
        assert result[0] is e1

    def test_no_filter_returns_all(self) -> None:
        snapshot = _make_snapshot(events=(_make_event(), _make_event(ProgressEventCategory.COMPLETION)))
        assert len(filter_events(snapshot)) == 2

    def test_filter_does_not_mutate_snapshot(self) -> None:
        e1 = _make_event(category=ProgressEventCategory.BLOCKER)
        e2 = _make_event(category=ProgressEventCategory.COMPLETION)
        snapshot = _make_snapshot(events=(e1, e2))
        filter_events(snapshot, category=ProgressEventCategory.BLOCKER)
        assert len(snapshot.progress_events) == 2

    def test_filter_returns_empty_when_no_match(self) -> None:
        snapshot = _make_snapshot(events=(_make_event(ProgressEventCategory.COMPLETION),))
        result = filter_events(snapshot, category=ProgressEventCategory.BLOCKER)
        assert result == []

    def test_filter_on_empty_snapshot_returns_empty(self) -> None:
        snapshot = _make_snapshot()
        assert filter_events(snapshot, category=ProgressEventCategory.COMPLETION) == []


class TestLaneSummaryCounts:
    def test_empty_snapshot_returns_zeros(self) -> None:
        snapshot = _make_snapshot()
        assert lane_summary_counts(snapshot) == {"total": 0, "attention": 0, "blocked": 0, "stale": 0}

    def test_total_count(self) -> None:
        snapshot = _make_snapshot(lanes=(_make_lane("b1"), _make_lane("b2"), _make_lane("b3")))
        assert lane_summary_counts(snapshot)["total"] == 3

    def test_attention_count(self) -> None:
        snapshot = _make_snapshot(lanes=(
            _make_lane("b1", attention=True),
            _make_lane("b2", attention=False),
            _make_lane("b3", attention=True),
        ))
        assert lane_summary_counts(snapshot)["attention"] == 2

    def test_blocked_count(self) -> None:
        snapshot = _make_snapshot(lanes=(
            _make_lane("b1", LaneCockpitStatus.BLOCKED),
            _make_lane("b2", LaneCockpitStatus.RUNNING),
            _make_lane("b3", LaneCockpitStatus.BLOCKED),
        ))
        assert lane_summary_counts(snapshot)["blocked"] == 2

    def test_stale_count(self) -> None:
        snapshot = _make_snapshot(lanes=(
            _make_lane("b1", LaneCockpitStatus.STALE),
            _make_lane("b2", LaneCockpitStatus.IDLE),
        ))
        assert lane_summary_counts(snapshot)["stale"] == 1

    def test_counts_are_independent(self) -> None:
        snapshot = _make_snapshot(lanes=(
            _make_lane("b1", LaneCockpitStatus.BLOCKED, attention=True),
            _make_lane("b2", LaneCockpitStatus.STALE, attention=True),
            _make_lane("b3", LaneCockpitStatus.RUNNING, attention=False),
        ))
        counts = lane_summary_counts(snapshot)
        assert counts["total"] == 3
        assert counts["attention"] == 2
        assert counts["blocked"] == 1
        assert counts["stale"] == 1


class TestImmutability:
    def test_lane_summary_is_frozen(self) -> None:
        lane = _make_lane("b1")
        with pytest.raises(Exception):
            lane.attention = True  # type: ignore[misc]

    def test_progress_event_is_frozen(self) -> None:
        event = _make_event()
        with pytest.raises(Exception):
            event.message = "tampered"  # type: ignore[misc]

    def test_snapshot_is_frozen(self) -> None:
        snapshot = _make_snapshot()
        with pytest.raises(Exception):
            snapshot.review_gate_count = 99  # type: ignore[misc]

    def test_snapshot_lanes_is_tuple(self) -> None:
        snapshot = _make_snapshot(lanes=(_make_lane("b1"),))
        assert isinstance(snapshot.lanes, tuple)

    def test_snapshot_events_is_tuple(self) -> None:
        snapshot = _make_snapshot(events=(_make_event(),))
        assert isinstance(snapshot.progress_events, tuple)

    def test_list_lanes_converted_to_tuple(self) -> None:
        lanes_list = [_make_lane("b1"), _make_lane("b2")]
        snapshot = PrimeCockpitSnapshot(
            project="Test",
            bearing="V1",
            risk_tier="low",
            prime_status=CockpitStatus.ONLINE,
            queue_policy=QueuePolicy.ON,
            lanes=lanes_list,  # type: ignore[arg-type]
            progress_events=(),
            review_gate_count=0,
        )
        assert isinstance(snapshot.lanes, tuple)
        assert len(snapshot.lanes) == 2
        assert snapshot.lanes[0].lane_id == "b1"

    def test_list_progress_events_converted_to_tuple(self) -> None:
        events_list = [_make_event(ProgressEventCategory.ROUTINE_PROGRESS), _make_event(ProgressEventCategory.BLOCKER)]
        snapshot = PrimeCockpitSnapshot(
            project="Test",
            bearing="V1",
            risk_tier="low",
            prime_status=CockpitStatus.ONLINE,
            queue_policy=QueuePolicy.ON,
            lanes=(),
            progress_events=events_list,  # type: ignore[arg-type]
            review_gate_count=0,
        )
        assert isinstance(snapshot.progress_events, tuple)
        assert len(snapshot.progress_events) == 2
        assert snapshot.progress_events[0].category == ProgressEventCategory.ROUTINE_PROGRESS

    def test_mutating_source_lanes_list_does_not_affect_snapshot(self) -> None:
        lanes_list = [_make_lane("b1")]
        snapshot = PrimeCockpitSnapshot(
            project="Test",
            bearing="V1",
            risk_tier="low",
            prime_status=CockpitStatus.ONLINE,
            queue_policy=QueuePolicy.ON,
            lanes=lanes_list,  # type: ignore[arg-type]
            progress_events=(),
            review_gate_count=0,
        )
        original_len = len(snapshot.lanes)
        lanes_list.append(_make_lane("b2"))
        assert len(snapshot.lanes) == original_len
        assert len(lanes_list) == original_len + 1

    def test_mutating_source_events_list_does_not_affect_snapshot(self) -> None:
        events_list = [_make_event(ProgressEventCategory.ROUTINE_PROGRESS)]
        snapshot = PrimeCockpitSnapshot(
            project="Test",
            bearing="V1",
            risk_tier="low",
            prime_status=CockpitStatus.ONLINE,
            queue_policy=QueuePolicy.ON,
            lanes=(),
            progress_events=events_list,  # type: ignore[arg-type]
            review_gate_count=0,
        )
        original_len = len(snapshot.progress_events)
        events_list.append(_make_event(ProgressEventCategory.BLOCKER))
        assert len(snapshot.progress_events) == original_len
        assert len(events_list) == original_len + 1
