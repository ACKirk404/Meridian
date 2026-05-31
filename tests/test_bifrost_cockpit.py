"""Tests for the Bifrost cockpit static HTML renderer."""

from __future__ import annotations

import pytest

from bifrost.cockpit import (
    CockpitViewModel,
    HarnessCard,
    InstrumentBand,
    LaneRow,
    ProgressEvent,
    render_cockpit_html,
    sample_cockpit_view_model,
    view_model_from_snapshot,
)
from meridian_core.cockpit_state import (
    CockpitStatus,
    LaneCockpitStatus,
    LaneSummary,
    PrimeCockpitSnapshot,
    ProgressEvent as CoreProgressEvent,
    ProgressEventCategory,
    EventSeverity,
    QueuePolicy,
)


# ── sample_cockpit_view_model ───────────────────────────────────────────────


def test_sample_view_model_has_project_and_bearing():
    vm = sample_cockpit_view_model()
    assert vm.project == "Meridian"
    assert vm.bearing == "V1 Cockpit"


def test_sample_view_model_has_five_lanes():
    vm = sample_cockpit_view_model()
    assert len(vm.lanes) >= 5


def test_sample_view_model_lanes_include_b1_through_b5():
    vm = sample_cockpit_view_model()
    names = {lane.name for lane in vm.lanes}
    for expected in ("B1", "B2", "B3", "B4", "B5"):
        assert expected in names


def test_sample_view_model_has_prime_messages():
    vm = sample_cockpit_view_model()
    assert len(vm.prime_messages) >= 1


def test_sample_view_model_has_progress_events():
    vm = sample_cockpit_view_model()
    assert len(vm.progress_events) >= 1


def test_sample_view_model_has_harness_cards():
    vm = sample_cockpit_view_model()
    assert len(vm.harnesses) >= 10


def test_sample_view_model_instrument_queue_on():
    vm = sample_cockpit_view_model()
    assert vm.instrument.queue_state == "ON"


def test_sample_view_model_instrument_version():
    vm = sample_cockpit_view_model()
    assert vm.instrument.version.startswith("v")


# ── render_cockpit_html — document structure ────────────────────────────────


def test_render_returns_complete_html_document():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "<!DOCTYPE html>" in doc
    assert "<html" in doc
    assert "</html>" in doc
    assert "<head>" in doc
    assert "<body>" in doc


def test_render_includes_charset_meta():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'charset="utf-8"' in doc


def test_render_includes_title_with_project():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "Meridian" in doc
    assert "<title>" in doc


# ── Nav bar ─────────────────────────────────────────────────────────────────


def test_render_nav_settings():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Settings" in doc


def test_render_nav_projects():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Projects" in doc


def test_render_nav_reset():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Reset" in doc


def test_render_nav_close():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Close" in doc


def test_render_nav_cross_check():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Cross Check" in doc


def test_render_nav_backlog():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Backlog" in doc


def test_render_nav_skills():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Skills" in doc


def test_render_nav_balance():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Balance" in doc
    assert 'data-action="balance"' in doc


def test_render_nav_harness():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Harness" in doc


def test_render_nav_hud_title_plate():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "SET" in doc
    assert "HUD" in doc
    assert "hud-title-plate" in doc


# ── Prime panel ─────────────────────────────────────────────────────────────


def test_render_prime_panel_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "prime-panel" in doc


def test_render_orchestrator_queue_tab():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Orchestrator Queue" in doc


def test_render_review_console_tab():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Review Console" in doc


def test_render_prime_messages():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for msg in vm.prime_messages:
        assert msg in doc


def test_render_review_badge_when_nonzero():
    vm = sample_cockpit_view_model()
    vm.review_count = 5
    doc = render_cockpit_html(vm)
    assert 'class="review-badge"' in doc
    assert ">5<" in doc


