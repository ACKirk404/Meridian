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
    return {"ok": "GO", "warn": "CHECK", "error": "NO GO"}.get(status, "CHECK")


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
    category: str = "routine progress"
    severity: str = "info"
    drilldown_ref: str = ""


@dataclass
class HarnessCard:
    name: str
    family: str
    role: str
    status: str
    maturity: str
    version: str
    heartbeat: str
    recent_event: str
    capabilities: list[str] = field(default_factory=list)
    attention: bool = False


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
    harnesses: list[HarnessCard] = field(default_factory=list)
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
            ProgressEvent(
                "13:32", "Build 5", "V1 cockpit scaffold committed",
                "completion", "info", "commit:d13f1d1",
            ),
            ProgressEvent(
                "13:09", "Reviews B", "a412e90 PASS; Round B3 complete",
                "review result", "info", "review:B3",
            ),
            ProgressEvent(
                "12:48", "Aegis", "proof 47/47; no gaps",
                "proof summary", "info", "aegis:proof",
            ),
        ],
        harnesses=[
            HarnessCard(
                "Prime", "Cognition", "Local orchestrator and decision engine",
                "online", "integrated", "v1.0", "now", "bearing: V1 cockpit",
                ["plan", "prioritize", "coordinate"],
            ),
            HarnessCard(
                "Bifrost", "Coordination / UI", "Cockpit and user visibility surface",
                "online", "domain slice", "v1.0", "now", "rendering static cockpit",
                ["cockpit", "dashboard", "review console"],
            ),
            HarnessCard(
                "Relay", "Cognition", "Dispatches model work through adapter lanes",
                "stable", "integrated", "v0.8", "1m", "provider-neutral dispatch ready",
                ["route", "dispatch", "budget"],
            ),
            HarnessCard(
                "Beacon", "Coordination / UI", "Aggregates harness liveness and freshness",
                "stable", "integrated", "v0.6", "1m", "all known lanes fresh",
                ["heartbeat", "freshness", "stale checks"],
            ),
            HarnessCard(
                "Aegis", "Cognition", "Proof gates and review evidence",
                "busy", "integrated", "v0.5", "2m", "tier gates available",
                ["proof", "validate", "block"],
            ),
            HarnessCard(
                "Compass", "Coordination / UI", "Mission bearing and objective focus",
                "online", "domain slice", "v0.4", "2m", "bearing: V1 dashboard",
                ["objectives", "priority", "stage"],
            ),
            HarnessCard(
                "FileMap", "Knowledge & Memory", "Canonical important-file registry",
                "stable", "integrated", "v0.5", "3m", "registry in sync",
                ["discover", "register", "required paths"],
            ),
            HarnessCard(
                "Codex Reviews", "Queue / Review", "Independent review and repair routing",
                "online", "integrated", "v0.7", "now", "Round B7 cleared",
                ["review", "findings", "repair routing"],
            ),
            HarnessCard(
                "Echo", "Knowledge & Memory", "Long-term memory injection harness",
                "planned", "planned", "-", "-", "placeholder visible",
                ["memory", "ranking"],
            ),
            HarnessCard(
                "Atlas", "Knowledge & Memory", "Retrieval and knowledge graph harness",
                "planned", "planned", "-", "-", "placeholder visible",
                ["retrieval", "knowledge"],
            ),
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
            category=ev.category.value.replace("_", " "),
            severity=ev.severity.value,
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
        "Cross Check", "Backlog", "Skills", "Balance",
    ]
    buttons = "".join(
        f'<button class="nav-btn" type="button" data-action="{_e(label.lower().replace(" ", "-"))}">{label}</button>'
        for label in nav_labels
    )
    return (
        '<nav class="cockpit-nav">'
        '<div class="brand-block">'
        '<span class="brand-kicker">MERIDIAN</span>'
        '<strong>Prime Cockpit</strong>'
        '<span>Your AI Command Center</span>'
        "</div>"
        '<div class="nav-buttons">'
        f"{buttons}"
        '<button class="nav-btn nav-harness" type="button" data-action="harness">'
        'Harness <span class="harness-dot">ON</span>'
        "</button>"
        "</div>"
        "</nav>"
    )


