"""Static HTML renderer for the Bifrost cockpit surface.

Dependency-free rendering path: only Python standard library. Returns a complete,
self-contained HTML document from a CockpitViewModel. All user-visible strings
are escaped.

view_model_from_snapshot() maps meridian_core.PrimeCockpitSnapshot → CockpitViewModel
and is the only place that imports from meridian_core.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meridian_core.cockpit_state import PrimeCockpitSnapshot

_CSS_PATH = Path(__file__).parent / "static" / "cockpit.css"


def _load_css() -> str:
    try:
        return _CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _e(s: object) -> str:
    return html.escape(str(s))


def _status_glyph(status: str) -> str:
    return {"ok": "✓", "warn": "⚠", "error": "✗"}.get(status, "?")


@dataclass
class LaneRow:
    name: str
    status: str   # "running" | "idle" | "blocked" | "paused"
    label: str    # 3-char display abbreviation for the lane strip


@dataclass
class ProgressEvent:
    timestamp: str
    source: str
    summary: str


@dataclass
class InstrumentBand:
    beacon: str       # "ok" | "warn" | "error"
    relay: str        # "ok" | "warn" | "error"
    aegis: str        # "ok" | "warn" | "error"
    compass: str      # "ok" | "warn" | "error"
    queue_state: str  # "ON" | "OFF" | "PAUSED" | "DEGRADED" | "BLOCKED"
    tier: int
    version: str
    clock: str


@dataclass
class CockpitViewModel:
    project: str
    bearing: str
    prime_messages: list[str] = field(default_factory=list)
    review_count: int = 0
    lanes: list[LaneRow] = field(default_factory=list)
    progress_events: list[ProgressEvent] = field(default_factory=list)
    instrument: InstrumentBand = field(
        default_factory=lambda: InstrumentBand(
            beacon="ok", relay="ok", aegis="ok", compass="ok",
            queue_state="ON", tier=1, version="v1.0", clock="--:--",
        )
    )


def sample_cockpit_view_model() -> CockpitViewModel:
    """Return deterministic sample data for previewing the cockpit."""
    return CockpitViewModel(
        project="Meridian",
        bearing="V1 Cockpit",
        prime_messages=[
            "Good morning, Scott.",
            "Three items in the Review Console; one needs your judgment.",
        ],
        review_count=3,
        lanes=[
            LaneRow("B1", "running", "run"),
            LaneRow("B2", "idle",    "pol"),
            LaneRow("B3", "blocked", "blk"),
            LaneRow("B4", "idle",    "idl"),
            LaneRow("B5", "running", "run"),
        ],
        progress_events=[
            ProgressEvent("13:32", "Build 5",   "V1 cockpit scaffold committed"),
            ProgressEvent("13:09", "Reviews B",  "a412e90 PASS; Round B3 complete"),
            ProgressEvent("12:48", "Aegis",      "proof 47/47; no gaps"),
        ],
        instrument=InstrumentBand(
            beacon="ok",
            relay="ok",
            aegis="ok",
            compass="ok",
            queue_state="ON",
            tier=2,
            version="v1.0",
            clock="--:--",
        ),
    )


# ── Snapshot → ViewModel mapping ───────────────────────────────────────────


def _prime_status_to_instrument_status(status: object) -> str:
    from meridian_core.cockpit_state import CockpitStatus
    return {
        CockpitStatus.ONLINE: "ok",
        CockpitStatus.THINKING: "ok",
        CockpitStatus.WAITING_ON_SCOTT: "warn",
        CockpitStatus.BLOCKED: "error",
        CockpitStatus.DEGRADED: "warn",
        CockpitStatus.OFFLINE: "error",
    }.get(status, "warn")  # type: ignore[call-overload]


def _lane_cockpit_status_to_display(status: object) -> str:
    from meridian_core.cockpit_state import LaneCockpitStatus
    return {
        LaneCockpitStatus.RUNNING: "running",
        LaneCockpitStatus.POLLING: "running",
        LaneCockpitStatus.IDLE: "idle",
        LaneCockpitStatus.BLOCKED: "blocked",
        LaneCockpitStatus.STALE: "paused",
        LaneCockpitStatus.OFFLINE: "idle",
    }.get(status, "idle")  # type: ignore[call-overload]


def view_model_from_snapshot(snapshot: PrimeCockpitSnapshot) -> CockpitViewModel:
    """Map a PrimeCockpitSnapshot to a CockpitViewModel for rendering.

    Read-only and deterministic. Does not read files, env vars, or prompts.
    """
    from meridian_core.cockpit_state import ProgressEvent as _CoreProgressEvent

    lanes = [
        LaneRow(
            name=lane.lane_id,
            status=_lane_cockpit_status_to_display(lane.status),
            label=lane.lane_id[:3].upper(),
        )
        for lane in snapshot.lanes
    ]

    events = [
        ProgressEvent(
            timestamp=ev.timestamp,
            source=ev.category.value,
            summary=ev.message,
        )
        for ev in snapshot.progress_events
    ]

    instrument_status = _prime_status_to_instrument_status(snapshot.prime_status)

    try:
        tier = int(snapshot.risk_tier)
    except (ValueError, TypeError):
        tier = 1

    instrument = InstrumentBand(
        beacon=instrument_status,
        relay="ok",
        aegis="ok",
        compass="ok",
        queue_state=snapshot.queue_policy.value.upper(),
        tier=tier,
        version="v1.0",
        clock="--:--",
    )

    return CockpitViewModel(
        project=snapshot.project,
        bearing=snapshot.bearing,
        review_count=snapshot.review_gate_count,
        lanes=lanes,
        progress_events=events,
        instrument=instrument,
    )


# ── Private render helpers ──────────────────────────────────────────────────


def _render_nav() -> str:
    nav_labels = [
        "Settings", "Projects", "Reset", "Close",
        "Cross Check", "Backlog", "Skills",
    ]
    buttons = "".join(
        f'<button class="nav-btn">{label}</button>' for label in nav_labels
    )
    return (
        '<nav class="cockpit-nav">'
        '<div class="nav-buttons">'
        f"{buttons}"
        '<button class="nav-btn nav-harness">'
        'Harness <span class="harness-dot">●</span>'
        "</button>"
        "</div>"
        "</nav>"
    )


def _render_prime_panel(vm: CockpitViewModel) -> str:
    header = (
        '<div class="prime-header">'
        f'<span class="prime-project">{_e(vm.project)}</span>'
        '<span class="prime-sep">·</span>'
        f'<span class="prime-bearing">{_e(vm.bearing)}</span>'
        '<span class="prime-sep">·</span>'
        f'<span class="prime-tier">Tier {_e(vm.instrument.tier)}</span>'
        '<span class="prime-sep">·</span>'
        '<span class="prime-status">Prime: online</span>'
        "</div>"
    )

    badge = (
        f'<span class="review-badge">{_e(vm.review_count)}</span>'
        if vm.review_count
        else ""
    )
    tabs = (
        '<div class="prime-tabs">'
        '<button class="tab tab-active">Orchestrator Queue</button>'
        f'<button class="tab">Review Console{badge}</button>'
        "</div>"
    )

    messages = "".join(
        f'<p class="prime-msg">{_e(m)}</p>' for m in vm.prime_messages
    )

    return (
        '<section class="prime-panel">'
        f"{header}"
        f"{tabs}"
        f'<div class="prime-messages">{messages}</div>'
        '<div class="prime-input">'
        '<input type="text" placeholder="&gt; _" class="prime-prompt" />'
        "</div>"
        "</section>"
    )


def _render_lane_strip(lanes: list[LaneRow]) -> str:
    rows = "".join(
        f'<div class="lane-row" data-status="{_e(lane.status)}">'
        f'<span class="lane-name">{_e(lane.name)}</span>'
        f'<span class="lane-label">{_e(lane.label)}</span>'
        "</div>"
        for lane in lanes
    )
    total = len(lanes)
    attn = sum(1 for lane in lanes if lane.status in ("blocked", "paused"))
    return (
        '<aside class="lane-strip">'
        f'<div class="lane-rows">{rows}</div>'
        f'<div class="lane-summary">{total} tot. · {attn} attn</div>'
        "</aside>"
    )


def _render_progress_surface(events: list[ProgressEvent]) -> str:
    cards = "".join(
        '<div class="progress-card">'
        f'<span class="progress-ts">{_e(ev.timestamp)}</span>'
        f'<span class="progress-source">{_e(ev.source)}</span>'
        f'<p class="progress-summary">{_e(ev.summary)}</p>'
        "</div>"
        for ev in events
    )
    return (
        '<aside class="progress-surface">'
        '<div class="progress-header">'
        'Progress <span class="progress-filter">(all) ▾</span>'
        "</div>"
        f'<div class="progress-cards">{cards}</div>'
        "</aside>"
    )


def _render_instrument_band(inst: InstrumentBand) -> str:
    def chip(label: str, status: str) -> str:
        return (
            f'<span class="instr-chip instr-{_e(status)}">'
            f"{_e(label)} {_status_glyph(status)}"
            "</span>"
        )

    return (
        '<footer class="instrument-band">'
        f"{chip('Beacon', inst.beacon)}"
        f"{chip('Relay', inst.relay)}"
        f"{chip('Aegis', inst.aegis)}"
        f"{chip('Compass', inst.compass)}"
        f'<span class="instr-queue">Queue {_e(inst.queue_state)}</span>'
        f'<span class="instr-tier">Tier {_e(inst.tier)}</span>'
        f'<span class="instr-version">{_e(inst.version)}</span>'
        f'<span class="instr-clock">{_e(inst.clock)}</span>'
        "</footer>"
    )


# ── Public API ──────────────────────────────────────────────────────────────


def render_cockpit_html(vm: CockpitViewModel) -> str:
    """Return a complete, self-contained HTML document for the Bifrost cockpit.

    All dynamic content is HTML-escaped. No JavaScript or external dependencies.
    """
    css = _load_css()

    nav = _render_nav()
    prime = _render_prime_panel(vm)
    lanes = _render_lane_strip(vm.lanes)
    progress = _render_progress_surface(vm.progress_events)
    instrument = _render_instrument_band(vm.instrument)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        f"<title>Bifrost Cockpit — {_e(vm.project)}</title>\n"
        f"<style>\n{css}\n</style>\n"
        "</head>\n"
        "<body>\n"
        f"{nav}\n"
        '<div class="cockpit-content">\n'
        f"{prime}\n"
        f"{lanes}\n"
        f"{progress}\n"
        "</div>\n"
        f"{instrument}\n"
        "</body>\n"
        "</html>"
    )