def test_render_no_review_badge_when_zero():
    vm = sample_cockpit_view_model()
    vm.review_count = 0
    doc = render_cockpit_html(vm)
    assert 'class="review-badge"' not in doc


def test_render_prime_input_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "prime-prompt" in doc


def test_render_hud_command_core_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "hud-stage" in doc
    assert "Prime HUD command core" in doc
    assert "PRIME" in doc
    assert "ONLINE" in doc


def test_render_hud_source_reference_surfaces():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Provider Balance" in doc
    assert "Prompt Payload" in doc
    assert "Voice I/O" in doc
    assert "Delegation Map" in doc


def test_render_hud_lane_nodes():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for lane in vm.lanes:
        assert f"delegation-{lane.status}" in doc
        assert lane.name in doc


def test_render_hud_window_numbers():
    doc = render_cockpit_html(sample_cockpit_view_model())
    for label in ("01", "02", "03", "04", "05"):
        assert label in doc


# ── Harness dashboard ────────────────────────────────────────────────────────


def test_render_harness_dashboard_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Harness Dashboard" in doc
    assert "View only" in doc
    assert 'aria-label="Harness Dashboard"' in doc


def test_render_harness_dashboard_groups_and_cards():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Cognition" in doc
    assert "Knowledge &amp; Memory" in doc
    assert "Coordination / UI" in doc
    for expected in ("Prime", "Bifrost", "Relay", "Beacon", "Aegis", "Compass", "FileMap", "Codex Reviews"):
        assert expected in doc


def test_render_harness_dashboard_planned_placeholders():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Echo" in doc
    assert "Atlas" in doc
    assert 'data-status="planned"' in doc


def test_render_harness_dashboard_capability_chips():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "proof" in doc
    assert "heartbeat" in doc
    assert "review" in doc
    assert 'class="harness-chip"' in doc


def test_render_harness_dashboard_attention_hook():
    vm = sample_cockpit_view_model()
    vm.harnesses = [
        HarnessCard(
            "Relay", "Cognition", "dispatches work", "blocked",
            "integrated", "v1", "now", "blocked by proof", ["dispatch"],
            attention=True,
        )
    ]
    doc = render_cockpit_html(vm)
    assert 'data-status="blocked"' in doc
    assert 'data-attention="true"' in doc


# ── Lane strip ───────────────────────────────────────────────────────────────


def test_render_lane_strip_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "lane-strip" in doc


def test_render_all_sample_lanes():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for lane in vm.lanes:
        assert lane.name in doc


def test_render_lane_status_attribute():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'data-status="running"' in doc
    assert 'data-status="idle"' in doc
    assert 'data-status="blocked"' in doc


def test_render_lane_summary_totals():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    total = len(vm.lanes)
    assert f"{total} tot." in doc


# ── Progress surface ─────────────────────────────────────────────────────────


def test_render_progress_surface_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "progress-surface" in doc


def test_render_progress_events_source():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for ev in vm.progress_events:
        assert ev.source in doc


def test_render_progress_events_summary():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for ev in vm.progress_events:
        assert ev.summary in doc


def test_render_progress_metadata():
    vm = sample_cockpit_view_model()
    vm.progress_events = [
        ProgressEvent(
            "10:00", "Reviews B", "round clear",
            "review result", "warning", "review:B6",
        )
    ]
    doc = render_cockpit_html(vm)
    assert 'data-category="review result"' in doc
    assert 'data-severity="warning"' in doc
    assert "review result" in doc
    assert "warning" in doc
    assert "review:B6" in doc


def test_render_progress_summary_counts():
    vm = sample_cockpit_view_model()
    vm.progress_events = [
        ProgressEvent("10:00", "Aegis", "proof passed", "proof summary", "info"),
        ProgressEvent("10:01", "Aegis", "proof blocked", "proof summary", "error"),
        ProgressEvent("10:02", "Reviews B", "repair routed", "repair routed", "info"),
    ]
    doc = render_cockpit_html(vm)
    assert "info:2" in doc
    assert "error:1" in doc


