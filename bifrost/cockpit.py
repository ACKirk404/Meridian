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
class ProjectCard:
    name: str
    status: str
    summary: str
    sessions: list[LaneRow] = field(default_factory=list)


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
class VoiceIOState:
    listening: bool = False
    dictating: bool = False
    thinking: bool = False
    speaking: bool = False
    muted: bool = False
    blocked: bool = False


@dataclass
class ProviderBalanceItem:
    provider_id: str
    display_name: str
    model_name: str
    trust_state: str
    health: str
    context_budget_tokens: int = 0
    prompt_budget_tokens: int = 0
    current_prompt_tokens: int = 0
    prompt_budget_percent: float = 0.0
    prompt_delta_tokens: int = 0
    cost_pressure: str = "none"
    quota_state: str = "unknown"
    notes: str = ""


@dataclass
class ProviderBalanceView:
    providers: list[ProviderBalanceItem] = field(default_factory=list)
    selected_provider: str = ""
    routing_owner: str = "unknown"
    policy_state: str = "ok"


@dataclass
class PromptPayloadView:
    size_label: str = ""
    estimated_tokens: int = 0
    budget_percent: float = 0.0
    delta_tokens: int = 0
    status: str = "flat"
    source: str = ""
    evidence_ref: str = ""


@dataclass
class ProofGateStatus:
    gate_id: str
    gate_name: str
    status: str  # "pass" | "warning" | "block"
    reason: str = ""


@dataclass
class ProofStateView:
    proof_status: str = "no_proof"  # "no_proof" | "queue_read" | "verified" | "executed"
    gates: list[ProofGateStatus] = field(default_factory=list)
    blocker_count: int = 0
    open_findings: int = 0
    waived_count: int = 0
    notes: str = ""


@dataclass
class SessionLifecycleItem:
    session_id: str
    session_name: str
    project_name: str
    harness_role: str
    status: str
    health_state: str
    blocker_summary: str = ""
    last_queue_read_label: str = ""
    review_cadence_state: str = "none"
    proof_state: str = "no_proof"


@dataclass
class SessionLifecycleView:
    sessions: list[SessionLifecycleItem] = field(default_factory=list)
    active_session_id: str = ""


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
class SessionItem:
    session_id: str
    session_name: str
    project_name: str
    status: str  # "live" | "hidden" | "waiting" | "blocked" | "done"


@dataclass
class UserSessionModeView:
    sessions: list[SessionItem] = field(default_factory=list)
    selected_session_id: str = ""
    prompt_text: str = ""
    response_text: str = ""


@dataclass
class SettingsItem:
    setting_id: str
    setting_name: str
    setting_type: str  # "toggle" | "text" | "select" | "range"
    value: str


@dataclass
class SettingsModeView:
    settings: list[SettingsItem] = field(default_factory=list)


@dataclass
class HarnessItem:
    item_id: str
    item_name: str
    item_type: str
    description: str


@dataclass
class HarnessModeView:
    harness_items: list[HarnessItem] = field(default_factory=list)
    search_query: str = ""


