"""Tests for the Bifrost cockpit static HTML renderer."""

from __future__ import annotations

import pytest

from bifrost.cockpit import (
    CockpitViewModel,
    InstrumentBand,
    LaneRow,
    ProgressEvent,
    render_cockpit_html,
    sample_cockpit_view_model,
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


def test_render_nav_harness():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Harness" in doc


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