def test_render_progress_filter_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "(all)" in doc


# ── Instrument band ──────────────────────────────────────────────────────────


def test_render_instrument_band_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "instrument-band" in doc


def test_render_instrument_beacon():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Beacon" in doc


def test_render_instrument_relay():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Relay" in doc


def test_render_instrument_aegis():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Aegis" in doc


def test_render_instrument_compass():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Compass" in doc


def test_render_instrument_queue_state():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert f"Queue {vm.instrument.queue_state}" in doc


def test_render_instrument_version():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert vm.instrument.version in doc


def test_render_instrument_clock():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert vm.instrument.clock in doc


# ── XSS escaping ─────────────────────────────────────────────────────────────


def test_escapes_xss_in_project():
    vm = sample_cockpit_view_model()
    vm.project = '<script>alert("xss")</script>'
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_escapes_xss_in_bearing():
    vm = sample_cockpit_view_model()
    vm.bearing = '<img src=x onerror="alert(1)">'
    doc = render_cockpit_html(vm)
    assert '<img src=x' not in doc
    assert "&lt;img" in doc


def test_escapes_xss_in_prime_messages():
    vm = sample_cockpit_view_model()
    vm.prime_messages = ['<b onclick="evil()">click me</b>']
    doc = render_cockpit_html(vm)
    assert "<b " not in doc
    assert "&lt;b " in doc


def test_escapes_xss_in_lane_name():
    vm = sample_cockpit_view_model()
    vm.lanes = [LaneRow('<script>bad</script>', "idle", "idl")]
    doc = render_cockpit_html(vm)
    assert "<script>bad</script>" not in doc
    assert "&lt;script&gt;" in doc


def test_escapes_xss_in_progress_source():
    vm = sample_cockpit_view_model()
    vm.progress_events = [ProgressEvent("10:00", '<b>evil</b>', "ok")]
    doc = render_cockpit_html(vm)
    assert "<b>evil</b>" not in doc
    assert "&lt;b&gt;" in doc


def test_escapes_xss_in_progress_summary():
    vm = sample_cockpit_view_model()
    vm.progress_events = [ProgressEvent("10:00", "src", '<script>x</script>')]
    doc = render_cockpit_html(vm)
    assert "<script>x</script>" not in doc
    assert "&lt;script&gt;" in doc


def test_escapes_xss_in_progress_metadata():
    vm = sample_cockpit_view_model()
    vm.progress_events = [
        ProgressEvent(
            "10:00", "src", "ok",
            '<script>cat</script>', '<b>bad</b>', '<img src=x>',
        )
    ]
    doc = render_cockpit_html(vm)
    assert "<script>cat</script>" not in doc
    assert "<b>bad</b>" not in doc
    assert "<img src=x>" not in doc
    assert "&lt;script&gt;" in doc
    assert "&lt;b&gt;" in doc
    assert "&lt;img" in doc


def test_escapes_xss_in_harness_dashboard():
    vm = sample_cockpit_view_model()
    vm.harnesses = [
        HarnessCard(
            '<script>Relay</script>', '<b>Group</b>', '<img src=x>',
            '<i>bad</i>', '<u>planned</u>', '<em>v</em>',
            '<strong>now</strong>', '<script>event</script>',
            ['<span>cap</span>'],
        )
    ]
    doc = render_cockpit_html(vm)
    assert "<script>Relay</script>" not in doc
    assert "<b>Group</b>" not in doc
    assert "<img src=x>" not in doc
    assert "<span>cap</span>" not in doc
    assert "&lt;script&gt;" in doc
    assert "&lt;b&gt;" in doc
    assert "&lt;img" in doc
    assert "&lt;span&gt;" in doc


def test_escapes_xss_in_queue_state():
    vm = sample_cockpit_view_model()
    vm.instrument.queue_state = '<b>ON</b>'
    doc = render_cockpit_html(vm)
    assert "<b>ON</b>" not in doc
    assert "&lt;b&gt;" in doc