@dataclass
class CockpitViewModel:
    project: str
    bearing: str
    prime_messages: list[str] = field(default_factory=list)
    review_count: int = 0
    lanes: list[LaneRow] = field(default_factory=list)
    projects: list[ProjectCard] = field(default_factory=list)
    progress_events: list[ProgressEvent] = field(default_factory=list)
    harnesses: list[HarnessCard] = field(default_factory=list)
    voice: VoiceIOState = field(default_factory=VoiceIOState)
    provider_balance: ProviderBalanceView = field(default_factory=ProviderBalanceView)
    prompt_payload: PromptPayloadView = field(default_factory=PromptPayloadView)
    session_lifecycle: SessionLifecycleView = field(default_factory=SessionLifecycleView)
    proof_state: ProofStateView = field(default_factory=ProofStateView)
    user_session_mode: UserSessionModeView = field(default_factory=UserSessionModeView)
    settings_mode: SettingsModeView = field(default_factory=SettingsModeView)
    harness_mode: HarnessModeView = field(default_factory=HarnessModeView)
    right_panel_active_mode: str = "user_session"  # "user_session" | "settings" | "harness"
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
        bearing="Prime command surface",
        prime_messages=[
            "Command channel open.",
            "Say the panel name and I will bring it forward.",
        ],
        review_count=3,
        voice=VoiceIOState(
            listening=True,
            dictating=False,
            thinking=False,
            speaking=False,
            muted=False,
            blocked=False,
        ),
        provider_balance=ProviderBalanceView(
            providers=[
                ProviderBalanceItem(
                    provider_id="claude",
                    display_name="Claude",
                    model_name="claude-opus-4-7",
                    trust_state="trusted",
                    health="ok",
                    context_budget_tokens=200000,
                    prompt_budget_tokens=4000,
                    current_prompt_tokens=1240,
                    prompt_budget_percent=31.0,
                    prompt_delta_tokens=0,
                    cost_pressure="low",
                    quota_state="available",
                    notes="Primary provider ready",
                ),
                ProviderBalanceItem(
                    provider_id="openai",
                    display_name="OpenAI",
                    model_name="gpt-4-turbo",
                    trust_state="trusted",
                    health="ok",
                    context_budget_tokens=128000,
                    prompt_budget_tokens=3000,
                    current_prompt_tokens=890,
                    prompt_budget_percent=29.7,
                    prompt_delta_tokens=50,
                    cost_pressure="medium",
                    quota_state="available",
                    notes="Secondary provider with minor growth",
                ),
                ProviderBalanceItem(
                    provider_id="deepseek",
                    display_name="DeepSeek",
                    model_name="deepseek-v4-pro",
                    trust_state="candidate",
                    health="degraded",
                    context_budget_tokens=256000,
                    prompt_budget_tokens=5000,
                    current_prompt_tokens=2450,
                    prompt_budget_percent=49.0,
                    prompt_delta_tokens=240,
                    cost_pressure="high",
                    quota_state="limited",
                    notes="Q-mode prompt drag detected",
                ),
            ],
            selected_provider="claude",
            routing_owner="Relay",
            policy_state="warning",
        ),
        prompt_payload=PromptPayloadView(
            size_label="(1.2k)",
            estimated_tokens=1240,
            budget_percent=31.0,
            delta_tokens=0,
            status="flat",
            source="relay",
            evidence_ref="dispatch:latest",
        ),
        lanes=[
            LaneRow("Cockpit UI", "running", "hud"),
            LaneRow("Preview Shell", "idle", "html"),
            LaneRow("Voice Layer", "paused", "vox"),
            LaneRow("Harness Console", "running", "sub"),
            LaneRow("Mission Memory", "idle", "mem"),
        ],
        projects=[
            ProjectCard(
                "Meridian Cockpit",
                "running",
                "Prime command surface, project drill-in, and harness consoles.",
                [
                    LaneRow("Prime command bay", "running", "hud"),
                    LaneRow("Voice affordance pass", "paused", "vox"),
                    LaneRow("Harness focus panels", "running", "sub"),
                ],
            ),
            ProjectCard(
                "Meridian Core",
                "idle",
                "Cockpit state snapshots and lifecycle adapters.",
                [
                    LaneRow("Snapshot mapper", "idle", "map"),
                    LaneRow("Session lifecycle", "idle", "life"),
                ],
            ),
            ProjectCard(
                "Knowledge Fabric",
                "blocked",
                "Echo and Atlas surfaces waiting for runtime wiring.",
                [
                    LaneRow("Echo memory lane", "blocked", "mem"),
                    LaneRow("Atlas retrieval lane", "idle", "kg"),
                ],
            ),
        ],
        progress_events=[
            ProgressEvent(
                "13:32", "Bifrost", "Prime cockpit surface refreshed",
                "completion", "info", "surface:bifrost",
            ),
            ProgressEvent(
                "13:09", "Prime", "Project sessions available on drill-in",
                "mission state", "info", "project:sessions",
            ),
            ProgressEvent(
                "12:48", "Aegis", "Proof lane quiet; no active gate",
                "proof summary", "info", "aegis:proof",
            ),
        ],
        harnesses=[
            HarnessCard(
                "Prime", "Cognition", "Local orchestrator and decision engine",
                "online", "integrated", "command", "now", "voice command scope ready",
                ["plan", "prioritize", "coordinate"],
            ),
            HarnessCard(
                "Bifrost", "Coordination / UI", "Cockpit and user visibility surface",
                "online", "domain slice", "cockpit", "now", "rendering static cockpit",
                ["cockpit", "hud", "panels"],
            ),
            HarnessCard(
                "Relay", "Cognition", "Dispatches model work through adapter lanes",
                "stable", "integrated", "dispatch", "1m", "provider-neutral dispatch ready",
                ["route", "dispatch", "budget"],
            ),
            HarnessCard(
                "Beacon", "Coordination / UI", "Aggregates harness liveness and freshness",
                "stable", "integrated", "liveness", "1m", "all known lanes fresh",
                ["heartbeat", "freshness", "stale checks"],
            ),
            HarnessCard(
                "Aegis", "Cognition", "Proof gates and review evidence",
                "busy", "integrated", "proof", "2m", "gate evidence available",
                ["proof", "validate", "block"],
            ),
            HarnessCard(
                "Compass", "Coordination / UI", "Mission bearing and objective focus",
                "online", "domain slice", "bearing", "2m", "mission bearing ready",
                ["objectives", "priority", "stage"],
            ),
            HarnessCard(
                "FileMap", "Knowledge & Memory", "Canonical important-file registry",
                "stable", "integrated", "registry", "3m", "registry in sync",
                ["discover", "register", "required paths"],
            ),
            HarnessCard(
                "Codex Reviews", "Queue / Review", "Independent review and repair routing",
                "online", "integrated", "review", "now", "review lane quiet",
                ["review", "findings", "repair routing"],
            ),
            HarnessCard(
                "Session Lifecycle", "Runtime", "Session registration and restart posture",
                "stable", "planned", "lifecycle", "now", "session state surface reserved",
                ["register", "restart", "recover"],
            ),
            HarnessCard(
                "Workflow", "Runtime", "Sub-agent and workflow coordination surface",
                "planned", "planned", "sub-agent", "-", "workflow prompt reserved",
                ["sub-agent", "handoff", "sequence"],
            ),
            HarnessCard(
                "Federation", "Runtime", "Future cross-instance Meridian coordination",
                "planned", "planned", "future", "-", "federation panel reserved",
                ["federate", "sync"],
            ),
            HarnessCard(
                "Echo", "Knowledge & Memory", "Long-term memory injection harness",
                "planned", "planned", "memory", "-", "memory-only prompt reserved",
                ["memory", "ranking"],
            ),
            HarnessCard(
                "Atlas", "Knowledge & Memory", "Retrieval and knowledge graph harness",
                "planned", "planned", "retrieval", "-", "retrieval prompt reserved",
                ["retrieval", "knowledge"],
            ),
        ],
        session_lifecycle=SessionLifecycleView(
            sessions=[
                SessionLifecycleItem(
                    session_id="build-5-bifrost",
                    session_name="Build 5 Bifrost",
                    project_name="Meridian",
                    harness_role="build",
                    status="polling",
                    health_state="healthy",
                    blocker_summary="",
                    last_queue_read_label="2m ago",
                    review_cadence_state="cleared",
                    proof_state="executed",
                ),
                SessionLifecycleItem(
                    session_id="reviews-codex-b",
                    session_name="Reviews Codex B",
                    project_name="Meridian",
                    harness_role="review",
                    status="running",
                    health_state="healthy",
                    blocker_summary="",
                    last_queue_read_label="now",
                    review_cadence_state="cleared",
                    proof_state="executed",
                ),
                SessionLifecycleItem(
                    session_id="prime-main",
                    session_name="Prime Main",
                    project_name="Meridian",
                    harness_role="coordinator",
                    status="running",
                    health_state="healthy",
                    blocker_summary="",
                    last_queue_read_label="now",
                    review_cadence_state="cleared",
                    proof_state="executed",
                ),
            ],
            active_session_id="build-5-bifrost",
        ),
        proof_state=ProofStateView(
            proof_status="executed",
            gates=[
                ProofGateStatus(
                    gate_id="unknown_route_class",
                    gate_name="Unknown Route Class",
                    status="pass",
                    reason="route_class declared as direct_api",
                ),
                ProofGateStatus(
                    gate_id="missing_model_id",
                    gate_name="Missing Exact Model ID",
                    status="pass",
                    reason="model_id claude-opus-4-7 is exact/versioned",
                ),
                ProofGateStatus(
                    gate_id="tier3_dual_lane",
                    gate_name="Tier 3 Dual-Lane",
                    status="pass",
                    reason="risk_tier is Tier 2; dual-lane not required",
                ),
            ],
            blocker_count=0,
            open_findings=1,
            waived_count=0,
            notes="One review finding open: performance profiling incomplete for DeepSeek route",
        ),
        user_session_mode=UserSessionModeView(
            sessions=[
                # Meridian project sessions (alphabetically ordered)
                SessionItem(
                    session_id="session-meridian-cockpit",
                    session_name="Cockpit Development",
                    project_name="Meridian",
                    status="live",
                ),
                SessionItem(
                    session_id="session-meridian-core",
                    session_name="Core Integration",
                    project_name="Meridian",
                    status="live",
                ),
                SessionItem(
                    session_id="session-meridian-test",
                    session_name="Test Session",
                    project_name="Meridian",
                    status="waiting",
                ),
                SessionItem(
                    session_id="session-meridian-archive",
                    session_name="Archive Review",
                    project_name="Meridian",
                    status="hidden",
                ),
                # Polaris project sessions (alphabetically ordered)
                SessionItem(
                    session_id="session-polaris-debug",
                    session_name="Debug Sandbox",
                    project_name="Polaris",
                    status="live",
                ),
                SessionItem(
                    session_id="session-polaris-review",
                    session_name="Review Queue",
                    project_name="Polaris",
                    status="waiting",
                ),
                SessionItem(
                    session_id="session-polaris-old",
                    session_name="Old Session",
                    project_name="Polaris",
                    status="hidden",
                ),
            ],
            selected_session_id="session-meridian-cockpit",
            prompt_text="",
            response_text="",
        ),
        settings_mode=SettingsModeView(
            settings=[
                SettingsItem(
                    setting_id="project-focus",
                    setting_name="Project Focus",
                    setting_type="select",
                    value="Meridian",
                ),
                SettingsItem(
                    setting_id="quiet-mode",
                    setting_name="Quiet Mode",
                    setting_type="toggle",
                    value="off",
                ),
                SettingsItem(
                    setting_id="text-size",
                    setting_name="Text Size",
                    setting_type="range",
                    value="14",
                ),
                SettingsItem(
                    setting_id="risk-tier",
                    setting_name="Risk Tier Override",
                    setting_type="select",
                    value="Tier 2",
                ),
            ],
        ),
        harness_mode=HarnessModeView(
            harness_items=[
                HarnessItem(
                    item_id="gate-unknown-route",
                    item_name="Unknown Route Class Gate",
                    item_type="gate",
                    description="Validates route_class is declared",
                ),
                HarnessItem(
                    item_id="gate-missing-model",
                    item_name="Missing Exact Model ID Gate",
                    item_type="gate",
                    description="Validates model_id is versioned",
                ),
                HarnessItem(
                    item_id="finding-perf-profile",
                    item_name="Performance Profiling Finding",
                    item_type="finding",
                    description="DeepSeek route lacks performance baseline",
                ),
                HarnessItem(
                    item_id="waiver-tier-exception",
                    item_name="Tier Override Waiver",
                    item_type="waiver",
                    description="Risk tier override requires Aegis waiver",
                ),
            ],
            search_query="",
        ),
        right_panel_active_mode="user_session",
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
        projects=[
            ProjectCard(
                snapshot.project,
                "running" if lanes else "idle",
                snapshot.bearing,
                lanes,
            )
        ],
        progress_events=events,
        voice=VoiceIOState(listening=True),
        instrument=instrument,
    )


