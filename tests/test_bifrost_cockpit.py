"""Tests for the Bifrost cockpit static HTML renderer."""

from __future__ import annotations

import pytest

from bifrost.cockpit import (
    CockpitViewModel,
    HarnessCard,
    InstrumentBand,
    LaneRow,
    ProgressEvent,
    ProjectCard,
    ProofGateStatus,
    ProofStateView,
    SessionLifecycleItem,
    SessionLifecycleView,
    VoiceIOState,
    _render_proof_state,
    _e,
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
    assert vm.bearing == "Prime command surface"


def test_sample_view_model_has_five_lanes():
    vm = sample_cockpit_view_model()
    assert len(vm.lanes) >= 5


def test_sample_view_model_lanes_are_project_named():
    vm = sample_cockpit_view_model()
    names = {lane.name for lane in vm.lanes}
    for expected in ("Cockpit UI", "Preview Shell", "Voice Layer"):
        assert expected in names


def test_sample_view_model_has_project_cards():
    vm = sample_cockpit_view_model()
    assert len(vm.projects) >= 3
    assert vm.projects[0].sessions


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


# ── Top navigation removal ───────────────────────────────────────────────────


def test_render_has_no_permanent_top_navigation():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "cockpit-nav" not in doc
    for label in ("Settings", "Reset", "Close", "Cross Check", "Backlog", "Skills"):
        assert label not in doc



# ── Prime panel ─────────────────────────────────────────────────────────────


def test_render_prime_panel_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "prime-panel" in doc


def test_render_no_orchestrator_queue_tab():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Orchestrator Queue" not in doc


def test_render_no_review_console_tab():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Review Console" not in doc


def test_render_prime_messages():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for msg in vm.prime_messages:
        assert msg in doc


def test_render_no_review_badge_even_when_nonzero():
    vm = sample_cockpit_view_model()
    vm.review_count = 5
    doc = render_cockpit_html(vm)
    assert 'class="review-badge"' not in doc
    assert ">5<" not in doc


def test_render_no_review_badge_when_zero():
    vm = sample_cockpit_view_model()
    vm.review_count = 0
    doc = render_cockpit_html(vm)
    assert 'class="review-badge"' not in doc


def test_render_prime_input_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "prime-prompt" in doc
    assert "Command Bay" in doc
    assert "<textarea" in doc
    assert "Mission Objectives" in doc
    assert 'data-action="voice"' in doc


def test_render_voice_first_states_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "mic armed" in doc
    assert 'voice-listening' in doc or 'class="voice-state voice-listening"' in doc
    assert 'data-action="mute"' in doc
    assert 'aria-label="Voice I/O state"' in doc


def test_render_hud_command_core_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "hud-stage" in doc
    assert "Prime HUD command core" in doc
    assert "PRIMED" in doc
    assert "ONLINE" not in doc


def test_render_hud_command_core_is_quiet():
    doc = render_cockpit_html(sample_cockpit_view_model())

    # Extract just the HUD core section to check for quiet-core violations
    core_start = doc.find('class="hud-command-core"')
    if core_start == -1:
        # No HUD core found, skip the core-specific checks
        core_section = ""
    else:
        # Find the closing tag of the hud-command-core div
        core_end = doc.find("</div>", core_start)
        if core_end != -1:
            core_section = doc[core_start:core_end]
        else:
            core_section = ""

    # These should NOT appear in the core specifically
    core_quiet_labels = (
        "Provider Balance",
        "Prompt Payload",
        "Delegation Map",
        "Claude / OpenAI / DeepSeek",
    )
    for label in core_quiet_labels:
        assert label not in core_section, f"{label} found in HUD core"

    # These class names should not appear in the core
    for class_name in ("delegation-node", "hud-metric", "hud-micro-panel"):
        assert f'class="{class_name}"' not in core_section

    # Provider Balance and Prompt Payload should appear somewhere else in the doc
    assert "Provider Balance" in doc
    assert "Prompt Payload" in doc



# ── Harness dashboard ────────────────────────────────────────────────────────


def test_render_harness_dashboard_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Harness Dashboard" in doc
    assert "on demand" in doc
    assert 'aria-label="Harness Dashboard"' in doc


def test_render_harness_dashboard_consoles():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="harness-console"' in doc
    for expected in (
        "Prime", "Bifrost", "Relay", "Beacon", "Aegis", "Echo", "Atlas",
        "Session Lifecycle", "Workflow", "Federation",
    ):
        assert expected in doc


def test_render_harness_dashboard_scoped_prompts():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Prime scoped prompt" in doc
    assert "Ask Echo about this subsystem only..." in doc
    assert 'class="harness-prompt"' in doc


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


# ── Project strip ────────────────────────────────────────────────────────────


def test_render_project_strip_class_present():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "project-strip" in doc
    assert "lane-strip" not in doc


def test_render_all_sample_projects():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for project in vm.projects:
        assert project.name in doc


def test_render_project_status_attribute():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'data-status="running"' in doc
    assert 'data-status="idle"' in doc
    assert 'data-status="blocked"' in doc


def test_render_project_summary_totals():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    total = len(vm.projects)
    assert f"{total} projects" in doc


def test_render_project_drilldown_sessions():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "project-drilldown" in doc
    assert "session-list" in doc
    assert "Prime command bay" in doc


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


def test_render_progress_surface_is_mission_feed():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Mission Feed" in doc
    assert "Review Console" not in doc


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


def test_render_instrument_version_is_not_visible():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert vm.instrument.version not in doc


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
    vm.projects = []
    doc = render_cockpit_html(vm)
    assert "<script>bad</script>" not in doc
    assert "&lt;script&gt;" in doc


def test_escapes_xss_in_project_card():
    vm = sample_cockpit_view_model()
    vm.projects = [
        ProjectCard(
            '<script>Project</script>',
            '<b>running</b>',
            '<img src=x>',
            [LaneRow('<i>session</i>', "idle", '<em>x</em>')],
        )
    ]
    doc = render_cockpit_html(vm)
    assert "<script>Project</script>" not in doc
    assert "<img src=x>" not in doc
    assert "<i>session</i>" not in doc
    assert "&lt;script&gt;" in doc
    assert "&lt;img" in doc
    assert "&lt;i&gt;" in doc


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
    assert "<img src=x>" not in doc
    assert "<span>cap</span>" not in doc
    assert "&lt;script&gt;" in doc
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
    assert "X1" in doc
    assert "X3" in doc
    assert "TestLane" in doc
    assert "task completed" in doc
    assert "PAUSED" in doc
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


# ── Voice I/O state ───────────────────────────────────────────────────────────


def test_sample_view_model_has_voice_state():
    vm = sample_cockpit_view_model()
    assert isinstance(vm.voice, VoiceIOState)
    assert vm.voice.listening is True
    assert vm.voice.muted is False


def test_voice_listening_state_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(listening=True)
    doc = render_cockpit_html(vm)
    assert "mic armed" in doc
    assert 'voice-listening' in doc or 'class="voice-state voice-listening"' in doc


def test_voice_dictating_state_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(dictating=True)
    doc = render_cockpit_html(vm)
    assert "dictating" in doc
    assert 'voice-dictating' in doc or 'class="voice-state voice-dictating"' in doc


def test_voice_thinking_state_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(thinking=True)
    doc = render_cockpit_html(vm)
    assert "thinking" in doc
    assert 'voice-thinking' in doc or 'class="voice-state voice-thinking"' in doc


def test_voice_speaking_state_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(speaking=True)
    doc = render_cockpit_html(vm)
    assert "speaker active" in doc
    assert 'voice-speaking' in doc or 'class="voice-state voice-speaking"' in doc


def test_voice_blocked_state_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(blocked=True)
    doc = render_cockpit_html(vm)
    assert "voice blocked" in doc
    assert 'voice-blocked' in doc or 'class="voice-state voice-blocked"' in doc


def test_voice_multiple_states_all_render():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(listening=True, thinking=True, speaking=True)
    doc = render_cockpit_html(vm)
    assert "mic armed" in doc
    assert "thinking" in doc
    assert "speaker active" in doc


def test_voice_muted_state_shows_unmute_button():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(muted=True)
    doc = render_cockpit_html(vm)
    assert 'data-action="unmute"' in doc
    assert "Unmute" in doc


def test_voice_not_muted_shows_mute_button():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(muted=False)
    doc = render_cockpit_html(vm)
    assert 'data-action="mute"' in doc
    assert "Mute" in doc


def test_voice_strip_always_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState()
    doc = render_cockpit_html(vm)
    assert 'class="voice-strip"' in doc
    assert 'aria-label="Voice I/O state"' in doc


def test_voice_state_with_no_states_active():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState()
    doc = render_cockpit_html(vm)
    assert 'class="voice-strip"' in doc
    assert 'data-action="mute"' in doc or 'data-action="unmute"' in doc


def test_snapshot_default_voice_state_listening():
    vm = view_model_from_snapshot(_make_snapshot())
    assert isinstance(vm.voice, VoiceIOState)
    assert vm.voice.listening is True
    assert vm.voice.muted is False


def test_voice_no_provider_labels_in_voice_states():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(speaking=True)
    doc = render_cockpit_html(vm)
    for label in ("Claude", "OpenAI", "DeepSeek"):
        assert label not in doc.split("voice-strip")[1].split("</div>")[0] if "voice-strip" in doc else True


# ── Session Lifecycle ───────────────────────────────────────────────────────


def test_sample_view_model_has_session_lifecycle():
    vm = sample_cockpit_view_model()
    assert vm.session_lifecycle is not None
    assert isinstance(vm.session_lifecycle, SessionLifecycleView)


def test_session_lifecycle_sample_has_sessions():
    vm = sample_cockpit_view_model()
    assert len(vm.session_lifecycle.sessions) >= 3


def test_session_lifecycle_renders_with_sample_data():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="session-lifecycle"' in doc
    assert 'aria-label="Session Lifecycle Preview"' in doc


def test_session_lifecycle_shows_session_names():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "Build 5 Bifrost" in doc
    assert "Reviews Codex B" in doc
    assert "Prime Main" in doc


def test_session_lifecycle_shows_all_sessions():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert doc.count('class="session-card') >= 3


def test_session_lifecycle_shows_project_name():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="session-project"' in doc
    assert "Meridian" in doc


def test_session_lifecycle_shows_harness_role():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "[build]" in doc
    assert "[review]" in doc
    assert "[coordinator]" in doc


def test_session_lifecycle_shows_status():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "polling" in doc
    assert "running" in doc


def test_session_lifecycle_shows_health_state():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "healthy" in doc


def test_session_lifecycle_shows_queue_read_label():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="session-queue-read"' in doc


def test_session_lifecycle_shows_cadence_state():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="session-cadence"' in doc
    assert "cleared" in doc


def test_session_lifecycle_shows_proof_state():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="session-proof"' in doc
    assert "executed" in doc


def test_session_lifecycle_shows_active_session():
    vm = sample_cockpit_view_model()
    vm.session_lifecycle.active_session_id = "build-5-bifrost"
    doc = render_cockpit_html(vm)
    assert 'class="session-card session-active' in doc


def test_session_lifecycle_empty_renders_empty():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(sessions=[])
    doc = render_cockpit_html(vm)
    assert 'class="session-lifecycle"' not in doc


def test_session_lifecycle_single_session():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(
        sessions=[
            SessionLifecycleItem(
                session_id="test",
                session_name="Test Session",
                project_name="TestProj",
                harness_role="build",
                status="running",
                health_state="healthy",
            )
        ],
        active_session_id="test",
    )
    doc = render_cockpit_html(vm)
    assert "Test Session" in doc
    assert "TestProj" in doc


def test_session_lifecycle_escapes_names():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(
        sessions=[
            SessionLifecycleItem(
                session_id="<script>",
                session_name="<Test & Name>",
                project_name="<Project>",
                harness_role="build",
                status="running",
                health_state="healthy",
            )
        ]
    )
    doc = render_cockpit_html(vm)
    assert "&lt;script&gt;" in doc
    assert "&lt;Test &amp; Name&gt;" in doc
    assert "&lt;Project&gt;" in doc
    assert "<script>" not in doc


def test_session_lifecycle_escapes_blocker_summary():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(
        sessions=[
            SessionLifecycleItem(
                session_id="test",
                session_name="Test",
                project_name="TestProj",
                harness_role="build",
                status="blocked",
                health_state="healthy",
                blocker_summary="<Alert>System down</Alert>",
            )
        ]
    )
    doc = render_cockpit_html(vm)
    assert "&lt;Alert&gt;" in doc
    assert "<Alert>" not in doc


def test_session_lifecycle_shows_blocker_when_present():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(
        sessions=[
            SessionLifecycleItem(
                session_id="test",
                session_name="Test",
                project_name="TestProj",
                harness_role="build",
                status="blocked",
                health_state="healthy",
                blocker_summary="Waiting for approval",
            )
        ]
    )
    doc = render_cockpit_html(vm)
    assert 'class="session-blocker"' in doc
    assert "Waiting for approval" in doc


def test_session_lifecycle_no_blocker_when_empty():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.session_lifecycle = SessionLifecycleView(
        sessions=[
            SessionLifecycleItem(
                session_id="test",
                session_name="Test",
                project_name="TestProj",
                harness_role="build",
                status="running",
                health_state="healthy",
                blocker_summary="",
            )
        ]
    )
    doc = render_cockpit_html(vm)
    assert 'class="session-blocker"' not in doc


# Proof State Tests

def test_sample_view_model_has_proof_state():
    vm = sample_cockpit_view_model()
    assert vm.proof_state is not None
    assert isinstance(vm.proof_state, ProofStateView)


def test_proof_state_sample_has_gates():
    vm = sample_cockpit_view_model()
    assert len(vm.proof_state.gates) >= 3


def test_proof_state_renders_with_sample_data():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="proof-state"' in doc
    assert 'aria-label="Proof State"' in doc


def test_proof_state_shows_status():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="proof-status"' in doc
    assert 'executed' in doc


def test_proof_state_shows_all_gates():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for gate in vm.proof_state.gates:
        assert _e(gate.gate_name) in doc


def test_proof_state_shows_gate_status():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="gate-item gate-pass"' in doc


def test_proof_state_shows_gate_reasons():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    for gate in vm.proof_state.gates:
        assert _e(gate.reason) in doc


def test_proof_state_shows_findings():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="finding-open"' in doc


def test_proof_state_with_default_status_renders():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView()
    html = _render_proof_state(vm.proof_state)
    assert 'class="proof-state"' in html
    assert 'no_proof' in html


def test_proof_state_single_gate():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView(
        proof_status="verified",
        gates=[
            ProofGateStatus(
                gate_id="test_gate",
                gate_name="Test Gate",
                status="pass",
                reason="Test reason",
            )
        ],
    )
    html = _render_proof_state(vm.proof_state)
    assert 'class="proof-state"' in html
    assert "Test Gate" in html


def test_proof_state_escapes_gate_names():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView(
        proof_status="verified",
        gates=[
            ProofGateStatus(
                gate_id="test",
                gate_name="<script>xss</script>",
                status="pass",
                reason="test",
            )
        ],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_proof_state_escapes_reasons():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView(
        proof_status="verified",
        gates=[
            ProofGateStatus(
                gate_id="test",
                gate_name="Test",
                status="pass",
                reason="<script>alert('xss')</script>",
            )
        ],
    )
    doc = render_cockpit_html(vm)
    # Check that the script tag is properly escaped in the gate-reason
    assert 'class="gate-reason">&lt;script&gt;' in doc
    assert "<script>" not in doc


def test_proof_state_escapes_notes():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView(
        proof_status="executed",
        gates=[],
        notes="<img src=x onerror=alert(1)>",
    )
    doc = render_cockpit_html(vm)
    # Check that the img tag is properly escaped in the notes
    assert 'class="proof-notes">&lt;img' in doc
    assert "<img" not in doc


def test_render_cockpit_includes_proof_state():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="proof-state"' in doc


def test_proof_state_in_cockpit_main_not_core():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    main_section = doc[doc.find('<main class="cockpit-main">'):doc.find('</main>')]
    assert 'class="proof-state"' in main_section