# ── Custom view model ─────────────────────────────────────────────────────────


def test_custom_view_model_rendered():
    vm = CockpitViewModel(
        project="TestProject",
        bearing="Alpha",
        prime_messages=["Hello from Prime."],
        review_count=2,
        lanes=[
            LaneRow("X1", "running", "run"),
            LaneRow("X2", "idle", "idl"),
            LaneRow("X3", "blocked", "blk"),
            LaneRow("X4", "paused", "pse"),
            LaneRow("X5", "idle", "idl"),
        ],
        progress_events=[
            ProgressEvent("09:00", "TestLane", "task completed"),
        ],
        instrument=InstrumentBand(
            beacon="ok", relay="warn", aegis="ok", compass="ok",
            queue_state="PAUSED", tier=3, version="v0.9", clock="09:01",
        ),
    )
    doc = render_cockpit_html(vm)
    assert "TestProject" in doc
    assert "Alpha" in doc
    assert "Hello from Prime." in doc
    assert 'class="review-badge"' in doc
    assert "X1" in doc
    assert "X3" in doc
    assert "TestLane" in doc
    assert "task completed" in doc
    assert "PAUSED" in doc
    assert "v0.9" in doc
    assert "09:01" in doc


# ── view_model_from_snapshot ──────────────────────────────────────────────────


def _make_snapshot(
    *,
    project: str = "TestProject",
    bearing: str = "Alpha",
    risk_tier: str = "2",
    prime_status: CockpitStatus = CockpitStatus.ONLINE,
    queue_policy: QueuePolicy = QueuePolicy.ON,
    lanes: tuple = (),
    progress_events: tuple = (),
    review_gate_count: int = 0,
) -> PrimeCockpitSnapshot:
    return PrimeCockpitSnapshot(
        project=project,
        bearing=bearing,
        risk_tier=risk_tier,
        prime_status=prime_status,
        queue_policy=queue_policy,
        lanes=lanes,
        progress_events=progress_events,
        review_gate_count=review_gate_count,
    )


def test_snapshot_maps_project_and_bearing():
    vm = view_model_from_snapshot(_make_snapshot(project="Meridian", bearing="V1"))
    assert vm.project == "Meridian"
    assert vm.bearing == "V1"


def test_snapshot_maps_review_gate_count():
    vm = view_model_from_snapshot(_make_snapshot(review_gate_count=4))
    assert vm.review_count == 4


def test_snapshot_maps_lanes():
    lanes = (
        LaneSummary("B1", "build", LaneCockpitStatus.RUNNING, "10:00", "abc", False),
        LaneSummary("B2", "review", LaneCockpitStatus.IDLE, "10:01", "def", False),
        LaneSummary("B3", "codex", LaneCockpitStatus.BLOCKED, "10:02", "ghi", True),
    )
    vm = view_model_from_snapshot(_make_snapshot(lanes=lanes))
    assert len(vm.lanes) == 3
    assert vm.lanes[0].name == "B1"
    assert vm.lanes[1].name == "B2"
    assert vm.lanes[2].name == "B3"


def test_snapshot_lane_status_running():
    lane = LaneSummary("B1", "build", LaneCockpitStatus.RUNNING, "10:00", "abc", False)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].status == "running"


def test_snapshot_lane_status_polling_maps_to_running():
    lane = LaneSummary("B1", "build", LaneCockpitStatus.POLLING, "10:00", "abc", False)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].status == "running"


def test_snapshot_lane_status_idle():
    lane = LaneSummary("B2", "build", LaneCockpitStatus.IDLE, "10:00", "abc", False)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].status == "idle"


def test_snapshot_lane_status_blocked():
    lane = LaneSummary("B3", "build", LaneCockpitStatus.BLOCKED, "10:00", "abc", True)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].status == "blocked"