# ── Private render helpers ──────────────────────────────────────────────────


def _render_prime_panel(vm: CockpitViewModel) -> str:
    header = (
        '<div class="prime-header">'
        "<div>"
        f"<h1>{_e(vm.project)}</h1>"
        f'<span class="sr-only cockpit-bearing">{_e(vm.bearing)}</span>'
        "</div>"
        "</div>"
    )

    messages = "".join(
        f'<p class="prime-msg"><span class="msg-source">Prime</span>{_e(m)}</p>'
        for m in vm.prime_messages
    )

    hud_core = (
        '<div class="hud-stage" aria-label="Prime HUD command core">'
        '<div class="hud-core">'
        '<div class="hud-ring hud-ring-outer"></div>'
        '<div class="hud-ring hud-ring-mid"></div>'
        '<div class="hud-ring hud-ring-inner"></div>'
        '<div class="hud-orb"><strong>PRIMED</strong></div>'
        "</div>"
        "</div>"
    )

    voice_states = []
    if vm.voice.listening:
        voice_states.append('<span class="voice-state voice-listening">mic armed</span>')
    if vm.voice.dictating:
        voice_states.append('<span class="voice-state voice-dictating">dictating</span>')
    if vm.voice.thinking:
        voice_states.append('<span class="voice-state voice-thinking">thinking</span>')
    if vm.voice.speaking:
        voice_states.append('<span class="voice-state voice-speaking">speaker active</span>')
    if vm.voice.blocked:
        voice_states.append('<span class="voice-state voice-blocked">voice blocked</span>')

    mute_button = '<button type="button" class="icon-btn" data-action="mute" title="Mute voice output">Mute</button>'
    mute_control = mute_button if not vm.voice.muted else '<button type="button" class="icon-btn" data-action="unmute" title="Unmute voice output">Unmute</button>'

    voice = (
        '<div class="voice-strip" aria-label="Voice I/O state">'
        + "".join(voice_states)
        + mute_control
        + "</div>"
    )

    return (
        '<section class="prime-panel">'
        f"{header}"
        '<div class="prime-input" aria-label="Prime command prompt">'
        '<div class="prompt-head"><span>Command Bay</span><em>voice + text</em></div>'
        '<textarea placeholder="Open harness panel, show project sessions, show mission objectives..." class="prime-prompt"></textarea>'
        '<div class="prompt-actions">'
        '<button type="button" class="prompt-btn" data-action="voice">Mic</button>'
        '<button type="button" class="prompt-btn" data-action="send">Send</button>'
        '<button type="button" class="prompt-btn prompt-primary" data-action="mission-objectives">Mission Objectives</button>'
        "</div>"
        "</div>"
        f"{voice}"
        f"{hud_core}"
        f'<div class="prime-messages">{messages}</div>'
        "</section>"
    )