def _render_prime_panel(vm: CockpitViewModel) -> str:
    header = (
        '<div class="prime-header">'
        "<div>"
        f"<h1>{_e(vm.project)}</h1>"
        f'<span class="sr-only cockpit-bearing">{_e(vm.bearing)}</span>'
        "</div>"
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
        f'<p class="prime-msg"><span class="msg-source">Prime</span>{_e(m)}</p>'
        for m in vm.prime_messages
    )

    active_lanes = sum(1 for lane in vm.lanes if lane.status == "running")
    blocked_lanes = sum(1 for lane in vm.lanes if lane.status in ("blocked", "paused"))
    lane_nodes = "".join(
        f'<span class="delegation-node delegation-{_e(lane.status)}">'
        f"{_e(lane.name)}"
        "</span>"
        for lane in vm.lanes
    )
    hud_core = (
        '<div class="hud-stage" aria-label="Prime HUD command core">'
        '<div class="hud-left-stack">'
        '<div class="hud-micro-panel"><span>Queue</span>'
        f'<em>{_e(active_lanes)} active / {len(vm.lanes)} lanes</em></div>'
        '<div class="hud-micro-panel"><span>Proof</span>'
        f'<em>{_e(vm.review_count)} review gates</em></div>'
        '<div class="hud-micro-panel"><span>Payload</span>'
        '<em>(under 1k) stable</em></div>'
        "</div>"
        '<div class="hud-core">'
        '<div class="hud-ring hud-ring-outer"></div>'
        '<div class="hud-ring hud-ring-mid"></div>'
        '<div class="hud-ring hud-ring-inner"></div>'
        '<div class="hud-orb"><span>PRIME</span><strong>ONLINE</strong></div>'
        '<span class="hud-marker hud-marker-a">A</span>'
        '<span class="hud-marker hud-marker-b">B</span>'
        '<span class="hud-marker hud-marker-c">C</span>'
        '<span class="hud-marker hud-marker-h">H</span>'
        "</div>"
        '<div class="hud-right-stack">'
        '<div class="hud-metric"><span>Provider Balance</span><strong>Claude / OpenAI / DeepSeek</strong><em>routing visible</em></div>'
        '<div class="hud-metric"><span>Prompt Payload</span><strong>(under 1k)</strong><em>growth flat</em></div>'
        '<div class="hud-metric"><span>Voice I/O</span><strong>mic + speaker</strong><em>wake audio armed</em></div>'
        '<div class="hud-metric"><span>Attention</span>'
        f'<strong>{_e(blocked_lanes)} lanes</strong><em>need review</em></div>'
        "</div>"
        '<div class="delegation-map" aria-label="Delegation Map">'
        '<span class="prime-node">Prime</span>'
        f'<div class="delegation-nodes">{lane_nodes}</div>'
        "</div>"
        "</div>"
    )

    return (
        '<section class="prime-panel">'
        f"{header}"
        '<div class="wake-line">'
        "<span>Relay GO</span><span>Bifrost GO</span>"
        "<span>Beacon GO</span><span>Aegis GO</span>"
        "</div>"
        f"{hud_core}"
        f"{tabs}"
        '<div class="prime-input" aria-label="Prime command prompt">'
        '<div class="prompt-head"><span>Prime Command Bay</span><em>voice + text armed</em></div>'
        '<textarea placeholder="&gt; Tell Prime what to build, approve, reroute, or inspect..." class="prime-prompt"></textarea>'
        '<div class="prompt-actions">'
        '<button type="button" class="prompt-btn" data-action="voice">Voice</button>'
        '<button type="button" class="prompt-btn" data-action="send">Send</button>'
        '<button type="button" class="prompt-btn prompt-primary" data-action="mission-objectives">Mission Objectives</button>'
        "</div>"
        "</div>"
        f'<div class="prime-messages">{messages}</div>'
        "</section>"
    )