def test_snapshot_lane_status_stale_maps_to_paused():
    lane = LaneSummary("B4", "build", LaneCockpitStatus.STALE, "10:00", "abc", False)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].status == "paused"


def test_snapshot_lane_label_is_first_three_chars():
    lane = LaneSummary("Build5", "build", LaneCockpitStatus.IDLE, "10:00", "abc", False)
    vm = view_model_from_snapshot(_make_snapshot(lanes=(lane,)))
    assert vm.lanes[0].label == "BUI"


def test_snapshot_maps_progress_events():
    events = (
        CoreProgressEvent(ProgressEventCategory.COMPLETION, EventSeverity.INFO, "14:00", "task done"),
        CoreProgressEvent(ProgressEventCategory.BLOCKER, EventSeverity.ERROR, "14:01", "lane blocked"),
    )
    vm = view_model_from_snapshot(_make_snapshot(progress_events=events))
    assert len(vm.progress_events) == 2
    assert vm.progress_events[0].timestamp == "14:00"
    assert vm.progress_events[0].source == "completion"
    assert vm.progress_events[0].summary == "task done"
    assert vm.progress_events[0].category == "completion"
    assert vm.progress_events[0].severity == "info"
    assert vm.progress_events[1].source == "blocker"
    assert vm.progress_events[1].category == "blocker"
    assert vm.progress_events[1].severity == "error"


def test_snapshot_instrument_queue_state_on():
    vm = view_model_from_snapshot(_make_snapshot(queue_policy=QueuePolicy.ON))
    assert vm.instrument.queue_state == "ON"


def test_snapshot_instrument_queue_state_paused():
    vm = view_model_from_snapshot(_make_snapshot(queue_policy=QueuePolicy.PAUSED))
    assert vm.instrument.queue_state == "PAUSED"


def test_snapshot_instrument_tier_from_risk_tier():
    vm = view_model_from_snapshot(_make_snapshot(risk_tier="3"))
    assert vm.instrument.tier == 3


def test_snapshot_instrument_tier_defaults_to_1_on_bad_value():
    vm = view_model_from_snapshot(_make_snapshot(risk_tier="unknown"))
    assert vm.instrument.tier == 1


def test_snapshot_prime_status_online_maps_beacon_ok():
    vm = view_model_from_snapshot(_make_snapshot(prime_status=CockpitStatus.ONLINE))
    assert vm.instrument.beacon == "ok"


def test_snapshot_prime_status_blocked_maps_beacon_error():
    vm = view_model_from_snapshot(_make_snapshot(prime_status=CockpitStatus.BLOCKED))
    assert vm.instrument.beacon == "error"


def test_snapshot_prime_status_degraded_maps_beacon_warn():
    vm = view_model_from_snapshot(_make_snapshot(prime_status=CockpitStatus.DEGRADED))
    assert vm.instrument.beacon == "warn"


def test_snapshot_relay_aegis_compass_default_ok():
    vm = view_model_from_snapshot(_make_snapshot())
    assert vm.instrument.relay == "ok"
    assert vm.instrument.aegis == "ok"
    assert vm.instrument.compass == "ok"


def test_snapshot_instrument_clock_placeholder():
    vm = view_model_from_snapshot(_make_snapshot())
    assert vm.instrument.clock == "--:--"


def test_snapshot_result_is_renderable():
    lane = LaneSummary("B1", "build", LaneCockpitStatus.RUNNING, "10:00", "abc", False)
    event = CoreProgressEvent(ProgressEventCategory.ROUTINE_PROGRESS, EventSeverity.INFO, "10:00", "all good")
    vm = view_model_from_snapshot(_make_snapshot(
        project="Meridian", bearing="V1", lanes=(lane,), progress_events=(event,),
    ))
    doc = render_cockpit_html(vm)
    assert "Meridian" in doc
    assert "B1" in doc
    assert "all good" in doc