def _render_harness_dashboard(harnesses: list[HarnessCard]) -> str:
    consoles = []
    for card in harnesses:
        capabilities = "".join(
            f'<span class="harness-chip">{_e(cap)}</span>'
            for cap in card.capabilities
        )
        consoles.append(
            f'<details class="harness-console" data-status="{_e(card.status)}" '
            f'data-attention="{_e(str(card.attention).lower())}">'
            '<summary>'
            f'<span class="harness-name">{_e(card.name)}</span>'
            f'<span class="harness-status">{_e(card.status)}</span>'
            "</summary>"
            '<div class="harness-window">'
            f'<p class="harness-role">{_e(card.role)}</p>'
            f'<p class="harness-event">{_e(card.recent_event)}</p>'
            f'<div class="harness-capabilities">{capabilities}</div>'
            '<label class="harness-prompt-label">'
            f'<span>{_e(card.name)} scoped prompt</span>'
            f'<textarea class="harness-prompt" placeholder="Ask {_e(card.name)} about this subsystem only..."></textarea>'
            "</label>"
            "</div>"
            "</details>"
        )

    return (
        '<section class="harness-dashboard" aria-label="Harness Dashboard">'
        '<div class="harness-dashboard-header">'
        '<h2>Systems</h2>'
        '<span class="harness-dashboard-mode">on demand</span>'
        "</div>"
        '<div class="harness-consoles">'
        + "".join(consoles)
        + "</div>"
        + "</section>"
    )