def _render_harness_dashboard(harnesses: list[HarnessCard]) -> str:
    grouped: dict[str, list[HarnessCard]] = {}
    for harness in harnesses:
        grouped.setdefault(harness.family, []).append(harness)

    sections = []
    for family, cards in grouped.items():
        card_html = "".join(
            f'<article class="harness-card" data-status="{_e(card.status)}" '
            f'data-attention="{_e(str(card.attention).lower())}">'
            '<div class="harness-card-head">'
            f'<span class="harness-name">{_e(card.name)}</span>'
            f'<span class="harness-status">{_e(card.status)}</span>'
            "</div>"
            f'<p class="harness-role">{_e(card.role)}</p>'
            '<div class="harness-meta">'
            f'<span>{_e(card.maturity)}</span>'
            f'<span>{_e(card.version)}</span>'
            f'<span>{_e(card.heartbeat)}</span>'
            "</div>"
            f'<p class="harness-event">{_e(card.recent_event)}</p>'
            '<div class="harness-capabilities">'
            + "".join(
                f'<span class="harness-chip">{_e(cap)}</span>'
                for cap in card.capabilities
            )
            + "</div>"
            + "</article>"
            for card in cards
        )
        sections.append(
            '<section class="harness-group">'
            f'<h3>{_e(family)}</h3>'
            f'<div class="harness-cards">{card_html}</div>'
            "</section>"
        )

    return (
        '<section class="harness-dashboard" aria-label="Harness Dashboard">'
        '<div class="harness-dashboard-header">'
        '<h2>Harness Dashboard</h2>'
        '<span class="harness-dashboard-mode">View only</span>'
        "</div>"
        + "".join(sections)
        + "</section>"
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
        '<div class="rail-title">Build Lanes</div>'
        f'<div class="lane-rows">{rows}</div>'
        f'<div class="lane-summary">{total} tot. / {attn} attn</div>'
        "</aside>"
    )


def _render_progress_surface(events: list[ProgressEvent]) -> str:
    severity_counts: dict[str, int] = {}
    for ev in events:
        severity_counts[ev.severity] = severity_counts.get(ev.severity, 0) + 1

    counts = "".join(
        f'<span class="progress-count progress-count-{_e(severity)}">'
        f"{_e(severity)}:{_e(count)}"
        "</span>"
        for severity, count in sorted(severity_counts.items())
    ) or '<span class="progress-count">none:0</span>'

    cards = "".join(
        f'<div class="progress-card progress-{_e(ev.severity)}" '
        f'data-category="{_e(ev.category)}" data-severity="{_e(ev.severity)}">'
        '<div class="progress-card-meta">'
        f'<span class="progress-ts">{_e(ev.timestamp)}</span>'
        f'<span class="progress-source">{_e(ev.source)}</span>'
        f'<span class="progress-category">{_e(ev.category)}</span>'
        f'<span class="progress-severity">{_e(ev.severity)}</span>'
        "</div>"
        f'<p class="progress-summary">{_e(ev.summary)}</p>'
        + (
            f'<span class="progress-drilldown">{_e(ev.drilldown_ref)}</span>'
            if ev.drilldown_ref
            else ""
        )
        + "</div>"
        for ev in events
    )
    return (
        '<aside class="progress-surface">'
        '<div class="progress-header">'
        'Review Console <span class="progress-filter">(all)</span>'
        f'<div class="progress-counts">{counts}</div>'
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
        '<span class="instr-title">Systems</span>'
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
    harness_dashboard = _render_harness_dashboard(vm.harnesses)
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
        '<div class="cockpit-shell">\n'
        f"{nav}\n"
        '<div class="cockpit-content">\n'
        f"{lanes}\n"
        '<main class="cockpit-main">\n'
        f"{prime}\n"
        f"{harness_dashboard}\n"
        "</main>\n"
        f"{progress}\n"
        "</div>\n"
        f"{instrument}\n"
        "</div>\n"
        "</body>\n"
        "</html>"
    )