def _render_project_strip(projects: list[ProjectCard], fallback_lanes: list[LaneRow]) -> str:
    if not projects and fallback_lanes:
        projects = [ProjectCard("Active Sessions", "running", "Live sessions", fallback_lanes)]

    rows = []
    for project in projects:
        sessions = "".join(
            f'<li class="session-row" data-status="{_e(session.status)}">'
            f'<span>{_e(session.name)}</span>'
            f'<em>{_e(session.label)}</em>'
            "</li>"
            for session in project.sessions
        )
        rows.append(
            f'<details class="project-node" data-status="{_e(project.status)}">'
            f'<summary><span class="project-name">{_e(project.name)}</span>'
            f'<span class="project-state">{_e(project.status)}</span>'
            f'<span class="project-summary">{_e(project.summary)}</span></summary>'
            '<div class="project-drilldown">'
            f'<ul class="session-list">{sessions}</ul>'
            "</div>"
            "</details>"
        )
    total = len(projects)
    attn = sum(1 for project in projects if project.status in ("blocked", "paused"))
    return (
        '<aside class="project-strip" aria-label="Projects">'
        '<div class="rail-title">Projects</div>'
        f'<div class="project-rows">{"".join(rows)}</div>'
        f'<div class="lane-summary">{total} projects / {attn} attention</div>'
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
        'Mission Feed <span class="progress-filter">(all)</span>'
        f'<div class="progress-counts">{counts}</div>'
        "</div>"
        f'<div class="progress-cards">{cards}</div>'
        "</aside>"
    )


def _render_provider_balance(balance: ProviderBalanceView) -> str:
    if not balance.providers:
        return ""

    provider_items = []
    for provider in balance.providers:
        status_class = f"provider-{_e(provider.health)}"
        trust_label = f"[{_e(provider.trust_state)}]"
        provider_items.append(
            f'<div class="provider-item {status_class}" data-provider="{_e(provider.provider_id)}">'
            f'<div class="provider-header">'
            f'<span class="provider-name">{_e(provider.display_name)}</span>'
            f'<span class="provider-trust">{trust_label}</span>'
            f'<span class="provider-model">{_e(provider.model_name)}</span>'
            f"</div>"
            f'<div class="provider-metrics">'
            f'<span class="metric">Budget: {provider.prompt_budget_percent:.0f}%</span>'
            f'<span class="metric">Tokens: {provider.current_prompt_tokens}/{provider.prompt_budget_tokens}</span>'
            f'<span class="metric">Pressure: {_e(provider.cost_pressure)}</span>'
            f"</div>"
            f'<span class="provider-notes">{_e(provider.notes)}</span>'
            f"</div>"
        )

    return (
        '<section class="provider-balance" aria-label="Provider Balance">'
        '<div class="provider-header-main">'
        '<h3>Provider Balance</h3>'
        f'<span class="routing-owner">{_e(balance.routing_owner)}</span>'
        f'<span class="policy-state policy-{_e(balance.policy_state)}">{_e(balance.policy_state)}</span>'
        "</div>"
        '<div class="provider-items">'
        + "".join(provider_items)
        + "</div>"
        + "</section>"
    )


def _render_prompt_payload(payload: PromptPayloadView) -> str:
    if not payload.size_label:
        return ""

    status_class = f"payload-{_e(payload.status)}"
    delta_display = f"+{payload.delta_tokens}" if payload.delta_tokens > 0 else f"{payload.delta_tokens}"

    return (
        '<section class="prompt-payload" aria-label="Prompt Payload Visibility">'
        '<div class="payload-header">'
        f'<span class="payload-size">{_e(payload.size_label)}</span>'
        f'<span class="payload-tokens">{payload.estimated_tokens} tokens</span>'
        f'<span class="payload-budget">{payload.budget_percent:.0f}% budget</span>'
        "</div>"
        f'<div class="payload-status {status_class}">'
        f'<span class="status-indicator">{_e(payload.status)}</span>'
        f'<span class="delta">Delta: {delta_display}</span>'
        f'<span class="source">From: {_e(payload.source)}</span>'
        f"</div>"
        + (
            f'<span class="payload-warning">⚠ Prompt drag detected</span>'
            if payload.status == "growing"
            else ""
        )
        + "</section>"
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
        '<span class="instr-title">Status</span>'
        f"{chip('Beacon', inst.beacon)}"
        f"{chip('Relay', inst.relay)}"
        f"{chip('Aegis', inst.aegis)}"
        f"{chip('Compass', inst.compass)}"
        f'<span class="instr-queue">Queue {_e(inst.queue_state)}</span>'
        f'<span class="instr-clock">{_e(inst.clock)}</span>'
        "</footer>"
    )


def _render_proof_state(proof: ProofStateView) -> str:
    if not proof.proof_status:
        return ""

    gate_items = []
    for gate in proof.gates:
        status_class = f"gate-{_e(gate.status)}"
        gate_items.append(
            f'<div class="gate-item {status_class}" data-gate-id="{_e(gate.gate_id)}">'
            f'<span class="gate-name">{_e(gate.gate_name)}</span>'
            f'<span class="gate-status">{_e(gate.status)}</span>'
            f'<span class="gate-reason">{_e(gate.reason)}</span>'
            f"</div>"
        )

    blocker_html = ""
    if proof.blocker_count > 0:
        blocker_html = f'<span class="blocker-count">{proof.blocker_count} gates blocking</span>'

    findings_html = ""
    if proof.open_findings > 0 or proof.waived_count > 0:
        findings_html = (
            f'<span class="finding-open">{proof.open_findings} open findings</span>'
            f'<span class="finding-waived">{proof.waived_count} waived</span>'
        )

    return (
        '<section class="proof-state" aria-label="Proof State">'
        '<div class="proof-header-main">'
        '<h3>Proof State</h3>'
        f'<span class="proof-status">{_e(proof.proof_status)}</span>'
        f'{blocker_html}'
        "</div>"
        '<div class="proof-gates">'
        + "".join(gate_items)
        + "</div>"
        + (
            f'<div class="proof-summary">{findings_html}</div>'
            if findings_html
            else ""
        )
        + (
            f'<span class="proof-notes">{_e(proof.notes)}</span>'
            if proof.notes
            else ""
        )
        + "</section>"
    )


def _render_session_lifecycle(lifecycle: SessionLifecycleView) -> str:
    if not lifecycle.sessions:
        return ""

    session_cards = []
    for session in lifecycle.sessions:
        is_active = session.session_id == lifecycle.active_session_id
        active_class = "session-active" if is_active else ""
        status_class = f"session-status-{_e(session.status)}"
        health_class = f"session-health-{_e(session.health_state)}"
        role_class = f"session-role-{_e(session.harness_role)}"

        blocker_html = ""
        if session.blocker_summary:
            blocker_html = f'<span class="session-blocker">{_e(session.blocker_summary)}</span>'

        session_cards.append(
            f'<div class="session-card {active_class} {status_class} {health_class} {role_class}" data-session-id="{_e(session.session_id)}">'
            f'<div class="session-header">'
            f'<span class="session-name">{_e(session.session_name)}</span>'
            f'<span class="session-role">[{_e(session.harness_role)}]</span>'
            f"</div>"
            f'<div class="session-context">'
            f'<span class="session-project">{_e(session.project_name)}</span>'
            f'<span class="session-status">{_e(session.status)}</span>'
            f'<span class="session-health">{_e(session.health_state)}</span>'
            f"</div>"
            f'<div class="session-lifecycle">'
            f'<span class="session-queue-read">{_e(session.last_queue_read_label)}</span>'
            f'<span class="session-cadence">{_e(session.review_cadence_state)}</span>'
            f'<span class="session-proof">{_e(session.proof_state)}</span>'
            f"</div>"
            f"{blocker_html}"
            f"</div>"
        )

    return (
        '<section class="session-lifecycle" aria-label="Session Lifecycle Preview">'
        '<div class="session-header-main">'
        '<h3>Session Lifecycle</h3>'
        "</div>"
        '<div class="session-cards">'
        + "".join(session_cards)
        + "</div>"
        + "</section>"
    )


def _render_user_session_mode(mode: UserSessionModeView) -> str:
    if not mode.sessions:
        return ""

    # Group sessions by project, sorting projects and sessions alphabetically
    sessions_by_project: dict[str, list[SessionItem]] = {}
    for session in mode.sessions:
        if session.project_name not in sessions_by_project:
            sessions_by_project[session.project_name] = []
        sessions_by_project[session.project_name].append(session)

    # Sort projects alphabetically, sort sessions within each project alphabetically
    sorted_projects = sorted(sessions_by_project.keys())
    for project in sessions_by_project:
        sessions_by_project[project].sort(key=lambda s: s.session_name)

    # Find currently selected session for title display
    selected_session_name = ""
    for session in mode.sessions:
        if session.session_id == mode.selected_session_id:
            selected_session_name = session.session_name
            break

    # Build optgroups for each project
    optgroups = []
    for project in sorted_projects:
        group_options = []
        for session in sessions_by_project[project]:
            selected = " selected" if session.session_id == mode.selected_session_id else ""
            status_label = ""
            if session.status == "waiting":
                status_label = " (waiting for test)"
            elif session.status == "hidden":
                status_label = " (hidden)"
            elif session.status != "live":
                status_label = f" ({session.status})"

            group_options.append(
                f'<option value="{_e(session.session_id)}"{selected}>'
                f'{_e(session.session_name)}{status_label}</option>'
            )

        optgroups.append(
            f'<optgroup label="{_e(project)}">'
            + "".join(group_options)
            + "</optgroup>"
        )

    return (
        '<div class="right-panel-user-session" aria-label="User Session Mode">'
        '<div class="right-panel-header">'
        f'<h3>Session: {_e(selected_session_name) if selected_session_name else "Select..."}</h3>'
        '<div class="sessions-dropdown">'
        '<select aria-label="Select session">'
        + "".join(optgroups)
        + "</select>"
        "</div>"
        "</div>"
        '<div class="prompt-response-area">'
        '<textarea class="prompt-input" placeholder="Enter prompt..."></textarea>'
        '<div class="response-output"></div>'
        "</div>"
        "</div>"
    )


def _render_settings_mode(mode: SettingsModeView) -> str:
    if not mode.settings:
        return ""

    settings_items = []
    for setting in mode.settings:
        settings_items.append(
            f'<div class="settings-item" data-setting-id="{_e(setting.setting_id)}">'
            f'<label>{_e(setting.setting_name)}</label>'
            f'<input type="{_e(setting.setting_type)}" value="{_e(setting.value)}" />'
            f"</div>"
        )

    return (
        '<div class="right-panel-settings" aria-label="Settings Mode">'
        '<div class="right-panel-header">'
        '<h3>Configuration</h3>'
        "</div>"
        '<div class="settings-list">'
        + "".join(settings_items)
        + "</div>"
        "</div>"
    )


def _render_harness_mode(mode: HarnessModeView) -> str:
    if not mode.harness_items:
        return ""

    harness_items = []
    for item in mode.harness_items:
        item_type_class = f"harness-item-{_e(item.item_type)}"
        harness_items.append(
            f'<div class="harness-item {item_type_class}" data-item-id="{_e(item.item_id)}">'
            f'<div class="harness-item-header">'
            f'<span class="harness-item-name">{_e(item.item_name)}</span>'
            f'<span class="harness-item-type">[{_e(item.item_type)}]</span>'
            f"</div>"
            f'<div class="harness-item-description">{_e(item.description)}</div>'
            f"</div>"
        )

    return (
        '<div class="right-panel-harness" aria-label="Harness Mode">'
        '<div class="right-panel-header">'
        '<h3>Harness Logic</h3>'
        '<input type="text" class="harness-search" placeholder="Search harness items..." />'
        "</div>"
        '<div class="harness-items-list">'
        + "".join(harness_items)
        + "</div>"
        "</div>"
    )


# ── Public API ──────────────────────────────────────────────────────────────


def render_cockpit_html(vm: CockpitViewModel) -> str:
    """Return a complete, self-contained HTML document for the Bifrost cockpit.

    All dynamic content is HTML-escaped. No JavaScript or external dependencies.
    """
    css = _load_css()

    prime = _render_prime_panel(vm)
    harness_dashboard = _render_harness_dashboard(vm.harnesses)
    session_lifecycle = _render_session_lifecycle(vm.session_lifecycle)
    proof_state = _render_proof_state(vm.proof_state)
    provider_balance = _render_provider_balance(vm.provider_balance)
    prompt_payload = _render_prompt_payload(vm.prompt_payload)
    projects = _render_project_strip(vm.projects, vm.lanes)
    progress = _render_progress_surface(vm.progress_events)
    instrument = _render_instrument_band(vm.instrument)

    right_panel_content = ""
    if vm.right_panel_active_mode == "user_session":
        right_panel_content = _render_user_session_mode(vm.user_session_mode)
    elif vm.right_panel_active_mode == "settings":
        right_panel_content = _render_settings_mode(vm.settings_mode)
    elif vm.right_panel_active_mode == "harness":
        right_panel_content = _render_harness_mode(vm.harness_mode)

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
        '<div class="cockpit-content">\n'
        f"{projects}\n"
        '<main class="cockpit-main">\n'
        f"{prime}\n"
        f"{harness_dashboard}\n"
        f"{session_lifecycle}\n"
        f"{proof_state}\n"
        f"{provider_balance}\n"
        f"{prompt_payload}\n"
        "</main>\n"
        '<aside class="right-panel">\n'
        f"{right_panel_content}\n"
        "</aside>\n"
        f"{progress}\n"
        "</div>\n"
        f"{instrument}\n"
        "</div>\n"
        "</body>\n"
        "</html>"
    )
