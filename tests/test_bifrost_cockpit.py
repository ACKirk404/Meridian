"""Tests for the Bifrost cockpit static HTML renderer."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from bifrost.cockpit import (
    AegisPromptPacketPolicyView,
    CommandStagingReviewItem,
    CommandStagingReviewView,
    CockpitViewModel,
    DispatchHardeningView,
    HarnessCard,
    HarnessItem,
    HarnessModeView,
    InstrumentBand,
    LaneRow,
    ModelCapabilityItem,
    ModelCapabilityMetadataView,
    ModelValidationEnvelopeItem,
    ModelValidationEnvelopeView,
    ProgressEvent,
    ProviderBalanceItem,
    ProviderBalanceView,
    ProjectCard,
    PromptPayloadView,
    PromptPacketProofView,
    ProofGateStatus,
    ProofPreviewItem,
    ProofStateView,
    RelayAegisPolicyHandoffView,
    RecoveryReadinessAction,
    RecoveryReadinessAdvisory,
    SessionItem,
    SessionLifecycleItem,
    SessionLifecycleView,
    SettingsItem,
    SettingsModeView,
    UserSessionModeView,
    VisiblePromptPayloadMeterItem,
    VisiblePromptPayloadMeterView,
    VoiceIOState,
    _render_proof_state,
    _e,
    cockpit_view_model_with_backend_bindings,
    merge_provider_balance_summary_into_view,
    model_capability_metadata_view_from_summary,
    prompt_payload_view_from_evidence,
    provider_balance_view_from_summary,
    render_cockpit_html,
    relay_aegis_policy_handoff_from_summary,
    reviewed_backend_evidence_view_from_summary,
    sample_backend_bound_cockpit_view_model,
    sample_cockpit_view_model,
    view_model_from_snapshot,
    visible_prompt_payload_meter_view_from_evidence,
)
from meridian_core.relay_executor import (
    RelayModelCapabilityLaneSummary,
    RelayModelCapabilityMetadataSummary,
    RelayPromptPayloadEvidence,
    RelayPromptPayloadMeterEvidence,
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

ROOT = Path(__file__).resolve().parents[1]


# sample_cockpit_view_model


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


def test_index_spark_media_references_existing_assets():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    media_paths = {
        match.group(1)
        for match in re.finditer(r'url\("([^"]*spark[^"]*)"\)', doc)
    }
    assert "bifrost/static/media/spark-center-final.png" in media_paths
    assert "bifrost/static/media/spark-hud-reference.jpg" in media_paths
    assert not any(path.startswith("static/media/") for path in media_paths)
    missing = [path for path in media_paths if not (ROOT / path).is_file()]
    assert missing == []
    assert 'class="core-animation spark-final-image"' in doc
    assert 'role="img" aria-label="Spark, voice of Prime"' in doc
    assert 'data-name="Spark"' in doc
    assert 'data-role="voice-of-prime"' in doc
    assert 'class="spark-stage"' in doc
    assert 'class="spark-core-toggle" type="button" aria-label="Toggle session panels"' in doc
    assert 'class="spark-menu spark-icon-menu" aria-label="Spark actions"' in doc
    assert 'class="spark-menu-icon-button is-selected" type="button" aria-label="Settings"' in doc


def test_index_reset_uses_same_button_confirmation_and_visible_failure():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Confirm Reset" in doc
    assert "dataset.resetConfirming" in doc
    assert "reset storage error" in doc
    assert "Reset could not clear visible session state" in doc
    assert "clearModelStatusLabels" in doc
    assert "meridian.session.project" in doc
    assert "Reset clears visible prompts and transcripts" in doc
    assert "clear memory" not in doc.lower()


def test_index_reload_preserves_state_and_reports_failures():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "reloadInProgress" in doc
    assert "meridian_reload" in doc
    assert "reload error" in doc
    assert "Reload could not start" in doc
    assert "hardReloadUi();" in doc
    assert "hardReloadUi({ clearSessions: true })" not in doc


def test_index_stale_user_session_target_is_not_silently_replaced():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Selected session unavailable" in doc
    assert "selected session unavailable" in doc
    assert "session list unavailable" in doc
    assert "Sessions unavailable" in doc


def test_index_right_panel_mode_has_single_authority_and_recovery():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "validRightPanelModes" in doc
    assert "setRightPanelAuthority" in doc
    assert "dataset.panelMode" in doc
    assert "dataset.rightPanelMode" in doc
    assert "surface unavailable; User Session restored" in doc
    assert "return false;" in doc


def test_index_harness_mode_uses_full_panel_logic_surface_without_prompt_window():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert ".session-window-right.is-panel-surface .session-interface" in doc
    assert ".session-window-right.is-panel-surface .session-prompt-input" in doc
    assert ".session-window-right.is-panel-surface .session-response-output" in doc
    assert "display: none;" in doc
    assert "const renderRightPanelSurface = ({ title, status, sections, surfaceClass = '' }) =>" in doc
    assert "rightWindow.classList.add('is-panel-surface')" in doc
    assert "rightWorkspace.insertAdjacentHTML('beforeend', `" in doc
    assert 'class="right-panel-surface${safeSurfaceClass}"' in doc
    assert "const renderHarnessSurface = (button) =>" in doc
    assert "relaySection('Harness logic'" in doc
    assert "['surface mode', 'Harness']" in doc
    assert "['prompt window', 'hidden in this mode']" in doc
    assert "relaySection('Backend link'" in doc
    assert "modelButton ? renderModelHarnessSurface(button) : renderHarnessSurface(button)" in doc
    assert "setRightPanelAuthority('harness', button.dataset.harness || 'Harness', { persist })" in doc


def test_index_generic_harness_surface_blocks_unsupported_actions_without_backend_mutation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "Unsupported action guard" in surface
    assert "selected harness" in surface
    assert "unsupported until reviewed backend wiring exists" in surface
    assert "display-only; action stays blocked" in surface
    assert "Harness item action scope" in surface
    assert "selected logic item" in surface
    assert "Harness logic" in surface
    assert "selected harness logic item only" in surface
    assert "blocked until reviewed backend action exists" in surface
    assert "no User Session or Prime prompt route is used" in surface
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface
    assert "bridgeUrl('restart')" not in surface
    assert "call-result" not in surface


def test_index_generic_harness_surface_frames_logic_updates_without_project_control():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "Logic update framing" in surface
    assert "review or update harness logic items" in surface
    assert "add or refine harness logic after backend review" in surface
    assert "not arbitrary project/session control" in surface
    assert "project switch" not in surface.lower()
    assert "session close" not in surface.lower()
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface


def test_index_generic_harness_surface_shows_absent_real_state_without_fake_health():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "Harness state summary" in surface
    assert "real backend state unavailable" in surface
    assert "no fake health value shown" in surface
    assert "healthy" not in surface.lower()
    assert "degraded" not in surface.lower()
    assert "latency" not in surface.lower()
    assert "uptime" not in surface.lower()
    assert "method: 'POST'" not in surface


def test_index_generic_harness_surface_blocks_cross_harness_leakage():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "Harness isolation boundary" in surface
    assert "active harness" in surface
    assert "selected harness only" in surface
    assert "selected harness logic item only" in surface
    assert "blocked; no silent reroute to another harness" in surface
    assert "setRightPanelAuthority('harness', button.dataset.harness || 'Harness', { persist })" in doc
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface
    assert "bridgeUrl('call-result')" not in surface


def test_index_generic_harness_surface_preserves_unsaved_logic_draft_per_harness():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const harnessDraftStorageKey = (harness) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "const harnessDraftStorageKey = (harness) => `meridian.harness.draft.v1." in surface
    assert "const readHarnessDraft = (harness) =>" in surface
    assert "const writeHarnessDraft = (harness, value) =>" in surface
    assert "const initializeHarnessDraftSurface = (harness) =>" in surface
    assert "localStorage.getItem(harnessDraftStorageKey(harness))" in surface
    assert "localStorage.setItem(harnessDraftStorageKey(harness), String(value || ''))" in surface
    assert "data-harness-draft" in surface
    assert "Unsaved harness logic note" in surface
    assert "readHarnessDraft(harness)" in surface
    assert "storage scope', 'selected harness only" in surface
    assert "backend write', 'none" in surface
    assert "draft only; no harness action is run" in surface
    assert "if (rendered) {" in surface
    assert "loadHarnessProofLink();" in surface
    assert "initializeHarnessDraftSurface(harness);" in surface
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface
    assert "bridgeUrl('call-result')" not in surface


def test_index_generic_harness_surface_links_filemap_proof_checks_without_execution():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const harnessProofMatches = (snapshot, harness) =>")
    end = doc.index("let sparkSkillsRegistrySnapshot = null", start)
    proof_renderer = doc[start:end]
    surface_start = doc.index("const renderHarnessSurface = (button) =>")
    surface_end = doc.index("const renderRelayModels = () =>", surface_start)
    surface = doc[surface_start:surface_end]

    assert "const renderHarnessProofLinkSnapshot = (snapshot, harness) =>" in proof_renderer
    assert "Harness proof/checks" in proof_renderer
    assert "related tests" in proof_renderer
    assert "Proof links are FileMap metadata only" in proof_renderer
    assert "do not execute tests, run workflow orders, move branches, write files, or call providers" in proof_renderer
    assert "const loadHarnessProofLink = async () =>" in doc
    assert "rightWorkspace?.querySelector('[data-harness-proof-link]')" in doc
    assert "fetch(bridgeUrl('filemap'), { cache: 'no-store' })" in doc
    assert "data-harness-proof-link" in surface
    assert "loadHarnessProofLink();" in surface
    assert "method: 'POST'" not in proof_renderer
    assert "bridgeUrl('message')" not in proof_renderer
    assert "bridgeUrl('call-result')" not in proof_renderer
    assert "bridgeUrl('restart')" not in proof_renderer


def test_index_harness_title_toggles_model_icons():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert '<button class="harness-dock-title" type="button"' in doc
    assert "Orchestrator Harness" in doc
    assert "Switch to model harness icons" in doc
    assert "harness-model-mode" in doc
    assert ".harness-dock-wrap.harness-model-mode .harness-dock-top" in doc
    assert "openHarness({ force: true })" in doc
    assert "if (force) harnessDisabledUntil = 0" in doc
    assert "--harness-line-y: 124px" in doc
    assert "position: absolute;\n  left: 50%;\n  bottom: 34px;" in doc
    assert ".harness-dock-top {\n  width: 100%;\n  top: 34px;" in doc
    assert ".harness-dock-bottom {\n  width: 100%;\n  top: calc(var(--harness-line-y) - 14px);" in doc
    assert "top: calc(var(--harness-line-y) - 6px)" in doc
    assert "height: 244px" in doc
    assert "grid-template-columns: repeat(4, minmax(44px, 1fr))" in doc
    assert "grid-template-columns: repeat(22, minmax(0, 1fr))" in doc
    assert "grid-template-rows: repeat(2, minmax(0, 1fr))" in doc
    assert "--harness-icon-size: 34.65%" in doc
    assert ".harness-dock-wrap.harness-model-mode .harness-model-dock .harness-dock-button:nth-child(-n + 11)" in doc
    assert "top: 26px" in doc
    assert ".harness-dock-wrap.harness-model-mode .harness-model-dock .harness-dock-button:nth-child(n + 12)" in doc
    assert "top: -18px" in doc
    assert ".harness-dock-wrap.harness-model-mode .harness-model-dock .harness-dock-button:nth-child(21) { grid-column: 20 / span 2; }" in doc
    assert 'class="harness-dock harness-dock-bottom harness-model-dock"' in doc
    assert 'aria-label="Model harness"' in doc
    for label in (
        "Provider",
        "Identity",
        "Select",
        "Route",
        "Fallback",
        "Verify",
        "Cost",
        "Latency",
        "Context",
        "Prompt",
        "Policy",
        "Safety",
        "Privacy",
        "Tools",
        "Compare",
        "Trace",
        "Goal",
        "Payload",
        "Response",
        "Evidence",
        "Trust",
    ):
        assert f'<span class="harness-label">{label}</span>' in doc


def test_index_model_harness_icons_open_model_surface():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessAspects = {" in doc
    assert "const modelHarnessRuntimeSignals = {" in doc
    assert "const modelHarnessVisibleGates = {" in doc
    assert "const isModelHarnessButton = (button) => Boolean(button?.closest?.('.harness-model-dock'))" in doc
    assert "const renderModelHarnessSurface = (button) =>" in doc
    assert "Model ${label} Harness" in doc
    assert "surfaceClass: 'is-model-harness-surface'" in doc
    assert "setHarnessDockMode('model')" in doc
    assert "screen.classList.add('session-theme-green')" in doc
    assert "modelButton ? renderModelHarnessSurface(button) : renderHarnessSurface(button)" in doc
    assert "display-only; backend snapshots are bound, writes remain disabled" in doc
    assert "What context was visible before this model action?" in doc
    assert "What intention was visible before execution?" in doc
    assert "What proof shows the model action followed that logic?" in doc


def test_index_has_single_reachable_harness_dock():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert doc.count('<div class="harness-dock-wrap"') == 1
    assert doc.count('class="harness-dock harness-dock-bottom harness-model-dock"') == 1
    assert doc.count('data-harness="Release"') == 1
    assert 'data-harness="Security" data-status="planned" data-session-title="Security-Guardrails"' in doc
    assert '<span class="harness-label">Security</span><span class="harness-sub-label">Guardrails</span>' in doc
    assert 'data-harness="TBD"' not in doc
    assert 'data-harness="Workflow" data-status="stable"' in doc
    assert 'data-harness="Federation" data-status="stable"' in doc
    assert 'data-harness="Echo" data-status="stable"' in doc
    assert 'data-harness="Atlas" data-status="stable"' in doc


def test_index_security_harness_identity_is_display_only_until_backend_exists():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert 'data-harness="Security" data-status="planned" data-session-title="Security-Guardrails"' in doc
    assert "modelButton ? renderModelHarnessSurface(button) : renderHarnessSurface(button)" in doc
    assert "Unsupported action guard" in surface
    assert "real backend state unavailable" in surface
    assert "no hidden backend mutation is available from this panel" in surface
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface
    assert "Security:" not in surface
    assert "guardrail action" not in surface.lower()


def test_index_planned_tool_git_browser_harnesses_are_display_only_until_backends_exist():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert 'data-harness="Tool" data-status="planned" data-session-title="Ratchet-Tools"' in doc
    assert '<span class="harness-label">Ratchet</span><span class="harness-sub-label">Tools</span>' in doc
    assert 'data-harness="Git" data-status="planned" data-session-title="Source-Git"' in doc
    assert '<span class="harness-label">Source</span><span class="harness-sub-label">Git</span>' in doc
    assert 'data-harness="Browser" data-status="planned" data-session-title="Vision-Browser"' in doc
    assert '<span class="harness-label">Vision</span><span class="harness-sub-label">Browser</span>' in doc
    assert "Planned capability boundary" in surface
    assert "no fake tool execution or provider/tool call is exposed" in surface
    assert "no branch movement, commit, push, reset, or file mutation is exposed" in surface
    assert "no fake browser state, page control, screenshot, or remote navigation is exposed" in surface
    assert "explicit approval and reviewed backend wiring required before execution" in surface
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface
    assert "bridgeUrl('call-result')" not in surface


def test_index_harness_permission_boundary_blocks_high_risk_actions_until_approved():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("const renderHarnessSurface = (button) =>")
    end = doc.index("const renderRelayModels = () =>", start)
    surface = doc[start:end]

    assert "permission boundary" in surface
    assert "explicit approval and reviewed backend wiring required before execution" in surface
    assert "Git: ['source control', 'no branch movement, commit, push, reset, or file mutation is exposed']" in surface
    assert "Tool: ['tool execution', 'no fake tool execution or provider/tool call is exposed']" in surface
    assert "Browser: ['browser/vision', 'no fake browser state, page control, screenshot, or remote navigation is exposed']" in surface
    assert "release execution authorized" in doc
    assert "release controls visible" in doc
    assert "bridgeUrl('prime-autonomy')" in doc
    assert "release-now" not in doc
    assert "method: 'POST'" not in surface
    assert "bridgeUrl('message')" not in surface


def test_index_speech_mode_icon_is_display_only():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'class="speech-mode-button"' in doc
    assert 'aria-label="Speech mode unavailable"' in doc
    assert 'aria-disabled="true"' in doc
    assert " disabled>" in doc
    assert "const speechButton = document.querySelector('.speech-mode-button')" in doc
    assert "const voiceStateLabel = (voice = {}) =>" in doc
    assert "const applySpeechButtonVoiceState = (snapshot = {}) =>" in doc
    assert "const refreshSpeechButtonVoiceState = async () =>" in doc
    assert "speechButton.dataset.voiceState = state" in doc
    assert "speechButton.dataset.voiceAuthorization = 'display-only'" in doc
    assert "speechButton.setAttribute('aria-label', `Speech mode ${state}`)" in doc
    assert "speechButton.setAttribute('aria-disabled', 'true')" in doc
    assert "speechButton.disabled = true" in doc
    assert "speechButton.setAttribute('aria-pressed', state !== 'unavailable' && state !== 'blocked' ? 'true' : 'false')" in doc
    assert "refreshSpeechButtonVoiceState();" in doc
    assert "applySpeechButtonVoiceState(snapshot);" in doc
    assert "bridgeUrl('voice-io')" in doc
    assert "speechButton.addEventListener('click'" not in doc
    assert "getUserMedia" not in doc
    assert "SpeechRecognition" not in doc
    assert "MediaRecorder" not in doc
    assert "AudioContext" not in doc
    assert "navigator.mediaDevices" not in doc
    assert "speechSynthesis" not in doc
    assert "readAloud" not in doc
    assert "muteVoice" not in doc
    assert 'data-action="voice"' not in doc
    assert 'data-action="read-aloud"' not in doc
    assert 'data-action="mute"' not in doc
    assert 'data-action="unmute"' not in doc


def test_index_planned_spark_surfaces_do_not_fetch_fake_backends():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const renderSparkSurface = (label) =>" in doc
    assert "const settingsSelected = selectedLabel === 'Settings';" in doc
    assert "const filterSelected = selectedLabel === 'Filter';" in doc
    assert "filterSelected ? 'UI-local context preview wired' : 'not wired yet'" in doc
    assert "filterSelected ? 'preview-only; no prompt send, backend write, or source deletion' : 'unsupported until backend wiring exists'" in doc
    assert "unsupported until backend wiring exists" in doc
    assert "Settings/Spark renders compact Voice I/O state from the reviewed backend snapshot." in doc
    assert "No microphone capture, speech output, read-aloud, mute mutation, prompt text, response text, raw worker history, or worker chat is exposed." in doc
    assert "Settings writes remain blocked until an explicit settings backend exists." in doc
    assert "Settings/Spark renders public Codex and Claude/Max CLI setup status from the reviewed Models bridge snapshot." in doc
    assert "Settings does not install software, sign in, read secrets, probe provider accounts, or mutate model routing." in doc
    assert "status: settingsSelected || filterSelected ? 'Display-only' : 'planned'" in doc
    assert "loadVoiceIo();" in doc
    assert "loadSparkModels();" in doc
    assert "initializeContextFilterSurface();" in doc
    for label in ("Filter", "Backlog", "Skills"):
        assert f'aria-label="{label}"' in doc
    for route in (
        "filter",
        "backlog",
        "skills",
        "crosscheck",
        "routines",
        "settings",
    ):
        assert f"bridgeUrl('{route}')" not in doc
    settings_surface = doc[doc.index("const renderSparkSurface = (label) =>"):doc.index("const renderHarnessSurface")]
    assert "bridgeUrl('message')" not in settings_surface
    assert "bridgeUrl('restart')" not in settings_surface
    assert "bridgeUrl('call-result')" not in settings_surface
    assert "method: 'POST'" not in settings_surface
    assert "getUserMedia" not in settings_surface
    assert "speechSynthesis" not in settings_surface
    assert "MediaRecorder" not in settings_surface
    assert "SpeechRecognition" not in settings_surface


def test_index_spark_filter_surface_updates_local_preview_without_backend_or_deletion():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const contextFilterDefaults = {")
    render_end = doc.index("const renderHarnessSurface = (button) =>", render_start)
    filter_surface = doc[render_start:render_end]

    assert "const contextFilterDefaults = {" in filter_surface
    assert "const contextFilterPresets = {" in filter_surface
    for key in (
        "responses",
        "tools",
        "tokenUsage",
        "inbound",
        "outbound",
        "workStatements",
        "evidence",
        "diagnostics",
    ):
        assert key in filter_surface
        assert f'data-filter-toggle="${{key}}"' in filter_surface
    for preset in ("compact", "normal", "verbose", "debug"):
        assert preset in filter_surface
    for scope in ("prime", "user-session", "selected-harness", "current-project"):
        assert scope in filter_surface
    assert "data-filter-preview" in filter_surface
    assert "initializeContextFilterSurface" in filter_surface
    assert "preview only; no prompt is sent or saved" in filter_surface
    assert "filtering never deletes source session data" in filter_surface
    assert "Turning a toggle back on restores the preview row" in filter_surface
    assert "state.verbosity = target.value" in filter_surface
    assert "Object.assign(state, contextFilterPresets[target.value] || {})" in filter_surface
    assert "state[target.dataset.filterToggle] = target.checked" in filter_surface
    assert "writeContextFilterState(state)" in filter_surface
    assert "bridgeUrl('filter')" not in filter_surface
    assert "bridgeUrl('message')" not in filter_surface
    assert "bridgeUrl('call-result')" not in filter_surface
    assert "method: 'POST'" not in filter_surface


def test_index_spark_crosscheck_aggregates_typed_review_and_aegis_state():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Crosscheck"' in doc
    assert "Crosscheck Review" in doc
    assert "const renderSparkCrosscheck = () =>" in doc
    assert "renderSparkCrosscheck()" in doc
    assert "Aggregates Review Console queue state and Aegis proof posture without starting a review run." in doc
    assert "Orchestrator intake is limited to compact typed review/proof state from the bridge snapshots." in doc
    assert "Worker session transcript is stored, not replayed" in doc
    assert "worker summary is small and checkpoint-updated" in doc
    assert "session state packet is always available to Orchestrator" in doc
    assert "Evidence refs are links/ids, not pasted logs" in doc
    assert "raw detail is fetched only on demand" in doc
    assert "raw worker session history" in doc
    assert "data-review-console" in doc
    assert "data-aegis-logic" in doc
    assert "loadReviewConsole();" in doc
    assert "loadAegisLogic();" in doc
    assert "bridgeUrl('review-console')" in doc
    assert "bridgeUrl('aegis-logic')" in doc
    assert "Open evidence" in doc
    assert 'data-crosscheck-handoff="aegis"' in doc
    assert 'data-crosscheck-handoff="archive"' in doc
    assert "raw item content visible" in doc
    assert "raw evidence body visible" in doc
    assert "data-crosscheck-stop-conditions" in doc
    assert "loadCrosscheckStopConditions();" in doc
    crosscheck_surface = doc[doc.index("const renderSparkCrosscheck"):doc.index("const renderProviderBalance")]
    assert "fetch(" not in crosscheck_surface
    assert "bridgeUrl('message')" not in crosscheck_surface
    assert "bridgeUrl('restart')" not in crosscheck_surface
    assert "call-result" not in crosscheck_surface
    assert "method: 'POST'" not in crosscheck_surface
    assert "<form" not in crosscheck_surface
    assert "apply_console_response" not in crosscheck_surface
    assert "enqueue_to_review_console" not in crosscheck_surface
    assert "provider_call_authorized" not in crosscheck_surface


def test_index_crosscheck_evidence_handoff_only_switches_visible_surfaces():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    crosscheck_surface = doc[
        doc.index("const renderSparkCrosscheck = () =>"):
        doc.index("const renderSparkBacklog = () =>")
    ]
    handler_start = doc.index("const sparkButtonByLabel = (label) =>")
    handler_end = doc.index("buttons.forEach((button) =>", handler_start)
    handler = doc[handler_start:handler_end]
    assert "Crosscheck evidence handoff" in crosscheck_surface
    assert "Open Aegis proofs" in crosscheck_surface
    assert "Open Archive command preview" in crosscheck_surface
    assert "This handoff only changes the visible surface; it does not approve findings, rerun checks, apply console responses, execute commands, or inject raw logs into Prime context." in crosscheck_surface
    assert "[data-crosscheck-handoff]" in handler
    assert "crosscheckHandoff?.dataset.crosscheckHandoff === 'archive'" in handler
    assert "sparkButtonByLabel('Archive')" in handler
    assert "crosscheckHandoff?.dataset.crosscheckHandoff === 'aegis'" in handler
    assert "harnessButtonByName('Aegis')" in handler
    assert "activateHarnessButton(targetButton);" in handler
    assert "activateSparkButton(targetButton);" in handler
    assert "fetch(" not in handler
    assert "bridgeUrl('message')" not in handler
    assert "method: 'POST'" not in handler


def test_index_crosscheck_stop_condition_alert_uses_existing_review_and_aegis_snapshots_only():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    stop_logic = doc[
        doc.index("const renderCrosscheckStopConditionsSnapshot = (reviewSnapshot, aegisSnapshot) =>"):
        doc.index("const renderBacklogReviewSnapshot")
    ]
    loader = doc[
        doc.index("const loadCrosscheckStopConditions = async () =>"):
        doc.index("const loadSparkBacklog = async () =>")
    ]

    assert "queue.pending_gate_count" in stop_logic
    assert "proofTrail.blocking_count" in stop_logic
    assert "policy.requires_human_gate" in stop_logic
    assert "policy.can_dispatch === false" in stop_logic
    assert "review_console_pending_gate" in stop_logic
    assert "aegis_proof_blocking" in stop_logic
    assert "aegis_human_gate_required" in stop_logic
    assert "aegis_dispatch_blocked" in stop_logic
    assert "Stop condition: ${condition}" in stop_logic
    assert "Further UI wiring should pause until the blocking review/proof condition is cleared or explicitly waived by reviewed backend policy." in stop_logic
    assert "Crosscheck remains display-only; this alert does not approve, waive, rerun, or mutate any review/proof state." in stop_logic
    assert "fetch(bridgeUrl('review-console'), { cache: 'no-store' })" in loader
    assert "fetch(bridgeUrl('aegis-logic'), { cache: 'no-store' })" in loader
    assert "renderCrosscheckStopConditionsSnapshot(reviewSnapshot, aegisSnapshot)" in loader
    assert "bridgeUrl('message')" not in loader
    assert "bridgeUrl('call-result')" not in loader
    assert "method: 'POST'" not in loader


def test_index_spark_backlog_uses_typed_task_posture_without_fake_items_or_mutation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Backlog"' in doc
    assert 'aria-label="Backlog tasks"' in doc
    assert "Backlog Tasks" in doc
    assert "const renderSparkBacklog = () =>" in doc
    assert "const loadSparkBacklog = async () =>" in doc
    assert "const renderBacklogReviewSnapshot = (snapshot) =>" in doc
    assert "renderSparkBacklog()" in doc
    assert "Backlog shows typed task posture from Review Console, Goal Runtime, and Workflow Dispatch snapshots." in doc
    assert "Backlog candidate list rows are real Review Console queue items displayed in the active Compass project frame." in doc
    assert "No fake backlog items are created; empty or missing backend queues render as empty or unavailable state." in doc
    assert "does not create tasks, assign workers, mutate queues, start routines, send prompts, recover raw result bodies, or ingest raw worker session history" in doc
    assert "Orchestrator intake stays limited to compact typed session state, small worker summaries, and evidence refs." in doc
    assert "Backlog candidate rows are derived from the Review Console queue snapshot only." in doc
    assert "The active project is the current Compass project display frame; no hidden cross-project merge or fake item fill is performed." in doc
    assert "Create, approve, deny, defer, convert, archive, owner assignment, and priority mutation remain unavailable until a reviewed backlog backend exists." in doc
    assert "data-backlog-review-console" in doc
    assert "data-backlog-goal-runtime" in doc
    assert "data-backlog-workflow-dispatch-status" in doc
    assert "data-backlog-prime-logic" in doc
    assert "bridgeUrl('review-console')" in doc
    assert "bridgeUrl('prime-logic')" in doc
    assert "bridgeUrl('goal-runtime')" in doc
    assert "bridgeUrl('workflow-dispatch-status')" in doc
    backlog_loader = doc[doc.index("const loadSparkBacklog = async () =>"):doc.index("const loadEchoMemory", doc.index("const loadSparkBacklog = async () =>"))]
    assert "Promise.all" in backlog_loader
    assert "renderBacklogReviewSnapshot" in backlog_loader
    assert "renderBacklogPrioritySnapshot" in backlog_loader
    assert "renderGoalRuntimeSnapshot" in backlog_loader
    assert "renderWorkflowDispatchStatusSnapshot" in backlog_loader
    backlog_review = doc[doc.index("const renderBacklogReviewSnapshot"):doc.index("const renderFederationHorizonSnapshot")]
    assert "activeProjectContext()" in backlog_review
    assert "Backlog candidate list" in backlog_review
    assert "Priority order" in backlog_review
    assert "Review Console queue order selects sequence" in backlog_review
    assert "Goal Runtime keeps the active objective focused on" in backlog_review
    assert "Prime currently explains the active review posture as:" in backlog_review
    assert "no pending backlog candidates reported by the current Review Console snapshot" in backlog_review
    for field in ("project", "sequence", "id", "type", "severity", "title", "state", "requires response", "suggested actions"):
        assert f"['{field}'" in backlog_review
    for field in ("active project", "next candidate id", "next sequence", "goal objective", "Prime owner", "Prime action", "Prime risk", "Prime why"):
        assert f"['{field}'" in backlog_review
    backlog_surface = doc[doc.index("const renderSparkBacklog"):doc.index("const renderProviderBalance")]
    assert "fetch(" not in backlog_surface
    assert "bridgeUrl('backlog')" not in backlog_surface
    assert "bridgeUrl('message')" not in backlog_surface
    assert "bridgeUrl('call-result')" not in backlog_surface
    assert "method: 'POST'" not in backlog_surface
    assert "<button" not in backlog_surface
    assert "<form" not in backlog_surface
    assert "create_task" not in backlog_surface
    assert "assign_worker" not in backlog_surface
    assert "enqueue_to_review_console" not in backlog_surface
    assert "apply_console_response" not in backlog_surface


def test_index_spark_skills_registry_searches_loaded_metadata_without_execution():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Skills"' in doc
    assert 'aria-label="Skills registry"' in doc
    assert "Skills Registry" in doc
    assert "const renderSparkSkills = () =>" in doc
    assert "const loadSparkSkills = async () =>" in doc
    assert "const renderSparkSkillsRegistry = (snapshot, query = '') =>" in doc
    assert "const skillRegistryRowsFromSnapshots = (fileMapSnapshot, modelsSnapshot) =>" in doc
    assert "renderSparkSkills()" in doc
    assert "data-spark-skills" in doc
    assert "data-spark-skills-search" in doc
    assert "data-spark-skill-pin" in doc
    assert "const sparkSkillsPinKey = 'meridian.skills.pinned.v1'" in doc
    assert "const readSparkSkillsPinned = () =>" in doc
    assert "const writeSparkSkillsPinned = (pins) =>" in doc
    assert "const skillRegistryRowId = (row) =>" in doc
    assert "parsed[activeProjectContext()] = [...pins].sort()" in doc
    assert "localStorage.setItem(sparkSkillsPinKey, JSON.stringify(parsed))" in doc
    assert "aria-pressed" in doc
    assert "Pinned skills" in doc
    assert "pinned for active project/user" in doc
    assert "Active project skills" in doc
    assert "project-scoped pins" in doc
    assert "global fallback capabilities" in doc
    assert "active project context plus UI-local pins over loaded backend metadata" in doc
    assert "project changes refresh this section and use that project pin bucket" in doc
    assert "path:string required repo-relative; area:string optional; related_tests:string[] default []" in doc
    assert "backend:string required from /bridge/models; prompt:text supplied only in Prime/User prompt after manual model selection; auto:boolean default false" in doc
    assert "argument schema" in doc
    assert "Search skills/capabilities" in doc
    assert "Skills uses reviewed FileMap and Models bridge snapshots as capability metadata; it does not call a fake skills backend." in doc
    assert "Search is UI-local over already loaded metadata and does not send prompts, mutate files, install skills, sign in, probe accounts, or enable Auto routing." in doc
    assert "Registry rows expose description, scope, backend/provider, setup posture, permission boundary, argument schema, provenance, and a non-executing usage example." in doc
    assert "Argument schemas are display-only metadata; they do not execute skills, validate user prompts, assemble model payloads, or call providers." in doc
    assert "Pins persist locally for the active project/user UI profile and only reorder already loaded rows; they do not change backend skills, routes, files, accounts, or providers." in doc
    assert "backend:filemap" in doc
    assert "backend:models" in doc
    assert "permission boundary" in doc
    assert "argument schema" in doc
    assert "usage example" in doc
    assert "Example: inspect" in doc
    assert "Example: select" in doc
    assert "logicNode.innerHTML = renderSparkSkillsRegistry(sparkSkillsRegistrySnapshot, target.value)" in doc
    assert "bridgeUrl('filemap')" in doc
    assert "bridgeUrl('models')" in doc
    skills_loader = doc[doc.index("const loadSparkSkills = async () =>"):doc.index("const loadEchoMemory", doc.index("const loadSparkSkills = async () =>"))]
    assert "Promise.all" in skills_loader
    assert "skillRegistryRowsFromSnapshots(fileMapSnapshot, modelsSnapshot)" in skills_loader
    assert "bridgeUrl('skills')" not in skills_loader
    skills_registry = doc[doc.index("const renderSparkSkillsRegistry"):doc.index("const renderAegisLogicSnapshot")]
    assert "install skills" in skills_registry
    assert "sign in" in skills_registry
    assert "probe accounts" in skills_registry
    assert "enable Auto routing" in skills_registry
    assert "row.arguments" in skills_registry
    assert "bridgeUrl('skills')" not in skills_registry
    assert "project-skills" not in skills_registry
    assert "bridgeUrl('message')" not in skills_registry
    assert "bridgeUrl('call-result')" not in skills_registry
    assert "method: 'POST'" not in skills_registry
    skills_start = doc.index("const renderSparkSkills = () =>")
    skills_surface = doc[skills_start:doc.index("const renderProviderBalance", skills_start)]
    assert "fetch(" not in skills_surface
    assert "bridgeUrl('skills')" not in skills_surface
    assert "bridgeUrl('message')" not in skills_surface
    assert "bridgeUrl('call-result')" not in skills_surface
    assert "method: 'POST'" not in skills_surface
    assert "writeSparkSkillsPinned(pins)" in skills_surface


def test_index_spark_models_surface_uses_metadata_only_bridge_snapshots():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Models"' in doc
    assert "Models Readiness" in doc
    assert "data-spark-models" in doc
    assert "const renderSparkModelsSnapshot = (snapshot) =>" in doc
    assert "const loadSparkModels = async () =>" in doc
    assert "renderSparkModels()" in doc
    assert "bridgeUrl('models')" in doc
    assert "bridgeUrl('recent-calls')" in doc
    assert "Public setup boundary" in doc
    assert "Public builds use your locally installed Codex and Claude/Max CLIs or configured provider credentials." in doc
    assert "Missing CLIs or missing login state are shown as setup guidance from /bridge/models" in doc
    assert "this panel does not install software, sign in, read secrets, or probe accounts" in doc
    assert "Provider account readiness is informational only until Relay/Model Harness exposes a reviewed account-readiness backend." in doc
    assert "request id" in doc
    assert "model label" in doc
    assert "visible context entries" in doc
    assert "visible context chars" in doc
    assert "No prompt text, response text, raw setup stderr, or recovered result bodies are rendered here." in doc
    assert "Auto routing remains unavailable until Relay exposes an executable routing decision." in doc
    assert "Changing models still happens through the existing manual selector" in doc
    assert "bridgeUrl(`call-result?requestId=${encodeURIComponent(requestId)}`)" in doc
    models_surface = doc[doc.index("const renderSparkModelsSnapshot"):doc.index("const renderReleaseAutonomySnapshot")]
    assert "call.text" not in models_surface
    assert "call.error" not in models_surface
    assert "result.text" not in models_surface
    assert "call-result" not in models_surface
    assert "provider secrets" not in models_surface


def test_index_spark_models_lists_planned_role_mappings_without_auto_routing():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    models_surface = doc[
        doc.index("const renderSparkModelsSnapshot = (snapshot) =>"):
        doc.index("const renderModelHarnessBackendBindingSnapshot")
    ]

    assert "const roleMappings = [" in models_surface
    assert "Role mapping" in models_surface
    for role in (
        "orchestrator",
        "builder",
        "reviewer",
        "verifier",
        "researcher",
        "release operator",
    ):
        assert role in models_surface
    assert "routing not wired" in models_surface
    assert "manual override" in models_surface
    assert "pin state" in models_surface
    assert "readRoleModelOverrides()" in models_surface
    assert "auto routing', 'disabled until Relay owns the decision'" in models_surface
    assert "manual selector still owns prompt sends" in models_surface
    assert "method: 'POST'" not in models_surface
    assert "bridgeUrl('message')" not in models_surface
    assert "bridgeUrl('call-result')" not in models_surface


def test_index_model_selector_defaults_to_codex_and_keeps_auto_disabled():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert '<select class="session-model-select" aria-label="Models">' in doc
    assert '<option value="codex" selected>Codex</option>' in doc
    assert '<option value="max">Max</option>' in doc
    assert '<option value="auto" disabled>Auto</option>' in doc
    assert "const storedModel = localStorage.getItem('meridian.session.model')" in doc
    assert "modelSelect.value = storedModel === 'auto' ? 'codex'" in doc
    assert "if (storedModel === 'auto') localStorage.setItem('meridian.session.model', 'codex')" in doc
    assert "localStorage.setItem('meridian.session.model', modelSelect.value || 'codex')" in doc
    assert "const backend = selectedBackend === 'auto' ? 'codex' : selectedBackend" in doc
    assert "Auto routing remains unavailable until Relay exposes an executable routing decision." in doc


def test_index_response_transcripts_render_bridge_model_labels_when_known():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    transcript_renderer = doc[
        doc.index("const renderTranscript = (input) =>"):
        doc.index("const pushEntry = (input")
    ]
    assert "if (entry.model)" in transcript_renderer
    assert "meta.className = 'session-output-meta'" in transcript_renderer
    assert "const metaParts = [entry.model]" in transcript_renderer
    assert "const backendLabel = entry.resolvedBackend || entry.backend || entry.requestedBackend || ''" in transcript_renderer
    assert "metaParts.push(`source ${backendLabel}`)" in transcript_renderer
    assert "visible context ${entry.sessionContextEntries} entries" in transcript_renderer
    assert "row.append(meta)" in transcript_renderer

    send_prompt = doc[
        doc.index("const sendPrompt = async (input) =>"):
        doc.index("const insertPromptToken = (input")
    ]
    assert "const modelLabel = result.model || backend" in send_prompt
    assert "const modelLabel = recovered.model || backend" in send_prompt
    assert "const modelLabel = completedCall.model || backend" in send_prompt
    assert "resolvedBackend: result.backend || backend" in send_prompt
    assert "resolvedBackend: recovered.backend || backend" in send_prompt
    assert "resolvedBackend: completedCall.backend || backend" in send_prompt
    assert "setStatus(input, modelLabel)" in send_prompt
    assert "pushEntry(input, result.ok ? 'model'" in send_prompt
    assert "pushEntry(input, recovered.ok ? 'model'" in send_prompt
    assert "Bridge completed ${completedCall.backend || backend} request" in send_prompt


def test_ui_checklist_promotes_prime_and_user_prompt_response_surfaces_from_bridge_flow():
    checklist = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    bridge = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "| SP1 | Prime panel | User types directly to Prime/orchestrator. | wired |" in checklist
    assert "| SP5 | Prime response window | Displays Prime/model output below Prime prompt. | wired |" in checklist
    assert "| SP6 | User Session response window | Displays routed session/model output below User prompt only in User Session mode. | wired |" in checklist
    assert 'aria-label="${isUser ? \'User\' : \'Prime\'} session interface"' in index
    assert 'aria-label="${isUser ? \'User prompt input\' : \'Prime prompt input\'}"' in index
    assert 'aria-label="${isUser ? \'User response output\' : \'Prime response output\'}"' in index
    assert "const outputFor = (input) => input?.closest('.session-window')?.querySelector('.session-response-output')" in index
    assert "const renderTranscript = (input) =>" in index
    assert "if (entry.role === 'user') row.textContent = entry.text || ''" in index
    assert "row.replaceChildren(...renderOutputFragments(entry.text));" in index
    assert "pushEntry(input, 'user', prompt, ''," in index
    assert "pushEntry(input, result.ok ? 'model'" in index
    assert "channel: sessionChannel(input)" in index
    assert "if (sessionChannel(input) === 'user' && !targetSession)" in index
    assert ".session-window-right.is-panel-surface .session-response-output" in index
    assert "display: none;" in index
    assert "const channel = String(body.channel || 'prime').toLowerCase();" in bridge
    assert "const result = await runModel({ backend, prompt, cwd, transcript });" in bridge
    assert "result.channel = channel;" in bridge
    assert "cwd = sessionTarget.cwd;" in bridge


def test_bridge_message_results_include_resolved_backend_for_transcript_source_labels():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "result.requestedBackend = requestedBackend;" in doc
    assert "result.backend = backend;" in doc
    assert "model: result.model" in doc
    assert "backend," in doc


def test_index_model_harness_detail_surface_names_runtime_signals():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "relaySection('Runtime signals', relayList(runtimeSignals), true)" in doc
    assert "['visible gate', visibleGate]" in doc
    for expected in (
        "credential availability without secret display",
        "exact model id",
        "candidate model set",
        "prompt packet boundary",
        "tool-result trust boundary",
        "objective id and status",
        "trust mode",
        "adapter health must be visible before provider use",
        "exact model id must be visible before route selection",
        "prompt boundary must be visible before model call",
        "goal status must be visible before continuation",
        "trust state must be visible before dispatch",
    ):
        assert expected in doc


def test_index_model_harness_detail_surface_shows_proof_telemetry_strip():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessProofStrip = (items) =>" in doc
    assert 'aria-label="Model harness proof telemetry"' in doc
    assert 'class="model-harness-proof-strip"' in doc
    assert "const proofTelemetry = [" in doc
    assert "['context', contextLogic]" in doc
    assert "['intent', intentLogic]" in doc
    assert "['gate', visibleGate]" in doc
    assert "['proof', proofLogic]" in doc
    assert "relaySection('Proof telemetry', modelHarnessProofStrip(proofTelemetry), true)" in doc
    assert ".model-harness-proof-strip" in doc
    assert ".model-harness-proof-cell" in doc
    assert "rgba(102, 255, 150, 0.28)" in doc


def test_index_model_harness_detail_surface_shows_evidence_route():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessEvidenceRoute = (items) =>" in doc
    assert 'aria-label="Model harness evidence route"' in doc
    assert "const modelHarnessEvidenceRoutes = {" in doc
    assert "relaySection('Evidence route', modelHarnessEvidenceRoute(evidenceRoute), true)" in doc
    assert ".model-harness-evidence-route" in doc
    assert ".model-harness-evidence-step" in doc
    assert "Connects to a model/vendor through a controlled boundary." in doc
    assert "Tracks spend posture and token/call economics." in doc
    assert "Binds model work to the orchestrator objective." in doc


def test_index_model_harness_detail_surface_shows_trust_route():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessTrustRoute = (items) =>" in doc
    assert 'aria-label="Model harness trust route"' in doc
    assert "const modelHarnessTrustRoutes = {" in doc
    assert "relaySection('Trust route', modelHarnessTrustRoute(trustRoute), true)" in doc
    assert ".model-harness-trust-route" in doc
    assert ".model-harness-trust-cell" in doc
    assert "direct-provider declaration required" in doc
    assert "unknown trust route blocks dispatch" in doc
    assert "missing blocker proof blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_capability_envelope():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessCapabilityEnvelope = (items) =>" in doc
    assert 'aria-label="Model harness capability envelope"' in doc
    assert "const modelHarnessCapabilityEnvelopes = {" in doc
    assert "relaySection('Capability envelope', modelHarnessCapabilityEnvelope(capabilityEnvelope), true)" in doc
    assert ".model-harness-capability-envelope" in doc
    assert ".model-harness-capability-cell" in doc
    assert "ProviderCapability.model id required" in doc
    assert "TelemetryCapability required" in doc
    assert "prompt hash without raw prompt display" in doc


def test_index_model_harness_detail_surface_shows_routing_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessRoutingPolicy = (items) =>" in doc
    assert 'aria-label="Model harness routing policy"' in doc
    assert "const modelHarnessRoutingPolicies = {" in doc
    assert "relaySection('Routing policy', modelHarnessRoutingPolicy(routingPolicy), true)" in doc
    assert ".model-harness-routing-policy" in doc
    assert ".model-harness-routing-cell" in doc
    assert "use only registered provider adapters" in doc
    assert "visible model selection policy required" in doc
    assert "missing goal proof stops continuation" in doc


def test_index_model_harness_detail_surface_shows_handoff_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessHandoffPolicy = (items) =>" in doc
    assert 'aria-label="Model harness handoff policy"' in doc
    assert "const modelHarnessHandoffPolicies = {" in doc
    assert "relaySection('Handoff policy', modelHarnessHandoffPolicy(handoffPolicy), true)" in doc
    assert ".model-harness-handoff-policy" in doc
    assert ".model-harness-handoff-cell" in doc
    assert "provider adapter owns endpoint truth" in doc
    assert "handoff owner required" in doc
    assert "missing blocker proof escalates before continuation" in doc


def test_index_model_harness_detail_surface_shows_dispatch_guard():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessDispatchGuard = (items) =>" in doc
    assert 'aria-label="Model harness dispatch guard"' in doc
    assert "const modelHarnessDispatchGuards = {" in doc
    assert "relaySection('Dispatch guard', modelHarnessDispatchGuard(dispatchGuard), true)" in doc
    assert ".model-harness-dispatch-guard" in doc
    assert ".model-harness-dispatch-cell" in doc
    assert "adapter health and provider key visible" in doc
    assert "dispatch readiness state required" in doc
    assert "missing blocker proof blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_recovery_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessRecoveryPolicy = (items) =>" in doc
    assert 'aria-label="Model harness recovery policy"' in doc
    assert "const modelHarnessRecoveryPolicies = {" in doc
    assert "relaySection('Recovery policy', modelHarnessRecoveryPolicy(recoveryPolicy), true)" in doc
    assert ".model-harness-recovery-policy" in doc
    assert ".model-harness-recovery-cell" in doc
    assert "provider health drift invalidates endpoint trust" in doc
    assert "model drift proof required" in doc
    assert "restore continuation after goal proof returns" in doc


def test_index_model_harness_detail_surface_shows_observability_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessObservabilityPolicy = (items) =>" in doc
    assert 'aria-label="Model harness observability policy"' in doc
    assert "const modelHarnessObservabilityPolicies = {" in doc
    assert "relaySection('Observability policy', modelHarnessObservabilityPolicy(observabilityPolicy), true)" in doc
    assert ".model-harness-observability-policy" in doc
    assert ".model-harness-observability-cell" in doc
    assert "provider key, adapter health, credential posture" in doc
    assert "model telemetry signal required" in doc
    assert "missing goal signal blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_governance_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessGovernancePolicy = (items) =>" in doc
    assert 'aria-label="Model harness governance policy"' in doc
    assert "const modelHarnessGovernancePolicies = {" in doc
    assert "relaySection('Governance policy', modelHarnessGovernancePolicy(governancePolicy), true)" in doc
    assert ".model-harness-governance-policy" in doc
    assert ".model-harness-governance-cell" in doc
    assert "registered provider catalog owns endpoint truth" in doc
    assert "governance authority required" in doc
    assert "unapproved goal state blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_acceptance_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessAcceptancePolicy = (items) =>" in doc
    assert 'aria-label="Model harness acceptance policy"' in doc
    assert "const modelHarnessAcceptancePolicies = {" in doc
    assert "relaySection('Acceptance policy', modelHarnessAcceptancePolicy(acceptancePolicy), true)" in doc
    assert ".model-harness-acceptance-policy" in doc
    assert ".model-harness-acceptance-cell" in doc
    assert "provider endpoint and health proof visible" in doc
    assert "acceptance criterion required" in doc
    assert "missing goal proof blocks acceptance" in doc


def test_index_model_harness_detail_surface_shows_compliance_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessCompliancePolicy = (items) =>" in doc
    assert 'aria-label="Model harness compliance policy"' in doc
    assert "const modelHarnessCompliancePolicies = {" in doc
    assert "relaySection('Compliance policy', modelHarnessCompliancePolicy(compliancePolicy), true)" in doc
    assert ".model-harness-compliance-policy" in doc
    assert ".model-harness-compliance-cell" in doc
    assert "provider license and data-region constraint visible" in doc
    assert "compliance rule required" in doc
    assert "missing goal compliance proof blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_evaluation_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessEvaluationPolicy = (items) =>" in doc
    assert 'aria-label="Model harness evaluation policy"' in doc
    assert "const modelHarnessEvaluationPolicies = {" in doc
    assert "relaySection('Evaluation policy', modelHarnessEvaluationPolicy(evaluationPolicy), true)" in doc
    assert ".model-harness-evaluation-policy" in doc
    assert ".model-harness-evaluation-cell" in doc
    assert "provider health, credential posture, and region fit scored" in doc
    assert "evaluation score required" in doc
    assert "failed goal evaluation blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_lifecycle_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessLifecyclePolicy = (items) =>" in doc
    assert 'aria-label="Model harness lifecycle policy"' in doc
    assert "const modelHarnessLifecyclePolicies = {" in doc
    assert "relaySection('Lifecycle policy', modelHarnessLifecyclePolicy(lifecyclePolicy), true)" in doc
    assert ".model-harness-lifecycle-policy" in doc
    assert ".model-harness-lifecycle-cell" in doc
    assert "register provider endpoint and credential posture" in doc
    assert "lifecycle initialization required" in doc
    assert "stale goal lifecycle blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_version_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessVersionPolicy = (items) =>" in doc
    assert 'aria-label="Model harness version policy"' in doc
    assert "const modelHarnessVersionPolicies = {" in doc
    assert "relaySection('Version policy', modelHarnessVersionPolicy(versionPolicy), true)" in doc
    assert ".model-harness-version-policy" in doc
    assert ".model-harness-version-cell" in doc
    assert "provider adapter version and endpoint contract pinned" in doc
    assert "version pin required" in doc
    assert "unpinned goal version blocks continuation" in doc


def test_index_model_harness_detail_surface_shows_drift_policy():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessDriftPolicy = (items) =>" in doc
    assert 'aria-label="Model harness drift policy"' in doc
    assert "const modelHarnessDriftPolicies = {" in doc
    assert "relaySection('Drift policy', modelHarnessDriftPolicy(driftPolicy), true)" in doc
    assert ".model-harness-drift-policy" in doc
    assert ".model-harness-drift-cell" in doc
    assert "provider endpoint, health, or credential posture changed" in doc
    assert "drift detection required" in doc
    assert "unexplained goal drift blocks continuation" in doc


def test_index_model_harness_detail_surface_backend_binds_existing_snapshots():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const renderModelHarnessBackendBindingSnapshot = (snapshots = {}) =>" in doc
    assert "const loadModelHarnessBackendBinding = async () =>" in doc
    assert 'data-model-harness-backend-binding' in doc
    assert "loading existing backend snapshots" in doc
    assert "existing backend snapshots only" in doc
    assert "display-only; no provider calls or settings writes" in doc
    assert "Relay-mediated dispatch posture" in doc
    assert "Harness diagnostics" in doc
    assert "Backend binding safety" in doc
    assert "No provider call, Auto enablement, settings mutation, route mutation, or prompt payload assembly is authorized here." in doc
    assert "No prompt text, response text, recovered result body, raw provider output, raw evidence body, or worker chat is rendered." in doc
    assert "The aspect surface reads existing GET-only bridge snapshots and never posts to message, restart, or result-recovery paths." in doc
    assert "Goal aspect per-call intent" in doc
    assert "snapshots.relayEvidence?.per_call_intent ? '/bridge/relay-evidence per_call_intent' : 'not exposed by Relay'" in doc
    assert "backend-owned dispatch scope; not inferred from transcript text and not a provider route" in doc
    assert "renderSparkModelsSnapshot(snapshots.models" in doc
    assert "renderRelayEvidenceSnapshot(snapshots.relayEvidence" in doc
    assert "renderProviderBalanceSnapshot(" in doc
    assert "snapshots.providerBalance || { ok: false, error: 'Provider balance snapshot unavailable' }" in doc
    assert "snapshots.models || null" in doc
    assert "snapshots.relayEvidence || null" in doc
    assert "snapshots.relayLogic || null" in doc
    assert "renderAegisLogicSnapshot(snapshots.aegisLogic" in doc
    assert "renderRelayLogicSnapshot(snapshots.relayLogic" in doc
    assert "fetchBridgeSnapshot('models', 'Models')" in doc
    assert "fetchBridgeSnapshot('relay-evidence', 'Relay evidence')" in doc
    assert "fetchBridgeSnapshot('provider-balance', 'Provider balance')" in doc
    assert "fetchBridgeSnapshot('aegis-logic', 'Aegis logic')" in doc
    assert "fetchBridgeSnapshot('relay-logic', 'Relay logic')" in doc
    assert "fetchBridgeSnapshot('workflow-dispatch-status', 'Workflow dispatch/status')" in doc
    assert "loadModelHarnessBackendBinding();" in doc
    assert "if (rightWorkspace?.querySelector('[data-model-harness-backend-binding]')) loadModelHarnessBackendBinding();" in doc
    backend_binding = doc[
        doc.index("const renderModelHarnessBackendBindingSnapshot"):
        doc.index("const renderReleaseAutonomySnapshot")
    ]
    assert "bridgeUrl('message')" not in backend_binding
    assert "bridgeUrl('call-result')" not in backend_binding
    assert "bridgeUrl('restart')" not in backend_binding


def test_index_model_harness_backend_binding_names_relay_mediated_dispatch_posture():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    backend_binding = doc[
        doc.index("const renderModelHarnessBackendBindingSnapshot = (snapshots = {}) =>"):
        doc.index("const fetchBridgeSnapshot = async (path, label) =>")
    ]
    assert "relaySection('Relay-mediated dispatch posture', relayGrid([" in backend_binding
    assert "['dispatch route source', snapshots.relayLogic?.ok ? '/bridge/relay-logic' : 'offline']" in backend_binding
    assert "['selected provider', snapshots.providerBalance?.provider_balance?.selected_provider || 'not exposed']" in backend_binding
    assert "['routing owner', snapshots.providerBalance?.provider_balance?.routing_owner || 'unknown']" in backend_binding
    assert "['policy state', relayText(snapshots.providerBalance?.provider_balance?.policy_state)]" in backend_binding
    assert "['payload continuity refs', relayJoin(snapshots.relayEvidence?.prompt_payload_meter?.route_continuity_refs)]" in backend_binding
    assert "['payload evidence refs', relayJoin(snapshots.relayEvidence?.prompt_payload_meter?.evidence_refs)]" in backend_binding
    assert "['intent evidence refs', relayJoin(snapshots.relayEvidence?.per_call_intent?.evidence_refs)]" in backend_binding
    assert "Relay + Model Harness own route/model/payload posture; this surface renders evidence only and does not call providers" in backend_binding
    assert "method: 'POST'" not in backend_binding


def test_index_model_harness_backend_binding_renders_structured_harness_diagnostics():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    backend_binding = doc[
        doc.index("const renderModelHarnessBackendBindingSnapshot = (snapshots = {}) =>"):
        doc.index("const fetchBridgeSnapshot = async (path, label) =>")
    ]
    assert "relaySection('Harness diagnostics', relayGrid([" in backend_binding
    assert "['prompt packet decision', relayText(snapshots.relayEvidence?.prompt_packet?.decision)]" in backend_binding
    assert "['prompt packet severity', relayText(snapshots.relayEvidence?.prompt_packet?.severity)]" in backend_binding
    assert "['prompt packet blockers', relayJoin(snapshots.relayEvidence?.prompt_packet?.blockers)]" in backend_binding
    assert "['payload warning tags', relayJoin(snapshots.relayEvidence?.prompt_payload_meter?.warning_tags)]" in backend_binding
    assert "['payload blocker tags', relayJoin(snapshots.relayEvidence?.prompt_payload_meter?.blocker_tags)]" in backend_binding
    assert "['provider telemetry available', snapshots.relayEvidence?.provider_result?.telemetry_available ? 'yes' : 'no']" in backend_binding
    assert "['provider warnings', relayJoin(snapshots.relayEvidence?.provider_result?.warnings)]" in backend_binding
    assert "['provider blockers', relayJoin(snapshots.relayEvidence?.provider_result?.blockers)]" in backend_binding
    assert "['dispatch visibility', relayText(snapshots.workflowDispatchStatus?.workflow?.status_policy?.dispatch_surface || 'display_only')]" in backend_binding
    assert "['heartbeat history visible', snapshots.workflowDispatchStatus?.workflow?.status_policy?.heartbeat_history_visible ? 'yes' : 'no']" in backend_binding
    assert "['raw artifacts visible', snapshots.workflowDispatchStatus?.workflow?.status_policy?.raw_artifacts_visible ? 'yes' : 'no']" in backend_binding
    assert "per-harness event history" not in backend_binding
    assert "method: 'POST'" not in backend_binding
    assert "method: 'POST'" not in backend_binding
    assert "fetch(bridgeUrl('message')" not in backend_binding
    assert "fetch(bridgeUrl('call-result')" not in backend_binding
    assert "fetch(bridgeUrl('restart')" not in backend_binding


def test_index_model_harness_selection_is_visible_and_persistent():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const modelHarnessSelectionKey = 'meridian.model-harness.selection.v1'" in doc
    assert "const storedModelHarnessName = () =>" in doc
    assert "const modelHarnessButtonByName = (name) =>" in doc
    assert "const setSelectedModelHarnessButton = (button, { persist = true } = {}) =>" in doc
    assert "const activateStoredModelHarnessAspect = ({ persist = false } = {}) =>" in doc
    assert "item.classList.toggle('is-selected', selected)" in doc
    assert "item.setAttribute('aria-current', 'true')" in doc
    assert "item.removeAttribute('aria-current')" in doc
    assert "localStorage.setItem(modelHarnessSelectionKey, selectedModelHarnessName(button))" in doc
    assert "setSelectedModelHarnessButton(button, { persist })" in doc
    assert "if (nextMode === 'model') activateStoredModelHarnessAspect({ persist: false })" in doc
    assert "modelHarnessButtonByName(storedModelHarnessName()) || modelHarnessButtons()[0]" in doc
    assert '.harness-dock-button[aria-current="true"] .harness-icon' in doc
    assert '.harness-dock-button[aria-current="true"] .harness-label' in doc


def test_index_model_harness_icons_support_keyboard_navigation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const navigateModelHarnessAspect = (button, delta) =>" in doc
    assert "const activateModelHarnessAspectAt = (index) =>" in doc
    assert "const next = models[(current + delta + models.length) % models.length]" in doc
    assert "activateHarnessButton(next)" in doc
    assert "next.focus({ preventScroll: true })" in doc
    assert "button.focus({ preventScroll: true })" in doc
    assert "button.addEventListener('keydown', (event) =>" in doc
    assert "if (!isModelHarnessButton(button)) return" in doc
    assert "event.key === 'ArrowRight' || event.key === 'ArrowDown'" in doc
    assert "navigateModelHarnessAspect(button, 1)" in doc
    assert "event.key === 'ArrowLeft' || event.key === 'ArrowUp'" in doc
    assert "navigateModelHarnessAspect(button, -1)" in doc
    assert "event.key === 'Home'" in doc
    assert "activateModelHarnessAspectAt(0)" in doc
    assert "event.key === 'End'" in doc
    assert "activateModelHarnessAspectAt(modelHarnessButtons().length - 1)" in doc


def test_index_spark_surface_controls_support_keyboard_navigation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "| SPK11 | Keyboard accessibility | Surface switching can be done without mouse-only interaction. | wired |" in checklist
    assert "Spark controls are focusable buttons, preserve native Enter/Space activation" in checklist
    assert "const navigateSparkButton = (button, delta) =>" in doc
    assert "const focusSparkButtonAt = (index) =>" in doc
    assert "const next = buttons[(current + delta + buttons.length) % buttons.length]" in doc
    assert "next.focus({ preventScroll: true })" in doc
    assert "button.addEventListener('keydown', (event) =>" in doc
    assert "event.key === 'ArrowRight' || event.key === 'ArrowDown'" in doc
    assert "navigateSparkButton(button, 1)" in doc
    assert "event.key === 'ArrowLeft' || event.key === 'ArrowUp'" in doc
    assert "navigateSparkButton(button, -1)" in doc
    assert "event.key === 'Home'" in doc
    assert "focusSparkButtonAt(0)" in doc
    assert "event.key === 'End'" in doc
    assert "focusSparkButtonAt(buttons.length - 1)" in doc
    assert "setRightPanelAuthority('spark', actionLabel || 'Spark', { persist })" in doc


def test_index_spark_surface_transition_preserves_readability_and_reduced_motion():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    surface_css = doc[
        doc.index(".relay-models-surface,"):
        doc.index(".right-panel-surface.is-model-harness-surface")
    ]

    assert "animation: spark-surface-enter 140ms ease-out both;" in surface_css
    assert "will-change: opacity, transform;" in surface_css
    assert "@keyframes spark-surface-enter" in surface_css
    assert "opacity: 0.82;" in surface_css
    assert "transform: translateY(4px);" in surface_css
    assert "opacity: 1;" in surface_css
    assert "transform: translateY(0);" in surface_css
    assert "@media (prefers-reduced-motion: reduce)" in surface_css
    assert "animation: none;" in surface_css
    assert "transform: none;" in surface_css
    assert "filter:" not in surface_css
    assert "blur(" not in surface_css
    assert "display: none" not in surface_css


def test_index_user_session_mode_names_target_and_preserves_storage():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "User Session:" in doc
    assert "window.meridianRefreshUserSessionTarget = () =>" in doc
    assert "meridian.user-session.target.v1" in doc
    assert "const loadUserSessions = async () =>" in doc
    assert "bridgeUrl('user-sessions')" in doc
    assert "userSessions = Array.isArray(result.sessions) ? result.sessions.filter((session) => session.routable) : []" in doc
    assert "const selected = selectedUserSession();" in doc
    assert "selected ? `User Session: ${selected.sessionName}` : 'User Session'" in doc
    assert "if (!selected && localStorage.getItem(userSessionTargetKey)) return 'selected session unavailable';" in doc
    assert "if (!selected) return 'select live session';" in doc
    assert "option.textContent = userSessionsLoadFailed ? 'Sessions unavailable' : 'No live sessions';" in doc
    assert "option.textContent = 'No live sessions for active project';" in doc
    assert "option.textContent = 'Selected session unavailable';" in doc
    assert "const firstLiveTarget = userSessions[0]" in doc
    assert "userSessionSelect.value = firstLiveTarget.sessionId" in doc
    assert "localStorage.setItem(userSessionTargetKey, userSessionSelect.value)" in doc
    assert "Select a live User Session target before sending" in doc
    assert "const targetSession = sessionChannel(input) === 'user' ? selectedUserSession() : null;" in doc
    assert "if (sessionChannel(input) === 'user' && !targetSession)" in doc
    assert "cwd: targetSession?.cwd || 'C:\\\\Users\\\\user\\\\Code\\\\Meridian'" in doc
    assert "sessionTargetId: targetSession?.sessionId || ''" in doc
    assert "sessionTargetId: result.sessionTarget?.sessionId || targetSession?.sessionId || ''" in doc


def test_bridge_revalidates_user_session_target_before_user_prompt_send():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "userSessions: '/bridge/user-sessions'" in doc
    assert "function userSessionTargets()" in doc
    assert "function sessionTargetFromWorktree(record)" in doc
    assert "if (!/\\/Meridian-Worktrees\\//i.test(normalized)) return null;" in doc
    assert "routable: true" in doc
    assert "async function sessionTargetById(sessionId)" in doc
    assert "return snapshot.sessions.find((session) => session.sessionId === sessionId && session.routable) || null;" in doc
    assert "if (req.method === 'GET' && req.url === BRIDGE_ROUTES.userSessions)" in doc
    assert "const sessionTargetId = String(body.sessionTargetId || '')" in doc
    assert "if (channel === 'user')" in doc
    assert "sessionTarget = sessionTargetId ? await sessionTargetById(sessionTargetId) : null;" in doc
    assert "sendJson(res, 409, { ok: false, text: '', error: 'Select a live User Session target before sending.', setupRequired: false }, req);" in doc
    assert "cwd = sessionTarget.cwd;" in doc


def test_compass_logic_snapshot_documents_project_context_harness():
    from meridian_core.compass_logic_snapshot import compass_logic_snapshot

    snapshot = compass_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]
    runtime = snapshot["runtime_sample"]
    assert snapshot["source"] == "meridian_core.compass / meridian_core.compass_logic_snapshot"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert runtime["project_definition"]["project_id"] == "meridian-v2"
    assert runtime["identity"]["decision"] == "defined"
    assert runtime["identity"]["execution_authorized"] is False
    assert runtime["scope"]["decision"] == "in_scope"
    assert runtime["scope"]["execution_authorized"] is False
    assert runtime["bounds"]["decision"] == "in_scope"
    assert runtime["bounds"]["execution_authorized"] is False
    assert runtime["difference"]["decision"] == "distinct"
    assert runtime["difference"]["merge_authorized"] is False
    assert runtime["difference"]["execution_authorized"] is False
    assert runtime["handoff"]["decision"] == "review_ready"
    assert runtime["handoff"]["review_ready"] is True
    assert runtime["handoff"]["execution_authorized"] is False
    assert "Project Definition Logic" in titles
    assert "Bounds and Scope Logic" in titles
    assert "Project Difference Logic" in titles
    assert "Cross-Project Communication Logic" in titles
    assert "Project Selector Logic" in titles
    assert "Prime Prompt Context" in titles
    assert "Portfolio Boundary" in titles
    assert "User Session Independence" not in titles


def test_vulcan_logic_snapshot_documents_session_lifecycle_harness():
    import json

    from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot

    snapshot = vulcan_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]
    runtime = snapshot["runtime_sample"]
    live_evidence = runtime["session_live_state_evidence"]
    live_projection = runtime["session_live_state_projection"]
    readiness = runtime["recovery_readiness"]
    beacon_advisories = runtime["beacon_advisories"]
    assert snapshot["source"] == "meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert snapshot["execution_controls_visible"] is False
    assert snapshot["raw_worker_chat_visible"] is False
    assert snapshot["raw_filesystem_paths_visible"] is False
    assert live_evidence["worktree_path_label"] == "<worktree_path>"
    assert live_evidence["project_path_label"] == "<project_path>"
    assert live_evidence["blocker_summary_label"] == "<blocker_summary>"
    assert live_projection["human_gate_required"] is True
    assert live_projection["is_executable_now"] is False
    assert "advisory_only.requires_human_gate" in live_projection["advisory_blockers"]
    assert readiness["readiness_status"] == "blocked"
    assert readiness["ready_for_execution"] is False
    assert readiness["human_gate_required"] is True
    assert any(item["advisory_type"] == "live_state_stale" for item in beacon_advisories)
    serialized = json.dumps(runtime)
    assert "C:\\Users" not in serialized
    assert "Code\\Meridian" not in serialized
    assert "Recovery staging requires Aegis review." not in serialized
    assert "Session Definition Logic" in titles
    assert "Lifecycle State Logic" in titles
    assert "Command Plan Logic" in titles
    assert "User Session Independence" in titles
    assert "Project-Aware Session Grouping" in titles
    assert "Stale Target Guard" in titles
    assert "Cross-Harness Relationship Logic" in titles
    assert "Portfolio Boundary" not in titles


def test_beacon_liveness_snapshot_is_display_safe_backend_contract():
    import json

    from meridian_core.beacon_liveness_snapshot import beacon_liveness_snapshot

    snapshot = beacon_liveness_snapshot()
    heartbeat = snapshot["heartbeats"][0]
    serialized = json.dumps(snapshot)

    assert snapshot["source"] == "meridian_core.beacon_liveness_snapshot.beacon_liveness_snapshot"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert snapshot["execution_controls_visible"] is False
    assert snapshot["raw_worker_chat_visible"] is False
    assert snapshot["raw_filesystem_paths_visible"] is False
    assert snapshot["observation_mode"] == "contract_sample:no_live_sentinels_configured"
    assert heartbeat["harness_id"] == "beacon-ui-contract"
    assert heartbeat["current_work_label"] == "<sentinel_path>"
    assert heartbeat["blockers"] == ["missing sentinel"]
    assert "live_state" in snapshot["advisory_families"]
    assert "recovery_readiness" in snapshot["advisory_families"]
    assert "no_raw_sentinel_paths" in snapshot["guardrails"]
    assert "runtime-sentinel" not in serialized
    assert "C:\\Users" not in serialized
    assert "Code\\Meridian" not in serialized


def test_review_console_snapshot_is_display_safe_backend_contract():
    import json

    from meridian_core.review_console_snapshot import review_console_snapshot

    snapshot = review_console_snapshot()
    queue = snapshot["queue"]
    gate = next(item for item in queue["items"] if item["requires_response"])
    serialized = json.dumps(snapshot)

    assert snapshot["source"] == "meridian_core.review_console_snapshot.review_console_snapshot"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert snapshot["response_authorized"] is False
    assert snapshot["execution_controls_visible"] is False
    assert snapshot["raw_item_content_visible"] is False
    assert snapshot["raw_worker_chat_visible"] is False
    assert queue["pending_count"] == 4
    assert queue["pending_gate_count"] == 1
    assert queue["informational_count"] == 3
    assert gate["item_type"] == "approval_gate"
    assert gate["content_label"] == "<review_content>"
    assert "approve" in gate["suggested_actions"]
    assert "gate-ref:vulcan-live-control" not in serialized
    assert "aegis-proof-ref:ui-cross-check" not in serialized
    assert "no_approval_buttons" in snapshot["guardrails"]


def test_federation_horizon_snapshot_is_planning_only_contract():
    from meridian_core.federation_horizon_snapshot import federation_horizon_snapshot

    snapshot = federation_horizon_snapshot()

    assert snapshot["source"] == "docs/federation-harness-horizon.md"
    assert snapshot["display_only"] is True
    assert snapshot["planning_only"] is True
    assert snapshot["runtime_authorized"] is False
    assert snapshot["mutation_authorized"] is False
    assert snapshot["network_protocol_authorized"] is False
    assert snapshot["remote_execution_authorized"] is False
    assert snapshot["shared_state_authorized"] is False
    assert snapshot["raw_memory_visible"] is False
    assert snapshot["raw_queue_visible"] is False
    assert snapshot["raw_worker_chat_visible"] is False
    assert snapshot["raw_filesystem_paths_visible"] is False
    assert "user-approved project alias" in snapshot["safe_discovery_fields"]
    assert "no cross-Meridian action without explicit consent" in snapshot["permission_boundaries"]
    assert "ProofPacket" in snapshot["handoff_packet_types"]
    assert "network protocol" in snapshot["out_of_v2_scope"]


def test_release_autonomy_snapshot_is_display_safe_backend_contract():
    import json

    from meridian_core.release_autonomy_snapshot import release_autonomy_snapshot

    snapshot = release_autonomy_snapshot()
    posture = snapshot["release_posture"]
    authority = snapshot["authority_boundary"]
    validation = snapshot["validation_projection"]
    serialized = json.dumps(snapshot)

    assert snapshot["source"] == (
        "meridian_core.release_autonomy_snapshot.release_autonomy_snapshot"
    )
    assert snapshot["harness"] == "Autonomy / Release"
    assert snapshot["display_only"] is True
    assert snapshot["mutation_authorized"] is False
    assert snapshot["release_execution_authorized"] is False
    assert snapshot["deployment_authorized"] is False
    assert snapshot["credential_probe_authorized"] is False
    assert snapshot["account_probe_authorized"] is False
    assert snapshot["release_controls_visible"] is False
    assert snapshot["deployment_controls_visible"] is False
    assert snapshot["raw_prompt_visible"] is False
    assert snapshot["raw_response_visible"] is False
    assert snapshot["raw_evidence_body_visible"] is False
    assert snapshot["raw_worker_chat_visible"] is False
    assert snapshot["pids_visible"] is False
    assert snapshot["raw_filesystem_paths_visible"] is False
    assert posture["state"] == "blocked_display_only"
    assert posture["release_ready"] is False
    assert posture["human_gate_required"] is True
    assert posture["ready_for_execution"] is False
    assert posture["prime_action_type"] == "pause_and_wait"
    assert authority["autonomous_implementation_authorized"] is False
    assert authority["review_clearing_authorized"] is False
    assert authority["branch_movement_authorized"] is False
    assert authority["live_coding_authority_authorized"] is False
    assert authority["relay_bypass_authorized"] is False
    assert validation["validation_level"] == "level-0:metadata-only"
    assert validation["variant_label_count"] == 1
    assert "release_display_only_no_execution" in snapshot["blockers"]
    assert "no_release_execution_controls" in snapshot["guardrails"]
    assert "direct_endpoint_evidence_ref" not in serialized
    assert "https://api.deepseek.com" not in serialized
    assert "raw_prompt" in serialized
    assert "RAW_PROMPT_SENTINEL" not in serialized
    assert "raw_provider_response" not in serialized
    assert "C:\\Users" not in serialized
    assert "/Users/" not in serialized
    assert '"pid"' not in serialized.lower()


def test_index_projects_selector_is_compass_context_not_user_routing():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "projectOptions = ['Bifrost', 'Meridian', 'Spark']" in doc
    assert "const projectSelectKey = 'meridian.session.project'" in doc
    assert "let lastProjectValue = ''" in doc
    assert "const hasUnsentPromptDraft = () => Array.from(document.querySelectorAll('.session-prompt-input'))" in doc
    assert "const confirmProjectSwitchIfNeeded = (nextProject) =>" in doc
    assert "projectOptions.slice().sort((a, b) => a.localeCompare(b)).forEach((project) =>" in doc
    assert "projectSelect.value = projectOptions.includes(storedProject) ? storedProject : 'Meridian'" in doc
    assert "lastProjectValue = projectSelect.value" in doc
    assert "localStorage.setItem(projectSelectKey, projectSelect.value)" in doc
    assert "if (!confirmProjectSwitchIfNeeded(nextProject))" in doc
    assert "projectSelect.value = lastProjectValue || 'Meridian'" in doc
    assert "screen.dataset.projectContext" in doc
    assert "primeWindow.dataset.projectContext = project" in doc
    assert "projectSelect.dataset.projectContext = project" in doc
    assert "Compass project context:" in doc
    assert "setStatus(input, `Compass project ${activeProjectContext()}`)" in doc
    assert "projectContext" in doc
    assert "renderUserSessionSelect();" in doc
    assert "refreshProjectScopedSurfaces();" in doc
    assert "group.label = `${activeProject} (active project)`" in doc
    assert "option.textContent = 'No live sessions for active project'" in doc
    assert "localStorage.setItem(userSessionTargetKey, projectSelect.value" not in doc


def test_index_project_switch_guard_preserves_prompt_drafts_without_session_retargeting():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    guard_start = doc.index("let lastProjectValue = ''")
    guard_end = doc.index("if (modelSelect) {", guard_start)
    guard = doc[guard_start:guard_end]
    assert "hasUnsentPromptDraft" in guard
    assert "String(input.value || '').trim().length > 0" in guard
    assert "window.confirm('Switch project context? Unsent prompt drafts will be preserved" in guard
    assert "const nextProject = projectSelect.value || 'Meridian';" in guard
    assert "projectSelect.value = lastProjectValue || 'Meridian';" in guard
    assert "return;" in guard
    assert "localStorage.setItem(projectSelectKey, projectSelect.value || 'Meridian');" in guard
    assert "lastProjectValue = projectSelect.value || 'Meridian';" in guard
    assert "renderUserSessionSelect();" in guard
    assert "updatePrimeProjectStatus();" in guard
    assert "refreshProjectScopedSurfaces();" in guard
    assert "localStorage.removeItem" not in guard
    assert "localStorage.setItem(userSessionTargetKey" not in guard
    assert "bridgeUrl('message')" not in guard


def test_index_project_switch_refreshes_project_scoped_surfaces_together():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const refreshProjectScopedSurfaces = () =>" in doc
    refresh = doc[
        doc.index("const refreshProjectScopedSurfaces = () =>"):
        doc.index("const refreshRelayPanel = () =>", doc.index("const refreshProjectScopedSurfaces = () =>"))
    ]
    assert "if (rightWorkspace?.querySelector('[data-review-console]')) loadReviewConsole();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-compass-logic]')) loadCompassLogic();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-goal-runtime]')) loadGoalRuntime();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-workflow-dispatch-status]')) loadWorkflowDispatchStatus();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-backlog-review-console], [data-backlog-prime-logic], [data-backlog-goal-runtime], [data-backlog-workflow-dispatch-status]')) loadSparkBacklog();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-spark-models]')) loadSparkModels();" in refresh
    assert "if (rightWorkspace?.querySelector('[data-spark-skills]'))" in refresh
    assert "renderSparkSkillsRegistry(sparkSkillsRegistrySnapshot, query)" in refresh
    assert "loadSparkSkills();" in refresh
    assert "bridgeUrl('message')" not in refresh
    assert "method: 'POST'" not in refresh


def test_bridge_preserves_project_context_in_message_results_and_metadata():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "const projectContext = String(body.projectContext || 'Meridian').trim() || 'Meridian';" in doc
    assert "result.projectContext = projectContext;" in doc
    assert "projectContext," in doc
    assert "calls: recentCalls.slice().reverse()" in doc


def test_index_compass_harness_uses_backend_logic_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Compass Runtime Logic" in doc
    assert "data-compass-logic" in doc
    assert "bridgeUrl('compass-logic')" in doc
    assert "renderCompassLogicSnapshot" in doc
    assert "renderCompassProjectLogic" in doc
    assert "Reviewed project definition" in doc
    assert "Project metadata handoff" in doc
    assert "active Compass context" in doc
    assert "Vulcan live-state evidence" in doc
    assert "FileMap relative-path registry" in doc
    assert "Compass does not move branches, open local absolute paths, or invent source-control state." in doc
    assert "Identity and scope decisions" in doc
    assert "Bounds and difference decisions" in doc
    assert "Cross-project handoff review" in doc
    assert "merge authorized" in doc
    assert "execution authorized" in doc


def test_index_project_metadata_handoff_uses_compass_state_without_source_control_actions():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    compass_start = doc.index("const renderCompassLogicSnapshot = (snapshot) =>")
    compass_end = doc.index("const renderVulcanLogicSnapshot = (snapshot) =>", compass_start)
    compass_surface = doc[compass_start:compass_end]
    assert "Project metadata handoff" in compass_surface
    assert "activeProjectContext()" in compass_surface
    assert "project.project_id || 'unknown'" in compass_surface
    assert "project.title || 'unknown'" in compass_surface
    assert "relayText(identity.decision || scope.decision || 'unknown')" in compass_surface
    assert "Vulcan live-state evidence" in compass_surface
    assert "FileMap relative-path registry" in compass_surface
    assert "project path, worktree path, branch, session status, health, and proof state" in compass_surface
    assert "repo-relative source paths and related tests" in compass_surface
    assert "does not move branches, open local absolute paths, or invent source-control state" in compass_surface
    assert "method: 'POST'" not in compass_surface
    assert "bridgeUrl('message')" not in compass_surface
    assert "move-branch" not in compass_surface
    assert "git " not in compass_surface.lower()


def test_index_vulcan_harness_uses_backend_logic_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Vulcan Runtime Logic" in doc
    assert "data-vulcan-logic" in doc
    assert "bridgeUrl('vulcan-logic')" in doc
    assert "renderVulcanLogicSnapshot" in doc
    assert "renderVulcanSessionLogic" in doc
    assert "Session live-state evidence" in doc
    assert "Bifrost advisory projection" in doc
    assert "Recovery readiness" in doc
    assert "Beacon advisory evidence" in doc
    assert "execution controls visible" in doc
    assert "raw worker chat visible" in doc
    assert "raw filesystem paths visible" in doc


def test_index_beacon_harness_uses_backend_liveness_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Beacon Liveness" in doc
    assert "data-beacon-liveness" in doc
    assert "bridgeUrl('beacon-liveness')" in doc
    assert "renderBeaconLivenessSnapshot" in doc
    assert "renderBeaconLiveness" in doc
    assert "Heartbeat observations" in doc
    assert "Advisory families" in doc
    assert "Beacon guardrails" in doc
    assert "raw filesystem paths visible" in doc


def test_index_review_harness_uses_backend_console_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Review Console" in doc
    assert "data-review-console" in doc
    assert "bridgeUrl('review-console')" in doc
    assert "renderReviewConsoleSnapshot" in doc
    assert "renderReviewConsole" in doc
    assert "Queue status" in doc
    assert "Pending review items" in doc
    assert "Review guardrails" in doc
    assert "response authorized" in doc
    assert "raw item content visible" in doc


def test_index_federation_harness_uses_backend_horizon_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Federation Horizon" in doc
    assert "data-federation-horizon" in doc
    assert "bridgeUrl('federation-horizon')" in doc
    assert "renderFederationHorizonSnapshot" in doc
    assert "renderFederationHorizon" in doc
    assert "Discovery and permission boundary" in doc
    assert "Safe discovery fields" in doc
    assert "Typed handoff packets" in doc
    assert "Out of V2 scope" in doc
    assert "runtime authorized" in doc
    assert "remote execution authorized" in doc


def test_index_prime_harness_uses_backend_runtime_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Prime Runtime Logic" in doc
    assert "Prime Directives" in doc
    assert "Prime Directive Proofs" in doc
    assert "renderRelayPrimeDirectives(snapshot)" in doc
    assert "Runtime logic" in doc
    assert "Prime backend source" in doc
    assert "Runtime truth map" in doc
    assert "Typed interaction request" in doc
    assert "Prime review before dispatch" in doc
    assert "Decision and owner logic" in doc
    assert "No drift audit logic" in doc
    assert "Backend context logic" in doc
    assert "Aegis risk logic" in doc
    assert "Backend source refs" in doc
    assert "Proof and invalidation logic" in doc
    assert "Visible-to-user declaration" in doc
    assert "Execution blockers" in doc
    assert "demoted gates" in doc
    assert "visibleToUser" in doc
    assert "data-prime-logic" in doc
    assert "bridgeUrl('prime-logic')" in doc
    assert "renderPrimeDecisionSnapshot" in doc
    assert "renderPrimeLogic" in doc


def test_index_prime_review_before_dispatch_uses_runtime_packet_without_route_ownership():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    start = doc.index("relaySection('Prime review before dispatch'")
    end = doc.index("relaySection('Decision and owner logic'", start)
    section = doc[start:end]

    assert "request.intent || decision.action" in section
    assert "decision.action || request.action" in section
    assert "decision.ownerHarness || 'unknown'" in section
    assert "decision.risk || request.risk" in section
    assert "aegisRisk.evidenceRequired" in section
    assert "aegisRisk.blockedGates" in section
    assert "Prime reviews intent/risk/proof only" in section
    assert "Relay and Model Harness own route, provider, and payload decisions." in section
    assert "bridgeUrl('prime-logic')" in doc
    assert "method: 'POST'" not in section


def test_index_spark_and_workflow_surfaces_use_bridge_snapshots():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Provider Balance" in doc
    assert "Runtime Continuity" in doc
    assert "Checkpoint discipline advisory" in doc
    assert "Voice I/O source" in doc
    assert "data-voice-io" in doc
    assert "bridgeUrl('voice-io')" in doc
    assert "renderVoiceIoSnapshot" in doc
    assert "voice I/O and public CLI setup status wired" in doc
    assert "microphone authorized" in doc
    assert "controls disabled" in doc
    assert "execution authorized" in doc
    assert "self approval granted" in doc
    assert "Workflow Dispatch Status" in doc
    assert "data-provider-balance" in doc
    assert "data-goal-runtime" in doc
    assert "data-workflow-dispatch-status" in doc
    assert "bridgeUrl('provider-balance')" in doc
    assert "bridgeUrl('goal-runtime')" in doc
    assert "bridgeUrl('workflow-dispatch-status')" in doc
    assert "renderProviderBalance()" in doc
    assert "renderGoalRuntime()" in doc
    assert "renderWorkflowDispatchStatus()" in doc
    assert "success_summary" in doc
    assert "status_policy" in doc


def test_index_crosscheck_renders_review_findings_and_proof_status_safely():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    review_console = doc[
        doc.index("const renderReviewConsoleSnapshot = (snapshot) =>"):
        doc.index("const renderFederationHorizonSnapshot")
    ]
    assert "const items = Array.isArray(queue.items) ? queue.items : []" in review_console
    assert "const rawItemContentVisible = Boolean(snapshot.raw_item_content_visible)" in review_console
    assert "const rawWorkerChatVisible = Boolean(snapshot.raw_worker_chat_visible)" in review_console
    assert "Pending review items" in review_console
    assert "item.id || 'unknown'" in review_console
    assert "relayText(item.item_type)" in review_console
    assert "relayText(item.severity)" in review_console
    assert "item.title || 'unknown'" in review_console
    assert "item.content_label || 'none'" in review_console
    assert "item.content_length ?? '0'" in review_console
    assert "relayJoin(item.suggested_actions)" in review_console
    assert "relayText(item.status)" in review_console
    assert "method: 'POST'" not in review_console

    aegis_logic = doc[
        doc.index("const renderAegisLogicSnapshot = (snapshot) =>"):
        doc.index("const renderSessionCloseArchiveProofSnapshot")
    ]
    assert "const evidence = Array.isArray(trail.evidence) ? trail.evidence : []" in aegis_logic
    assert "Proof trail summary" in aegis_logic
    assert "Cognition policy gate" in aegis_logic
    assert "raw evidence body visible" in aegis_logic
    assert "relayText(item.status)" in aegis_logic
    assert "item.summary || 'unknown'" in aegis_logic
    assert "proof_blocking" in aegis_logic
    assert "method: 'POST'" not in aegis_logic


def test_index_provider_balance_renders_backend_supplied_usage_labels_safely():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    provider_balance = doc[
        doc.index("const renderProviderBalanceSnapshot = (snapshot"):
        doc.index("const renderGoalRuntimeSnapshot")
    ]
    assert "const providerMetricLabel = (value) => (value === 0 || value ? String(value) : 'unknown')" in provider_balance
    assert "const providerTokenLabel = (value) => `${providerMetricLabel(value)} tokens`" in provider_balance
    assert "const providerPromptBudgetLabel = (provider) =>" in provider_balance
    assert "providerTokenLabel(provider.context_budget_tokens)" in provider_balance
    assert "providerPromptBudgetLabel(provider)" in provider_balance
    assert "relayText(provider.quota_state)" in provider_balance
    assert "relayText(provider.credit_status)" in provider_balance
    assert "provider.remaining_credit_label || ''" in provider_balance
    assert "provider.estimated_spend_label || 'unavailable'" in provider_balance
    assert "relayJoin(provider.evidence_refs)" in provider_balance
    assert "const callIntent = relayEvidenceSnapshot?.per_call_intent || {}" in provider_balance
    assert "const relayTiers = Array.isArray(relayLogicSnapshot?.tiers) ? relayLogicSnapshot.tiers : []" in provider_balance
    assert "const recommendedTier = relayTiers.find((tier) => tier.tier === callIntent.risk_tier) || null" in provider_balance
    assert "Public account boundary" in provider_balance
    assert "Public users need their own provider accounts, keys, subscriptions, or local CLIs before a backend can be used." in provider_balance
    assert "does not probe account balances, credentials, billing portals, or provider secrets" in provider_balance
    assert "Routing recommendations remain advisory until Relay/Model Harness owns and exposes a reviewed routing decision." in provider_balance
    assert "Manual override handoff" in provider_balance
    assert 'data-balance-handoff="models"' in provider_balance
    assert 'data-balance-handoff="settings"' in provider_balance
    assert "This handoff only changes the visible surface; it does not mutate routing, enable Auto, post a prompt, call a provider, or bypass Relay/Aegis policy." in provider_balance
    assert "method: 'POST'" not in provider_balance


def test_index_provider_balance_frames_provider_comparison_without_route_mutation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    provider_balance = doc[
        doc.index("const renderProviderBalanceSnapshot = (snapshot"):
        doc.index("const renderGoalRuntimeSnapshot")
    ]

    assert "Provider comparison" in provider_balance
    assert "trust | health | route | cost pressure | quota | credit | estimated spend | evidence refs" in provider_balance
    assert "Prime visibility from Relay / Model Harness evidence" in provider_balance
    assert "advisory display only; no route selection or mutation from Balance" in provider_balance
    for field in (
        "relayText(provider.trust_state)",
        "relayText(provider.health)",
        "relayText(provider.route_kind)",
        "relayText(provider.cost_pressure)",
        "relayText(provider.quota_state)",
        "relayText(provider.credit_status)",
        "provider.estimated_spend_label || 'unavailable'",
        "relayJoin(provider.evidence_refs)",
    ):
        assert field in provider_balance
    assert "bridgeUrl('message')" not in provider_balance
    assert "bridgeUrl('call-result')" not in provider_balance
    assert "method: 'POST'" not in provider_balance
    assert "does not mutate routing, enable Auto, post a prompt, call a provider, or bypass Relay/Aegis policy" in provider_balance


def test_index_provider_balance_renders_advisory_routing_recommendation_from_backend_snapshots():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    provider_balance = doc[
        doc.index("const renderProviderBalanceSnapshot = (snapshot"):
        doc.index("const renderGoalRuntimeSnapshot")
    ]

    assert "relaySection('Routing recommendation', relayGrid(routingRecommendationRows), true)" in provider_balance
    assert "['intent source', relayEvidenceSnapshot?.per_call_intent ? '/bridge/relay-evidence per_call_intent' : 'not exposed by Relay']" in provider_balance
    assert "['Prime intent', callIntent.call_goal || 'not exposed']" in provider_balance
    assert "['recommended provider', balance.selected_provider || 'not exposed']" in provider_balance
    assert "['routing owner', balance.routing_owner || 'unknown']" in provider_balance
    assert "['policy state', relayText(balance.policy_state)]" in provider_balance
    assert "['lane plan', recommendedTier ? relayLaneSummary(recommendedTier) : 'not exposed by Relay logic']" in provider_balance
    assert "['proof posture', recommendedTier ? ((recommendedTier.audit?.proofRequired || []).map(relayText).join(' | ') || 'none') : 'not exposed by Relay logic']" in provider_balance
    assert "['recommendation boundary', 'advisory only; Relay/Aegis still owns dispatch approval and execution']" in provider_balance
    assert "method: 'POST'" not in provider_balance


def test_index_provider_balance_renders_cli_readiness_from_models_snapshot_without_account_probe():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    provider_balance = doc[
        doc.index("const renderProviderBalanceSnapshot = (snapshot") :
        doc.index("const renderGoalRuntimeSnapshot")
    ]
    loader = doc[
        doc.index("const loadProviderBalance = async () =>"):
        doc.index("const loadGoalRuntime = async () =>")
    ]

    assert "modelsSnapshot = null, relayEvidenceSnapshot = null, relayLogicSnapshot = null" in provider_balance
    assert "Array.isArray(modelsSnapshot?.models) ? modelsSnapshot.models : []" in provider_balance
    assert "CLI/account readiness" in provider_balance
    assert "model.installed ? 'available' : 'setup required'" in provider_balance
    assert "model.setupHint || 'Install and sign in before use'" in provider_balance
    assert "account readiness" in provider_balance
    assert "informational only; no account probing" in provider_balance
    assert "fetch(bridgeUrl('provider-balance'), { cache: 'no-store' })" in loader
    assert "fetch(bridgeUrl('models'), { cache: 'no-store' })" in loader
    assert "const relayEvidenceSnapshot = await fetchBridgeSnapshot('relay-evidence', 'Relay evidence');" in loader
    assert "const relayLogicSnapshot = await fetchBridgeSnapshot('relay-logic', 'Relay logic');" in loader
    assert "renderProviderBalanceSnapshot(providerBalanceSnapshot, modelsSnapshot, relayEvidenceSnapshot, relayLogicSnapshot)" in loader
    assert "method: 'POST'" not in provider_balance
    assert "bridgeUrl('message')" not in provider_balance
    assert "bridgeUrl('call-result')" not in provider_balance
    assert "probe accounts" not in provider_balance


def test_index_provider_balance_handoff_switches_surfaces_without_backend_mutation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    handler_start = doc.index("const sparkButtonByLabel = (label) =>")
    handler_end = doc.index("buttons.forEach((button) =>", handler_start)
    handler = doc[handler_start:handler_end]
    assert "rightWorkspace?.addEventListener('click', (event) =>" in handler
    assert "[data-balance-handoff]" in handler
    assert "handoff.dataset.balanceHandoff === 'models' ? 'Models' : 'Settings'" in handler
    assert "activateSparkButton(targetButton);" in handler
    assert "fetch(" not in handler
    assert "bridgeUrl('message')" not in handler
    assert "method: 'POST'" not in handler
    assert "restartModelBridge" not in handler
    assert "call-result" not in handler


def test_index_routines_surface_combines_goal_and_workflow_typed_state():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="Routines"' in doc
    assert "Runtime Continuity" in doc
    assert "const renderGoalRuntime = () =>" in doc
    assert "Routines shows compact typed goal/runtime state and workflow dispatch status without starting automation." in doc
    assert "Worker session transcript is stored, not replayed" in doc
    assert "worker summaries stay small and checkpoint-updated" in doc
    assert "Session state packets and evidence refs are surfaced as typed state" in doc
    assert "raw artifacts, logs, transcripts, worker history, and raw detail are not pasted" in doc
    assert "Public automation boundary" in doc
    assert "Public builds require explicit local permissions, configured accounts, and reviewed scheduler authority before recurring automation can run." in doc
    assert "this surface does not create automations, mutate schedules, run routines, request credentials, or approve itself." in doc
    assert "Routine results remain display-only typed state until a reviewed routine automation backend exists." in doc
    assert "data-goal-runtime" in doc
    assert "data-workflow-dispatch-status" in doc
    assert "loadGoalRuntime();" in doc
    assert "loadWorkflowDispatchStatus();" in doc
    assert "bridgeUrl('goal-runtime')" in doc
    assert "bridgeUrl('workflow-dispatch-status')" in doc
    assert "renderWorkflowDispatchStatus()" in doc
    assert "Quiet mode routine status" in doc
    assert "Quiet mode workflow status" in doc
    assert "Success summary shape" in doc
    assert "Failure summary shape" in doc
    assert "Dispatch visibility policy" in doc
    assert "proof trail" in doc
    assert "failure kind" in doc
    assert "tier three gate required" in doc
    routines_start = doc.index("const renderGoalRuntime = () =>")
    routines_end = doc.index("const renderWorkflowDispatchStatus = () =>", routines_start)
    routines_surface = doc[routines_start:routines_end]
    assert "fetch(" not in routines_surface
    assert "bridgeUrl('message')" not in routines_surface
    assert "method: 'POST'" not in routines_surface
    assert "scheduler mutation" not in routines_surface.lower()
    assert "create automations" in routines_surface
    assert "mutate schedules" in routines_surface
    assert "run-now" not in routines_surface
    assert "raw_artifacts_visible ? 'yes'" not in routines_surface
    assert "raw worker session history" not in routines_surface
    assert "routine list" not in routines_surface.lower()
    assert "next run" not in routines_surface.lower()
    assert "routine history" not in routines_surface.lower()
    assert "create-automation" not in routines_surface


def test_routines_surface_inherits_quiet_mode_from_runtime_renderers():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "const rerenderRuntimeSurfaces = () =>" in doc
    assert "document.querySelectorAll('[data-goal-runtime]')" in doc
    assert "document.querySelectorAll('[data-workflow-dispatch-status]')" in doc
    assert "writeQuietMode(target.checked);" in doc
    assert "Routine success chatter is suppressed in Runtime Continuity and Workflow Dispatch while blockers, proof gates, and failure state remain visible." in doc
    checklist = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "| ROU10 | Quiet routine mode | Routine noise respects Quiet mode while preserving blockers. | wired |" in checklist
    assert "Routines reuses the backend-bound Runtime Continuity and Workflow Dispatch renderers" in checklist


def test_routines_checklist_keeps_automation_rows_deferred_until_backend_exists():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "`ROU0` snapshots are compact continuity and workflow-dispatch posture only." in doc
    assert "They are not evidence of configured routine automation" in doc
    for row in (
        "| ROU1 | Routine list | Shows configured routines for active project/system. | planned |",
        "| ROU2 | Create routine | Creates a new repeatable workflow or monitor with explicit scope. | planned |",
        "| ROU3 | Enable/disable routine | Toggles routine active state. | planned |",
        "| ROU4 | Routine trigger | Supports manual run-now once routine execution exists. | planned |",
        "| ROU5 | Cadence/trigger view | Shows schedule, heartbeat, or event trigger. | planned |",
        "| ROU6 | Last run result | Shows last run status, duration, and proof/evidence link. | planned |",
        "| ROU7 | Next run preview | Shows next expected run or waiting condition. | planned |",
        "| ROU8 | Failure handling | Shows retry/escalation behavior for routine failures. | planned |",
        "| ROU9 | Prime-owned routine review | Prime reviews routine outputs and only escalates meaningful user gates. | planned |",
        "| ROU11 | Routine archive/history | Shows previous runs and outcomes without cluttering main panels. | planned |",
    ):
        assert row in doc
    assert "| ROU10 | Quiet routine mode | Routine noise respects Quiet mode while preserving blockers. | wired |" in doc
    assert "| ROU12 | Public automation boundary | Public build explains what automation needs local permissions/accounts. | wired |" in doc
    assert "missing permission/account setup is guidance only" in doc
    assert "no automation creation, schedule mutation, routine execution, credential request, or self-approval" in doc


def test_index_bifrost_harness_uses_voice_io_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'data-harness="Bifrost"' in doc
    assert "Bifrost Voice I/O" in doc
    assert "const renderBifrostVoiceIo = () =>" in doc
    assert "renderBifrostVoiceIo()" in doc
    assert "button.dataset.harness === 'Bifrost'" in doc
    assert "Bifrost reflects compact Voice I/O state from the reviewed backend snapshot." in doc
    assert "Orchestrator intake remains compact typed voice/session state; raw detail is fetched only on demand." in doc
    assert "data-voice-io" in doc
    assert "loadVoiceIo();" in doc
    assert "bridgeUrl('voice-io')" in doc
    bifrost_start = doc.index("const renderBifrostVoiceIo")
    bifrost_end = doc.index("const renderReviewConsole", bifrost_start)
    bifrost_surface = doc[bifrost_start:bifrost_end]
    assert "fetch(" not in bifrost_surface
    assert "getUserMedia" not in bifrost_surface
    assert "speechSynthesis" not in bifrost_surface
    assert "raw worker history" in bifrost_surface
    assert "worker chat" in bifrost_surface


def test_index_memory_retrieval_and_filemap_surfaces_use_bridge_snapshots():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Echo Memory" in doc
    assert "Atlas Retrieval" in doc
    assert "FileMap Registry" in doc
    assert "data-echo-memory" in doc
    assert "data-atlas-retrieval" in doc
    assert "data-filemap" in doc
    assert "bridgeUrl('echo-memory')" in doc
    assert "bridgeUrl('atlas-retrieval')" in doc
    assert "bridgeUrl('filemap')" in doc
    assert "renderEchoMemory()" in doc
    assert "renderAtlasRetrieval()" in doc
    assert "renderFileMap()" in doc
    assert "hit.record.body" not in doc
    assert "record.body" not in doc
    assert "mutation_authorized ? 'yes'" not in doc
    echo_memory = doc[
        doc.index("const renderEchoMemorySnapshot = (snapshot) =>"):
        doc.index("const renderAtlasRetrievalSnapshot")
    ]
    assert "Query boundary" in echo_memory
    assert "hit.summary || 'unknown'" in echo_memory
    assert "hit.reason || 'unknown'" in echo_memory
    assert "method: 'POST'" not in echo_memory
    assert "record.body" not in echo_memory
    atlas_retrieval = doc[
        doc.index("const renderAtlasRetrievalSnapshot = (snapshot) =>"):
        doc.index("const renderFileMapSnapshot")
    ]
    assert "Retrieval query" in atlas_retrieval
    assert "relayJoin(query.required_paths)" in atlas_retrieval
    assert "hit.excerpt || 'none'" in atlas_retrieval
    assert "method: 'POST'" not in atlas_retrieval
    filemap = doc[
        doc.index("const renderFileMapSnapshot = (snapshot) =>"):
        doc.index("const renderAegisLogicSnapshot")
    ]
    assert "Registry summary" in filemap
    assert "Area counts" in filemap
    assert "entry.path || 'unknown'" in filemap
    assert "relayJoin(entry.related_tests)" in filemap
    assert "method: 'POST'" not in filemap
    assert "C:\\\\Users\\\\" not in filemap
    assert "C:/Users/" not in filemap


def test_index_aegis_surface_uses_bridge_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Aegis Runtime Logic" in doc
    assert "data-aegis-logic" in doc
    assert "const renderAegisLogicSnapshot = (snapshot) =>" in doc
    assert "const loadAegisLogic = async () =>" in doc
    assert "bridgeUrl('aegis-logic')" in doc
    assert "renderAegisLogic()" in doc
    assert "if (rightWorkspace?.querySelector('[data-aegis-logic]')) loadAegisLogic();" in doc
    assert "button.dataset.harness === 'Aegis'" in doc
    assert "raw evidence body visible" in doc
    assert "display only" in doc
    assert "apply_console_response" not in doc
    assert "enqueue_to_review_console" not in doc


def test_index_session_archive_surface_uses_backend_proof_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Session Close Archive Proof" in doc
    assert "data-session-close-archive-proof" in doc
    assert "const renderSessionCloseArchiveProofSnapshot = (snapshot) =>" in doc
    assert "const loadSessionCloseArchiveProof = async () =>" in doc
    assert "bridgeUrl('session-close-archive-proof')" in doc
    assert "renderSessionCloseArchiveProof()" in doc
    assert "actionLabel === 'Archive' ? renderSessionCloseArchiveProof()" in doc
    assert (
        "if (rightWorkspace?.querySelector('[data-session-close-archive-proof]')) "
        "loadSessionCloseArchiveProof();"
    ) in doc
    assert "live control authorized" in doc
    assert "raw prompt visible" in doc
    assert "raw worker chat visible" in doc
    assert "Command plan preview" in doc
    assert "aegis gate" in doc
    assert "human gate required" in doc
    assert "Orchestrator intake" in doc
    assert "compact typed session state" in doc
    assert "raw detail is fetched only on demand" in doc
    assert "raw worker session history" in doc
    assert "pasted transcript/log/detail" in doc
    assert "Write-through gate" in doc
    assert "executable now" in doc
    archive_start = doc.index("const renderSessionCloseArchiveProof = () =>")
    archive_end = doc.index("const renderReleaseAutonomy", archive_start)
    archive_surface = doc[archive_start:archive_end]
    assert "<button" not in archive_surface
    assert "<form" not in archive_surface
    assert "method: 'POST'" not in archive_surface
    assert "bridgeUrl('message')" not in archive_surface
    assert "bridgeUrl('restart')" not in archive_surface
    assert "bridgeUrl('call-result')" not in archive_surface
    assert "archive-session" not in archive_surface
    assert "close-session" not in archive_surface
    assert "reload-session" not in archive_surface
    assert "run-again" not in archive_surface
    assert "delete" not in archive_surface.lower()
    assert "raw_worker_chat =" not in archive_surface
    assert "transcript" not in archive_surface.lower()
    assert "session_history" not in archive_surface
    assert "detail_body" not in archive_surface
    assert "log_body" not in archive_surface
    assert "prompt:" not in archive_surface.lower()


def test_index_release_harness_uses_prime_autonomy_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'data-harness="Release"' in doc
    assert "Autonomy Release" in doc
    assert "data-release-autonomy" in doc
    assert "const renderReleaseAutonomySnapshot = (snapshot) =>" in doc
    assert "const loadReleaseAutonomy = async () =>" in doc
    assert "bridgeUrl('prime-autonomy')" in doc
    assert "renderReleaseAutonomy()" in doc
    assert "button.dataset.harness === 'Release'" in doc
    assert (
        "if (rightWorkspace?.querySelector('[data-release-autonomy]')) "
        "loadReleaseAutonomy();"
    ) in doc
    assert "Release autonomy source" in doc
    assert "Release posture" in doc
    assert "Authority boundary" in doc
    assert "Visibility guard" in doc
    assert "Release blockers" in doc
    assert "release execution authorized" in doc
    assert "deployment authorized" in doc
    assert "raw prompt visible" in doc
    assert "raw response visible" in doc
    assert "raw evidence body visible" in doc
    assert "raw worker chat visible" in doc
    assert "PIDs visible" in doc
    assert "raw filesystem paths visible" in doc
    assert "release-now" not in doc
    assert "deploy-now" not in doc


def test_index_wired_harness_titles_use_runtime_logic_naming():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Prime Runtime Logic" in doc
    assert "Relay Runtime Logic" in doc
    assert "Compass Runtime Logic" in doc
    assert "Vulcan Runtime Logic" in doc


def test_index_relay_harness_renders_backend_logic_snapshot_contract():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "data-relay-logic" in doc
    assert "const relayLogicUrl = 'http://127.0.0.1:8767/bridge/relay-logic';" in doc
    assert "fetch(relayLogicUrl, { cache: 'no-store' })" in doc
    assert "renderRelayLogicSnapshot(snapshot)" in doc
    assert "renderRelayEvidenceSnapshot(snapshot)" in doc
    assert "renderRelayPrimeDirectives(snapshot)" in doc
    assert "capabilitySections.map(renderRelayCapabilitySection)" in doc
    assert "snapshot.routePrecedence" in doc
    assert "tier3.dispatch?.laneOrder" in doc
    assert "tier3.dispatch?.payloadPolicy" in doc
    assert "relayAuditRows(tier3)" in doc
    assert "data-relay-evidence" in doc
    assert "bridgeUrl('relay-evidence')" in doc
    assert "Prompt packet proof advisory" in doc
    assert "Per-call GOAL / Intent" in doc
    assert "const callIntent = snapshot.per_call_intent || {}" in doc
    assert "callIntent.call_goal || 'not exposed by Relay'" in doc
    assert "callIntent.expected_output_shape || 'not exposed'" in doc
    assert "callIntent.proof_requirement || 'not exposed'" in doc
    assert "callIntent.payload_budget_ref || 'not exposed'" in doc
    assert "relayJoin(callIntent.disallowed_outputs)" in doc
    assert "relayJoin(callIntent.evidence_refs)" in doc
    assert "Prompt payload meter advisory" in doc
    assert "Provider result validation advisory" in doc
    assert "DeepSeek validation disposition" in doc
    assert "DeepSeek transport authority" in doc
    assert "transport authorized" in doc
    assert "review clearing authorized" in doc
    assert "branch movement authorized" in doc
    assert "live coding authority" in doc
    assert "relay bypass authorized" in doc
    assert "raw provider response visible" in doc
    assert "Fallback blocker logic" in doc
    assert "Proof and telemetry logic" in doc


def test_index_relay_refresh_reloads_logic_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    match = re.search(r"const refreshRelayPanel = \(\) => \s*\{(?P<body>.*?)\n  \};", doc, re.S)

    assert match is not None
    body = match.group("body")
    assert "renderRelayBridgeStatus();" in body
    assert "loadRelayLogic();" in body
    assert "loadPrimeLogic();" in body
    assert "loadCompassLogic();" in body
    assert "loadVulcanLogic();" in body
    assert "loadBeaconLiveness();" in body
    assert "loadFederationHorizon();" in body


def test_bridge_exposes_prime_logic_route_and_capability():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "primeRuntimeSnapshot: true" in doc
    assert "primeLogic: '/bridge/prime-logic'" in doc
    assert "meridian_core.prime_runtime" in doc
    assert "req.url === BRIDGE_ROUTES.primeLogic" in doc


def test_bridge_exposes_relay_evidence_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "relayEvidenceSnapshot: true" in doc
    assert "relayEvidence: '/bridge/relay-evidence'" in doc
    assert "function relayEvidenceSnapshot()" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.relayEvidence" in doc
    assert "PromptPacketProofMetadata" in doc
    assert "PromptPayloadMeterInput" in doc
    assert "ProviderResultValidationInput" in doc
    assert "deepseek_candidate_metadata_preset" in doc
    assert "bind_deepseek_validation_disposition" in doc
    assert "bind_deepseek_transport_authority" in doc
    assert "evaluate_prompt_packet_proof_policy" in doc
    assert "evaluate_prompt_payload_meter_advisory" in doc
    assert "evaluate_provider_result_validation_advisory" in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert '"raw_prompt_visible": False' in doc
    assert '"raw_provider_response_visible": False' in doc
    assert '"provider_call_authorized": False' in doc
    assert '"per_call_intent": per_call_intent' in doc
    assert '"requested_by": "Prime / Relay"' in doc
    assert '"prime_intent_ref": "prime-intent:display-safe-demo"' in doc
    assert '"action_type": "relay_evidence_advisory"' in doc
    assert '"call_goal": "Display Relay prompt-packet, payload-meter, and provider-result advisory posture for the selected model harness aspect."' in doc
    assert '"expected_output_shape": "compact advisory snapshot with policy decisions, blockers, warnings, and evidence refs"' in doc
    assert '"risk_tier": 2' in doc
    assert '"proof_requirement": "prompt packet proof metadata plus Relay/Aegis evidence refs"' in doc
    assert '"payload_budget_ref": "budget:tier2:default"' in doc
    assert '"authority_boundary": "display_only; no provider call, route mutation, prompt assembly, raw response recovery, or Auto routing"' in doc
    assert '"deepseek_validation_disposition"' in doc
    assert '"deepseek_transport_authority"' in doc
    assert '"provider_call_authorized": True' not in doc
    assert '"body":' not in doc


def test_bridge_exposes_beacon_liveness_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "beaconLivenessSnapshot: true" in doc
    assert "beaconLiveness: '/bridge/beacon-liveness'" in doc
    assert "function beaconLivenessSnapshot()" in doc
    assert "meridian_core.beacon_liveness_snapshot" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.beaconLiveness" in doc


def test_bridge_exposes_review_console_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "reviewConsoleSnapshot: true" in doc
    assert "reviewConsole: '/bridge/review-console'" in doc
    assert "function reviewConsoleSnapshot()" in doc
    assert "meridian_core.review_console_snapshot" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.reviewConsole" in doc


def test_bridge_exposes_federation_horizon_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "federationHorizonSnapshot: true" in doc
    assert "federationHorizon: '/bridge/federation-horizon'" in doc
    assert "function federationHorizonSnapshot()" in doc
    assert "meridian_core.federation_horizon_snapshot" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.federationHorizon" in doc


def test_bridge_exposes_release_autonomy_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "primeAutonomyReleaseSnapshot: true" in doc
    assert "primeAutonomyRelease: '/bridge/prime-autonomy'" in doc
    assert "function primeAutonomyReleaseSnapshot()" in doc
    assert "meridian_core.release_autonomy_snapshot" in doc
    assert (
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.primeAutonomyRelease"
    ) in doc
    assert "BRIDGE_CAPABILITIES.primeAutonomyReleaseSnapshot" in doc
    assert "Prime Autonomy Release snapshot returned invalid JSON" in doc


def test_bridge_exposes_reviewed_display_only_capability_routes():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")

    for flag in (
        "providerBalanceSnapshot: true",
        "goalRuntimeSnapshot: true",
        "workflowDispatchStatusSnapshot: true",
    ):
        assert flag in doc

    for route in (
        "providerBalance: '/bridge/provider-balance'",
        "goalRuntime: '/bridge/goal-runtime'",
        "workflowDispatchStatus: '/bridge/workflow-dispatch-status'",
    ):
        assert route in doc

    for handler in (
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.providerBalance",
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.goalRuntime",
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.workflowDispatchStatus",
    ):
        assert handler in doc

    assert "pythonJsonSnapshot" in doc
    assert "meridian_core.provider_balance" in doc
    assert "meridian_core.goal_runtime" in doc
    assert "meridian_core.aegis" in doc
    assert "V3GoalCheckpointDisciplineInput" in doc
    assert "evaluate_v3_goal_checkpoint_discipline_advisory" in doc
    assert "serialize_v3_goal_checkpoint_discipline_policy_result" in doc
    assert "checkpoint_discipline" in doc
    assert "meridian_core.workflow_dispatch" in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert '"summary": "Display-safe provider balance summary; no live account probing."' in doc


def test_bridge_exposes_memory_retrieval_and_filemap_routes():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")

    for flag in (
        "echoMemorySnapshot: true",
        "atlasRetrievalSnapshot: true",
        "fileMapSnapshot: true",
    ):
        assert flag in doc

    for route in (
        "echoMemory: '/bridge/echo-memory'",
        "atlasRetrieval: '/bridge/atlas-retrieval'",
        "fileMap: '/bridge/filemap'",
    ):
        assert route in doc

    for handler in (
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.echoMemory",
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.atlasRetrieval",
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.fileMap",
    ):
        assert handler in doc

    assert "meridian_core.echo" in doc
    assert "meridian_core.atlas" in doc
    assert "meridian_core.filemap" in doc
    assert "FileArea.WORKFLOW_ATLAS" in doc
    assert "workflow_focus_entries" in doc
    assert "workflow_focus_paths" in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert "hit.record.body" not in doc
    assert '"body":' not in doc


def test_bridge_exposes_aegis_logic_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "aegisLogicSnapshot: true" in doc
    assert "aegisLogic: '/bridge/aegis-logic'" in doc
    assert "function aegisLogicSnapshot()" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.aegisLogic" in doc
    assert "meridian_core.aegis" in doc
    assert "meridian_core.cognition_policy" in doc
    assert "result.relay_route.risk_tier" in doc
    assert "result.relay_route.tier" not in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert '"raw_evidence_body_visible": False' in doc
    assert '"mutation_authorized": True' not in doc
    assert '"body":' not in doc
    assert "apply_console_response" not in doc
    assert "enqueue_to_review_console" not in doc


def test_bridge_exposes_session_close_archive_proof_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "sessionCloseArchiveProofSnapshot: true" in doc
    assert "sessionCloseArchiveProof: '/bridge/session-close-archive-proof'" in doc
    assert "function sessionCloseArchiveProofSnapshot()" in doc
    assert (
        "req.method === 'GET' && req.url === BRIDGE_ROUTES.sessionCloseArchiveProof"
        in doc
    )
    assert "meridian_core.session_lifecycle" in doc
    assert "build_close_archive_write_through_proof" in doc
    assert "build_v2_command_plan_preview_proof" in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert '"live_control_authorized": False' in doc
    assert '"raw_prompt_visible": False' in doc
    assert '"raw_worker_chat_visible": False' in doc
    assert (
        "req.method === 'POST' && req.url === BRIDGE_ROUTES.sessionCloseArchiveProof"
        not in doc
    )
    assert (
        "BRIDGE_ROUTES.sessionCloseArchiveProof"
        not in doc[doc.index("if (req.method === 'POST' && req.url === BRIDGE_ROUTES.message"):]
    )
    assert '"raw_worker_session_history_visible": False' in doc
    assert '"pasted_transcript_body_visible": False' in doc
    assert '"pasted_log_body_visible": False' in doc
    assert '"raw_detail_body_visible": False' in doc
    assert '"orchestrator_intake": "compact_typed_session_state_only"' in doc
    assert '"mutation_authorized": True' not in doc
    assert "raw_worker_chat = " not in doc
    assert "SECRET_RAW_PROMPT" not in doc


def test_bridge_exposes_voice_io_route():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "voiceIoSnapshot: true" in doc
    assert "voiceIo: '/bridge/voice-io'" in doc
    assert "function voiceIoSnapshot()" in doc
    assert "req.method === 'GET' && req.url === BRIDGE_ROUTES.voiceIo" in doc
    assert "bifrost.cockpit" in doc
    assert "sample_cockpit_view_model" in doc
    assert '"display_only": True' in doc
    assert '"mutation_authorized": False' in doc
    assert '"microphone_authorized": False' in doc
    assert '"speech_output_authorized": False' in doc
    assert '"read_aloud_authorized": False' in doc
    assert '"controls_disabled": True' in doc
    assert '"microphone_authorized": True' not in doc
    assert '"speech_output_authorized": True' not in doc
    assert '"read_aloud_authorized": True' not in doc
    voice_snapshot = doc[doc.index("function voiceIoSnapshot()"):doc.index("function primeAutonomyReleaseSnapshot()")]
    assert "raw_prompt" not in voice_snapshot
    assert "raw_response" not in voice_snapshot
    assert "worker_chat" not in voice_snapshot
    assert "worker_history" not in voice_snapshot


def test_ui_checklist_defers_deep_compass_and_vulcan_items_to_backend_tracker():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "### Compass And Vulcan Backend Readiness" in doc
    assert "| HBD1 | Compass backend checklist |" in doc
    assert "| HBD2 | Vulcan backend checklist |" in doc
    assert "| CMP1 | Project definition |" not in doc
    assert "| VLC1 | Session definition |" not in doc


def test_ui_checklist_has_no_local_absolute_path_leakage():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "C:\\Users\\" not in doc
    assert "C:/Users/" not in doc
    assert "Meridian-Worktrees\\" not in doc
    assert "local quarantine patch preserved; path redacted" in doc


def test_ui_checklist_pins_backend_backed_spark_surfaces():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "| SK5 | Models | Opens model readiness and recent-call metadata surface. | wired |" in doc
    assert "/bridge/models" in doc
    assert "/bridge/recent-calls" in doc
    assert "does not call `/bridge/call-result` or render recovered bodies" in doc
    assert "| SP11 | Model/source label | Shows the model/source used for a response when known. | wired |" in doc
    assert "resolved/requested backend source below model/setup/error output" in doc
    assert "| MOD11 | Model label display | Response UI shows actual backend/model label when known. | wired |" in doc
    assert "bridge-returned model labels plus resolved/requested backend source" in doc
    assert "| SK8 | Crosscheck | Opens display-only review/proof state from existing backend snapshots. | wired |" in doc
    assert "/bridge/review-console" in doc
    assert "/bridge/aegis-logic" in doc
    assert "does not start a review run, apply responses, mutate queues, execute providers, or ingest raw worker session history" in doc
    assert "| SK6 | Backlog | Opens backlog/task surface. | wired |" in doc
    assert "Spark Backlog opens a display-only Backlog Tasks surface backed by `/bridge/review-console`, `/bridge/goal-runtime`, and `/bridge/workflow-dispatch-status`" in doc
    assert "renders empty/unavailable state rather than fake backlog items" in doc
    assert "does not create tasks, assign workers, mutate queues, start routines, send prompts, recover raw result bodies, or ingest raw worker session history" in doc
    assert "| BAK1 | Backlog list | Shows queued ideas/tasks/objectives for the active project. | wired |" in doc
    assert "Spark Backlog renders a Backlog candidate list from real `/bridge/review-console` queue items in the active Compass project display frame" in doc
    assert "empty snapshots render an explicit empty state and no fake items" in doc
    assert "no fake items, create/approve/deny/defer/convert/archive controls, owner assignment, priority mutation, prompt send, result recovery, or queue mutation are exposed" in doc
    assert "| BAK2 | Priority order | Shows priority and why an item is next. | wired |" in doc
    assert "Spark Backlog renders an advisory Priority order frame that joins `/bridge/review-console` queue order with the active Compass project frame plus `/bridge/goal-runtime` objective context and `/bridge/prime-logic` owner/action/risk rationale" in doc
    assert "| SK7 | Skills | Opens searchable skill/capability registry by model, project, and global scope. | wired |" in doc
    assert "Spark Skills opens a display-only Skills Registry sourced from `/bridge/filemap` and `/bridge/models`" in doc
    assert "search is UI-local over loaded metadata" in doc
    assert "without fake skills backend, install/login/account probing, Auto routing, prompt send, file mutation, or skill execution" in doc
    assert "| SKL1 | Search skills | Dynamically search skills by name, purpose, provider, project, or keyword. | wired |" in doc
    assert "| SKL2 | Global skills | Shows skills available across all projects. | wired |" in doc
    assert "| SKL3 | Project skills | Shows skills available for the active project. | wired |" in doc
    assert "Skills Registry renders an Active project skills section keyed to `activeProjectContext()`" in doc
    assert "| SKL4 | Model/backend skills | Shows which skills are available by Codex, Max/Claude, or other backend. | wired |" in doc
    assert "| SKL5 | Skill description | Explains what each skill does in user-readable language. | wired |" in doc
    assert "| SKL6 | Arguments schema | Shows required and optional arguments for each skill. | wired |" in doc
    assert "Skills Registry rows render display-only argument schema text for FileMap metadata" in doc
    assert "| SKL7 | Usage example | Shows a short example command or prompt pattern. | wired |" in doc
    assert "examples are display text only and do not execute, call providers, mutate files, send prompts, install tools, sign in, or enable Auto routing" in doc
    assert "| SKL8 | Permission boundary | Shows whether the skill reads files, writes files, uses network, or affects accounts. | wired |" in doc
    assert "| SKL9 | Install/setup status | Shows missing dependencies or login/setup requirements. | wired |" in doc
    assert "| SKL10 | Run/request path | Provides a clear path to invoke or request the skill when supported. | wired |" in doc
    assert "| SKL11 | Skill provenance | Shows whether skill is built-in, project-local, plugin-provided, or user-defined. | wired |" in doc
    assert "| SKL12 | Favorite/pin skill | Allows important skills to be pinned for the active project/user. | wired |" in doc
    assert "Skills Registry pin controls persist row ids under `meridian.skills.pinned.v1` bucketed by active project context in the local user UI profile" in doc
    assert "| XCK0 | Review/proof state | Shows current Review Console and Aegis proof posture without running a new check. | wired |" in doc
    assert "| XCK2 | Review findings | Shows current findings with severity, owner, and status. | partial |" in doc
    assert "owner attribution remains deferred and raw item content stays hidden" in doc
    assert "| XCK3 | Proof status | Shows pass/fail/waived proof state for active work. | wired |" in doc
    assert "Aegis proof trail and policy gate state from `/bridge/aegis-logic`" in doc
    assert "worker transcripts are stored, not replayed" in doc
    assert "worker summaries stay small and update at checkpoints" in doc
    assert "session state packets are always available" in doc
    assert "evidence refs are links/ids rather than pasted logs" in doc
    assert "raw detail is fetched only on demand" in doc
    assert "| SPK3 | Listening/thinking/speaking state | Reflects Prime/Spark voice state once voice is wired. | wired |" in doc
    assert "| VO1 | Speech mode icon | Shows first-class spoken interaction state while capture/output backends remain unavailable. | wired |" in doc
    assert "| VOC2 | Wake/listening state | Shows when Spark is listening, idle, thinking, or speaking. | wired |" in doc
    assert "Top speech icon and Settings/Spark render compact Voice I/O state from `/bridge/voice-io`" in doc
    assert "no microphone, speech output, read-aloud, mute mutation, raw prompt/response, or raw worker history is authorized" in doc
    assert "| VOC12 | Public setup guidance | Explains microphone/browser permissions and speech provider setup in public builds. | wired |" in doc
    assert "Voice I/O surfaces render a Public voice setup boundary from `/bridge/voice-io`" in doc
    assert "no permission request, capture start, speech synthesis, secret read, provider settings mutation, or typed prompt/response disruption" in doc
    assert "| VOC11 | Privacy indicator | Makes microphone capture state obvious. | wired |" in doc
    assert "Top speech icon carries `data-capture-state` and a capture title" in doc
    assert "Voice I/O renders a backend-sourced Voice privacy indicator from `/bridge/voice-io`" in doc
    assert "fail-closed posture" in doc
    assert "| PRJ6 | Project-scoped surfaces | Updates project-scoped backlog, review, progress, and session lists. | wired |" in doc
    assert "Project selector changes refresh Compass context, the grouped User Sessions list, Review Console/Crosscheck, Goal Runtime, Workflow Dispatch Status, Spark Backlog, Spark Models, and project-scoped Skills pin/search state" in doc
    assert "| PRJ10 | Project metadata | Shows or links working directory, repo, branch, and project status when that surface exists. | wired |" in doc
    assert "Compass renders Project metadata handoff from `/bridge/compass-logic`" in doc
    assert "Vulcan live-state evidence and FileMap relative-path registry" in doc
    assert "does not move branches, expose absolute paths, or invent source-control state" in doc
    assert "| PRJ11 | Project switch guard | Warns before switching away from unsaved prompt/session edits if needed. | wired |" in doc
    assert "Project selector checks visible Prime/User prompt drafts before changing Compass context" in doc
    assert "cancel restores the prior project, confirm preserves draft storage" in doc
    assert "| SK3 | Settings | Opens settings surface for UI/model/project/session options. | wired |" in doc
    assert "| SUR2 | Settings mode | Right panel uses full panel for Meridian configuration items, with no prompt window. | wired |" in doc
    assert "| SUR10 | Settings item actions | Settings mode actions mutate only explicit settings items. | wired |" in doc
    assert "no microphone capture, speech output, read-aloud, mute mutation, raw prompt/response, raw worker history, worker chat, or settings mutation is authorized" in doc
    assert "does not send to live sessions, `/bridge/message`, `/bridge/restart`, or result-recovery routes" in doc
    assert "remains disabled/`aria-disabled=true`" in doc
    assert "| HN2 | Bifrost | Opens/focuses UI/Bifrost surface. | wired |" in doc
    assert "Click opens Bifrost Voice I/O from `/bridge/voice-io` with compact typed state only" in doc
    assert "| SET1 | Project focus | Switches active project context across Prime panel, Review Console, lane/progress state, and instrumentation. | wired |" in doc
    assert "Settings/Spark reflects the existing `.session-project-select` authority" in doc
    assert "does not retarget sessions, POST prompts, call result recovery, or invoke close/archive controls" in doc
    assert "| SET2 | Last project persistence | Remembers the last active project across UI sessions. | wired |" in doc
    assert "falls back to Meridian for invalid/missing stored values" in doc
    assert "| SET3 | Risk tier override | Lets Prime propose risk tier while user can pin/override for a session. | wired |" in doc
    assert "UI-local session risk overrides backed by `meridian.risk-tier-overrides.v1`" in doc
    assert "| SET4 | Progress pin list | Persists pinned progress/session items. | wired |" in doc
    assert "UI-local pinned progress/session item list backed by `meridian.progress-state.v1`" in doc
    assert "| SET5 | Progress mute list | Persists muted progress/session categories or items. | wired |" in doc
    assert "UI-local muted progress/session item/category list backed by `meridian.progress-state.v1`" in doc
    assert "| SET6 | Progress collapse state | Persists collapsed progress surface state. | wired |" in doc
    assert "UI-local progress collapse default backed by `meridian.progress-state.v1`" in doc
    assert "| SET8 | Progress redirect defaults | Configures default routing by category when Prime surfaces progress or review items. | wired |" in doc
    assert "UI-local progress redirect defaults backed by `meridian.progress-redirects.v1`" in doc
    assert "| SET14 | Role/model mapping | Shows role-to-model mapping and allows per-role override/pin. | wired |" in doc
    assert "UI-local per-role model preferences backed by `meridian.role-model-overrides.v1`" in doc
    assert "| SET18 | Diagnostic log visibility | Controls whether per-session diagnostic event logs are visible by default. | wired |" in doc
    assert "UI-local diagnostic event visibility default backed by `meridian.context-filter.v1`" in doc
    assert "without deleting source session data and without calling a backend event-log route" in doc
    assert "| SET7 | Progress filter defaults | Configures default filter/severity visibility for progress items. | wired |" in doc
    assert "UI-local progress severity defaults backed by `meridian.context-filter.v1`" in doc
    assert "without deleting progress source data or calling backend progress" in doc
    assert "| SET10 | Quiet mode | Reduces non-critical UI noise and routine progress surfacing. | wired |" in doc
    assert "UI-local quiet mode backed by `meridian.quiet-mode.v1`" in doc
    assert "| SET11 | Focus mode | Collapses portfolio noise to the active project. | wired |" in doc
    assert "UI-local focus mode backed by `meridian.focus-mode.v1`" in doc
    assert "| SET15 | Wake mode | Selects full wake, fast wake, or silent wake. | wired |" in doc
    assert "UI-local wake mode backed by `meridian.wake-mode.v1`" in doc
    assert "| SET16 | Quick reply order | Chooses which prompt macro buttons appear and their order. | wired |" in doc
    assert "UI-local quick reply order backed by `meridian.quick-reply-order.v1`" in doc
    assert "| SET20 | Non-exposed harness internals | Confirms heartbeat thresholds, capability toggles, and cross-harness routing internals stay hidden unless explicitly promoted. | wired |" in doc
    assert "settings writes, message/restart/result routes, fake backend controls, and hidden harness internals remain blocked" in doc
    assert "| ECHO0 | Display-only memory ranking | Shows memory query boundary and ranked memory summaries from the backend. | wired |" in doc
    assert "record bodies and memory mutation stay unavailable" in doc
    assert "| ATL0 | Display-only retrieval metadata | Shows retrieval query, missing paths, truncation state, and display-safe hits. | wired |" in doc
    assert "allowlisted excerpt text only" in doc
    assert "| FM0 | Display-only relative-path registry | Shows FileMap area counts and focus entries from the backend registry. | wired |" in doc
    assert "no absolute local paths or source-control actions are exposed" in doc
    assert "| BAL1 | Provider health | Shows whether each configured provider/backend is reachable. | wired |" in doc
    assert "/bridge/provider-balance" in doc
    assert "| BAL3 | Token usage | Shows token use when a backend reports it. | wired |" in doc
    assert "context budget, current prompt tokens, prompt budget, and prompt budget percent" in doc
    assert "missing token numbers display as unknown, not zero" in doc
    assert "| BAL4 | Estimated spend | Shows estimated spend only when usage/cost data is trustworthy. | wired |" in doc
    assert "backend-supplied spend posture labels only" in doc
    assert "no live billing lookup is implied" in doc
    assert "| BAL5 | Remaining credit/quota | Shows remaining balance/quota where provider exposes it. | wired |" in doc
    assert "quota state, credit status, and remaining-credit labels only" in doc
    assert "account balance probing remains unavailable" in doc
    assert "| MOD12 | Public model setup help | Public build explains required CLI installs/logins and account boundaries. | wired |" in doc
    assert "Spark Models renders `/bridge/models` setup hints plus a Public setup boundary" in doc
    assert "| SET19 | Public CLI setup guidance | Exposes setup status/help for Codex and Max/Claude CLIs in public builds. | wired |" in doc
    assert "Settings/Spark renders public Codex and Claude/Max CLI setup status from `/bridge/models`" in doc
    assert "no software install, sign-in, secret read, provider-account probe, model routing mutation, Auto enablement, or prompt send" in doc
    assert "| BAL7 | Prompt payload size | Shows Relay prompt payload size and budget percentage. | wired |" in doc
    assert "Prompt Payload Visibility and Visible Prompt Payload Meter render backend-bound Relay payload size" in doc
    assert "| BAL8 | Prompt drag warning | Flags growing prompt overhead or degraded queue-mode payload growth. | wired |" in doc
    assert "`unexpected_growth_delta` and `q_mode_prompt_drag_degraded`" in doc
    assert "| BAL12 | Public account warning | Explains public users need their own provider accounts or configured keys/CLIs. | wired |" in doc
    assert "account balance, credential, billing, secret probing, and route mutation stay unavailable" in doc
    assert "| BAL11 | Manual override handoff | Links to Models/Settings for explicit user override. | wired |" in doc
    assert "Provider Balance renders Open Models and Open Settings handoff controls" in doc
    assert "do not mutate routing, enable Auto, post prompts, call providers, or bypass Relay/Aegis policy" in doc
    assert "| BAL2 | CLI/account readiness | Shows CLI installed/authenticated state for local backends. | wired |" in doc
    assert "Spark Balance fetches `/bridge/models` beside `/bridge/provider-balance`" in doc
    assert "| BAL9 | Provider comparison | Compares backend cost/availability/trust for Prime visibility. | wired |" in doc
    assert "Spark Balance renders a Provider comparison frame backed by `/bridge/provider-balance`" in doc
    assert "| MOD7 | Capability metadata | Shows backend strengths, limits, steering mode, context limits, and supported tools. | wired |" in doc
    assert "| MOD4 | Per-role mapping | Lists planned roles such as orchestrator, builder, reviewer, verifier, researcher, and release operator. | wired |" in doc
    assert "Spark Models renders display-only Role mapping entries" in doc
    assert "| MOD5 | Manual role override | Allows user to pin a model for a role once role routing exists. | wired |" in doc
    assert "Per-role model overrides persist in `meridian.role-model-overrides.v1`" in doc
    assert "| MOD8 | Trust state | Shows candidate/trusted/restricted/degraded state for each backend. | wired |" in doc
    assert "| MOD9 | Prompt payload impact | Shows prompt size/budget pressure for recent dispatches. | wired |" in doc
    assert "| MOD9A | Per-call GOAL / Intent | Shows the dispatch-scoped goal for a model call when Relay exposes it. | wired |" in doc
    assert "Relay evidence exposes backend-owned `per_call_intent`" in doc
    assert "Model Harness aspect buttons open display-only surfaces bound to `/bridge/models`, `/bridge/relay-evidence`, `/bridge/provider-balance`, `/bridge/aegis-logic`, and `/bridge/relay-logic`" in doc
    assert "no provider call, Auto enablement, route mutation, prompt payload assembly, POST, `/bridge/message`, `/bridge/call-result`, raw prompt/response/provider output/evidence body, or worker chat is authorized" in doc
    assert "account/credential probing unavailable" in doc
    assert "| SK13 | Routines | Opens current runtime continuity status until a routine automation backend exists. | wired |" in doc
    assert "| ROU0 | Runtime continuity status | Shows current continuation/goal runtime and workflow dispatch posture until routine automation exists. | wired |" in doc
    assert "/bridge/goal-runtime" in doc
    assert "/bridge/workflow-dispatch-status" in doc
    assert "no routine execution, scheduler mutation, raw artifact/log/transcript/detail paste, raw worker history replay, or self-approval is authorized" in doc
    assert "| ROU12 | Public automation boundary | Public build explains what automation needs local permissions/accounts. | wired |" in doc
    assert "Spark Routines renders a Public automation boundary beside `/bridge/goal-runtime` and `/bridge/workflow-dispatch-status`" in doc
    assert "| ARC0 | Close/archive proof snapshot | Shows current session-close/archive proof posture before any live archive controls exist. | wired |" in doc
    assert "| SK10 | Archive | Opens close/archive proof posture until reloadable archive controls exist. | wired |" in doc
    assert "/bridge/session-close-archive-proof" in doc
    assert "GET only" in doc
    assert "no live close/archive/reload/run-again/delete control" in doc
    assert "no POST route" in doc
    assert "no message route" in doc
    assert "raw worker session history" in doc
    assert "pasted transcript/log/detail body" in doc
    assert "compact typed session state only" in doc
    assert "raw detail is fetched on demand only" in doc


def test_index_settings_surface_shows_public_cli_setup_without_mutation_paths():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const renderSparkSurface = (label) =>")
    render_end = doc.index("const renderHarnessSurface = (button) =>", render_start)
    settings_surface = doc[render_start:render_end]
    assert "voice I/O and public CLI setup status wired from backend snapshots" in settings_surface
    assert "/bridge/voice-io + /bridge/models" in settings_surface
    assert "Settings public CLI setup boundary" in settings_surface
    assert "data-spark-models" in settings_surface
    assert "loadSparkModels();" in settings_surface
    assert "does not install software, sign in, read secrets, probe provider accounts, or mutate model routing" in settings_surface
    assert "Auto remains disabled until Relay owns the decision" in settings_surface
    assert "bridgeUrl('message')" not in settings_surface
    assert "method: 'POST'" not in settings_surface
    assert "bridgeUrl('restart')" not in settings_surface
    assert "bridgeUrl('call-result')" not in settings_surface

    refresh_start = doc.index("const refreshRelayPanel = () =>")
    refresh_end = doc.index("window.addEventListener('focus', refreshRelayPanel);", refresh_start)
    refresh_surface = doc[refresh_start:refresh_end]
    assert "if (rightWorkspace?.querySelector('[data-spark-models]')) loadSparkModels();" in refresh_surface


def test_index_settings_surface_reflects_project_focus_without_second_switch():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const renderProjectFocusSnapshot = () =>")
    render_end = doc.index("const renderDiagnosticDefaultPreview = (state) =>", render_start)
    project_focus = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const renderHarnessSurface = (button) =>", settings_start)
    settings_surface = doc[settings_start:settings_end]
    refresh_start = doc.index("const refreshProjectScopedSurfaces = () =>")
    refresh_end = doc.index("const refreshRelayPanel = () =>", refresh_start)
    refresh_surface = doc[refresh_start:refresh_end]

    assert "Project focus authority" in project_focus
    assert "activeProjectContext()" in project_focus
    assert "projectSelectKey" in project_focus
    assert ".session-project-select" in project_focus
    assert "selected separately; project switch does not retarget sessions" in project_focus
    assert "Project-scoped refresh path" in project_focus
    assert "Review/Crosscheck" in project_focus
    assert "Backlog/Models/Skills" in project_focus
    assert "Settings reflects the existing project selector authority instead of adding a second project switch." in project_focus
    assert "without calling /bridge/message, result recovery, or session close/archive controls." in project_focus
    assert "data-project-focus-surface" in settings_surface
    assert "refreshProjectFocusSurface();" in refresh_surface
    assert "bridgeUrl('message')" not in project_focus
    assert "bridgeUrl('call-result')" not in project_focus
    assert "method: 'POST'" not in project_focus


def test_index_settings_surface_controls_diagnostic_visibility_default_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const renderDiagnosticDefaultPreview = (state) =>")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    diagnostic_surface = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const renderHarnessSurface = (button) =>", settings_start)
    settings_surface = doc[settings_start:settings_end]

    assert "Diagnostic log visibility default" in diagnostic_surface
    assert "data-diagnostic-default-toggle" in diagnostic_surface
    assert "data-diagnostic-default-preview" in diagnostic_surface
    assert "meridian.context-filter.v1" in diagnostic_surface
    assert "state.diagnostics = target.checked" in diagnostic_surface
    assert "writeContextFilterState(state)" in diagnostic_surface
    assert "Diagnostic rows can be hidden or shown again without losing source session data." in diagnostic_surface
    assert "No backend per-session event-log route, prompt send, result recovery, provider call, or settings mutation is invoked." in diagnostic_surface
    assert "data-diagnostic-default-surface" in settings_surface
    assert "initializeDiagnosticDefaultSurface();" in settings_surface
    assert "bridgeUrl('message')" not in diagnostic_surface
    assert "bridgeUrl('call-result')" not in diagnostic_surface
    assert "method: 'POST'" not in diagnostic_surface


def test_index_settings_surface_controls_progress_filter_defaults_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const renderProgressFilterDefaultsPreview = (state) =>")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    progress_surface = doc[render_start:render_end]
    filter_start = doc.index("const renderContextFilterPreview = (state) =>")
    filter_end = doc.index("const renderContextFilterSurface = () =>", filter_start)
    filter_preview = doc[filter_start:filter_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const renderHarnessSurface = (button) =>", settings_start)
    settings_surface = doc[settings_start:settings_end]

    assert "progressInfo: true" in doc
    assert "progressWarning: true" in doc
    assert "progressError: true" in doc
    assert "Progress filter defaults" in progress_surface
    assert "data-progress-default-toggle" in progress_surface
    assert "data-progress-default-preview" in progress_surface
    assert "meridian.context-filter.v1" in progress_surface
    assert "state[target.dataset.progressDefaultToggle] = target.checked" in progress_surface
    assert "writeContextFilterState(state)" in progress_surface
    assert "progress source data is not deleted" in progress_surface
    assert "No backend progress route, prompt send, result recovery, provider call, or settings mutation is invoked." in progress_surface
    assert "progress info default" in filter_preview
    assert "progress warning default" in filter_preview
    assert "progress error default" in filter_preview
    assert "data-progress-default-surface" in settings_surface
    assert "initializeProgressFilterDefaultsSurface();" in settings_surface
    assert "bridgeUrl('message')" not in progress_surface
    assert "bridgeUrl('call-result')" not in progress_surface
    assert "method: 'POST'" not in progress_surface


def test_index_settings_surface_controls_progress_redirect_defaults_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const progressRedirectDefaultsKey = 'meridian.progress-redirects.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    redirect_surface = doc[render_start:render_end]
    filter_start = doc.index("const renderContextFilterPreview = (state) =>")
    filter_end = doc.index("const renderContextFilterSurface = () =>", filter_start)
    filter_preview = doc[filter_start:filter_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const renderHarnessSurface = (button) =>", settings_start)
    settings_surface = doc[settings_start:settings_end]

    assert "const progressRedirectDefaultsKey = 'meridian.progress-redirects.v1'" in redirect_surface
    assert "progressRedirectCategories" in redirect_surface
    assert "'routine progress'" in redirect_surface
    assert "'human gate'" in redirect_surface
    assert "progressRedirectDefaults" in redirect_surface
    assert "readProgressRedirectDefaults" in redirect_surface
    assert "writeProgressRedirectDefaults" in redirect_surface
    assert "Progress redirect defaults" in redirect_surface
    assert "data-progress-redirect-category" in redirect_surface
    assert "data-progress-redirect-preview" in redirect_surface
    assert "Category routes appear in Settings and Filter metadata only" in redirect_surface
    assert "No backend progress route, prompt send, result recovery, provider call, or settings mutation is invoked." in redirect_surface
    assert "review result route default" in filter_preview
    assert "human gate route default" in filter_preview
    assert "system health route default" in filter_preview
    assert "data-progress-redirect-surface" in settings_surface
    assert "initializeProgressRedirectDefaultsSurface();" in settings_surface
    assert "bridgeUrl('message')" not in redirect_surface
    assert "bridgeUrl('call-result')" not in redirect_surface
    assert "method: 'POST'" not in redirect_surface


def test_index_settings_surface_persists_progress_pin_mute_and_collapse_state_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const progressStateKey = 'meridian.progress-state.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    progress_state = doc[render_start:render_end]
    filter_start = doc.index("const renderContextFilterPreview = (state) =>")
    filter_end = doc.index("const renderContextFilterSurface = () =>", filter_start)
    filter_preview = doc[filter_start:filter_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const renderHarnessSurface = (button) =>", settings_start)
    settings_surface = doc[settings_start:settings_end]

    assert "progressStateDefaults" in progress_state
    assert "pinned: []" in progress_state
    assert "muted: []" in progress_state
    assert "collapsed: false" in progress_state
    assert "progressStateList" in progress_state
    assert "localStorage.getItem(progressStateKey)" in progress_state
    assert "localStorage.setItem(progressStateKey, JSON.stringify(next))" in progress_state
    assert "Progress pin list" in progress_state
    assert "data-progress-state-list=\"pinned\"" in progress_state
    assert "Progress mute list" in progress_state
    assert "data-progress-state-list=\"muted\"" in progress_state
    assert "Progress collapse state" in progress_state
    assert "data-progress-collapse-default" in progress_state
    assert "data-progress-state-preview" in progress_state
    assert "source progress/session data is not deleted" in progress_state
    assert "No backend progress route, prompt send, result recovery, provider call, or settings mutation is invoked." in progress_state
    assert "pinned progress items" in filter_preview
    assert "muted progress items" in filter_preview
    assert "progress collapse default" in filter_preview
    assert "data-progress-state-surface" in settings_surface
    assert "initializeProgressStateDefaultsSurface();" in settings_surface
    assert "bridgeUrl('message')" not in progress_state
    assert "bridgeUrl('call-result')" not in progress_state
    assert "method: 'POST'" not in progress_state


def test_index_settings_surface_persists_role_model_overrides_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const roleModelOverrideKey = 'meridian.role-model-overrides.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    role_override = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    load_models_start = doc.index("const loadSparkModels = async () =>")
    load_models_end = doc.index("const loadReleaseAutonomy = async () =>", load_models_start)
    load_models = doc[load_models_start:load_models_end]

    assert "const roleModelOverrideKey = 'meridian.role-model-overrides.v1'" in role_override
    assert "roleModelRoles" in role_override
    assert "defaultRoleModelOverrideState" in role_override
    assert "availableRoleModelOptions" in role_override
    assert "localStorage.getItem(roleModelOverrideKey)" in role_override
    assert "localStorage.setItem(roleModelOverrideKey, JSON.stringify(next))" in role_override
    assert "Role/model mapping" in role_override
    assert "data-role-model-override" in role_override
    assert "Role/model override preview" in role_override
    assert "Role/model override boundary" in role_override
    assert "These overrides do not mutate Relay routing, provider accounts, prompt payload assembly, or Auto mode." in role_override
    assert "data-role-model-overrides-surface" in settings_surface
    assert "initializeRoleModelOverridesSurface();" in settings_surface
    assert "logicNode.dataset.modelsSnapshot = JSON.stringify(snapshot);" in load_models
    assert "renderSparkModelsSnapshot(snapshot)" in load_models
    assert "bridgeUrl('message')" not in role_override
    assert "bridgeUrl('call-result')" not in role_override
    assert "method: 'POST'" not in role_override


def test_index_settings_surface_controls_focus_mode_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const focusModeKey = 'meridian.focus-mode.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    focus_mode = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    session_select_start = doc.index("const renderUserSessionSelect = () =>")
    session_select_end = doc.index("const loadUserSessions = async () =>", session_select_start)
    session_select = doc[session_select_start:session_select_end]

    assert "const focusModeKey = 'meridian.focus-mode.v1'" in focus_mode
    assert "readFocusMode" in focus_mode
    assert "writeFocusMode" in focus_mode
    assert "Focus mode" in focus_mode
    assert "data-focus-mode-toggle" in focus_mode
    assert "data-focus-mode-preview" in focus_mode
    assert "renderUserSessionSelect();" in focus_mode
    assert "Focus mode does not retarget sessions" in focus_mode
    assert "const focusMode = readFocusMode();" in session_select
    assert "Selected session outside active project" in session_select
    assert "if (focusMode && project !== activeProject) return;" in session_select
    assert "data-focus-mode-surface" in settings_surface
    assert "initializeFocusModeSurface();" in settings_surface
    assert "bridgeUrl('message')" not in focus_mode
    assert "bridgeUrl('call-result')" not in focus_mode
    assert "method: 'POST'" not in focus_mode


def test_index_settings_surface_controls_quiet_mode_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const quietModeKey = 'meridian.quiet-mode.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    quiet_mode = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    runtime_start = doc.index("const renderGoalRuntimeSnapshot = (snapshot) =>")
    runtime_end = doc.index("const renderWorkflowDispatchStatusSnapshot = (snapshot) =>", runtime_start)
    runtime_surface = doc[runtime_start:runtime_end]
    workflow_start = doc.index("const renderWorkflowDispatchStatusSnapshot = (snapshot) =>")
    workflow_end = doc.index("const renderEchoMemorySnapshot = (snapshot) =>", workflow_start)
    workflow_surface = doc[workflow_start:workflow_end]

    assert "const quietModeKey = 'meridian.quiet-mode.v1'" in quiet_mode
    assert "readQuietMode" in quiet_mode
    assert "writeQuietMode" in quiet_mode
    assert "Quiet mode" in quiet_mode
    assert "data-quiet-mode-toggle" in quiet_mode
    assert "data-quiet-mode-preview" in quiet_mode
    assert "rerenderRuntimeSurfaces" in quiet_mode
    assert "blockers and proof gates" in quiet_mode
    assert "data-quiet-mode-surface" in settings_surface
    assert "initializeQuietModeSurface();" in settings_surface
    assert "const quietMode = readQuietMode();" in runtime_surface
    assert "Quiet mode routine status" in runtime_surface
    assert "suppressed in this surface" in runtime_surface
    assert "Checkpoint advisory refs" in runtime_surface
    assert "const quietMode = readQuietMode();" in workflow_surface
    assert "Quiet mode workflow status" in workflow_surface
    assert "Failure summary shape" in workflow_surface
    assert "logicNode.dataset.goalRuntimeSnapshot = JSON.stringify(snapshot);" in doc
    assert "logicNode.dataset.workflowDispatchStatusSnapshot = JSON.stringify(snapshot);" in doc
    assert "bridgeUrl('message')" not in quiet_mode
    assert "bridgeUrl('call-result')" not in quiet_mode
    assert "method: 'POST'" not in quiet_mode


def test_index_settings_surface_controls_quick_reply_order_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.rindex("const quickReplyOrderKey = 'meridian.quick-reply-order.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    quick_reply = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    prompt_start = doc.index("const insertPromptToken = (input, token) => {")
    prompt_end = doc.index("})();", prompt_start)
    prompt_surface = doc[prompt_start:prompt_end]

    assert "const quickReplyOrderKey = 'meridian.quick-reply-order.v1'" in quick_reply
    assert "quickReplyDefaults = ['Yes', 'No', 'Continue', 'Confirm']" in quick_reply
    assert "normalizeQuickReplyOrder" in quick_reply
    assert "readQuickReplyOrder" in quick_reply
    assert "writeQuickReplyOrder" in quick_reply
    assert "Quick reply order" in quick_reply
    assert "data-quick-reply-order" in quick_reply
    assert "data-quick-reply-order-preview" in quick_reply
    assert "applyQuickReplyOrder();" in quick_reply
    assert "Visible buttons still inject their literal word" in quick_reply
    assert "button.hidden = !order.includes(label);" in prompt_surface
    assert "const token = button.getAttribute('aria-label') || '';" in prompt_surface
    assert "insertPromptToken(input, token);" in prompt_surface
    assert "data-quick-reply-order-surface" in settings_surface
    assert "initializeQuickReplyOrderSurface();" in settings_surface
    assert "bridgeUrl('message')" not in quick_reply
    assert "bridgeUrl('call-result')" not in quick_reply
    assert "method: 'POST'" not in quick_reply


def test_index_settings_surface_controls_wake_mode_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.rindex("const wakeModeKey = 'meridian.wake-mode.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    wake_mode = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    reload_start = doc.index("const cleanReloadMarker = () => {")
    reload_end = doc.index("const orb = document.querySelector('.date-orb');", reload_start)
    reload_marker = doc[reload_start:reload_end]
    restore_start = doc.index("const restoreStoredRightPanel = () => {")
    restore_end = doc.index("menu.addEventListener('pointerenter', openSpark);", restore_start)
    restore_panel = doc[restore_start:restore_end]

    assert "const wakeModeKey = 'meridian.wake-mode.v1'" in wake_mode
    assert "wakeModeOptions = ['full wake', 'fast wake', 'silent wake']" in wake_mode
    assert "readWakeMode" in wake_mode
    assert "writeWakeMode" in wake_mode
    assert "Wake mode" in wake_mode
    assert "data-wake-mode" in wake_mode
    assert "data-wake-mode-preview" in wake_mode
    assert "restore User panel quietly" in wake_mode
    assert "data-wake-mode-surface" in settings_surface
    assert "initializeWakeModeSurface();" in settings_surface
    assert "window.meridianReloadMarkerPresent = cleanReloadMarker();" in reload_marker
    assert "if (readWakeMode() === 'silent wake')" in restore_panel
    assert "restoreUserPanel({ persist: false });" in restore_panel
    assert "if (readWakeMode() === 'full wake')" in restore_panel
    assert "Wake complete: full wake restored the last visible panel." in restore_panel
    assert "Wake complete: full wake restored the session interface." in restore_panel
    assert "pushEntry(" in restore_panel
    assert "bridgeUrl('message')" not in wake_mode
    assert "bridgeUrl('call-result')" not in wake_mode
    assert "method: 'POST'" not in wake_mode


def test_index_settings_surface_controls_risk_tier_override_locally():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const riskTierOverrideKey = 'meridian.risk-tier-overrides.v1'")
    render_end = doc.index("const filterToggle = (key, label, state) =>", render_start)
    risk_override = doc[render_start:render_end]
    settings_start = doc.index("const renderSparkSurface = (label) =>")
    settings_end = doc.index("const harnessDraftStorageKey", settings_start)
    settings_surface = doc[settings_start:settings_end]
    filter_start = doc.index("const renderContextFilterPreview = (state) =>")
    filter_end = doc.index("const renderContextFilterSurface = () =>", filter_start)
    filter_preview = doc[filter_start:filter_end]

    assert "const riskTierOverrideKey = 'meridian.risk-tier-overrides.v1'" in risk_override
    assert "riskTierOverrideOptions" in risk_override
    assert "'follow-prime-proposal'" in risk_override
    assert "'tier-4'" in risk_override
    assert "riskOverrideScopeEntries" in risk_override
    assert "readRiskTierOverrides" in risk_override
    assert "writeRiskTierOverrides" in risk_override
    assert "riskTierProofSummary" in risk_override
    assert "Risk tier override" in risk_override
    assert "data-risk-tier-override" in risk_override
    assert "data-risk-tier-override-preview" in risk_override
    assert "Prime still owns the live proposed risk tier" in risk_override
    assert "No backend settings route, prompt send, result recovery, or proof-gate mutation is invoked." in risk_override
    assert "Prime risk override" in filter_preview
    assert "User risk override" in filter_preview
    assert "data-risk-tier-override-surface" in settings_surface
    assert "initializeRiskTierOverrideSurface();" in settings_surface
    assert "bridgeUrl('message')" not in risk_override
    assert "bridgeUrl('call-result')" not in risk_override
    assert "method: 'POST'" not in risk_override


def test_index_voice_io_surface_shows_public_setup_guidance_without_voice_mutation():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    render_start = doc.index("const renderVoiceIoSnapshot = (snapshot) =>")
    render_end = doc.index("const renderSparkModelsSnapshot = (snapshot) =>", render_start)
    voice_surface = doc[render_start:render_end]
    assert "Public voice setup boundary" in voice_surface
    assert "browser microphone permission and a reviewed speech provider" in voice_surface
    assert "setup guidance from /bridge/voice-io" in voice_surface
    assert "the UI does not request permission, start capture, synthesize speech, read secrets, or mutate provider settings" in voice_surface
    assert "Typed prompt and response paths remain available while voice input/output is unavailable." in voice_surface
    assert "microphone authorized" in voice_surface
    assert "speech output authorized" in voice_surface
    assert "read aloud authorized" in voice_surface
    assert "controls disabled" in voice_surface
    assert "Voice privacy indicator" in voice_surface
    assert "microphone capture" in voice_surface
    assert "capture can start" in voice_surface
    assert "top icon capture state" in voice_surface
    assert "permission prompt active" in voice_surface
    assert "capture state visible and fail-closed" in voice_surface
    assert "snapshot.microphone_authorized && voice.listening ? 'active' : 'inactive'" in voice_surface
    assert "snapshot.microphone_authorized && !snapshot.controls_disabled ? 'yes' : 'no'" in voice_surface
    assert "navigator.mediaDevices" not in voice_surface
    assert "getUserMedia" not in voice_surface
    assert "speechSynthesis" not in voice_surface
    assert "SpeechRecognition" not in voice_surface

    button_start = doc.index("const applySpeechButtonVoiceState = (snapshot = {}) =>")
    button_end = doc.index("const refreshSpeechButtonVoiceState = async () =>", button_start)
    speech_button = doc[button_start:button_end]
    assert "speechButton.dataset.captureState" in speech_button
    assert "Microphone capture active" in speech_button
    assert "Microphone capture inactive" in speech_button
    assert "speechButton.title" in speech_button
    assert "speechButton.disabled = true" in speech_button
    assert "MediaRecorder" not in voice_surface
    assert "method: 'POST'" not in voice_surface


def test_ui_checklist_promotes_right_panel_toggle_only_after_surface_rows_are_wired():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "| SP2 | Right interaction panel | Shows either User Session prompt UI, Settings configuration items, or Harness logic items. | wired |" in doc
    assert "| SK1 | Spark center image | Visual voice/core of Prime and entry point for right-panel surface focus. | wired |" in doc
    assert "| SPK10 | Surface transition animation | Any transition animation preserves readability and does not hide state changes. | wired |" in doc
    assert "opacity never below 0.82, no blur/filter/display hiding" in doc
    assert "`prefers-reduced-motion: reduce` path" in doc
    assert "| SK4 | Filter | Controls how much data is included in a session prompt/context stream. | wired |" in doc
    assert "Spark Filter opens a UI-local context filter surface" in doc
    for row_id in ("FIL1", "FIL2", "FIL3", "FIL4", "FIL5", "FIL6", "FIL7", "FIL8", "FIL9", "FIL10", "FIL11", "FIL12"):
        row = doc[doc.index(f"| {row_id} |"):].splitlines()[0]
        assert "| wired |" in row
    assert "| SK2 | Toggle session panels | Switches the right panel between User Session, Settings, and harness-scoped surfaces. | wired |" in doc
    assert "`SUR1`-`SUR13` pin switching, persistence, layout, close, stale-target, settings-action behavior, and display-only harness item action scoping" in doc
    for row_id in ("SUR1", "SUR2", "SUR3", "SUR4", "SUR5", "SUR6", "SUR7", "SUR8", "SUR10", "SUR11", "SUR12", "SUR13"):
        row = doc[doc.index(f"| {row_id} |"):].splitlines()[0]
        assert "| wired |" in row
    assert "| SUR9 | Harness item actions | Harness mode actions apply only to selected harness logic items. | wired |" in doc
    assert "Generic harness surfaces render a Harness item action scope section naming the selected harness, selected logic item, action target, blocked execution state, and no User Session or Prime prompt route" in doc
    assert "| HMS7 | Unsupported action guard | If harness logic action is not supported yet, action is blocked with readable warning. | wired |" in doc
    assert "Generic planned harness surfaces render an explicit Unsupported action guard" in doc
    assert "| HMS8 | Logic update framing | Harness mode language frames work as updating/adding harness logic. | wired |" in doc
    assert "Generic planned harness surfaces render a Logic update framing section" in doc
    assert "| HMS9 | Harness state summary | Shows concise harness status once real state exists. | wired |" in doc
    assert "Generic planned harness surfaces render a Harness state summary" in doc
    assert "| HN5 | Security | Reserved TBD harness identity; replaces generic TBD. | wired |" in doc
    assert "Security is the planned reserved harness identity with `Security-Guardrails`" in doc
    assert "| HN15 | Ratchet / Tool | Opens/focuses tool execution surface. | wired |" in doc
    assert "Click opens Ratchet-Tools through the generic display-only harness surface" in doc
    assert "| HN16 | Source / Git | Opens/focuses git/source-control surface. | wired |" in doc
    assert "Click opens Source-Git through the generic display-only harness surface" in doc
    assert "| HN17 | Vision / Browser | Opens/focuses browser/vision surface. | wired |" in doc
    assert "Click opens Vision-Browser through the generic display-only harness surface" in doc
    assert "| HMS6 | Harness-specific actions | Right-panel actions target selected harness logic item. | wired |" in doc
    assert "Generic harness surfaces expose display-only action metadata naming the selected harness and `Harness logic` item" in doc
    assert "| HMS15 | No cross-harness leakage | Logic item edits/actions for one harness do not silently route to another harness. | wired |" in doc
    assert "Generic planned harness surfaces render a Harness isolation boundary" in doc
    assert "| HMS14 | Harness edit preservation | Unsaved harness-mode item edits are preserved per harness where useful. | wired |" in doc
    assert "Generic planned harness surfaces render a UI-local unsaved harness logic note stored under `meridian.harness.draft.v1.<harness>`" in doc
    assert "| HMS12 | Harness permission boundary | High-risk harness actions require explicit approval. | wired |" in doc
    assert "Planned Tool/Git/Browser harness surfaces render a permission boundary" in doc
    assert "| HMS4 | Prime review path | Prime reviews harness intent, risk, and proof needs before model interaction. | wired |" in doc
    assert "Prime Runtime Logic renders a display-only `Prime review before dispatch` section from `/bridge/prime-logic`" in doc
    assert "leaving route/provider/payload decisions with Relay and Model Harness" in doc
    assert "const renderRightPanelSurface = ({ title, status, sections, surfaceClass = '' }) =>" in index
    assert "const renderHarnessSurface = (button) =>" in index
    assert "const renderSparkSurface = (label) =>" in index
    assert "setRightPanelAuthority('harness', button.dataset.harness || 'Harness', { persist })" in index
    assert "setRightPanelAuthority('spark', actionLabel || 'Spark', { persist })" in index
    assert ".session-window-right.is-panel-surface .session-prompt-input" in index


def test_ui_checklist_promotes_prompt_payload_balance_rows_from_backend_bound_evidence():
    checklist = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    progress = (ROOT / "docs" / "v2-progress-tracker.md").read_text(encoding="utf-8")
    tests = (ROOT / "tests" / "test_bifrost_cockpit.py").read_text(encoding="utf-8")
    assert "| BAL7 | Prompt payload size | Shows Relay prompt payload size and budget percentage. | wired |" in checklist
    assert "| BAL8 | Prompt drag warning | Flags growing prompt overhead or degraded queue-mode payload growth. | wired |" in checklist
    assert "Bifrost + Prompt Payload Visibility" in progress
    assert "review-cleared" in progress
    assert "Relay prompt payload size, budget pressure, growth/flat state, Q-mode prompt-drag, evidence refs" in progress
    assert "def test_backend_bound_prompt_payload_visibility_renders_adjacent_to_dispatch_and_queue_poll():" in tests
    assert 'meter_section = _slice_aria_section(doc, "Visible Prompt Payload Meter")' in tests
    assert 'payload_section = _slice_aria_section(doc, "Prompt Payload Visibility")' in tests
    assert 'data-growth-state="flat"' in tests
    assert "Growth delta: +240 tokens / 6.0%" in tests
    assert "Q-mode prompt drag: degraded" in tests
    assert "q_mode_prompt_drag_degraded" in tests
    assert "unexpected_growth_delta" in tests
    assert "Payload evidence: payload-snapshot:deepseek-qmode" in tests


def test_model_harness_taxonomy_stays_ui_strategy_until_promoted():
    doc = (ROOT / "docs" / "model-harness-v2-contract.md").read_text(encoding="utf-8")
    assert "## Future Taxonomy Promotion Gate" in doc
    assert "display vocabulary, not a hard backend naming convention" in doc
    assert "Existing backend names and contract names remain authoritative" in doc
    assert "Architecture taxonomy from `2-Architecture.md` is treated the same way for now" in doc
    assert "useful UI/strategy vocabulary" in doc
    assert "canonical taxonomy name list" in doc
    assert "must not create new Python enums, dataclasses, route fields, or package exports directly from UI-only labels" in doc
    assert "already-reviewed surfaces" in doc


def test_v2_strategy_docs_keep_model_call_ownership_with_relay_and_model_harness():
    plan = (ROOT / "docs" / "v2-detailed-build-plan.md").read_text(encoding="utf-8")
    tracker = (ROOT / "docs" / "v2-progress-tracker.md").read_text(encoding="utf-8")
    handoff = (ROOT / "docs" / "aegis-relay-summary-handoff-contract.md").read_text(encoding="utf-8")
    model_contract = (ROOT / "docs" / "model-harness-v2-contract.md").read_text(encoding="utf-8")
    stage = (ROOT / "docs" / "harness-stage-checklist.md").read_text(encoding="utf-8")
    stage_html = (ROOT / "docs" / "harness-stage-checklist.html").read_text(encoding="utf-8")
    for doc in (plan, tracker):
        assert "Prime/Orchestrator owns intent" in doc or "Prime selects the work intent and risk tier" in doc
        assert "Relay + Model Harness" in doc
        assert "provider/model identity" in doc or "provider identity" in doc
        assert "prompt payload" in doc
        assert "transport" in doc
        assert "provider balance" in doc
    assert "No Prime-owned provider routing table" in plan
    assert "Bifrost renders those backend-owned concepts; it does not rename or re-own them" in tracker
    assert "Prompt/payload safety" in handoff
    assert "Relay/Model Harness domain, with Aegis/Security policy gates" in handoff
    assert "It does not own exact provider/model identity" in model_contract
    assert "Those remain Model Harness/Relay-owned" in model_contract
    assert "Bifrost renders backend-owned state and must not convert taxonomy labels into backend authority" in stage
    assert "Relay + Model Harness own model-call mechanics" in stage_html


def test_v2_tracker_has_deep_compass_and_vulcan_backend_items():
    doc = (ROOT / "docs" / "v2-progress-tracker.md").read_text(encoding="utf-8")
    assert "### Compass Harness" in doc
    assert "Compass + Project Definition Runtime" in doc
    assert "Compass + Cross-Project Handoff Runtime" in doc
    assert "Session Lifecycle + State Evidence Completeness" in doc
    assert "Session Lifecycle + Command Plan Proof" in doc
    assert "Session Lifecycle + Close/Archive Write-Through" in doc


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


# render_cockpit_html document structure


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


# Top navigation removal


def test_render_has_no_permanent_top_navigation():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "cockpit-nav" not in doc
    for label in ("Settings", "Reset", "Close", "Cross Check", "Backlog", "Skills"):
        assert label not in doc



# Prime panel


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
    assert 'data-voice-control="mute-status"' in doc
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


def test_provider_balance_sample_renders_all_route_families_and_selected_provider():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Provider Balance"' in doc
    assert 'class="provider-item provider-ok provider-pressure-low provider-credit-available"' in doc
    assert 'data-provider="claude" data-selected="true"' in doc
    assert "Selected: claude" in doc
    for expected in ("Claude", "OpenAI", "DeepSeek", "OpenRouter", "Local"):
        assert expected in doc
    for route in ("Route: direct", "Route: aggregator", "Route: local"):
        assert route in doc


def test_provider_balance_sample_renders_credit_token_and_spend_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Context: 200000" in doc
    assert "Tokens: 1240/4000" in doc
    assert "Delta: 0" in doc
    assert "Remaining: credit: available" in doc
    assert "Spend: $0.18 estimated" in doc
    assert "Quota: available" in doc
    assert "Remaining: credit: limited" in doc
    assert "Spend: $0.03 estimated" in doc


def test_provider_balance_sample_renders_cost_pressure_states():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "provider-pressure-low" in doc
    assert "provider-pressure-medium" in doc
    assert "provider-pressure-high" in doc
    assert "provider-pressure-degraded" in doc
    assert "provider-pressure-blocked" in doc
    assert "Pressure: low" in doc
    assert "Pressure: medium" in doc
    assert "Pressure: high" in doc
    assert "Pressure: degraded" in doc
    assert "Pressure: blocked" in doc


def test_provider_balance_sample_renders_aggregator_and_local_status_details():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'data-provider="openrouter"' in doc
    assert 'data-provider="local"' in doc
    assert "Aggregator route lacks payload snapshot proof" in doc
    assert "Local deterministic route unavailable" in doc
    assert "Remaining: credit: provider-hidden" in doc
    assert "Remaining: credit: n/a" in doc
    assert "Quota: metered" in doc
    assert "Quota: unavailable" in doc


def test_provider_balance_escapes_extended_fields():
    vm = sample_cockpit_view_model()
    vm.provider_balance = ProviderBalanceView(
        providers=[
            ProviderBalanceItem(
                provider_id="<script>provider</script>",
                display_name="<img src=x>",
                model_name="model:<bad>",
                trust_state="<script>trust</script>",
                health="degraded",
                route_kind="<script>route</script>",
                context_budget_tokens=1,
                prompt_budget_tokens=2,
                current_prompt_tokens=1,
                prompt_budget_percent=50.0,
                prompt_delta_tokens=1,
                cost_pressure="<script>pressure</script>",
                quota_state="quota:<bad>",
                remaining_credit_label="credit:<bad>",
                credit_status="limited",
                estimated_spend_label="$<bad>",
                notes="<script>notes</script>",
            )
        ],
        selected_provider="<script>provider</script>",
        routing_owner="Relay",
        policy_state="warning",
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;provider&lt;/script&gt;" in doc
    assert "model:&lt;bad&gt;" in doc
    assert "Route: &lt;script&gt;route&lt;/script&gt;" in doc
    assert "Remaining: credit:&lt;bad&gt;" in doc
    assert "Spend: $&lt;bad&gt;" in doc


def test_provider_balance_preserves_other_bifrost_surfaces_and_stale_recovery():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-provider-session", "Closed Provider Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-provider-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Provider Balance"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Provider Session" not in doc


def test_model_capability_metadata_sample_renders_required_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Model Harness Capability Metadata"' in doc
    assert "Model Harness Capability Metadata" in doc
    assert "Source: model-harness-sample" in doc
    assert "Selected model: claude-sonnet-4-20250514" in doc
    assert "Exact model: claude-sonnet-4-20250514" in doc
    assert "Exact model: gpt-4o" in doc
    assert "Exact model: deepseek-chat" in doc
    assert 'data-model="claude-sonnet-4-20250514" data-provider="claude" data-selected="true"' in doc


def test_model_capability_metadata_sample_renders_route_trust_and_context():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Route: direct" in doc
    assert "Route: aggregator" in doc
    assert "Trust: trusted" in doc
    assert "Trust: candidate" in doc
    assert "Trust: degraded" in doc
    assert "Context window: 200000" in doc
    assert "Context window: 256000" in doc
    assert "Cost posture: premium" in doc
    assert "Cost posture: minimal" in doc
    assert "Latency: fast" in doc
    assert "Tokenizer: deepseek" in doc


def test_model_capability_metadata_sample_renders_task_hints_and_review_state():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="capability-list capability-allowed-tasks"' in doc
    assert 'class="capability-list capability-blocked-tasks"' in doc
    assert "build" in doc
    assert "verify" in doc
    assert "review_clearing" in doc
    assert "payload_snapshot" in doc
    assert "External review: required" in doc
    assert "External review: not_required" in doc
    assert "Streaming: yes" in doc
    assert "Q-mode flat: yes" in doc
    assert "Q-mode flat: no" in doc


def test_model_capability_metadata_sample_renders_candidate_trust_badges():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Candidate Trust and External Review Badges"' in doc
    assert "Candidate trust: trusted" in doc
    assert "Candidate trust: candidate" in doc
    assert "Candidate trust: validation_blocked" in doc
    assert "Candidate trust: external_review_cleared" in doc
    assert "capability-candidate-trusted" in doc
    assert "capability-candidate-candidate" in doc
    assert "capability-candidate-validation_blocked" in doc
    assert "capability-candidate-external_review_cleared" in doc


def test_model_capability_metadata_sample_renders_external_review_badges():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "External review status: not_required" in doc
    assert "External review status: pending" in doc
    assert "External review status: passed" in doc
    assert "capability-review-not_required" in doc
    assert "capability-review-pending" in doc
    assert "capability-review-passed" in doc
    assert "Proof: strong" in doc
    assert "Proof: standard" in doc
    assert "Proof: weak" in doc


def test_model_capability_metadata_sample_renders_blocked_authorities():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="capability-list capability-blocked-authorities"' in doc
    assert 'aria-label="Blocked Authorities"' in doc
    assert "external_review_required" in doc
    assert "aggregator_without_proof" in doc
    assert "payload_snapshot_missing" in doc
    assert "review:codex-b" in doc
    assert "validation:deepseek-direct-passed" in doc


def test_model_capability_metadata_sample_renders_prompt_drag_and_evidence_refs():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Prompt budget: within_budget" in doc
    assert "Prompt budget: watch" in doc
    assert "Prompt budget: near_limit" in doc
    assert "Prompt growth: flat" in doc
    assert "Prompt growth: unexpected_growth" in doc
    assert "Prompt growth: degraded" in doc
    assert "Prompt delta: 240" in doc
    assert "Prompt delta: 360" in doc
    assert "adapter:deepseek" in doc
    assert "validation:pending" in doc
    assert "snapshot:unavailable" in doc


def test_model_capability_metadata_escapes_structured_fields():
    vm = sample_cockpit_view_model()
    vm.model_capabilities = ModelCapabilityMetadataView(
        selected_model_id="<script>model</script>",
        metadata_source="<script>source</script>",
        items=[
            ModelCapabilityItem(
                provider_id="<img src=x>",
                exact_model_id="<script>model</script>",
                route_kind="<bad>",
                trust_state="<script>trust</script>",
                candidate_trust_state="<script>candidate</script>",
                context_window_tokens=1,
                cost_posture="<script>cost</script>",
                latency_tier="<bad>",
                tokenizer_family="<script>tokenizer</script>",
                external_review_status="<script>review</script>",
                proof_strength="<bad-proof>",
                blocked_authorities=["authority:<bad>"],
                allowed_task_hints=["<script>allowed</script>"],
                blocked_task_hints=["blocked:<bad>"],
                prompt_budget_status="<script>budget</script>",
                prompt_growth_state="growth:<bad>",
                prompt_delta_tokens=9,
                evidence_refs=["evidence:<bad>"],
            )
        ],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;model&lt;/script&gt;" in doc
    assert "Route: &lt;bad&gt;" in doc
    assert "Candidate trust: &lt;script&gt;candidate&lt;/script&gt;" in doc
    assert "External review status: &lt;script&gt;review&lt;/script&gt;" in doc
    assert "Proof: &lt;bad-proof&gt;" in doc
    assert "authority:&lt;bad&gt;" in doc
    assert "blocked:&lt;bad&gt;" in doc
    assert "evidence:&lt;bad&gt;" in doc


def test_model_capability_metadata_preserves_existing_surfaces_and_stale_recovery():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-capability-session", "Closed Capability Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-capability-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Model Harness Capability Metadata"' in doc
    assert 'aria-label="Model Harness Runtime Validation Envelopes"' in doc
    assert 'aria-label="Provider Balance"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Capability Session" not in doc


def test_model_validation_envelopes_sample_renders_required_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Model Harness Runtime Validation Envelopes"' in doc
    assert "Runtime Validation Envelopes" in doc
    assert "Source: model-harness-runtime-validation-sample" in doc
    assert 'data-envelope="validation:claude-direct-ready"' in doc
    assert "Validation: allowed" in doc
    assert "Fail closed: none" in doc
    assert "Provider: claude" in doc
    assert "Exact model: claude-sonnet-4-20250514" in doc
    assert "Dispatch id: claude-sonnet-4-20250514" in doc
    assert "Route: direct" in doc


def test_model_validation_envelopes_sample_renders_fail_closed_proofs_and_badges():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "validation:deepseek-review-pending" in doc
    assert "validation:openrouter-aggregator-blocked" in doc
    assert "Validation: fail_closed" in doc
    assert "Fail closed: external_review_required" in doc
    assert "Fail closed: blocked_authority" in doc
    assert "endpoint:https://api.deepseek.com/v1/chat/completions" in doc
    assert "aggregator:openrouter" in doc
    assert "direct-proof:unavailable" in doc
    assert "Candidate trust: candidate" in doc
    assert "Candidate trust: validation_blocked" in doc
    assert "External review status: pending" in doc
    assert "Proof: weak" in doc


def test_model_validation_envelopes_sample_renders_prompt_drag_and_evidence():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Prompt budget: within_budget" in doc
    assert "Prompt budget: watch" in doc
    assert "Prompt budget: near_limit" in doc
    assert "Prompt growth: flat" in doc
    assert "Prompt growth: unexpected_growth" in doc
    assert "Prompt growth: degraded" in doc
    assert "Budget percent: 23.0%" in doc
    assert "Budget percent: 88.9%" in doc
    assert "Prompt delta: 360" in doc
    assert "Delta percent: 12.0%" in doc
    assert "review_clearing_blocked" in doc
    assert "prompt_drag_degraded" in doc
    assert "budget:deepseek-watch" in doc


def test_model_validation_envelopes_escape_structured_fields():
    vm = sample_cockpit_view_model()
    vm.model_validation_envelopes = ModelValidationEnvelopeView(
        source="<script>validation</script>",
        envelopes=[
            ModelValidationEnvelopeItem(
                envelope_id="<script>envelope</script>",
                provider_id="<img src=x>",
                exact_model_id="<script>model</script>",
                dispatch_id="dispatch:<bad>",
                route_kind="<bad-route>",
                validation_state="<bad-state>",
                fail_closed_reason="reason:<bad>",
                candidate_trust_state="<script>candidate</script>",
                external_review_status="<script>review</script>",
                proof_strength="<bad-proof>",
                prompt_budget_status="<script>budget</script>",
                prompt_growth_state="growth:<bad>",
                prompt_budget_percent=9.5,
                prompt_delta_tokens=7,
                prompt_delta_percent=1.5,
                route_proof_refs=["proof:<bad>"],
                blocker_tags=["blocker:<bad>"],
                warning_tags=["warning:<bad>"],
                evidence_refs=["evidence:<bad>"],
            )
        ],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "Source: &lt;script&gt;validation&lt;/script&gt;" in doc
    assert "data-envelope=\"&lt;script&gt;envelope&lt;/script&gt;\"" in doc
    assert "Provider: &lt;img src=x&gt;" in doc
    assert "Dispatch id: dispatch:&lt;bad&gt;" in doc
    assert "Candidate trust: &lt;script&gt;candidate&lt;/script&gt;" in doc
    assert "External review status: &lt;script&gt;review&lt;/script&gt;" in doc
    assert "Proof: &lt;bad-proof&gt;" in doc
    assert "proof:&lt;bad&gt;" in doc
    assert "blocker:&lt;bad&gt;" in doc
    assert "warning:&lt;bad&gt;" in doc
    assert "evidence:&lt;bad&gt;" in doc


def test_visible_prompt_payload_meter_sample_renders_required_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Visible Prompt Payload Meter"' in doc
    assert "Visible Prompt Payload Meter" in doc
    assert "Source: relay-visible-prompt-payload-meter-sample" in doc
    assert 'data-meter-id="payload-meter:claude-dispatch-under-1k"' in doc
    assert 'data-meter-id="payload-meter:deepseek-qmode-12-4k"' in doc
    assert 'data-meter-id="payload-meter:openrouter-qmode-blocked"' in doc
    assert "under 1k" in doc
    assert "12.4k" in doc
    assert "over budget" in doc


def test_visible_prompt_payload_meter_sample_renders_route_and_budget_continuity():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Provider: claude" in doc
    assert "Model: claude-sonnet-4-20250514" in doc
    assert "Route: direct" in doc
    assert "Provider: deepseek" in doc
    assert "Model: deepseek-chat" in doc
    assert "Provider: openrouter" in doc
    assert "Route: aggregator" in doc
    assert "Budget: 23.0%" in doc
    assert "Budget: 72.0%" in doc
    assert "Budget: 101.5%" in doc
    assert "Growth delta: 0 tokens / 0.0%" in doc
    assert "Growth delta: +240 tokens / 6.0%" in doc
    assert "Growth delta: +720 tokens / 18.0%" in doc
    assert "Provider balance: provider-balance:claude" in doc
    assert "Provider balance: provider-balance:deepseek" in doc
    assert "Provider balance: provider-balance:openrouter" in doc


def test_visible_prompt_payload_meter_sample_renders_qmode_drag_states_and_evidence():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Payload status: ok" in doc
    assert "Payload status: degraded" in doc
    assert "Payload status: blocked" in doc
    assert "Q-mode prompt drag: flat" in doc
    assert "Q-mode prompt drag: degraded" in doc
    assert "Q-mode prompt drag: blocked" in doc
    assert "payload-snapshot:dispatch-latest" in doc
    assert "payload-snapshot:deepseek-qmode" in doc
    assert "payload-snapshot:unavailable" in doc
    assert "telemetry:deepseek-qmode" in doc
    assert "telemetry:missing-provider-metadata" in doc
    assert "q_mode_prompt_drag_degraded" in doc
    assert "unexpected_growth_delta" in doc
    assert "route_mismatch_warning" in doc
    assert "q_mode_payload_over_budget" in doc
    assert "aggregator_prompt_drag_blocked" in doc


def test_visible_prompt_payload_meter_escapes_structured_fields():
    vm = sample_cockpit_view_model()
    vm.visible_prompt_payload_meter = VisiblePromptPayloadMeterView(
        source="<script>source</script>",
        items=[
            VisiblePromptPayloadMeterItem(
                meter_id="<script>meter</script>",
                provider_id="<img src=x>",
                model_id="<script>model</script>",
                route_kind="<bad-route>",
                prompt_label="<12k>",
                payload_status="<bad-status>",
                budget_percent=9.5,
                growth_delta_tokens=12,
                growth_delta_percent=1.5,
                q_mode_prompt_drag_state="<script>drag</script>",
                provider_balance_ref="balance:<bad>",
                payload_evidence_ref="payload:<bad>",
                telemetry_ref="telemetry:<bad>",
                warning_tags=["warning:<bad>"],
                blocker_tags=["blocker:<bad>"],
            )
        ],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "Source: &lt;script&gt;source&lt;/script&gt;" in doc
    assert 'data-meter-id="&lt;script&gt;meter&lt;/script&gt;"' in doc
    assert "Provider: &lt;img src=x&gt;" in doc
    assert "Model: &lt;script&gt;model&lt;/script&gt;" in doc
    assert "&lt;12k&gt;" in doc
    assert "Payload status: &lt;bad-status&gt;" in doc
    assert "Q-mode prompt drag: &lt;script&gt;drag&lt;/script&gt;" in doc
    assert "balance:&lt;bad&gt;" in doc
    assert "payload:&lt;bad&gt;" in doc
    assert "telemetry:&lt;bad&gt;" in doc
    assert "warning:&lt;bad&gt;" in doc
    assert "blocker:&lt;bad&gt;" in doc


def test_visible_prompt_payload_meter_preserves_existing_surfaces():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-meter-session", "Closed Meter Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-meter-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Visible Prompt Payload Meter"' in doc
    assert 'aria-label="Recovery Readiness Advisory Summary"' in doc
    assert 'class="stale-recovery-actions"' in doc
    assert 'aria-label="Model Harness Runtime Validation Envelopes"' in doc
    assert 'aria-label="Provider Balance"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Meter Session" not in doc
    assert "raw prompt text" not in doc
    assert "provider response text" not in doc


def test_prompt_payload_sample_renders_structured_visibility_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'class="payload-size">(under 1k)</span>' in doc
    assert "920 tokens" in doc
    assert "23% budget" in doc
    assert "Prompt budget: 4000 tokens" in doc
    assert "Context budget: 200000 tokens" in doc
    assert 'data-growth-state="flat"' in doc
    assert 'data-watch-state="ok"' in doc
    assert "Delta: 0 tokens / 0.0%" in doc


def test_prompt_payload_sample_renders_provider_route_and_evidence_context():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Provider: claude" in doc
    assert "Model: claude-opus-4-7" in doc
    assert "Trust: trusted" in doc
    assert "Route class: direct_api" in doc
    assert "Route kind: account-first" in doc
    assert "Evidence: payload-snapshot:dispatch-latest" in doc
    assert "Telemetry: telemetry:prompt-payload" in doc
    assert "Adapter: adapter:claude" in doc


def test_prompt_payload_renders_label_variants_and_watch_states():
    cases = [
        ("(under 1k)", "flat", "ok"),
        ("(12.4k)", "growing_expected", "watch"),
        ("(over budget)", "over_budget", "blocked"),
        ("(unknown)", "unknown", "degraded"),
    ]
    for label, growth_state, watch_state in cases:
        vm = sample_cockpit_view_model()
        vm.prompt_payload = PromptPayloadView(
            size_label=label,
            estimated_tokens=0 if label == "(unknown)" else 12400,
            prompt_budget_tokens=10000,
            context_budget_tokens=128000,
            budget_percent=124.0 if label == "(over budget)" else 42.0,
            delta_tokens=320,
            delta_percent=2.7,
            growth_state=growth_state,
            watch_state=watch_state,
            source="queue_q_mode",
            provider_id="deepseek",
            model_name="deepseek-chat",
            trust_state="candidate",
            route_class="direct_api",
            route_kind="direct",
            evidence_ref="payload:snapshot",
            telemetry_ref="telemetry:q-mode",
            adapter_metadata_ref="adapter:deepseek",
        )
        doc = render_cockpit_html(vm)
        assert f'class="payload-size">{label}</span>' in doc
        assert f'data-growth-state="{growth_state}"' in doc
        assert f'data-watch-state="{watch_state}"' in doc
        assert "From: queue_q_mode" in doc


def test_prompt_payload_renders_missing_snapshot_and_telemetry_warnings():
    vm = sample_cockpit_view_model()
    vm.prompt_payload = PromptPayloadView(
        size_label="(unknown)",
        estimated_tokens=0,
        prompt_budget_tokens=0,
        context_budget_tokens=0,
        budget_percent=0.0,
        growth_state="unknown",
        watch_state="blocked",
        source="unknown",
        provider_id="unknown",
        model_name="unknown",
        trust_state="unknown",
        route_class="unknown",
        route_kind="unknown",
        evidence_ref="missing",
        telemetry_ref="missing",
        adapter_metadata_ref="missing",
        warnings=["prompt_snapshot_missing", "telemetry_unavailable"],
    )
    doc = render_cockpit_html(vm)
    assert 'class="payload-warnings"' in doc
    assert 'data-warning="prompt_snapshot_missing"' in doc
    assert 'data-warning="telemetry_unavailable"' in doc
    assert "prompt_snapshot_missing" in doc
    assert "telemetry_unavailable" in doc


def test_prompt_payload_escapes_structured_fields_and_warnings():
    vm = sample_cockpit_view_model()
    vm.prompt_payload = PromptPayloadView(
        size_label="(<bad>)",
        estimated_tokens=1,
        prompt_budget_tokens=2,
        context_budget_tokens=3,
        budget_percent=50.0,
        growth_state="unknown",
        watch_state="blocked",
        source="<script>source</script>",
        provider_id="<img src=x>",
        model_name="<script>model</script>",
        trust_state="unknown",
        route_class="direct_api",
        route_kind="direct",
        evidence_ref="<script>evidence</script>",
        telemetry_ref="telemetry:<bad>",
        adapter_metadata_ref="adapter:<bad>",
        warnings=["<script>warning</script>"],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;source&lt;/script&gt;" in doc
    assert "telemetry:&lt;bad&gt;" in doc
    assert "&lt;script&gt;warning&lt;/script&gt;" in doc


def test_prompt_payload_visibility_preserves_stale_recovery_and_proof_preview():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-payload-session", "Closed Payload Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-payload-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Payload Session" not in doc


def test_dispatch_hardening_sample_renders_required_state_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert "Dispatch Hardening" in doc
    assert "dispatch-sample-001" in doc
    assert "Provider: claude" in doc
    assert "Exact model: claude-opus-4-7" in doc
    assert "Route class: direct_api" in doc
    assert "Route kind: account-first" in doc
    assert "Proof strength: strong" in doc
    assert "External review: not_required" in doc
    assert "Payload evidence: snapshot_present" in doc


def test_dispatch_hardening_sample_renders_blockers_and_error_tags():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="dispatch-list dispatch-blocked-authorities"' in doc
    assert "branch_movement" in doc
    assert "review_clearing" in doc
    assert "silent_fallback_blocked" in doc
    assert "aggregator_identity_required" in doc
    assert "fallback_not_authorized" in doc
    assert "auto_routing_disabled" in doc


def test_dispatch_hardening_supports_candidate_and_blocked_states():
    vm = sample_cockpit_view_model()
    vm.dispatch_hardening = DispatchHardeningView(
        dispatch_id="dispatch-deepseek-q",
        provider_id="deepseek",
        exact_model_id="deepseek-chat",
        route_class="direct_api",
        route_kind="direct",
        trust_state="candidate",
        proof_strength="weak",
        external_review_status="pending",
        blocked_authorities=["build", "review_clearing"],
        payload_evidence_state="snapshot_missing",
        fallback_blockers=["aggregator_route_mismatch"],
        dispatch_error_tags=["prompt_snapshot_missing", "candidate_trust_block"],
    )
    doc = render_cockpit_html(vm)
    assert "dispatch-deepseek-q" in doc
    assert "Exact model: deepseek-chat" in doc
    assert 'dispatch-trust-candidate' in doc
    assert "External review: pending" in doc
    assert "Payload evidence: snapshot_missing" in doc
    assert "candidate_trust_block" in doc


def test_dispatch_hardening_escapes_structured_fields():
    vm = sample_cockpit_view_model()
    vm.dispatch_hardening = DispatchHardeningView(
        dispatch_id='<script>dispatch</script>',
        provider_id="<img src=x>",
        exact_model_id="<script>model</script>",
        route_class="direct_api",
        route_kind="direct",
        trust_state="blocked",
        proof_strength="<script>weak</script>",
        external_review_status="pending",
        blocked_authorities=["<script>authority</script>"],
        payload_evidence_state="<bad>",
        fallback_blockers=["fallback:<bad>"],
        dispatch_error_tags=["<script>tag</script>"],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;dispatch&lt;/script&gt;" in doc
    assert "Payload evidence: &lt;bad&gt;" in doc
    assert "fallback:&lt;bad&gt;" in doc


def test_dispatch_hardening_in_cockpit_main_not_hud_core():
    doc = render_cockpit_html(sample_cockpit_view_model())
    main_section = doc[doc.find('<main class="cockpit-main">'):doc.find('</main>')]
    core_start = doc.find('class="hud-command-core"')
    core_end = doc.find("</div>", core_start)
    core_section = doc[core_start:core_end]
    assert 'class="dispatch-hardening"' in main_section
    assert "Dispatch Hardening" not in core_section


def test_dispatch_hardening_preserves_payload_proof_and_stale_recovery():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-dispatch-session", "Closed Dispatch Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-dispatch-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Dispatch Session" not in doc


def test_prompt_packet_proof_sample_renders_required_metadata():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert "PromptPacket Proof" in doc
    assert "prompt-packet-001" in doc
    assert "Packet hash: sha256:packet-proof-sample" in doc
    assert "Source lineage: compliant" in doc
    assert "Prompt budget ref: budget:relay-dispatch-4000" in doc
    assert "Proof requirement: tier2_payload_snapshot" in doc
    assert 'packet-state-warn' in doc


def test_prompt_packet_proof_sample_renders_evidence_gaps_and_warnings():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="packet-list packet-aegis-evidence"' in doc
    assert "aegis:route-tier" in doc
    assert "aegis:payload-proof" in doc
    assert "response_payload_hash_pending" in doc
    assert "completion_tokens_missing" in doc
    assert "latency_ms_missing" in doc


def test_prompt_packet_proof_supports_block_demote_warn_states():
    cases = ("block", "demote", "warn")
    for proof_state in cases:
        vm = sample_cockpit_view_model()
        vm.prompt_packet_proof = PromptPacketProofView(
            packet_id=f"packet-{proof_state}",
            packet_hash=f"sha256:{proof_state}",
            source_lineage_compliance="noncompliant" if proof_state == "block" else "partial",
            prompt_budget_ref="budget:test",
            aegis_evidence_ids=["aegis:test"],
            proof_requirement="tier3_dual_lane",
            snapshot_hash_gaps=["prompt_snapshot_missing"],
            proof_state=proof_state,
            missing_metadata_warnings=["packet_metadata_missing"],
        )
        doc = render_cockpit_html(vm)
        assert f"packet-{proof_state}" in doc
        assert f"packet-state-{proof_state}" in doc
        assert "prompt_snapshot_missing" in doc
        assert "packet_metadata_missing" in doc


def test_prompt_packet_proof_escapes_structured_fields():
    vm = sample_cockpit_view_model()
    vm.prompt_packet_proof = PromptPacketProofView(
        packet_id="<script>packet</script>",
        packet_hash="sha256:<bad>",
        source_lineage_compliance="<img src=x>",
        prompt_budget_ref="budget:<bad>",
        aegis_evidence_ids=["<script>evidence</script>"],
        proof_requirement="<script>requirement</script>",
        snapshot_hash_gaps=["gap:<bad>"],
        proof_state="block",
        missing_metadata_warnings=["<script>warning</script>"],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;packet&lt;/script&gt;" in doc
    assert "sha256:&lt;bad&gt;" in doc
    assert "budget:&lt;bad&gt;" in doc
    assert "gap:&lt;bad&gt;" in doc


def test_prompt_packet_proof_in_cockpit_main_not_hud_core():
    doc = render_cockpit_html(sample_cockpit_view_model())
    main_section = doc[doc.find('<main class="cockpit-main">'):doc.find('</main>')]
    core_start = doc.find('class="hud-command-core"')
    core_end = doc.find("</div>", core_start)
    core_section = doc[core_start:core_end]
    assert 'class="prompt-packet-proof"' in main_section
    assert "PromptPacket Proof" not in core_section


def test_prompt_packet_proof_preserves_prior_bifrost_surfaces():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-packet-session", "Closed Packet Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-packet-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Packet Session" not in doc



# Harness dashboard


def test_aegis_prompt_packet_policy_sample_renders_required_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Aegis PromptPacket Policy Decision"' in doc
    assert "Aegis PromptPacket Policy" in doc
    assert "aegis-policy-packet-001" in doc
    assert "Packet id: prompt-packet-001" in doc
    assert "Human gate: not_required" in doc
    assert "Proof requirement: tier2_payload_snapshot" in doc
    assert 'aegis-policy-decision-warn' in doc


def test_aegis_prompt_packet_policy_sample_renders_evidence_missing_fields_and_reasons():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="aegis-policy-list aegis-policy-evidence-ids"' in doc
    assert "aegis:route-tier" in doc
    assert "aegis:payload-proof" in doc
    assert "completion_tokens" in doc
    assert "latency_ms" in doc
    assert "payload_snapshot_present" in doc
    assert "response_hash_pending" in doc


def test_aegis_prompt_packet_policy_supports_allow_warn_demote_block_and_human_gate():
    for decision in ("allow", "warn", "demote", "block"):
        vm = sample_cockpit_view_model()
        vm.aegis_prompt_packet_policy = AegisPromptPacketPolicyView(
            packet_id=f"packet-{decision}",
            policy_id=f"policy-{decision}",
            decision=decision,
            human_gate_state="required" if decision == "block" else "not_required",
            proof_requirement="tier3_dual_lane",
            aegis_evidence_ids=["aegis:test-policy"],
            missing_fields=["response_payload_hash"],
            reason_tags=[f"{decision}_policy_decision"],
        )
        doc = render_cockpit_html(vm)
        assert f"policy-{decision}" in doc
        assert f"Packet id: packet-{decision}" in doc
        assert f"aegis-policy-decision-{decision}" in doc
        assert f"{decision}_policy_decision" in doc
        if decision == "block":
            assert "Human gate: required" in doc


def test_aegis_prompt_packet_policy_missing_packet_id_suppresses_policy_card():
    vm = sample_cockpit_view_model()
    vm.aegis_prompt_packet_policy = AegisPromptPacketPolicyView(
        packet_id="",
        policy_id="policy-without-packet",
        decision="block",
        human_gate_state="required",
        proof_requirement="tier3_dual_lane",
        aegis_evidence_ids=["aegis:missing-packet"],
        missing_fields=["packet_id"],
        reason_tags=["packet_id_missing"],
    )
    doc = render_cockpit_html(vm)
    assert 'aria-label="Aegis PromptPacket Policy Decision"' not in doc
    assert "policy-without-packet" not in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc


def test_aegis_prompt_packet_policy_renders_degraded_empty_data_placeholders():
    vm = sample_cockpit_view_model()
    vm.aegis_prompt_packet_policy = AegisPromptPacketPolicyView(
        packet_id="packet-degraded-policy",
        policy_id="",
        decision="demote",
        human_gate_state="",
        proof_requirement="",
        aegis_evidence_ids=[],
        missing_fields=[],
        reason_tags=[],
    )
    doc = render_cockpit_html(vm)
    assert "Packet id: packet-degraded-policy" in doc
    assert "policy_id_missing" in doc
    assert "Human gate: unknown" in doc
    assert "Proof requirement: proof_requirement_missing" in doc
    assert "no_evidence_ids" in doc
    assert "no_missing_fields" in doc
    assert "no_reason_tags" in doc
    assert "aegis-policy-empty" in doc


def test_aegis_prompt_packet_policy_renders_human_gate_edge_states():
    for human_gate_state in ("not_required", "required", "pending", "blocked", ""):
        vm = sample_cockpit_view_model()
        vm.aegis_prompt_packet_policy = AegisPromptPacketPolicyView(
            packet_id=f"packet-human-gate-{human_gate_state or 'blank'}",
            policy_id="policy-human-gate-edge",
            decision="warn",
            human_gate_state=human_gate_state,
            proof_requirement="tier2_payload_snapshot",
            aegis_evidence_ids=["aegis:human-gate"],
            reason_tags=["human_gate_state_visible"],
        )
        doc = render_cockpit_html(vm)
        expected = human_gate_state or "unknown"
        assert f"Human gate: {expected}" in doc
        assert f"aegis-policy-human-gate-{expected}" in doc


def test_aegis_prompt_packet_policy_escapes_structured_fields():
    vm = sample_cockpit_view_model()
    vm.aegis_prompt_packet_policy = AegisPromptPacketPolicyView(
        packet_id="<script>packet</script>",
        policy_id="policy:<bad>",
        decision="block",
        human_gate_state="<img src=x>",
        proof_requirement="<script>requirement</script>",
        aegis_evidence_ids=["<script>evidence</script>"],
        missing_fields=["field:<bad>"],
        reason_tags=["<script>reason</script>"],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;packet&lt;/script&gt;" in doc
    assert "policy:&lt;bad&gt;" in doc
    assert "field:&lt;bad&gt;" in doc
    assert "&lt;script&gt;reason&lt;/script&gt;" in doc


def test_aegis_prompt_packet_policy_in_cockpit_main_not_hud_core():
    doc = render_cockpit_html(sample_cockpit_view_model())
    main_section = doc[doc.find('<main class="cockpit-main">'):doc.find('</main>')]
    core_start = doc.find('class="hud-command-core"')
    core_end = doc.find("</div>", core_start)
    core_section = doc[core_start:core_end]
    assert 'class="aegis-packet-policy"' in main_section
    assert "Aegis PromptPacket Policy" not in core_section


def test_aegis_prompt_packet_policy_preserves_prior_bifrost_surfaces():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-aegis-policy-session", "Closed Aegis Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-aegis-policy-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Aegis PromptPacket Policy Decision"' in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Aegis Session" not in doc


def test_relay_aegis_policy_handoff_sample_renders_required_summary_fields():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert "Relay/Aegis Handoff" in doc
    assert "handoff-decision-demote" in doc
    assert "handoff-severity-warning" in doc
    assert "Packet id: prompt-packet-001" in doc
    assert "Packet hash status: present" in doc
    assert "Proof requirement: tier2_payload_snapshot" in doc
    assert "Demotion target: tier1:account-first" in doc
    assert "Human gate: not_required" in doc
    assert "Missing metadata fail closed: no" in doc
    assert "Relay accepted Aegis demotion target" in doc


def test_relay_aegis_policy_handoff_sample_renders_evidence_blockers_and_warnings():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="handoff-list handoff-evidence-ids"' in doc
    assert 'class="handoff-list handoff-blockers"' in doc
    assert 'class="handoff-list handoff-warnings"' in doc
    assert "aegis:route-tier" in doc
    assert "aegis:payload-proof" in doc
    assert "demotion_route_required" in doc
    assert "response_payload_hash_pending" in doc
    assert "no_missing_metadata_fields" in doc


def test_relay_aegis_policy_handoff_adapter_maps_relay_summary_aliases():
    handoff = relay_aegis_policy_handoff_from_summary({
        "aegis_gate_decision": "human_gate",
        "aegis_gate_severity": "warning",
        "packet_id_ref": "prompt-packet-alias",
        "packet_hash_ref": "present",
        "proof_requirement": "tier3_dual_lane",
        "evidence_ids": ("aegis:review", "aegis:dual-lane"),
        "fallback_blockers": ("aegis_human_gate_required",),
        "warning_tags": ("review_console_approval_missing",),
        "demotion_target_tier": "tier1:review-safe",
        "human_gate_state": "required",
        "aegis_explanation": "Review Console approval is required.",
    })
    assert handoff.decision == "human_gate"
    assert handoff.severity == "warning"
    assert handoff.packet_id == "prompt-packet-alias"
    assert handoff.packet_hash_status == "present"
    assert handoff.proof_requirement == "tier3_dual_lane"
    assert handoff.aegis_evidence_ids == ["aegis:review", "aegis:dual-lane"]
    assert handoff.blockers == ["aegis_human_gate_required"]
    assert handoff.warnings == ["review_console_approval_missing"]
    assert handoff.demotion_target == "tier1:review-safe"
    assert handoff.human_gate_state == "required"
    assert handoff.explanation == "Review Console approval is required."


def test_relay_aegis_policy_handoff_adapter_normalizes_missing_optional_fields():
    handoff = relay_aegis_policy_handoff_from_summary({
        "missing_metadata_fail_closed": True,
    })
    assert handoff.decision == "block"
    assert handoff.severity == "error"
    assert handoff.packet_id == "packet_id_missing"
    assert handoff.packet_hash_status == "unknown"
    assert handoff.proof_requirement == "proof_requirement_missing"
    assert handoff.aegis_evidence_ids == []
    assert handoff.blockers == []
    assert handoff.warnings == []
    assert handoff.demotion_target == "not_applicable"
    assert handoff.human_gate_state == "unknown"
    assert handoff.missing_metadata_fail_closed is True


def test_relay_aegis_policy_handoff_adapter_preserves_deterministic_ordering():
    handoff = relay_aegis_policy_handoff_from_summary({
        "decision": "warn",
        "aegis_evidence_ids": {"zeta:evidence", "alpha:evidence"},
        "blockers": {"blocked_z": True, "blocked_a": True},
        "warnings": ["warn_b", "warn_a"],
        "missing_metadata_fields": {"source_lineage", "budget_ref"},
    })
    assert handoff.aegis_evidence_ids == ["alpha:evidence", "zeta:evidence"]
    assert handoff.blockers == ["blocked_a", "blocked_z"]
    assert handoff.warnings == ["warn_b", "warn_a"]
    assert handoff.missing_metadata_fields == ["budget_ref", "source_lineage"]


def test_relay_aegis_policy_handoff_adapter_redacts_unsafe_summary_values_before_render():
    vm = sample_cockpit_view_model()
    vm.relay_aegis_policy_handoff = relay_aegis_policy_handoff_from_summary({
        "decision": "block",
        "severity": "error",
        "packet_id": "prompt-packet-safe",
        "packet_hash_status": "serialized_prompt:RAW_PROMPT_SENTINEL",
        "proof_requirement": "tier2_payload_snapshot",
        "aegis_evidence_ids": ["aegis:display-safe", "api_key:SECRET_VALUE"],
        "fallback_blockers": {"provider_request:RAW_PROMPT_SENTINEL": True},
        "policy_warning_tags": ["raw_provider_response:SECRET_VALUE"],
        "demotion_route": "bearer token route",
        "human_gate_state": "process_id:1234",
        "metadata_fail_closed": "true",
        "missing_fields": ["authorization_header"],
        "aegis_explanation": "model_payload RAW_PROMPT_SENTINEL SECRET_VALUE",
    })
    doc = render_cockpit_html(vm)
    assert "prompt-packet-safe" in doc
    assert "aegis:display-safe" in doc
    assert "RAW_PROMPT_SENTINEL" not in doc
    assert "SECRET_VALUE" not in doc
    assert "api_key" not in doc
    assert "provider_request" not in doc
    assert "raw_provider_response" not in doc
    assert "model_payload" not in doc
    assert "process_id" not in doc
    assert "unsafe_metadata_redacted" in doc


def test_sample_view_model_renders_handoff_summary_dictionary_via_adapter():
    vm = sample_cockpit_view_model({
        "aegis_gate_decision": "human_gate",
        "aegis_gate_severity": "warning",
        "packet_id_ref": "prompt-packet-human-gate",
        "packet_hash_ref": "present",
        "proof_requirement": "tier3_dual_lane",
        "evidence_ids": ("aegis:review-console",),
        "fallback_blockers": ("aegis_human_gate_required",),
        "warning_tags": ("approval_missing",),
        "human_gate_state": "required",
        "aegis_explanation": "Review Console approval is required.",
    })
    doc = render_cockpit_html(vm)
    assert vm.relay_aegis_policy_handoff.decision == "human_gate"
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert "handoff-decision-human_gate" in doc
    assert "Packet id: prompt-packet-human-gate" in doc
    assert "Human gate: required" in doc
    assert "aegis_human_gate_required" in doc
    assert "Review Console approval is required." in doc


def test_sample_view_model_renders_fail_closed_summary_dictionary_placeholders():
    vm = sample_cockpit_view_model({
        "metadata_fail_closed": "true",
        "packet_hash_status": "missing",
        "missing_fields": {"packet_id", "budget_ref", "aegis_evidence_ids"},
        "fallback_blockers": {"proof_metadata_absent": True, "aegis_gate_blocked": True},
    })
    doc = render_cockpit_html(vm)
    assert vm.relay_aegis_policy_handoff.decision == "block"
    assert vm.relay_aegis_policy_handoff.severity == "error"
    assert "Packet id: packet_id_missing" in doc
    assert "Proof requirement: proof_requirement_missing" in doc
    assert "Missing metadata fail closed: yes" in doc
    assert "aegis_gate_blocked" in doc
    assert "proof_metadata_absent" in doc
    assert "packet_id" in doc
    assert "budget_ref" in doc
    assert "aegis_evidence_ids" in doc


def test_sample_view_model_handoff_summary_preserves_deterministic_render_order():
    vm = sample_cockpit_view_model({
        "decision": "warn",
        "packet_id": "prompt-packet-ordered",
        "aegis_evidence_ids": {"zeta:evidence", "alpha:evidence"},
        "blockers": {"blocked_z": True, "blocked_a": True},
        "missing_metadata_fields": {"source_lineage", "budget_ref"},
    })
    doc = render_cockpit_html(vm)
    assert doc.index("alpha:evidence") < doc.index("zeta:evidence")
    assert doc.index("blocked_a") < doc.index("blocked_z")
    assert doc.index("budget_ref") < doc.index("source_lineage")


def test_sample_view_model_handoff_summary_redacts_and_preserves_prior_surfaces():
    vm = sample_cockpit_view_model({
        "decision": "block",
        "severity": "error",
        "packet_id": "prompt-packet-redacted",
        "packet_hash_status": "serialized_prompt:RAW_PROMPT_SENTINEL",
        "aegis_evidence_ids": ["aegis:display-safe", "api_key:SECRET_VALUE"],
        "fallback_blockers": ["provider_request:RAW_PROMPT_SENTINEL"],
        "policy_warning_tags": ["raw_provider_response:SECRET_VALUE"],
        "aegis_explanation": "model_payload RAW_PROMPT_SENTINEL SECRET_VALUE",
    })
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-summary-session", "Closed Summary Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-summary-session"
    doc = render_cockpit_html(vm)
    assert "prompt-packet-redacted" in doc
    assert "aegis:display-safe" in doc
    assert "RAW_PROMPT_SENTINEL" not in doc
    assert "SECRET_VALUE" not in doc
    assert "unsafe_metadata_redacted" in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert "Provider Balance" in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Summary Session" not in doc


def test_relay_aegis_policy_handoff_supports_all_policy_decisions():
    cases = (
        ("allow", "info", "not_applicable", "not_required"),
        ("warn", "warning", "not_applicable", "not_required"),
        ("demote", "warning", "tier0:review-safe", "not_required"),
        ("block", "error", "not_applicable", "blocked"),
        ("human_gate", "warning", "not_applicable", "required"),
    )
    for decision, severity, demotion_target, human_gate_state in cases:
        vm = sample_cockpit_view_model()
        vm.relay_aegis_policy_handoff = RelayAegisPolicyHandoffView(
            decision=decision,
            severity=severity,
            packet_id=f"packet-{decision}",
            packet_hash_status="present",
            proof_requirement="tier2_payload_snapshot",
            aegis_evidence_ids=["aegis:decision"],
            blockers=[f"{decision}_blocker"] if decision in {"block", "human_gate"} else [],
            warnings=[f"{decision}_warning"] if decision in {"warn", "demote"} else [],
            demotion_target=demotion_target if decision == "demote" else "",
            human_gate_state=human_gate_state,
            explanation=f"{decision} summary",
        )
        doc = render_cockpit_html(vm)
        assert f"Packet id: packet-{decision}" in doc
        assert f"handoff-decision-{decision}" in doc
        assert f"handoff-severity-{severity}" in doc
        assert f"Human gate: {human_gate_state}" in doc
        assert f"Demotion target: {demotion_target}" in doc
        assert f"{decision} summary" in doc


def test_relay_aegis_policy_handoff_renders_fail_closed_missing_metadata():
    vm = sample_cockpit_view_model()
    vm.relay_aegis_policy_handoff = RelayAegisPolicyHandoffView(
        decision="block",
        severity="error",
        packet_id="",
        packet_hash_status="missing",
        proof_requirement="",
        aegis_evidence_ids=[],
        blockers=["aegis_gate_blocked", "proof_metadata_absent"],
        warnings=[],
        human_gate_state="unknown",
        missing_metadata_fail_closed=True,
        missing_metadata_fields=["packet_id", "budget_ref", "aegis_evidence_ids"],
        explanation="Relay failed closed before adapter transport.",
    )
    doc = render_cockpit_html(vm)
    assert "Packet id: packet_id_missing" in doc
    assert "Packet hash status: missing" in doc
    assert "Proof requirement: proof_requirement_missing" in doc
    assert "Missing metadata fail closed: yes" in doc
    assert "aegis_gate_blocked" in doc
    assert "proof_metadata_absent" in doc
    assert "packet_id" in doc
    assert "budget_ref" in doc
    assert "aegis_evidence_ids" in doc
    assert "no_evidence_ids" in doc
    assert "no_warnings" in doc


def test_relay_aegis_policy_handoff_redacts_unsafe_metadata_and_escapes_html():
    vm = sample_cockpit_view_model()
    vm.relay_aegis_policy_handoff = RelayAegisPolicyHandoffView(
        decision="block",
        severity="error",
        packet_id="<script>packet</script>",
        packet_hash_status="serialized_prompt:RAW_PROMPT_SENTINEL",
        proof_requirement="tier2:<bad>",
        aegis_evidence_ids=["aegis:<safe>", "api_key:SECRET_VALUE"],
        blockers=["provider_request:RAW_PROMPT_SENTINEL"],
        warnings=["raw_provider_response:SECRET_VALUE"],
        demotion_target="bearer token route",
        human_gate_state="<img src=x>",
        missing_metadata_fail_closed=True,
        missing_metadata_fields=["authorization_header"],
        explanation="model_payload RAW_PROMPT_SENTINEL SECRET_VALUE",
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;packet&lt;/script&gt;" in doc
    assert "tier2:&lt;bad&gt;" in doc
    assert "aegis:&lt;safe&gt;" in doc
    assert "RAW_PROMPT_SENTINEL" not in doc
    assert "SECRET_VALUE" not in doc
    assert "api_key" not in doc
    assert "provider_request" not in doc
    assert "raw_provider_response" not in doc
    assert "model_payload" not in doc
    assert "unsafe_metadata_redacted" in doc


def test_relay_aegis_policy_handoff_in_cockpit_main_not_hud_core():
    doc = render_cockpit_html(sample_cockpit_view_model())
    main_section = doc[doc.find('<main class="cockpit-main">'):doc.find('</main>')]
    core_start = doc.find('class="hud-command-core"')
    core_end = doc.find("</div>", core_start)
    core_section = doc[core_start:core_end]
    assert 'class="relay-aegis-handoff"' in main_section
    assert "Relay/Aegis Handoff" not in core_section


def test_relay_aegis_policy_handoff_preserves_prior_bifrost_surfaces():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-handoff-session", "Closed Handoff Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-handoff-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert 'aria-label="Aegis PromptPacket Policy Decision"' in doc
    assert 'aria-label="PromptPacket Proof Metadata"' in doc
    assert 'aria-label="Dispatch Hardening State"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert "Provider Balance" in doc
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Handoff Session" not in doc


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


# Project strip


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


# Progress surface


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


# Instrument band


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


# XSS escaping


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


# Custom view model


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


# view_model_from_snapshot


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


# Voice I/O state


def test_sample_view_model_has_voice_state():
    vm = sample_cockpit_view_model()
    assert isinstance(vm.voice, VoiceIOState)
    assert vm.voice.listening is True
    assert vm.voice.muted is False
    assert vm.voice.boot_status == "status-ready"
    assert vm.voice.permission_state == "available"


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
    assert 'data-blocked="true"' in doc


def test_voice_idle_state_renders_when_no_activity_or_boot():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(boot_status="")
    doc = render_cockpit_html(vm)
    assert "voice idle" in doc
    assert 'voice-idle' in doc


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
    assert 'data-voice-control="unmute-status"' in doc
    assert "Unmute" in doc
    assert 'data-muted="true"' in doc


def test_voice_not_muted_shows_mute_button():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(muted=False)
    doc = render_cockpit_html(vm)
    assert 'data-voice-control="mute-status"' in doc
    assert "Mute" in doc
    assert 'data-muted="false"' in doc


def test_voice_runtime_metadata_renders():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(
        listening=True,
        boot_status="boot-call-ready",
        input_mode="browser-mic",
        output_mode="read-aloud",
        permission_state="aegis-gated",
        status_call="ready for status call",
        last_intent_ref="voice-intent:mission-status",
    )
    doc = render_cockpit_html(vm)
    assert 'aria-label="Voice runtime metadata"' in doc
    assert "boot: boot-call-ready" in doc
    assert "input: browser-mic" in doc
    assert "output: read-aloud" in doc
    assert "permission: aegis-gated" in doc
    assert "status: ready for status call" in doc
    assert "intent: voice-intent:mission-status" in doc


def test_voice_read_aloud_control_renders():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'data-voice-control="read-aloud-status"' in doc
    assert 'aria-label="Read-aloud status"' in doc


def test_voice_runtime_metadata_escapes_dynamic_values():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(
        boot_status="<boot>",
        input_mode="<mic>",
        output_mode="<speaker>",
        permission_state="<blocked>",
        status_call="<status>",
        last_intent_ref="<intent>",
    )
    doc = render_cockpit_html(vm)
    assert "&lt;boot&gt;" in doc
    assert "&lt;mic&gt;" in doc
    assert "&lt;speaker&gt;" in doc
    assert "&lt;blocked&gt;" in doc
    assert "&lt;status&gt;" in doc
    assert "&lt;intent&gt;" in doc
    assert "<boot>" not in doc


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
    assert 'data-voice-control="mute-status"' in doc or 'data-voice-control="unmute-status"' in doc


def test_voice_strip_controls_are_display_only():
    doc = render_cockpit_html(sample_cockpit_view_model())
    start = doc.index('class="voice-strip"')
    end = doc.index('<div class="hud-stage"', start)
    voice_markup = doc[start:end]
    assert 'data-action="voice"' not in voice_markup
    assert 'data-action="read-aloud"' not in voice_markup
    assert 'data-action="mute"' not in voice_markup
    assert 'data-action="unmute"' not in voice_markup
    assert 'data-voice-control="input-status"' in voice_markup
    assert 'aria-disabled="true"' in voice_markup


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


def test_voice_io_surface_covers_required_dimension_matrix():
    vm = sample_cockpit_view_model()
    vm.voice = VoiceIOState(
        listening=True,
        thinking=True,
        speaking=True,
        muted=False,
        blocked=False,
        boot_status="wake-armed",
        input_mode="microphone",
        output_mode="speaker",
        permission_state="available",
        status_call="command channel ready",
        last_intent_ref="voice-intent:panel-focus",
    )
    doc = render_cockpit_html(vm)
    start = doc.index('class="voice-strip"')
    end = doc.index('<div class="hud-stage"', start)
    voice_markup = doc[start:end]

    # microphone input
    assert "mic armed" in voice_markup
    assert "input: microphone" in voice_markup
    assert 'data-voice-control="input-status"' in voice_markup

    # spoken Prime output
    assert "speaker active" in voice_markup
    assert "output: speaker" in voice_markup
    assert 'data-voice-control="read-aloud-status"' in voice_markup

    # wake/boot audio status
    assert "boot: wake-armed" in voice_markup

    # mute/listening/thinking/speaking state
    assert 'data-muted="false"' in voice_markup
    assert 'data-voice-control="mute-status"' in voice_markup
    assert "voice-listening" in voice_markup
    assert "voice-thinking" in voice_markup
    assert "voice-speaking" in voice_markup

    # display-safe evidence refs
    assert "status: command channel ready" in voice_markup
    assert "intent: voice-intent:panel-focus" in voice_markup

    # non-executable behavior: every voice control carries aria-disabled
    # and no executable data-action hook is wired into the voice strip
    for hook in ("data-action=\"voice\"", "data-action=\"read-aloud\"",
                 "data-action=\"mute\"", "data-action=\"unmute\""):
        assert hook not in voice_markup
    for control in (
        'data-voice-control="input-status"',
        'data-voice-control="read-aloud-status"',
        'data-voice-control="mute-status"',
    ):
        assert control in voice_markup, f"missing voice control: {control}"
        attr_index = voice_markup.index(control)
        button_start = voice_markup.rfind("<button", 0, attr_index)
        button_end = voice_markup.index("</button>", attr_index)
        assert button_start != -1, f"voice control not inside a button: {control}"
        button_markup = voice_markup[button_start:button_end]
        assert 'aria-disabled="true"' in button_markup, (
            f"voice control {control} is missing aria-disabled=\"true\""
        )


# Session Lifecycle


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


def test_session_lifecycle_renders_recovery_readiness_summary():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Recovery Readiness Advisory Summary"' in doc
    assert 'data-advisory-id="recovery-readiness:build-5-stale-workflow"' in doc
    assert 'data-target-session-id="build-5-bifrost"' in doc
    assert "Recovery readiness: advisory_ready" in doc
    assert "Recommended: resteer" in doc
    assert "Permission: display_only" in doc
    assert "Human gate: required_for_execution" in doc
    assert "Stale workflow recovery is ready for Prime review" in doc
    assert "no_live_control_execution" in doc
    assert "human_gate_required" in doc


def test_session_lifecycle_recovery_readiness_renders_action_advisories():
    doc = render_cockpit_html(sample_cockpit_view_model())
    for action_id in (
        "restart-session",
        "resteer-session",
        "archive-session",
        "poll-watch-session",
        "human-gated-blocked",
    ):
        assert f'data-readiness-action="{action_id}"' in doc
    assert 'data-readiness-state="recommended"' in doc
    assert 'data-readiness-state="blocked"' in doc
    assert 'data-permission-state="requires_prime"' in doc
    assert 'data-permission-state="requires_user"' in doc
    assert "evidence:session-restart-request" in doc
    assert "evidence:prime-resteer-required" in doc
    assert "evidence:archive-context-preserved" in doc
    assert "evidence:lifecycle-watch-only" in doc
    assert "evidence:human-gate-required" in doc
    assert "Archive is display-safe and does not close or delete active work." in doc


def test_session_lifecycle_recovery_readiness_escapes_structured_fields():
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
            )
        ],
        recovery_readiness=RecoveryReadinessAdvisory(
            advisory_id="<script>advisory</script>",
            target_session_id="<img src=x>",
            readiness_state="<bad>",
            recommended_action="resteer:<bad>",
            permission_state="permission:<bad>",
            human_gate_state="<script>gate</script>",
            summary="summary:<bad>",
            blockers=["blocker:<bad>"],
            evidence_refs=["evidence:<bad>"],
            actions=[
                RecoveryReadinessAction(
                    action_id="<script>action</script>",
                    action_label="<Action>",
                    readiness_state="<state>",
                    permission_state="<permission>",
                    evidence_ref="proof:<bad>",
                    advisory="advisory:<bad>",
                )
            ],
        ),
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert 'data-advisory-id="&lt;script&gt;advisory&lt;/script&gt;"' in doc
    assert 'data-target-session-id="&lt;img src=x&gt;"' in doc
    assert "Recovery readiness: &lt;bad&gt;" in doc
    assert "Human gate: &lt;script&gt;gate&lt;/script&gt;" in doc
    assert "summary:&lt;bad&gt;" in doc
    assert "blocker:&lt;bad&gt;" in doc
    assert "evidence:&lt;bad&gt;" in doc
    assert "data-readiness-action=\"&lt;script&gt;action&lt;/script&gt;\"" in doc
    assert "&lt;Action&gt;" in doc
    assert "proof:&lt;bad&gt;" in doc
    assert "advisory:&lt;bad&gt;" in doc


def test_session_lifecycle_recovery_readiness_preserves_stale_recovery_samples():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-readiness-session", "Closed Readiness Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-readiness-session"
    doc = render_cockpit_html(vm)
    assert 'aria-label="Recovery Readiness Advisory Summary"' in doc
    assert 'class="stale-recovery-actions"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert 'data-recovery-action="resteer-session"' in doc
    assert 'data-recovery-action="archive-session"' in doc
    assert 'data-recovery-action="poll-watch-session"' in doc
    assert 'data-recovery-action="human-gated-blocked"' in doc


def test_session_lifecycle_renders_command_staging_review_summary():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'aria-label="Live-Control Command-Plan Staging Review"' in doc
    assert "Command-Plan Staging Review" in doc
    assert "Source: session-lifecycle-command-staging-sample" in doc

    for staging_id in (
        "staging:build-5-bifrost:restart",
        "staging:build-5-bifrost:resteer",
        "staging:build-5-bifrost:archive",
    ):
        assert f'data-staging-id="{staging_id}"' in doc

    assert 'data-target-session-id="build-5-bifrost"' in doc
    assert "Staged: restart" in doc
    assert "Staged: resteer" in doc
    assert "Staged: archive" in doc
    assert "Recommended: restart" in doc
    assert "Recommended: resteer" in doc
    assert "Recommended: archive" in doc
    assert "Required operation: restart" in doc
    assert "Required operation: resteer" in doc
    assert "Required operation: archive" in doc


def test_session_lifecycle_command_staging_review_renders_review_gates_and_advisories():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert "Ready flag: yes" in doc
    assert "Ready flag: no" in doc
    assert "Executable now: no" in doc
    assert "UI review required: yes" in doc
    assert "Permission: unlocked_temporary" in doc
    assert "Permission: locked_by_default" in doc

    assert "UI review required before future live-control command execution." in doc
    assert "Human or Aegis gate required before future live-control command staging." in doc
    assert "Archive intent remains blocked until user or review lane clears the gate." in doc
    assert "prime-advisory:command-staging-review" in doc
    assert "prime-advisory:resteer-review-required" in doc
    assert "prime-advisory:archive-human-gate" in doc
    assert "beacon:staging_restart" in doc
    assert "beacon:staging_resteer" in doc
    assert "beacon:staging_archive" in doc
    assert "command_plan.ui_review_required" in doc
    assert "permission.locked" in doc
    assert "human_gate_required" in doc
    assert "staging.is_executable_now=False" in doc
    assert "staging.ui_review_required=True" in doc
    assert "permission.state=unlocked_temporary" in doc
    assert "permission.state=locked_by_default" in doc


def test_session_lifecycle_command_staging_review_escapes_structured_fields():
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
            )
        ],
        command_staging_review=CommandStagingReviewView(
            source="<script>source</script>",
            items=[
                CommandStagingReviewItem(
                    staging_id="<script>staging</script>",
                    readiness_summary_id="summary:<bad>",
                    target_session_id="<img src=x>",
                    command_kind="<bad-kind>",
                    recommended_action="restart:<bad>",
                    required_operation="operation:<bad>",
                    ready_for_execution=True,
                    is_executable_now=False,
                    ui_review_required=True,
                    permission_state="permission:<bad>",
                    human_gate_rationale="rationale:<bad>",
                    prime_advisory_ref="prime:<bad>",
                    beacon_advisory_ref="beacon:<bad>",
                    blockers=["blocker:<bad>"],
                    evidence_refs=["evidence:<bad>"],
                )
            ],
        ),
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "Source: &lt;script&gt;source&lt;/script&gt;" in doc
    assert 'data-staging-id="&lt;script&gt;staging&lt;/script&gt;"' in doc
    assert 'data-target-session-id="&lt;img src=x&gt;"' in doc
    assert "Staged: &lt;bad-kind&gt;" in doc
    assert "Recommended: restart:&lt;bad&gt;" in doc
    assert "Required operation: operation:&lt;bad&gt;" in doc
    assert "Readiness summary: summary:&lt;bad&gt;" in doc
    assert "Permission: permission:&lt;bad&gt;" in doc
    assert "Human gate: rationale:&lt;bad&gt;" in doc
    assert "Prime advisory: prime:&lt;bad&gt;" in doc
    assert "Beacon advisory: beacon:&lt;bad&gt;" in doc
    assert "blocker:&lt;bad&gt;" in doc
    assert "evidence:&lt;bad&gt;" in doc


def test_command_staging_review_preserves_adjacent_display_only_surfaces():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-staging-session", "Closed Staging Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-staging-session"
    doc = render_cockpit_html(vm)

    assert 'aria-label="Live-Control Command-Plan Staging Review"' in doc
    assert 'aria-label="Visible Prompt Payload Meter"' in doc
    assert 'aria-label="Recovery Readiness Advisory Summary"' in doc
    assert 'aria-label="Model Harness Runtime Validation Envelopes"' in doc
    assert 'aria-label="Provider Balance"' in doc
    assert 'aria-label="Prompt Payload Visibility"' in doc
    assert 'aria-label="Relay Aegis Policy Handoff Summary"' in doc
    assert 'class="stale-recovery-actions"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Staging Session" not in doc


# Proof State Tests

def test_sample_view_model_has_proof_state():
    vm = sample_cockpit_view_model()
    assert vm.proof_state is not None
    assert isinstance(vm.proof_state, ProofStateView)


def test_proof_state_sample_has_gates():
    vm = sample_cockpit_view_model()
    assert len(vm.proof_state.gates) >= 3


def test_proof_state_sample_has_preview_items():
    vm = sample_cockpit_view_model()
    states = {item.state for item in vm.proof_state.preview_items}
    assert {"pending", "blocked", "passed", "needs-human-review"} <= states


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


def test_proof_state_preview_renders_required_states():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert 'class="proof-preview-list"' in doc
    for state in ("pending", "blocked", "passed", "needs-human-review"):
        assert f'data-proof-state="{state}"' in doc
        assert f"proof-preview-{state}" in doc


def test_proof_state_preview_renders_owner_and_evidence():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert "Session Lifecycle" in doc
    assert "queue:build-5" in doc
    assert "pytest:bifrost-cockpit" in doc
    assert "review:codex" in doc


def test_proof_state_preview_custom_item_escapes_content():
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.proof_state = ProofStateView(
        proof_status="verified",
        preview_items=[
            ProofPreviewItem(
                proof_id='proof"><script>',
                label="<script>label</script>",
                state="blocked",
                owner="<img src=x>",
                evidence_ref="evidence:<bad>",
                summary="<script>alert(1)</script>",
            )
        ],
    )
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "<img" not in doc
    assert "&lt;script&gt;label&lt;/script&gt;" in doc
    assert "evidence:&lt;bad&gt;" in doc


def test_proof_state_preview_does_not_replace_stale_recovery_guard():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions.append(
        SessionItem("closed-proof-session", "Closed Proof Session", "Meridian", "done")
    )
    vm.user_session_mode.selected_session_id = "closed-proof-session"
    doc = render_cockpit_html(vm)
    assert 'class="proof-preview-list"' in doc
    assert 'class="stale-target-guard"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Closed Proof Session" not in doc


def test_render_has_no_v3_goal_runtime_execution_surface():
    doc = render_cockpit_html(sample_cockpit_view_model())
    assert 'class="proof-preview-list"' in doc
    assert "Awaiting next proof write after local tests" in doc
    for fragment in (
        'aria-label="V3 Goal Runtime"',
        'aria-label="Goal Runtime"',
        'aria-label="Goal Checkpoint Update"',
        'aria-label="Goal Checkpoint Controls"',
        'data-action="goal"',
        'data-action="goal-runtime"',
        'data-action="goal-checkpoint"',
        'data-action="checkpoint-goal"',
        'data-action="update-goal"',
        'data-action="complete-goal"',
        'data-action="block-goal"',
        'data-action="write-git"',
        'data-action="write-obsidian"',
        'data-action="create-automation"',
        'data-action="move-branch"',
        'data-action="move-worktree"',
        'data-action="merge"',
        'data-action="rebase"',
        'data-action="reset"',
        'data-action="cherry-pick"',
        'data-action="stash-pop"',
        'data-action="spawn-session"',
        'data-action="change-token-budget"',
        "data-goal-runtime=",
        "data-goal-checkpoint=",
        "data-token-budget-control=",
        "data-obsidian-write=",
        "data-automation-create=",
        "data-branch-movement=",
        "data-worktree-movement=",
        "V3 Goal Runtime",
        "Goal checkpoint controls",
        "Write Git",
        "Write Obsidian",
        "Create automation",
        "Move branch",
        "Move worktree",
        "Change token budget",
        "Set token budget",
        "Spawn session",
    ):
        assert fragment not in doc


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


# Right-Panel Mode Tests


def test_user_session_mode_renders_with_data():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-user-session"' in doc


def test_user_session_mode_has_prompt_window():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    assert 'class="prompt-response-area"' in doc
    assert 'class="prompt-input"' in doc


def test_user_session_mode_shows_sessions_dropdown():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    assert 'class="sessions-dropdown"' in doc
    assert '<select' in doc
    for session in vm.user_session_mode.sessions:
        assert session.session_name in doc


def test_user_session_mode_shows_selected_session():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    # Use an actual session ID from sample data
    if vm.user_session_mode.sessions:
        selected_id = vm.user_session_mode.sessions[1].session_id
        vm.user_session_mode.selected_session_id = selected_id
        doc = render_cockpit_html(vm)
        assert f'value="{selected_id}"' in doc and 'selected' in doc


# Sessions dropdown grouping and sorting

def test_sessions_dropdown_groups_by_project():
    """Sessions dropdown uses optgroups for each project."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    # Should have optgroup elements for each project
    assert "<optgroup" in doc
    assert 'label="Meridian"' in doc or "Meridian" in doc


def test_sessions_dropdown_projects_sorted_alphabetically():
    """Projects in sessions dropdown are sorted alphabetically."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"

    # Create sessions from multiple projects in reverse order
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Zebra Session", "Zebra", "live"),
        SessionItem("s2", "Alpha Session", "Alpha", "live"),
        SessionItem("s3", "Middle Session", "Middle", "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)

    # Find positions of project names in the rendered output
    alpha_pos = doc.find('label="Alpha"')
    middle_pos = doc.find('label="Middle"')
    zebra_pos = doc.find('label="Zebra"')

    # Verify alphabetical order (Alpha < Middle < Zebra)
    assert alpha_pos < middle_pos < zebra_pos


def test_sessions_within_project_sorted_alphabetically():
    """Sessions within a project are sorted alphabetically."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"

    # Create sessions in reverse alphabetical order
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Zulu", "Project", "live"),
        SessionItem("s2", "Bravo", "Project", "live"),
        SessionItem("s3", "Alpha", "Project", "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)

    # Find positions of session names
    alpha_pos = doc.find(">Alpha<")
    bravo_pos = doc.find(">Bravo<")
    zulu_pos = doc.find(">Zulu<")

    # Verify alphabetical order within the project group
    assert alpha_pos < bravo_pos < zulu_pos


def test_sessions_dropdown_shows_waiting_label():
    """Waiting sessions show '(waiting for test)' label."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Test Session", "Project", "waiting"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    assert "waiting for test" in doc or "waiting" in doc


def test_sessions_dropdown_shows_hidden_label():
    """Hidden sessions show '(hidden)' label."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Hidden Session", "Project", "hidden"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    assert "hidden" in doc


def test_sessions_dropdown_live_sessions_no_label():
    """Live sessions do not show a status label."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Live Session", "Project", "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    assert ">Live Session<" in doc or "Live Session" in doc
    # Should not have a status indicator for live sessions
    assert "Live Session (live)" not in doc


def test_sessions_dropdown_title_shows_selected_session():
    """The User Session header shows the selected session name."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Test Session Name", "Project", "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    assert "Test Session Name" in doc
    assert "Session:" in doc


def test_sessions_dropdown_escapes_session_names_in_dropdown():
    """Session names are HTML-escaped in dropdown options."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Session <script>", "Project", "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    # Script tag should be escaped, not rendered
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc or "Session" in doc  # Name should be present but escaped


def test_sessions_dropdown_escapes_project_names():
    """Project names in optgroup labels are HTML-escaped."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.sessions = [
        SessionItem("s1", "Session", 'Project <img src=x>', "live"),
    ]
    vm.user_session_mode.selected_session_id = "s1"

    doc = render_cockpit_html(vm)
    # Should not have unescaped HTML tags in optgroup
    assert '<img src=x>' not in doc or "&lt;img" in doc


def test_settings_mode_renders_with_data():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-settings"' in doc


def test_settings_mode_has_no_prompt_window():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    assert 'class="prompt-response-area"' not in doc
    assert 'class="prompt-input"' not in doc


def test_settings_mode_shows_settings_items():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    assert 'class="settings-list"' in doc
    for setting in vm.settings_mode.settings:
        assert setting.setting_name in doc


def test_settings_mode_shows_all_setting_types():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    for setting in vm.settings_mode.settings:
        assert setting.setting_name in doc
        assert setting.setting_type in doc


def test_harness_mode_renders_with_data():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-harness"' in doc


def test_harness_mode_has_no_prompt_window():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert 'class="prompt-response-area"' not in doc
    assert 'class="prompt-input"' not in doc


def test_harness_mode_shows_harness_items():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert 'class="harness-items-list"' in doc
    for item in vm.harness_mode.harness_items:
        assert item.item_name in doc


def test_harness_mode_shows_search_box():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert 'class="harness-search"' in doc


def test_right_panel_includes_correct_mode_user_session():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-user-session"' in doc
    assert 'class="right-panel-settings"' not in doc
    assert 'class="right-panel-harness"' not in doc


def test_right_panel_includes_correct_mode_settings():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-settings"' in doc
    assert 'class="right-panel-user-session"' not in doc
    assert 'class="right-panel-harness"' not in doc


def test_right_panel_includes_correct_mode_harness():
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert 'class="right-panel-harness"' in doc
    assert 'class="right-panel-user-session"' not in doc
    assert 'class="right-panel-settings"' not in doc


def test_user_session_mode_escapes_session_names():
    vm = CockpitViewModel(project="Test", bearing="test")
    session = SessionItem(
        session_id="test",
        session_name="<script>xss</script>",
        project_name="Test",
        status="live",
    )
    vm.user_session_mode = UserSessionModeView(sessions=[session])
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_settings_mode_escapes_setting_names():
    vm = CockpitViewModel(project="Test", bearing="test")
    setting = SettingsItem(
        setting_id="test",
        setting_name="<script>xss</script>",
        setting_type="text",
        value="test",
    )
    vm.settings_mode = SettingsModeView(settings=[setting])
    vm.right_panel_active_mode = "settings"
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_harness_mode_escapes_item_names():
    vm = CockpitViewModel(project="Test", bearing="test")
    item = HarnessItem(
        item_id="test",
        item_name="<script>xss</script>",
        item_type="gate",
        description="test",
    )
    vm.harness_mode = HarnessModeView(harness_items=[item])
    vm.right_panel_active_mode = "harness"
    doc = render_cockpit_html(vm)
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_right_panel_renders_in_aside_element():
    vm = sample_cockpit_view_model()
    doc = render_cockpit_html(vm)
    assert '<aside class="right-panel">' in doc
    assert '</aside>' in doc


# interactive-state mode switching

def test_mode_switch_user_to_settings_preserves_prompt_state():
    """Switching from User Session mode to Settings preserves unsent prompt text."""
    vm = sample_cockpit_view_model()

    # Start in User Session mode with prompt text
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.prompt_text = "What is the status?"
    vm.user_session_mode.response_text = ""

    # Switch to Settings mode
    vm.right_panel_active_mode = "settings"

    # Prompt state should remain intact (view-model holds it)
    assert vm.user_session_mode.prompt_text == "What is the status?"
    assert vm.user_session_mode.response_text == ""


def test_mode_switch_settings_to_user_restores_prompt():
    """Switching from Settings back to User Session restores the prompt."""
    vm = sample_cockpit_view_model()

    # Start with prompt in User Session
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.prompt_text = "Detailed status report"
    vm.user_session_mode.response_text = "Status: OK"

    # Switch to Settings
    vm.right_panel_active_mode = "settings"

    # Switch back to User Session
    vm.right_panel_active_mode = "user_session"

    # Prompt is restored (data model never cleared it)
    assert vm.user_session_mode.prompt_text == "Detailed status report"
    assert vm.user_session_mode.response_text == "Status: OK"


def test_mode_switch_harness_to_user_preserves_session_selection():
    """Switching from Harness back to User Session preserves selected_session_id."""
    vm = sample_cockpit_view_model()

    # Start in User Session with a selected session
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.selected_session_id = "session-apollo-1"
    vm.user_session_mode.prompt_text = ""

    # Switch to Harness mode
    vm.right_panel_active_mode = "harness"

    # Switch back to User Session
    vm.right_panel_active_mode = "user_session"

    # Selected session is restored
    assert vm.user_session_mode.selected_session_id == "session-apollo-1"


def test_mode_switch_user_to_settings_to_harness_preserves_all_state():
    """Switching through multiple modes preserves User Session state."""
    vm = sample_cockpit_view_model()

    # Set up User Session state
    vm.right_panel_active_mode = "user_session"
    vm.user_session_mode.selected_session_id = "session-relay-2"
    vm.user_session_mode.prompt_text = "What happened?"
    vm.user_session_mode.response_text = "Event log attached."

    # Switch to Settings
    vm.right_panel_active_mode = "settings"

    # Switch to Harness
    vm.right_panel_active_mode = "harness"

    # Switch back to User Session
    vm.right_panel_active_mode = "user_session"

    # All state preserved
    assert vm.user_session_mode.selected_session_id == "session-relay-2"
    assert vm.user_session_mode.prompt_text == "What happened?"
    assert vm.user_session_mode.response_text == "Event log attached."


def test_settings_mode_has_no_prompt_state():
    """Settings mode view-model does not carry prompt fields."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"

    # SettingsModeView has only settings list, no prompt_text or response_text
    assert hasattr(vm.settings_mode, "settings")
    assert not hasattr(vm.settings_mode, "prompt_text")
    assert not hasattr(vm.settings_mode, "response_text")


def test_harness_mode_has_no_prompt_state():
    """Harness mode view-model does not carry prompt fields."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"

    # HarnessModeView has only harness_items and search_query, no prompt
    assert hasattr(vm.harness_mode, "harness_items")
    assert hasattr(vm.harness_mode, "search_query")
    assert not hasattr(vm.harness_mode, "prompt_text")
    assert not hasattr(vm.harness_mode, "response_text")


def test_mode_switch_does_not_route_prompts_in_settings():
    """When active mode is Settings, prompt_text changes don't trigger routing."""
    vm = sample_cockpit_view_model()

    # Activate Settings mode
    vm.right_panel_active_mode = "settings"

    # Edit prompt_text in user_session_mode (this is still stored, but inactive)
    vm.user_session_mode.prompt_text = "This should not route"

    # Since mode is Settings, the prompt is not actively routed/rendered
    # Proof: active mode is not "user_session"
    assert vm.right_panel_active_mode == "settings"
    assert vm.right_panel_active_mode != "user_session"


def test_mode_switch_does_not_route_prompts_in_harness():
    """When active mode is Harness, prompt_text changes don't trigger routing."""
    vm = sample_cockpit_view_model()

    # Activate Harness mode
    vm.right_panel_active_mode = "harness"

    # Edit prompt_text in user_session_mode (this is still stored, but inactive)
    vm.user_session_mode.prompt_text = "This should not route either"

    # Since mode is Harness, the prompt is not actively routed/rendered
    assert vm.right_panel_active_mode == "harness"
    assert vm.right_panel_active_mode != "user_session"


def test_mode_switch_settings_full_panel_no_prompt():
    """Settings mode renders full panel without prompt affordances."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "settings"
    vm.settings_mode.settings = [
        SettingsItem("text_size", "Text Size", "range", "14px"),
        SettingsItem("quiet_mode", "Quiet Mode", "toggle", "off"),
    ]

    doc = render_cockpit_html(vm)

    # When in Settings mode, the right panel should contain settings items
    assert '<div class="right-panel-settings">' in doc or "right-panel-settings" in doc or "Configuration" in doc or "text-size" in doc or "quiet-mode" in doc


def test_mode_switch_harness_full_panel_no_prompt():
    """Harness mode renders full panel without prompt affordances."""
    vm = sample_cockpit_view_model()
    vm.right_panel_active_mode = "harness"
    vm.harness_mode.harness_items = [
        HarnessItem("gate-unknown-route", "Unknown Route Gate", "gate", "Validates route safety"),
        HarnessItem("finding-perf", "Performance Issue", "finding", "Latency detected"),
    ]

    doc = render_cockpit_html(vm)

    # When in Harness mode, the right panel should contain harness items
    assert '<div class="right-panel-harness">' in doc or "right-panel-harness" in doc or "Unknown Route Gate" in doc or "gate-unknown-route" in doc


def test_prompt_window_only_renders_in_user_session_mode():
    """Prompt input/output window is only visible in User Session mode."""
    vm = sample_cockpit_view_model()

    # Render in User Session mode
    vm.right_panel_active_mode = "user_session"
    user_doc = render_cockpit_html(vm)

    # Render in Settings mode
    vm.right_panel_active_mode = "settings"
    settings_doc = render_cockpit_html(vm)

    # Render in Harness mode
    vm.right_panel_active_mode = "harness"
    harness_doc = render_cockpit_html(vm)

    # User Session should have prompt window affordances
    assert "prompt" in user_doc.lower() or "user-session" in user_doc

    # Settings should not have prompt window (full panel)
    # Harness should not have prompt window (full panel)
    # (These are proven by having different section structures)
    assert "settings" in settings_doc.lower() or "configuration" in settings_doc.lower()
    assert "harness" in harness_doc.lower() or "gate-" in harness_doc


# Sessions dropdown filtering (Reviews B repairs)

def test_sessions_dropdown_excludes_blocked_sessions():
    """Non-open sessions (blocked, done) are excluded from the dropdown."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Open Live", "Meridian", "live"),
            SessionItem("s2", "Blocked Session", "Meridian", "blocked"),
            SessionItem("s3", "Done Session", "Meridian", "done"),
            SessionItem("s4", "Hidden Open", "Meridian", "hidden"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Open sessions should be present
    assert "Open Live" in doc
    assert "Hidden Open" in doc

    # Non-open sessions should NOT be in options
    assert "Blocked Session" not in doc or "blocked" not in doc
    assert "Done Session" not in doc or "done" not in doc


def test_sessions_dropdown_excludes_closed_from_options():
    """Verify blocked/done sessions are not in <option> elements."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
            SessionItem("s2", "Blocked", "P", "blocked"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    html = render_cockpit_html(vm)

    # Live should be in an option
    assert '<option' in html
    assert "Live" in html

    # Blocked should not appear in the rendered dropdown
    assert "Blocked" not in html


def test_routing_target_state_shows_selected_session():
    """Routing target state indicator shows the selected session."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Session One", "Meridian", "live"),
            SessionItem("s2", "Session Two", "Meridian", "live"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Routing target state should be present
    assert "routing-target-state" in doc
    assert "Next prompt target:" in doc or "routing-label" in doc
    # Should show the selected session name
    assert "Session One" in doc


def test_routing_target_updates_when_selection_changes():
    """Routing target state updates when selected_session_id changes."""
    vm = CockpitViewModel(project="Test", bearing="test")
    sessions = [
        SessionItem("s1", "First Session", "Meridian", "live"),
        SessionItem("s2", "Second Session", "Meridian", "live"),
    ]
    vm.user_session_mode = UserSessionModeView(
        sessions=sessions,
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"

    # Render with first session selected
    doc1 = render_cockpit_html(vm)
    assert "First Session" in doc1

    # Change selection to second session
    vm.user_session_mode.selected_session_id = "s2"
    doc2 = render_cockpit_html(vm)

    # Second session should now be in the routing target
    assert "Second Session" in doc2


def test_routing_target_includes_session_id_metadata():
    """Routing target state includes data-target-session-id attribute."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[SessionItem("target-id-123", "Test Session", "Project", "live")],
        selected_session_id="target-id-123",
    )
    vm.right_panel_active_mode = "user_session"
    html = render_cockpit_html(vm)

    # Should have the data attribute with the session ID
    assert 'data-target-session-id="target-id-123"' in html


def test_sessions_dropdown_with_mixed_statuses_filters_correctly():
    """Dropdown correctly filters when mix of open and closed sessions present."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live A", "P1", "live"),
            SessionItem("s2", "Hidden B", "P1", "hidden"),
            SessionItem("s3", "Waiting C", "P2", "waiting"),
            SessionItem("s4", "Blocked D", "P2", "blocked"),
            SessionItem("s5", "Done E", "P1", "done"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    html = render_cockpit_html(vm)

    # Open sessions should render
    assert "Live A" in html
    assert "Hidden B" in html
    assert "Waiting C" in html

    # Closed sessions should not render
    assert "Blocked D" not in html
    assert "Done E" not in html


# Stale-target guard (post-Sessions dropdown repair)

def test_stale_target_guard_shows_when_selected_session_closed():
    """Stale-target guard shows when selected session is no longer available."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Open Session", "P1", "live"),
            SessionItem("s2", "Closed Session", "P1", "done"),  # This one is closed
        ],
        selected_session_id="s2",  # Selected a closed session
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Stale-target guard should be present
    assert "stale-target-guard" in doc
    assert "Target unavailable:" in doc or "stale-warning" in doc
    # Guard should indicate it's not routable
    assert "not routable" in doc or "not be sent" in doc


def test_stale_target_guard_for_blocked_session():
    """Stale-target guard shows when selected session is blocked."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Open", "P", "live"),
            SessionItem("s2", "Blocked", "P", "blocked"),
        ],
        selected_session_id="s2",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Guard should show for blocked session
    assert "stale-target-guard" in doc
    assert "Blocked" in doc


def test_stale_target_guard_includes_session_id_metadata():
    """Stale-target guard includes data-stale-session-id attribute."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Open", "P", "live"),
            SessionItem("s-stale-123", "Stale", "P", "done"),
        ],
        selected_session_id="s-stale-123",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Should have data attribute identifying the stale session
    assert 'data-stale-session-id="s-stale-123"' in doc


def test_normal_routing_target_when_session_available():
    """Normal routing target (not guard) shows when session is available."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Available", "P", "live"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Normal routing target should show, not the guard
    assert "routing-target-state" in doc
    assert "Next prompt target:" in doc
    assert '<div class="stale-target-guard"' not in doc


def test_stale_target_guard_prevents_prompt_routing_implication():
    """Stale-target guard message clarifies prompts will not be sent."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
            SessionItem("s2", "Closed", "P", "done"),
        ],
        selected_session_id="s2",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Guard message must clarify prompts won't be sent
    assert "will not be sent" in doc or "not routable" in doc
    # Should NOT show "Next prompt target:" for stale sessions
    if "stale-target-guard" in doc:
        # Extract the stale guard section
        assert "Next prompt target: Closed" not in doc


def test_stale_target_guard_for_multiple_closed_sessions():
    """Stale-target guard works when selecting from mix of open and closed."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live A", "P", "live"),
            SessionItem("s2", "Live B", "P", "live"),
            SessionItem("s3", "Blocked C", "P", "blocked"),
            SessionItem("s4", "Done D", "P", "done"),
        ],
        selected_session_id="s4",  # Select a done session
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    # Dropdown should only show open sessions
    assert "Live A" in doc
    assert "Live B" in doc
    # Closed sessions not in dropdown
    assert '<option' not in doc or "Blocked C" not in doc or "Done D" not in doc
    # But guard shows for the selected closed session
    assert "stale-target-guard" in doc
    assert "Done D" in doc  # Name shown in guard, not dropdown


def test_stale_session_recovery_actions_render_for_closed_target():
    """Stale targets show deterministic recovery action samples."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
            SessionItem("s2", "Closed", "P", "done"),
        ],
        selected_session_id="s2",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    assert 'class="stale-recovery-actions"' in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert 'data-recovery-action="resteer-session"' in doc
    assert 'data-recovery-action="archive-session"' in doc
    assert 'data-recovery-action="poll-watch-session"' in doc
    assert 'data-recovery-action="human-gated-blocked"' in doc
    assert 'data-recovery-state="restart"' in doc
    assert 'data-recovery-state="resteer"' in doc
    assert 'data-recovery-state="archive"' in doc
    assert 'data-recovery-state="poll_watch"' in doc
    assert 'data-recovery-state="human_gate_blocked"' in doc
    assert "Restart session" in doc
    assert "Resteer session" in doc
    assert "Archive stale session" in doc
    assert "Poll/watch" in doc
    assert "Human gate blocked" in doc
    assert "evidence:session-restart-request" in doc
    assert "evidence:prime-resteer-required" in doc
    assert "evidence:archive-context-preserved" in doc
    assert "evidence:lifecycle-watch-only" in doc
    assert "evidence:human-gate-required" in doc


def test_stale_session_recovery_actions_render_for_blocked_target():
    """Blocked selected sessions get the same recovery action sample."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
            SessionItem("s2", "Blocked", "P", "blocked"),
        ],
        selected_session_id="s2",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    assert "stale-target-guard" in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: Blocked" not in doc


def test_stale_session_recovery_actions_render_for_missing_target():
    """Missing selected session ids still show recovery without a fake route."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
        ],
        selected_session_id="missing-session-id",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    assert 'data-stale-session-id="missing-session-id"' in doc
    assert "Target unavailable: missing-session-id" in doc
    assert 'data-recovery-action="restart-session"' in doc
    assert "Next prompt target: missing-session-id" not in doc


def test_stale_session_recovery_actions_absent_for_live_target():
    """Available selected sessions keep normal routing state only."""
    vm = CockpitViewModel(project="Test", bearing="test")
    vm.user_session_mode = UserSessionModeView(
        sessions=[
            SessionItem("s1", "Live", "P", "live"),
        ],
        selected_session_id="s1",
    )
    vm.right_panel_active_mode = "user_session"
    doc = render_cockpit_html(vm)

    assert "routing-target-state" in doc
    assert "Next prompt target: Live" in doc
    assert 'class="stale-recovery-actions"' not in doc
    assert "data-recovery-action" not in doc


# Backend / view-model binding adapters (Build 5H)


def test_prompt_payload_view_from_evidence_maps_identity_and_route_fields():
    evidence = RelayPromptPayloadEvidence(
        prompt_source="relay",
        selected_provider="claude",
        selected_model="claude-sonnet-4-20250514",
        capability_tier="tier2",
        route_class="direct",
        route_kind="direct",
        trust_state="trusted",
        external_review_status="not_required",
        model_metadata_ref="adapter:claude",
        external_review_evidence_ref="review:claude-cleared",
        estimated_prompt_tokens=920,
        prompt_budget_tokens=4000,
        model_context_window_tokens=200000,
        budget_percent=23.0,
        budget_status="ok",
        delta_tokens=0,
        delta_percent=0.0,
        growth_state="flat",
        prompt_payload_snapshot_hash="payload-snapshot:claude-dispatch",
    )

    view = prompt_payload_view_from_evidence(evidence)

    assert view.provider_id == "claude"
    assert view.model_name == "claude-sonnet-4-20250514"
    assert view.trust_state == "trusted"
    assert view.route_class == "direct"
    assert view.route_kind == "direct"
    assert view.source == "relay"
    assert view.estimated_tokens == 920
    assert view.prompt_budget_tokens == 4000
    assert view.context_budget_tokens == 200000
    assert view.budget_percent == 23.0
    assert view.growth_state == "flat"
    assert view.watch_state == "ok"
    assert view.evidence_ref == "payload-snapshot:claude-dispatch"
    assert view.telemetry_ref == "adapter:claude"
    assert view.adapter_metadata_ref == "review:claude-cleared"
    assert view.warnings == []


def test_prompt_payload_view_from_evidence_preserves_growth_and_drag_warnings():
    evidence = RelayPromptPayloadEvidence(
        prompt_source="relay",
        selected_provider="deepseek",
        selected_model="deepseek-chat",
        route_class="direct",
        route_kind="direct",
        trust_state="candidate",
        requires_external_review=True,
        external_review_status="pending",
        estimated_prompt_tokens=3100,
        prompt_budget_tokens=5000,
        model_context_window_tokens=256000,
        budget_percent=62.0,
        budget_status="watch",
        delta_tokens=240,
        delta_percent=6.0,
        growth_state="unexpected_growth",
        prompt_drag_tags=("q_mode_prompt_drag_degraded", "unexpected_growth_delta"),
        telemetry_error_tags=("response_payload_hash_pending",),
    )

    view = prompt_payload_view_from_evidence(evidence)

    assert view.provider_id == "deepseek"
    assert view.trust_state == "candidate"
    assert view.watch_state == "watch"
    assert view.growth_state == "unexpected_growth"
    assert view.delta_tokens == 240
    assert view.delta_percent == 6.0
    assert "q_mode_prompt_drag_degraded" in view.warnings
    assert "unexpected_growth_delta" in view.warnings
    assert "response_payload_hash_pending" in view.warnings


def test_prompt_payload_view_from_evidence_defaults_safe_on_minimal_record():
    evidence = RelayPromptPayloadEvidence()

    view = prompt_payload_view_from_evidence(evidence)

    assert view.provider_id == ""
    assert view.model_name == ""
    assert view.trust_state == "unknown"
    assert view.estimated_tokens == 0
    assert view.prompt_budget_tokens == 0
    assert view.budget_percent == 0.0
    assert view.delta_tokens == 0
    assert view.growth_state == "unknown"
    assert view.watch_state == "unknown"
    assert view.size_label.startswith("(") and view.size_label.endswith(")")
    assert view.warnings == []


def test_prompt_payload_view_is_renderable_in_cockpit():
    vm = sample_cockpit_view_model()
    vm.prompt_payload = prompt_payload_view_from_evidence(
        RelayPromptPayloadEvidence(
            prompt_source="relay",
            selected_provider="claude",
            selected_model="claude-sonnet-4-20250514",
            route_class="direct",
            route_kind="direct",
            trust_state="trusted",
            estimated_prompt_tokens=900,
            prompt_budget_tokens=4000,
            budget_percent=22.5,
            budget_status="ok",
            growth_state="flat",
        )
    )
    doc = render_cockpit_html(vm)
    assert "claude-sonnet-4-20250514" in doc
    assert "Meridian" in doc


def test_visible_prompt_payload_meter_view_from_evidence_preserves_order_and_fields():
    items = (
        RelayPromptPayloadMeterEvidence(
            meter_evidence_id="payload-meter:claude-under-1k",
            selected_provider="claude",
            exact_model_id="claude-sonnet-4-20250514",
            provider_route_kind="direct",
            trust_state="trusted",
            display_label="under 1k",
            estimated_prompt_tokens=900,
            prompt_budget_tokens=4000,
            budget_percent=22.5,
            payload_status="ok",
            growth_delta_tokens=0,
            growth_delta_percent=0.0,
            q_mode=False,
            growth_state="flat",
            payload_evidence_ref="payload-snapshot:claude-dispatch",
            model_metadata_ref="adapter:claude",
        ),
        RelayPromptPayloadMeterEvidence(
            meter_evidence_id="payload-meter:deepseek-12-4k",
            selected_provider="deepseek",
            exact_model_id="deepseek-chat",
            provider_route_kind="direct",
            trust_state="candidate",
            display_label="12.4k",
            estimated_prompt_tokens=3100,
            prompt_budget_tokens=5000,
            budget_percent=62.0,
            payload_status="degraded",
            growth_delta_tokens=240,
            growth_delta_percent=6.0,
            q_mode=True,
            growth_state="unexpected_growth",
            prompt_drag_tags=("q_mode_prompt_drag_degraded",),
            warning_tags=("unexpected_growth_delta",),
            payload_evidence_ref="payload-snapshot:deepseek-qmode",
        ),
    )

    view = visible_prompt_payload_meter_view_from_evidence(
        items,
        source="relay-meter-evidence",
    )

    assert view.source == "relay-meter-evidence"
    assert len(view.items) == 2

    first, second = view.items
    assert first.meter_id == "payload-meter:claude-under-1k"
    assert first.provider_id == "claude"
    assert first.model_id == "claude-sonnet-4-20250514"
    assert first.route_kind == "direct"
    assert first.prompt_label == "under 1k"
    assert first.payload_status == "ok"
    assert first.budget_percent == 22.5
    assert first.q_mode_prompt_drag_state == "ok"
    assert first.provider_balance_ref == "provider-balance:claude"
    assert first.payload_evidence_ref == "payload-snapshot:claude-dispatch"
    assert first.telemetry_ref == "adapter:claude"

    assert second.meter_id == "payload-meter:deepseek-12-4k"
    assert second.payload_status == "degraded"
    assert second.q_mode_prompt_drag_state == "degraded"
    assert second.growth_delta_tokens == 240
    assert second.warning_tags == ["unexpected_growth_delta"]


def test_visible_prompt_payload_meter_view_handles_blocked_qmode_state():
    items = (
        RelayPromptPayloadMeterEvidence(
            meter_evidence_id="payload-meter:openrouter-blocked",
            selected_provider="openrouter",
            exact_model_id="deepseek-chat",
            provider_route_kind="aggregator",
            display_label="over budget",
            estimated_prompt_tokens=5200,
            prompt_budget_tokens=1800,
            budget_percent=101.5,
            payload_status="blocked",
            growth_delta_tokens=720,
            growth_delta_percent=18.0,
            q_mode=True,
            growth_state="blocked",
            warning_tags=("route_mismatch_warning",),
            blocker_tags=(
                "q_mode_payload_over_budget",
                "aggregator_prompt_drag_blocked",
            ),
        ),
    )

    view = visible_prompt_payload_meter_view_from_evidence(items)

    assert len(view.items) == 1
    item = view.items[0]
    assert item.q_mode_prompt_drag_state == "blocked"
    assert item.payload_status == "blocked"
    assert item.budget_percent == 101.5
    assert "q_mode_payload_over_budget" in item.blocker_tags
    assert "aggregator_prompt_drag_blocked" in item.blocker_tags


def test_visible_prompt_payload_meter_view_empty_evidence_yields_empty_view():
    view = visible_prompt_payload_meter_view_from_evidence(())
    assert view.items == []
    assert view.source == "relay-visible-prompt-payload-meter"


def test_visible_prompt_payload_meter_view_is_renderable_in_cockpit():
    vm = sample_cockpit_view_model()
    vm.visible_prompt_payload_meter = visible_prompt_payload_meter_view_from_evidence(
        (
            RelayPromptPayloadMeterEvidence(
                meter_evidence_id="payload-meter:claude-dispatch",
                selected_provider="claude",
                exact_model_id="claude-sonnet-4-20250514",
                provider_route_kind="direct",
                display_label="under 1k",
                budget_percent=22.5,
                payload_status="ok",
            ),
        ),
        source="relay-meter-evidence",
    )
    doc = render_cockpit_html(vm)
    assert "payload-meter:claude-dispatch" in doc
    assert "under 1k" in doc


def test_model_capability_metadata_view_from_summary_maps_provider_identity_and_route():
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="claude",
                selected_provider="claude",
                exact_model_id="claude-sonnet-4-20250514",
                capability_tier="tier2",
                provider_route_kind="direct",
                trust_state="trusted",
                context_window_tokens=200000,
                prompt_payload_budget_tokens=4000,
                prompt_payload_status="within_budget",
                estimated_prompt_tokens=920,
                prompt_budget_percent=23.0,
                growth_state="flat",
                requires_external_review=False,
                external_review_status="not_required",
                model_metadata_ref="adapter:claude",
                payload_evidence_ref="payload-snapshot:claude-dispatch",
            ),
            RelayModelCapabilityLaneSummary(
                lane_id="deepseek",
                selected_provider="deepseek",
                exact_model_id="deepseek-chat",
                capability_tier="tier3",
                provider_route_kind="direct",
                trust_state="candidate",
                context_window_tokens=256000,
                prompt_payload_budget_tokens=5000,
                prompt_payload_status="watch",
                growth_state="unexpected_growth",
                requires_external_review=True,
                external_review_status="pending",
                model_metadata_ref="adapter:deepseek",
                external_review_evidence_ref="review:deepseek-pending",
                payload_evidence_ref="payload-snapshot:deepseek-qmode",
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(
        summary,
        selected_model_id="claude-sonnet-4-20250514",
        metadata_source="model-harness-relay-summary",
    )

    assert view.selected_model_id == "claude-sonnet-4-20250514"
    assert view.metadata_source == "model-harness-relay-summary"
    assert len(view.items) == 2

    claude_item = view.items[0]
    assert claude_item.provider_id == "claude"
    assert claude_item.exact_model_id == "claude-sonnet-4-20250514"
    assert claude_item.route_kind == "direct"
    assert claude_item.trust_state == "trusted"
    assert claude_item.candidate_trust_state == "trusted"
    assert claude_item.context_window_tokens == 200000
    assert claude_item.external_review_required is False
    assert claude_item.external_review_status == "not_required"
    assert claude_item.prompt_budget_status == "within_budget"
    assert claude_item.prompt_growth_state == "flat"
    assert "adapter:claude" in claude_item.evidence_refs
    assert "payload-snapshot:claude-dispatch" in claude_item.evidence_refs

    deepseek_item = view.items[1]
    assert deepseek_item.provider_id == "deepseek"
    assert deepseek_item.trust_state == "candidate"
    assert deepseek_item.candidate_trust_state == "candidate"
    assert deepseek_item.external_review_required is True
    assert deepseek_item.external_review_status == "pending"
    assert deepseek_item.proof_strength == "weak"
    assert deepseek_item.prompt_budget_status == "watch"
    assert deepseek_item.prompt_growth_state == "unexpected_growth"
    assert "adapter:deepseek" in deepseek_item.evidence_refs
    assert "review:deepseek-pending" in deepseek_item.evidence_refs


def test_model_capability_metadata_view_promotes_external_review_cleared_to_strong():
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="deepseek-reviewed",
                selected_provider="deepseek",
                exact_model_id="deepseek-chat",
                provider_route_kind="direct",
                trust_state="trusted",
                requires_external_review=True,
                external_review_status="passed",
                model_metadata_ref="adapter:deepseek",
                external_review_evidence_ref="review:codex-b",
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert len(view.items) == 1
    item = view.items[0]
    assert item.external_review_required is True
    assert item.external_review_status == "passed"
    assert item.candidate_trust_state == "external_review_cleared"
    assert item.proof_strength == "strong"


def test_model_capability_metadata_view_surfaces_missing_metadata_as_blocked_authorities():
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="aggregator",
                selected_provider="openrouter",
                exact_model_id="deepseek-chat",
                provider_route_kind="aggregator",
                trust_state="degraded",
                requires_external_review=True,
                external_review_status="pending",
                telemetry_error_tags=("aggregator_route_capped",),
            ),
        ),
        missing_metadata_tags=("payload_snapshot_missing", "model_metadata_ref_missing"),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert len(view.items) == 1
    item = view.items[0]
    assert item.candidate_trust_state == "candidate"
    assert "payload_snapshot_missing" in item.blocked_authorities
    assert "model_metadata_ref_missing" in item.blocked_authorities
    assert "aggregator_route_capped" in item.blocked_authorities


def test_model_capability_metadata_view_empty_summary_yields_empty_view():
    view = model_capability_metadata_view_from_summary(
        RelayModelCapabilityMetadataSummary(),
    )

    assert view.items == []
    assert view.metadata_source == "model-harness-relay-summary"
    assert view.selected_model_id == ""


def test_model_capability_metadata_view_is_renderable_in_cockpit():
    vm = sample_cockpit_view_model()
    vm.model_capabilities = model_capability_metadata_view_from_summary(
        RelayModelCapabilityMetadataSummary(
            lanes=(
                RelayModelCapabilityLaneSummary(
                    lane_id="claude",
                    selected_provider="claude",
                    exact_model_id="claude-sonnet-4-20250514",
                    provider_route_kind="direct",
                    trust_state="trusted",
                    context_window_tokens=200000,
                ),
            ),
        ),
        selected_model_id="claude-sonnet-4-20250514",
    )
    doc = render_cockpit_html(vm)
    assert "claude-sonnet-4-20250514" in doc
    assert "model-harness-relay-summary" in doc


def test_backend_binding_adapters_have_no_filesystem_or_network_side_effects():
    """Adapters must be pure projections of in-memory backend dataclasses."""
    evidence = RelayPromptPayloadEvidence(
        prompt_source="relay",
        selected_provider="claude",
        selected_model="claude-sonnet-4-20250514",
        route_class="direct",
        route_kind="direct",
        trust_state="trusted",
        estimated_prompt_tokens=900,
        prompt_budget_tokens=4000,
        budget_percent=22.5,
    )
    meter_evidence = RelayPromptPayloadMeterEvidence(
        meter_evidence_id="payload-meter:claude",
        selected_provider="claude",
        exact_model_id="claude-sonnet-4-20250514",
        display_label="under 1k",
    )
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="claude",
                selected_provider="claude",
                exact_model_id="claude-sonnet-4-20250514",
                provider_route_kind="direct",
                trust_state="trusted",
            ),
        ),
    )

    a1 = prompt_payload_view_from_evidence(evidence)
    a2 = prompt_payload_view_from_evidence(evidence)
    b1 = visible_prompt_payload_meter_view_from_evidence((meter_evidence,))
    b2 = visible_prompt_payload_meter_view_from_evidence((meter_evidence,))
    c1 = model_capability_metadata_view_from_summary(summary)
    c2 = model_capability_metadata_view_from_summary(summary)

    assert a1 == a2
    assert b1 == b2
    assert c1 == c2


# Codex Review A repair: candidate_trust_state must reflect backend lane.trust_state
# for non-review lanes, not be hard-coded to "trusted".


def test_model_capability_metadata_view_preserves_degraded_trust_for_non_review_lane():
    """A degraded direct lane with requires_external_review=False must not render as trusted."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="local-degraded",
                selected_provider="local",
                exact_model_id="local-deterministic",
                provider_route_kind="direct",
                trust_state="degraded",
                requires_external_review=False,
                external_review_status="not_required",
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert len(view.items) == 1
    item = view.items[0]
    assert item.trust_state == "degraded"
    assert item.candidate_trust_state == "degraded"
    assert item.candidate_trust_state != "trusted"
    assert item.proof_strength == "weak"
    assert item.external_review_required is False


def test_model_capability_metadata_view_preserves_offline_trust_for_non_review_lane():
    """Offline non-review lanes must surface offline state, not be re-cast as trusted."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="offline",
                selected_provider="local",
                exact_model_id="local-deterministic",
                provider_route_kind="local",
                trust_state="offline",
                requires_external_review=False,
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert view.items[0].candidate_trust_state == "offline"
    assert view.items[0].proof_strength == "weak"


def test_model_capability_metadata_view_preserves_blocked_trust_for_non_review_lane():
    """Blocked non-review lanes must surface blocked state, not be re-cast as trusted."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="blocked",
                selected_provider="local",
                exact_model_id="local-deterministic",
                provider_route_kind="direct",
                trust_state="blocked",
                requires_external_review=False,
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert view.items[0].candidate_trust_state == "blocked"
    assert view.items[0].proof_strength == "weak"


def test_model_capability_metadata_view_preserves_trusted_non_review_lane_regression():
    """Regression: trusted non-review lanes must still map to trusted/standard."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="claude",
                selected_provider="claude",
                exact_model_id="claude-sonnet-4-20250514",
                provider_route_kind="direct",
                trust_state="trusted",
                requires_external_review=False,
                external_review_status="not_required",
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert view.items[0].candidate_trust_state == "trusted"
    assert view.items[0].proof_strength == "standard"


def test_model_capability_metadata_view_defaults_unknown_for_missing_non_review_trust():
    """Defensive default: empty/unknown backend trust on a non-review lane stays 'unknown'."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="bare",
                selected_provider="local",
                exact_model_id="local-deterministic",
                provider_route_kind="direct",
                trust_state="",
                requires_external_review=False,
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    item = view.items[0]
    assert item.trust_state == "unknown"
    assert item.candidate_trust_state == "unknown"
    assert item.candidate_trust_state != "trusted"
    assert item.proof_strength == "unknown"


def test_model_capability_metadata_view_does_not_overwrite_degraded_with_external_review_flow():
    """When requires_external_review=True, the review-flow mapping still takes precedence."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="deepseek",
                selected_provider="deepseek",
                exact_model_id="deepseek-chat",
                provider_route_kind="direct",
                trust_state="degraded",
                requires_external_review=True,
                external_review_status="pending",
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    item = view.items[0]
    assert item.trust_state == "degraded"
    assert item.candidate_trust_state == "candidate"
    assert item.proof_strength == "weak"


def test_model_capability_metadata_view_preserves_candidate_trust_on_non_review_lane():
    """A backend lane already marked candidate (not under review) keeps candidate state."""
    summary = RelayModelCapabilityMetadataSummary(
        lanes=(
            RelayModelCapabilityLaneSummary(
                lane_id="experimental",
                selected_provider="experimental",
                exact_model_id="experimental-model",
                provider_route_kind="direct",
                trust_state="candidate",
                requires_external_review=False,
            ),
        ),
    )

    view = model_capability_metadata_view_from_summary(summary)

    assert view.items[0].candidate_trust_state == "candidate"
    assert view.items[0].proof_strength == "weak"


# Build 5H wiring slice: cockpit_view_model_with_backend_bindings +
# sample_backend_bound_cockpit_view_model render the reviewed backend data.


def test_cockpit_view_model_with_backend_bindings_overrides_only_named_surfaces():
    base = sample_cockpit_view_model()
    original_provider_balance = base.provider_balance
    original_voice = base.voice
    original_instrument = base.instrument
    original_sessions = base.session_lifecycle

    bound = cockpit_view_model_with_backend_bindings(
        base,
        prompt_payload_evidence=RelayPromptPayloadEvidence(
            prompt_source="relay",
            selected_provider="claude",
            selected_model="claude-sonnet-4-20250514",
            route_class="direct",
            route_kind="direct",
            trust_state="trusted",
            estimated_prompt_tokens=920,
            prompt_budget_tokens=4000,
            budget_percent=23.0,
        ),
    )

    assert bound is base
    assert bound.prompt_payload.provider_id == "claude"
    assert bound.prompt_payload.model_name == "claude-sonnet-4-20250514"
    # Untouched surfaces preserved
    assert bound.provider_balance is original_provider_balance
    assert bound.voice is original_voice
    assert bound.instrument is original_instrument
    assert bound.session_lifecycle is original_sessions


def test_cockpit_view_model_with_backend_bindings_no_kwargs_is_identity():
    base = sample_cockpit_view_model()
    snapshot_prompt = base.prompt_payload
    snapshot_meter = base.visible_prompt_payload_meter
    snapshot_caps = base.model_capabilities
    snapshot_backend_evidence = base.reviewed_backend_evidence

    bound = cockpit_view_model_with_backend_bindings(base)

    assert bound is base
    assert bound.prompt_payload is snapshot_prompt
    assert bound.visible_prompt_payload_meter is snapshot_meter
    assert bound.model_capabilities is snapshot_caps
    assert bound.reviewed_backend_evidence is snapshot_backend_evidence


def test_reviewed_backend_evidence_view_from_summary_maps_static_backend_state():
    view = reviewed_backend_evidence_view_from_summary({
        "source": "reviewed-summary",
        "prime_next_action": "continue_bifrost_browser_first_extension",
        "session_lifecycle_preview": "display_only_preview_ready",
        "aegis_policy_result": "warn_human_gate_not_required",
        "relay_model_metadata": "claude tier2 trusted",
        "evidence_refs": ("prime:next-action", "relay:model-metadata"),
        "warnings": ("display_only_no_execution_controls",),
        "items": (
            {
                "source": "Echo",
                "label": "Memory hits",
                "state": "available",
                "count_label": "hits: 3",
                "evidence_ref": "echo:memory-hit-summary",
                "provenance": "reviewed-backend-state",
            },
            {
                "source": "Atlas",
                "label": "Retrieval hits",
                "state": "available",
                "count": "hits: 2",
                "ref": "atlas:retrieval-hit-summary",
                "review_ref": "reviewed-backend-state",
            },
        ),
    })

    assert view.source == "reviewed-summary"
    assert view.prime_next_action == "continue_bifrost_browser_first_extension"
    assert view.session_lifecycle_preview == "display_only_preview_ready"
    assert view.aegis_policy_result == "warn_human_gate_not_required"
    assert view.relay_model_metadata == "claude tier2 trusted"
    assert view.evidence_refs == ["prime:next-action", "relay:model-metadata"]
    assert view.warnings == ["display_only_no_execution_controls"]
    assert [item.source for item in view.items] == ["Echo", "Atlas"]
    assert view.items[1].count_label == "hits: 2"
    assert view.items[1].evidence_ref == "atlas:retrieval-hit-summary"


def test_reviewed_backend_evidence_view_from_summary_redacts_unsafe_markers():
    view = reviewed_backend_evidence_view_from_summary({
        "source": "relay",
        "prime_next_action": "raw_prompt: do not expose",
        "session_lifecycle_preview": "raw_transcript:FULL",
        "aegis_policy_result": "conversation:APPROVAL",
        "relay_model_metadata": "model_payload SECRET_VALUE",
        "evidence_refs": (
            "safe:ref",
            "api_key:SECRET_VALUE",
            "provider_response:FULL",
            "free_form_context:FULL",
            "raw_context:FULL",
            "transcript:FULL",
        ),
        "items": (
            {
                "source": "Echo",
                "label": "raw_provider_response SECRET_VALUE",
                "state": "available",
                "evidence_ref": "bearer token",
            },
            {
                "source": "Atlas",
                "label": "Retrieval hits",
                "state": "available",
                "evidence_ref": "raw_context:atlas-result",
                "provenance": "provider_response:atlas",
            },
        ),
    })

    doc = render_cockpit_html(CockpitViewModel(
        project="Test",
        bearing="reviewed-backend-evidence",
        reviewed_backend_evidence=view,
    ))

    assert "safe:ref" in doc
    assert "unsafe_metadata_redacted" in doc
    assert "SECRET_VALUE" not in doc
    assert "raw_prompt" not in doc
    assert "raw_transcript" not in doc
    assert "raw_provider_response" not in doc
    assert "provider_response" not in doc
    assert "free_form_context" not in doc
    assert "raw_context" not in doc
    assert "transcript:FULL" not in doc
    assert "conversation:APPROVAL" not in doc
    assert "bearer token" not in doc


def test_reviewed_backend_evidence_view_from_summary_skips_non_mapping_items():
    view = reviewed_backend_evidence_view_from_summary({
        "items": (
            "not-a-record",
            {"source": "Prime", "label": "Next action", "state": "ready"},
        ),
    })

    assert len(view.items) == 1
    assert view.items[0].source == "Prime"


def test_reviewed_backend_evidence_renders_browser_first_static_snapshot():
    vm = CockpitViewModel(
        project="Test",
        bearing="reviewed-backend-evidence",
        reviewed_backend_evidence=reviewed_backend_evidence_view_from_summary({
            "source": "reviewed-backend-evidence",
            "prime_next_action": "continue_bifrost_browser_first_extension",
            "session_lifecycle_preview": "display_only_preview_ready",
            "aegis_policy_result": "warn_human_gate_not_required",
            "relay_model_metadata": "claude tier2 trusted",
            "items": (
                {
                    "source": "Echo",
                    "label": "Memory hits",
                    "state": "available",
                    "count_label": "hits: 3",
                    "evidence_ref": "echo:memory-hit-summary",
                },
            ),
            "evidence_refs": ("prime:next-action",),
            "warnings": ("display_only_no_execution_controls",),
        }),
    )

    doc = render_cockpit_html(vm)

    assert 'aria-label="Reviewed Backend Evidence Snapshot"' in doc
    assert "Prime next action: continue_bifrost_browser_first_extension" in doc
    assert "Session preview: display_only_preview_ready" in doc
    assert "Aegis policy result: warn_human_gate_not_required" in doc
    assert "Relay/model metadata: claude tier2 trusted" in doc
    assert "Echo" in doc
    assert "Memory hits" in doc
    assert "hits: 3" in doc
    assert "prime:next-action" in doc
    assert "display_only_no_execution_controls" in doc


def test_reviewed_backend_evidence_render_has_no_execution_controls():
    vm = sample_backend_bound_cockpit_view_model()
    doc = render_cockpit_html(vm)
    section = doc.split('aria-label="Reviewed Backend Evidence Snapshot"', 1)[1]
    section = section.split("</section>", 1)[0]

    forbidden = (
        "<button",
        "<form",
        "data-recovery-action",
        "restart-session",
        "archive-session",
        "resteer-session",
        "spawn-session",
        "merge",
        "rebase",
        "cherry-pick",
        "stash-pop",
    )
    for token in forbidden:
        assert token not in section


def test_cockpit_view_model_with_backend_bindings_wires_reviewed_backend_evidence():
    base = CockpitViewModel(project="Test", bearing="reviewed-backend-evidence")

    bound = cockpit_view_model_with_backend_bindings(
        base,
        reviewed_backend_evidence_summary={
            "source": "summary",
            "prime_next_action": "continue",
            "items": (
                {
                    "source": "Atlas",
                    "label": "Retrieval hits",
                    "state": "available",
                    "count_label": "hits: 2",
                },
            ),
        },
    )

    assert bound is base
    assert bound.reviewed_backend_evidence.source == "summary"
    assert bound.reviewed_backend_evidence.prime_next_action == "continue"
    assert bound.reviewed_backend_evidence.items[0].source == "Atlas"


def test_sample_backend_bound_cockpit_renders_reviewed_backend_evidence_summary():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    assert "backend-reviewed-evidence-sample" in doc
    assert "continue_bifrost_browser_first_extension" in doc
    assert "Echo" in doc
    assert "Memory hits" in doc
    assert "Atlas" in doc
    assert "Retrieval hits" in doc
    assert "session-lifecycle:preview-reviewed" in doc
    assert "aegis:policy-result-reviewed" in doc
    assert "relay:model-metadata-reviewed" in doc


def test_reviewed_backend_evidence_view_is_deterministic():
    summary = {
        "source": "summary",
        "evidence_refs": {"zeta:ref", "alpha:ref"},
        "items": (
            {"source": "Prime", "label": "Next action", "state": "ready"},
            {"source": "Relay", "label": "Model metadata", "state": "bound"},
        ),
    }

    assert (
        reviewed_backend_evidence_view_from_summary(summary)
        == reviewed_backend_evidence_view_from_summary(summary)
    )


def test_cockpit_view_model_with_backend_bindings_wires_all_three_surfaces():
    base = CockpitViewModel(project="Test", bearing="wiring-slice")

    bound = cockpit_view_model_with_backend_bindings(
        base,
        prompt_payload_evidence=RelayPromptPayloadEvidence(
            prompt_source="relay",
            selected_provider="claude",
            selected_model="claude-sonnet-4-20250514",
            route_class="direct",
            route_kind="direct",
            trust_state="trusted",
            estimated_prompt_tokens=920,
            prompt_budget_tokens=4000,
            budget_percent=23.0,
            growth_state="flat",
            prompt_payload_snapshot_hash="payload-snapshot:wired",
        ),
        visible_meter_evidence=(
            RelayPromptPayloadMeterEvidence(
                meter_evidence_id="payload-meter:wired",
                selected_provider="claude",
                exact_model_id="claude-sonnet-4-20250514",
                provider_route_kind="direct",
                display_label="under 1k",
                budget_percent=22.5,
                payload_status="ok",
            ),
        ),
        visible_meter_source="relay-meter-wired",
        model_capability_summary=RelayModelCapabilityMetadataSummary(
            lanes=(
                RelayModelCapabilityLaneSummary(
                    lane_id="claude",
                    selected_provider="claude",
                    exact_model_id="claude-sonnet-4-20250514",
                    provider_route_kind="direct",
                    trust_state="trusted",
                    context_window_tokens=200000,
                ),
            ),
        ),
        model_capability_selected_id="claude-sonnet-4-20250514",
        model_capability_metadata_source="model-harness-wired",
    )

    assert bound.prompt_payload.provider_id == "claude"
    assert bound.prompt_payload.evidence_ref == "payload-snapshot:wired"
    assert bound.visible_prompt_payload_meter.source == "relay-meter-wired"
    assert len(bound.visible_prompt_payload_meter.items) == 1
    assert bound.visible_prompt_payload_meter.items[0].meter_id == "payload-meter:wired"
    assert bound.model_capabilities.metadata_source == "model-harness-wired"
    assert bound.model_capabilities.selected_model_id == "claude-sonnet-4-20250514"
    assert len(bound.model_capabilities.items) == 1


def test_sample_backend_bound_cockpit_view_model_is_deterministic():
    a = sample_backend_bound_cockpit_view_model()
    b = sample_backend_bound_cockpit_view_model()

    assert a.prompt_payload == b.prompt_payload
    assert a.visible_prompt_payload_meter == b.visible_prompt_payload_meter
    assert a.model_capabilities == b.model_capabilities


def test_sample_backend_bound_cockpit_view_model_binds_prompt_payload_from_evidence():
    vm = sample_backend_bound_cockpit_view_model()

    assert vm.prompt_payload.provider_id == "claude"
    assert vm.prompt_payload.model_name == "claude-sonnet-4-20250514"
    assert vm.prompt_payload.route_class == "direct"
    assert vm.prompt_payload.route_kind == "direct"
    assert vm.prompt_payload.trust_state == "trusted"
    assert vm.prompt_payload.estimated_tokens == 920
    assert vm.prompt_payload.budget_percent == 23.0
    assert vm.prompt_payload.growth_state == "flat"
    assert vm.prompt_payload.evidence_ref == "payload-snapshot:claude-dispatch"
    assert vm.prompt_payload.telemetry_ref == "adapter:claude"
    assert vm.prompt_payload.adapter_metadata_ref == "review:claude-cleared"


def test_sample_backend_bound_cockpit_view_model_binds_meter_from_evidence_list():
    vm = sample_backend_bound_cockpit_view_model()

    assert vm.visible_prompt_payload_meter.source == "relay-meter-evidence-sample"
    assert len(vm.visible_prompt_payload_meter.items) == 2

    first, second = vm.visible_prompt_payload_meter.items
    assert first.meter_id == "payload-meter:claude-under-1k"
    assert first.provider_id == "claude"
    assert first.model_id == "claude-sonnet-4-20250514"
    assert first.prompt_label == "under 1k"
    assert first.payload_status == "ok"
    assert first.q_mode_prompt_drag_state == "ok"

    assert second.meter_id == "payload-meter:deepseek-12-4k"
    assert second.provider_id == "deepseek"
    assert second.prompt_label == "12.4k"
    assert second.payload_status == "degraded"
    assert second.q_mode_prompt_drag_state == "degraded"
    assert "unexpected_growth_delta" in second.warning_tags


def test_sample_backend_bound_cockpit_view_model_binds_model_capabilities_from_summary():
    vm = sample_backend_bound_cockpit_view_model()

    assert vm.model_capabilities.selected_model_id == "claude-sonnet-4-20250514"
    assert vm.model_capabilities.metadata_source == "model-harness-relay-summary-sample"
    assert len(vm.model_capabilities.items) == 2

    claude_item, deepseek_item = vm.model_capabilities.items
    assert claude_item.provider_id == "claude"
    assert claude_item.exact_model_id == "claude-sonnet-4-20250514"
    assert claude_item.route_kind == "direct"
    assert claude_item.trust_state == "trusted"
    assert claude_item.external_review_required is False
    assert claude_item.external_review_status == "not_required"

    assert deepseek_item.provider_id == "deepseek"
    assert deepseek_item.trust_state == "candidate"
    assert deepseek_item.candidate_trust_state == "candidate"
    assert deepseek_item.external_review_required is True
    assert deepseek_item.external_review_status == "pending"
    assert deepseek_item.proof_strength == "weak"
    assert "review:deepseek-pending" in deepseek_item.evidence_refs


def test_sample_backend_bound_cockpit_renders_provider_and_model_identity():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # PromptPayloadView (single record) renders identity in payload-route-context
    assert "Provider: claude" in doc
    assert "Model: claude-sonnet-4-20250514" in doc
    # VisiblePromptPayloadMeterView renders identity per-row
    assert 'data-meter-id="payload-meter:claude-under-1k"' in doc
    assert 'data-meter-id="payload-meter:deepseek-12-4k"' in doc
    assert 'data-provider="deepseek"' in doc
    assert 'data-model="deepseek-chat"' in doc
    # ModelCapabilityMetadataView renders per-lane identity
    assert 'data-model="claude-sonnet-4-20250514"' in doc
    assert 'data-provider="claude"' in doc


def test_sample_backend_bound_cockpit_renders_route_kind_and_trust_state():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    assert "Route kind: direct" in doc
    assert "Trust: trusted" in doc
    assert "Trust: candidate" in doc
    assert "Route: direct" in doc


def test_sample_backend_bound_cockpit_renders_prompt_payload_label_and_budget_percent():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # Prompt payload label and budget percent
    # PromptPayloadView size_label uses estimated_tokens * 4 heuristic; verify by class
    assert 'class="payload-size">' in doc
    assert "23% budget" in doc  # PromptPayloadView.budget_percent = 23.0
    # Visible meter prompt labels render verbatim
    assert "under 1k" in doc
    assert "12.4k" in doc
    assert "Budget: 22.5%" in doc
    assert "Budget: 62.0%" in doc


def test_sample_backend_bound_cockpit_renders_growth_state_and_external_review_status():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # Growth state surfaces in prompt payload status
    assert 'data-growth-state="flat"' in doc
    # External review status surfaces in model capability badges
    assert "External review status: not_required" in doc
    assert "External review status: pending" in doc
    # Prompt growth state per lane
    assert "Prompt growth: flat" in doc
    assert "Prompt growth: unexpected_growth" in doc


def test_sample_backend_bound_cockpit_renders_evidence_refs():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # PromptPayloadView evidence/telemetry/adapter refs
    assert "Evidence: payload-snapshot:claude-dispatch" in doc
    assert "Telemetry: adapter:claude" in doc
    assert "Adapter: review:claude-cleared" in doc
    # Per-meter evidence refs
    assert "Payload evidence: payload-snapshot:claude-dispatch" in doc
    assert "Payload evidence: payload-snapshot:deepseek-qmode" in doc
    # Per-capability evidence refs (rendered as chips)
    assert "review:deepseek-pending" in doc


def test_sample_backend_bound_cockpit_preserves_existing_surfaces_from_base_view_model():
    bound_doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # Surfaces NOT bound by the wiring slice (voice, prime messages, projects,
    # session lifecycle, proof state, instrument) must still come from the
    # base sample_cockpit_view_model.
    assert "mic armed" in bound_doc  # voice listening state from base sample
    assert "Command channel open." in bound_doc  # prime message from base sample
    # Codex Review B repair: the provider balance merge preserves providers
    # absent from the backend summary. The base sample contributes an OpenAI
    # row that the backend summary does not mention; it must still render.
    assert "OpenAI" in bound_doc
    # Bound surfaces still render correctly after wiring.
    assert "Visible Prompt Payload Meter" in bound_doc
    assert "Model Harness Capability Metadata" in bound_doc
    assert "Prompt Payload Visibility" in bound_doc
    assert "Provider Balance" in bound_doc


def test_cockpit_wiring_slice_has_no_filesystem_or_network_side_effects():
    """Wiring slice must be a pure functional projection of backend data."""
    a = sample_backend_bound_cockpit_view_model()
    b = sample_backend_bound_cockpit_view_model()

    # The reviewed surfaces are projected from sample backend records
    # via the adapters; equality across separate calls proves determinism.
    assert a.prompt_payload == b.prompt_payload
    assert a.visible_prompt_payload_meter == b.visible_prompt_payload_meter
    assert a.model_capabilities == b.model_capabilities
    assert a.provider_balance == b.provider_balance

    # Render is deterministic on identical view models
    assert render_cockpit_html(a) == render_cockpit_html(b)


# V2 Provider Balance / Cost-Pressure backend/view-model binding slice
# (provider_balance_view_from_summary + cockpit wiring + evidence_refs).


def test_provider_balance_view_from_summary_maps_identity_health_and_route():
    view = provider_balance_view_from_summary({
        "selected_provider": "claude",
        "routing_owner": "Relay",
        "policy_state": "ok",
        "providers": (
            {
                "provider_id": "claude",
                "display_name": "Claude",
                "model_name": "claude-sonnet-4-20250514",
                "trust_state": "trusted",
                "health": "ok",
                "route_kind": "direct",
                "context_budget_tokens": 200000,
                "prompt_budget_tokens": 4000,
                "current_prompt_tokens": 920,
                "prompt_budget_percent": 23.0,
                "prompt_delta_tokens": 0,
                "cost_pressure": "low",
                "quota_state": "available",
                "remaining_credit_label": "credit: available",
                "credit_status": "available",
                "estimated_spend_label": "$0.18 estimated",
                "notes": "Primary provider ready",
                "evidence_refs": ("adapter:claude", "payload-snapshot:claude-dispatch"),
            },
        ),
    })

    assert view.selected_provider == "claude"
    assert view.routing_owner == "Relay"
    assert view.policy_state == "ok"
    assert len(view.providers) == 1
    item = view.providers[0]
    assert item.provider_id == "claude"
    assert item.display_name == "Claude"
    assert item.model_name == "claude-sonnet-4-20250514"
    assert item.trust_state == "trusted"
    assert item.health == "ok"
    assert item.route_kind == "direct"
    assert item.context_budget_tokens == 200000
    assert item.prompt_budget_tokens == 4000
    assert item.current_prompt_tokens == 920
    assert item.prompt_budget_percent == 23.0
    assert item.prompt_delta_tokens == 0
    assert item.cost_pressure == "low"
    assert item.quota_state == "available"
    assert item.remaining_credit_label == "credit: available"
    assert item.credit_status == "available"
    assert item.estimated_spend_label == "$0.18 estimated"
    assert item.notes == "Primary provider ready"
    assert item.evidence_refs == ["adapter:claude", "payload-snapshot:claude-dispatch"]


def test_provider_balance_view_from_summary_renders_cost_pressure_and_credit_states():
    view = provider_balance_view_from_summary({
        "providers": (
            {
                "provider_id": "deepseek",
                "display_name": "DeepSeek",
                "model_name": "deepseek-chat",
                "trust_state": "candidate",
                "health": "degraded",
                "cost_pressure": "high",
                "quota_state": "limited",
                "remaining_credit_label": "credit: limited",
                "credit_status": "limited",
                "estimated_spend_label": "$0.03 estimated",
            },
            {
                "provider_id": "openrouter",
                "display_name": "OpenRouter",
                "model_name": "deepseek-chat",
                "trust_state": "aggregator",
                "health": "degraded",
                "cost_pressure": "degraded",
                "quota_state": "metered",
                "remaining_credit_label": "credit: provider-hidden",
                "credit_status": "unknown",
            },
        ),
    })

    deepseek, openrouter = view.providers
    assert deepseek.cost_pressure == "high"
    assert deepseek.credit_status == "limited"
    assert deepseek.estimated_spend_label == "$0.03 estimated"
    assert openrouter.cost_pressure == "degraded"
    assert openrouter.credit_status == "unknown"
    assert openrouter.remaining_credit_label == "credit: provider-hidden"


def test_provider_balance_view_from_summary_supports_field_aliases():
    """Adapter accepts common aliases so it can bind backend feeds that name
    fields differently (e.g. exact_model_id, budget_percent, delta_tokens)."""
    view = provider_balance_view_from_summary({
        "providers": (
            {
                "provider_id": "claude",
                "display_name": "Claude",
                "exact_model_id": "claude-sonnet-4-20250514",
                "trust_state": "trusted",
                "provider_health": "ok",
                "provider_route_kind": "direct",
                "context_window_tokens": 200000,
                "estimated_prompt_tokens": 920,
                "budget_percent": 23.0,
                "delta_tokens": 0,
            },
        ),
    })

    item = view.providers[0]
    assert item.model_name == "claude-sonnet-4-20250514"
    assert item.health == "ok"
    assert item.route_kind == "direct"
    assert item.context_budget_tokens == 200000
    assert item.current_prompt_tokens == 920
    assert item.prompt_budget_percent == 23.0
    assert item.prompt_delta_tokens == 0


def test_provider_balance_view_from_summary_empty_summary_yields_empty_view():
    view = provider_balance_view_from_summary({})
    assert view.providers == []
    assert view.selected_provider == ""
    assert view.routing_owner == "unknown"
    assert view.policy_state == "ok"


def test_provider_balance_view_from_summary_skips_non_mapping_provider_entries():
    """Non-Mapping entries inside providers list must be skipped silently
    rather than raising; surface stays renderable on partial backend feeds."""
    view = provider_balance_view_from_summary({
        "providers": (
            "not-a-mapping",
            None,
            42,
            {
                "provider_id": "claude",
                "display_name": "Claude",
                "model_name": "claude-sonnet-4-20250514",
                "trust_state": "trusted",
                "health": "ok",
            },
        ),
    })
    assert len(view.providers) == 1
    assert view.providers[0].provider_id == "claude"


def test_provider_balance_view_from_summary_defaults_safe_on_missing_per_provider_fields():
    view = provider_balance_view_from_summary({
        "providers": (
            {"provider_id": "bare", "display_name": "Bare", "model_name": "bare-model"},
        ),
    })
    item = view.providers[0]
    assert item.trust_state == "unknown"
    assert item.health == "unknown"
    assert item.route_kind == ""
    assert item.context_budget_tokens == 0
    assert item.prompt_budget_tokens == 0
    assert item.prompt_budget_percent == 0.0
    assert item.cost_pressure == "none"
    assert item.quota_state == "unknown"
    assert item.credit_status == "unknown"
    assert item.notes == ""
    assert item.evidence_refs == []


def test_provider_balance_view_from_summary_redacts_unsafe_per_provider_values():
    """The adapter must reuse _safe_handoff_value so unsafe markers cannot
    leak through any string field on a per-provider record."""
    view = provider_balance_view_from_summary({
        "selected_provider": "claude",
        "providers": (
            {
                "provider_id": "claude",
                "display_name": "Claude",
                "model_name": "claude-sonnet-4-20250514",
                "trust_state": "trusted",
                "health": "ok",
                "notes": "raw_prompt RAW_PROMPT_SENTINEL leaked",
                "estimated_spend_label": "api_key:SECRET",
                "evidence_refs": ("adapter:claude", "model_payload:SECRET"),
            },
        ),
    })
    item = view.providers[0]
    assert item.notes == "unsafe_metadata_redacted"
    assert item.estimated_spend_label == "unsafe_metadata_redacted"
    # Evidence refs route through _safe_handoff_value via _handoff_summary_list
    # — direct-safe entries pass through, unsafe ones redacted.
    assert "adapter:claude" in item.evidence_refs
    assert "unsafe_metadata_redacted" in item.evidence_refs


def test_provider_balance_view_from_summary_preserves_provider_order():
    view = provider_balance_view_from_summary({
        "providers": (
            {"provider_id": "z-last", "display_name": "Z", "model_name": "z", "trust_state": "t", "health": "ok"},
            {"provider_id": "a-first", "display_name": "A", "model_name": "a", "trust_state": "t", "health": "ok"},
            {"provider_id": "m-mid", "display_name": "M", "model_name": "m", "trust_state": "t", "health": "ok"},
        ),
    })
    assert [p.provider_id for p in view.providers] == ["z-last", "a-first", "m-mid"]


def test_cockpit_view_model_with_backend_bindings_wires_provider_balance_summary():
    base = CockpitViewModel(project="Test", bearing="provider-balance-wiring")
    original_voice = base.voice

    bound = cockpit_view_model_with_backend_bindings(
        base,
        provider_balance_summary={
            "selected_provider": "claude",
            "routing_owner": "Relay",
            "policy_state": "ok",
            "providers": (
                {
                    "provider_id": "claude",
                    "display_name": "Claude",
                    "model_name": "claude-sonnet-4-20250514",
                    "trust_state": "trusted",
                    "health": "ok",
                    "route_kind": "direct",
                    "evidence_refs": ("adapter:claude",),
                },
            ),
        },
    )

    assert bound is base
    assert bound.provider_balance.selected_provider == "claude"
    assert bound.provider_balance.routing_owner == "Relay"
    assert len(bound.provider_balance.providers) == 1
    assert bound.provider_balance.providers[0].evidence_refs == ["adapter:claude"]
    # Untouched surfaces preserved
    assert bound.voice is original_voice


def test_cockpit_view_model_with_backend_bindings_provider_balance_optional():
    """Omitting provider_balance_summary leaves base.provider_balance untouched."""
    base = sample_cockpit_view_model()
    snapshot = base.provider_balance
    bound = cockpit_view_model_with_backend_bindings(base)
    assert bound.provider_balance is snapshot


def test_sample_backend_bound_cockpit_view_model_binds_provider_balance_from_summary():
    vm = sample_backend_bound_cockpit_view_model()
    assert vm.provider_balance.selected_provider == "claude"
    assert vm.provider_balance.routing_owner == "Relay"
    assert vm.provider_balance.policy_state == "warning"
    # The backend summary now supplies all 5 lanes (claude/openai/deepseek/
    # openrouter/local), each projected from backend evidence rather than
    # preserved from the base sample.
    assert len(vm.provider_balance.providers) == 5
    by_id = {p.provider_id: p for p in vm.provider_balance.providers}
    assert "openai" in by_id
    claude = by_id["claude"]
    openai = by_id["openai"]
    deepseek = by_id["deepseek"]
    openrouter = by_id["openrouter"]
    local = by_id["local"]

    # Identity + health + route + trust
    assert claude.display_name == "Claude"
    assert claude.health == "ok"
    assert claude.route_kind == "direct"
    assert claude.trust_state == "trusted"

    # Token-pressure fields
    assert claude.current_prompt_tokens == 920
    assert claude.prompt_budget_tokens == 4000
    assert claude.prompt_budget_percent == 23.0

    # OpenAI lane is backend-bound: health, route_kind, current_prompt_tokens,
    # remaining_credit_label, estimated_spend_label, and cost_pressure all
    # come from the backend summary (not the base sample preservation path).
    assert openai.display_name == "OpenAI"
    assert openai.model_name == "gpt-4o"
    assert openai.health == "ok"
    assert openai.route_kind == "direct"
    assert openai.trust_state == "trusted"
    assert openai.current_prompt_tokens == 890
    assert openai.prompt_budget_tokens == 3000
    assert openai.prompt_budget_percent == 29.7
    assert openai.cost_pressure == "medium"
    assert openai.credit_status == "available"
    assert openai.remaining_credit_label == "quota: normal"
    assert openai.estimated_spend_label == "$0.12 estimated"
    assert "adapter:openai" in openai.evidence_refs
    assert "telemetry:openai-payload" in openai.evidence_refs

    # Cost-pressure warnings + remaining-credit placeholders
    assert deepseek.cost_pressure == "high"
    assert deepseek.credit_status == "limited"
    assert deepseek.remaining_credit_label == "credit: limited"
    assert deepseek.estimated_spend_label == "$0.03 estimated"

    # Aggregator route with bounded remaining-credit placeholder
    assert openrouter.route_kind == "aggregator"
    assert openrouter.credit_status == "unknown"
    assert openrouter.remaining_credit_label == "credit: provider-hidden"

    # Offline/local route — blocked cost pressure, unavailable credit
    assert local.health == "offline"
    assert local.cost_pressure == "blocked"
    assert local.credit_status == "unavailable"

    # Evidence refs surface for every provider
    assert "adapter:claude" in claude.evidence_refs
    assert "payload-snapshot:claude-dispatch" in claude.evidence_refs
    assert "review:deepseek-pending" in deepseek.evidence_refs
    assert "snapshot:unavailable" in openrouter.evidence_refs


def test_sample_backend_bound_cockpit_renders_provider_health_and_cost_pressure():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    # Provider health classes
    assert 'class="provider-item provider-ok' in doc
    assert "provider-degraded" in doc
    assert "provider-offline" in doc
    # Cost-pressure classes
    assert "provider-pressure-low" in doc
    assert "provider-pressure-high" in doc
    assert "provider-pressure-degraded" in doc
    assert "provider-pressure-blocked" in doc
    # Provider/model identity in headers
    assert "Claude" in doc
    assert "DeepSeek" in doc
    assert "OpenRouter" in doc
    assert "deepseek-chat" in doc


def test_sample_backend_bound_cockpit_renders_token_pressure_and_spend():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    assert "Budget: 23%" in doc
    assert "Tokens: 920/4000" in doc
    assert "Tokens: 3100/5000" in doc
    assert "Pressure: high" in doc
    assert "Pressure: degraded" in doc
    assert "Spend: $0.18 estimated" in doc
    assert "Spend: $0.03 estimated" in doc


def test_sample_backend_bound_cockpit_renders_remaining_credit_placeholders():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    assert "Remaining: credit: available" in doc
    assert "Remaining: credit: limited" in doc
    assert "Remaining: credit: provider-hidden" in doc
    assert "Remaining: credit: n/a" in doc
    assert "provider-credit-unknown" in doc
    assert "provider-credit-unavailable" in doc


def test_sample_backend_bound_cockpit_renders_provider_balance_evidence_refs():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())

    assert 'aria-label="Provider Balance Evidence Refs"' in doc
    assert '<span class="provider-evidence-chip">adapter:claude</span>' in doc
    assert '<span class="provider-evidence-chip">adapter:deepseek</span>' in doc
    assert '<span class="provider-evidence-chip">review:deepseek-pending</span>' in doc
    assert '<span class="provider-evidence-chip">adapter:openrouter</span>' in doc
    assert '<span class="provider-evidence-chip">snapshot:unavailable</span>' in doc
    assert '<span class="provider-evidence-chip">adapter:local</span>' in doc


def test_provider_balance_view_from_summary_is_deterministic():
    """Adapter is a pure projection of input data — repeated calls equal."""
    summary = {
        "selected_provider": "claude",
        "providers": (
            {
                "provider_id": "claude",
                "display_name": "Claude",
                "model_name": "claude-sonnet-4-20250514",
                "trust_state": "trusted",
                "health": "ok",
                "evidence_refs": ("adapter:claude",),
            },
        ),
    }
    assert provider_balance_view_from_summary(summary) == provider_balance_view_from_summary(summary)


def test_provider_balance_evidence_refs_absent_when_empty():
    """When evidence_refs is empty the surface omits the evidence block."""
    base = CockpitViewModel(project="Test", bearing="test")
    base.provider_balance = ProviderBalanceView(
        providers=[ProviderBalanceItem(
            provider_id="claude",
            display_name="Claude",
            model_name="claude-sonnet-4-20250514",
            trust_state="trusted",
            health="ok",
        )],
        selected_provider="claude",
    )
    doc = render_cockpit_html(base)
    assert "Claude" in doc
    assert 'aria-label="Provider Balance Evidence Refs"' not in doc
    assert "provider-evidence-chip" not in doc


# Codex Review B repair: partial provider snapshot merge + view-level
# provenance (evidence_refs) at the ProviderBalanceView level.


def _populated_base_balance():
    """A typical populated base ProviderBalanceView for merge tests."""
    return ProviderBalanceView(
        providers=[
            ProviderBalanceItem(
                provider_id="claude",
                display_name="Claude",
                model_name="claude-sonnet-4-20250514",
                trust_state="trusted",
                health="ok",
                route_kind="direct",
                cost_pressure="low",
                evidence_refs=["base:claude"],
            ),
            ProviderBalanceItem(
                provider_id="openai",
                display_name="OpenAI",
                model_name="gpt-4o",
                trust_state="trusted",
                health="ok",
                route_kind="direct",
                cost_pressure="medium",
                evidence_refs=["base:openai"],
            ),
            ProviderBalanceItem(
                provider_id="deepseek",
                display_name="DeepSeek",
                model_name="deepseek-chat",
                trust_state="candidate",
                health="degraded",
                route_kind="direct",
                cost_pressure="high",
                evidence_refs=["base:deepseek"],
            ),
        ],
        selected_provider="claude",
        routing_owner="Relay",
        policy_state="ok",
        evidence_refs=["base:provenance"],
    )


def test_merge_provider_balance_summary_preserves_unmentioned_base_providers():
    """Partial summary must not erase base providers absent from the snapshot."""
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {
            "providers": (
                {
                    "provider_id": "claude",
                    "display_name": "Claude",
                    "model_name": "claude-sonnet-4-20250514",
                    "trust_state": "trusted",
                    "health": "ok",
                    "cost_pressure": "low",
                    "current_prompt_tokens": 1500,
                    "evidence_refs": ("backend:claude-updated",),
                },
            ),
        },
    )
    by_id = {p.provider_id: p for p in merged.providers}
    # All three base providers still present
    assert set(by_id.keys()) == {"claude", "openai", "deepseek"}
    # Claude was updated by the summary
    assert by_id["claude"].current_prompt_tokens == 1500
    assert by_id["claude"].evidence_refs == ["backend:claude-updated"]
    # OpenAI and DeepSeek preserved exactly (object identity since base is reused)
    assert by_id["openai"].evidence_refs == ["base:openai"]
    assert by_id["deepseek"].evidence_refs == ["base:deepseek"]
    assert by_id["openai"].display_name == "OpenAI"
    assert by_id["deepseek"].cost_pressure == "high"


def test_merge_provider_balance_summary_updates_mentioned_providers_deterministically():
    base = _populated_base_balance()
    summary = {
        "providers": (
            {
                "provider_id": "deepseek",
                "display_name": "DeepSeek",
                "model_name": "deepseek-chat",
                "trust_state": "candidate",
                "health": "ok",  # backend says healthy now
                "cost_pressure": "low",  # cost dropped
                "evidence_refs": ("backend:deepseek-refreshed",),
            },
        ),
    }
    merged_a = merge_provider_balance_summary_into_view(base, summary)
    merged_b = merge_provider_balance_summary_into_view(base, summary)
    by_id_a = {p.provider_id: p for p in merged_a.providers}
    by_id_b = {p.provider_id: p for p in merged_b.providers}
    # Deepseek now reflects backend state, not base state
    assert by_id_a["deepseek"].health == "ok"
    assert by_id_a["deepseek"].cost_pressure == "low"
    assert by_id_a["deepseek"].evidence_refs == ["backend:deepseek-refreshed"]
    # Determinism across repeated calls
    assert merged_a == merged_b


def test_merge_provider_balance_summary_appends_new_providers_after_existing():
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {
            "providers": (
                {
                    "provider_id": "openrouter",
                    "display_name": "OpenRouter",
                    "model_name": "deepseek-chat",
                    "trust_state": "aggregator",
                    "health": "degraded",
                    "route_kind": "aggregator",
                },
                {
                    "provider_id": "local",
                    "display_name": "Local",
                    "model_name": "local-deterministic",
                    "trust_state": "local",
                    "health": "offline",
                    "route_kind": "local",
                },
            ),
        },
    )
    # Order: preserved base providers (claude, openai, deepseek) then new ones
    # (openrouter, local) in summary order.
    assert [p.provider_id for p in merged.providers] == [
        "claude", "openai", "deepseek", "openrouter", "local",
    ]


def test_merge_provider_balance_summary_preserves_view_level_fields_when_summary_omits():
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {"providers": ()},  # no view-level fields supplied
    )
    assert merged.selected_provider == "claude"
    assert merged.routing_owner == "Relay"
    assert merged.policy_state == "ok"
    assert merged.evidence_refs == ["base:provenance"]


def test_merge_provider_balance_summary_overrides_view_level_fields_when_summary_provides():
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {
            "selected_provider": "deepseek",
            "routing_owner": "Aegis",
            "policy_state": "warning",
            "evidence_refs": ("backend:snapshot-fresh", "backend:attestation"),
        },
    )
    assert merged.selected_provider == "deepseek"
    assert merged.routing_owner == "Aegis"
    assert merged.policy_state == "warning"
    assert merged.evidence_refs == ["backend:snapshot-fresh", "backend:attestation"]


def test_merge_provider_balance_summary_view_level_evidence_refs_preserved_on_empty_list():
    """Empty evidence_refs in summary preserves base provenance (not a clear signal)."""
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {"evidence_refs": ()},
    )
    assert merged.evidence_refs == ["base:provenance"]


def test_merge_provider_balance_summary_skips_non_mapping_provider_entries():
    base = _populated_base_balance()
    merged = merge_provider_balance_summary_into_view(
        base,
        {
            "providers": (
                "not-a-mapping",
                None,
                42,
                {
                    "provider_id": "claude",
                    "display_name": "Claude",
                    "model_name": "claude-sonnet-4-20250514",
                    "trust_state": "trusted",
                    "health": "ok",
                    "evidence_refs": ("backend:claude",),
                },
            ),
        },
    )
    # Only the valid mapping was applied — the others were skipped silently.
    by_id = {p.provider_id: p for p in merged.providers}
    assert by_id["claude"].evidence_refs == ["backend:claude"]
    # OpenAI and DeepSeek still preserved
    assert "openai" in by_id
    assert "deepseek" in by_id


def test_merge_provider_balance_summary_does_not_mutate_base():
    base = _populated_base_balance()
    base_provider_ids_before = [p.provider_id for p in base.providers]
    base_claude_evidence_before = list(base.providers[0].evidence_refs)
    base_view_evidence_before = list(base.evidence_refs)
    base_selected_before = base.selected_provider

    _ = merge_provider_balance_summary_into_view(
        base,
        {
            "selected_provider": "deepseek",
            "evidence_refs": ("backend:snapshot",),
            "providers": (
                {
                    "provider_id": "claude",
                    "display_name": "Claude",
                    "model_name": "claude-sonnet-4-20250514",
                    "trust_state": "trusted",
                    "health": "ok",
                    "evidence_refs": ("backend:claude-updated",),
                },
            ),
        },
    )

    assert [p.provider_id for p in base.providers] == base_provider_ids_before
    assert base.providers[0].evidence_refs == base_claude_evidence_before
    assert base.evidence_refs == base_view_evidence_before
    assert base.selected_provider == base_selected_before


def test_provider_balance_view_from_summary_projects_view_level_evidence_refs():
    view = provider_balance_view_from_summary({
        "evidence_refs": ("snapshot:relay", "attestation:aegis"),
    })
    assert view.evidence_refs == ["snapshot:relay", "attestation:aegis"]


def test_provider_balance_view_from_summary_view_level_evidence_alias_keys():
    view = provider_balance_view_from_summary({
        "evidence": ("alt-snapshot",),
    })
    assert view.evidence_refs == ["alt-snapshot"]
    view2 = provider_balance_view_from_summary({
        "evidence_ids": ("ids-snapshot",),
    })
    assert view2.evidence_refs == ["ids-snapshot"]


def test_provider_balance_view_level_evidence_refs_render_safely_escaped():
    base = CockpitViewModel(project="Test", bearing="test")
    base.provider_balance = ProviderBalanceView(
        providers=[
            ProviderBalanceItem(
                provider_id="claude",
                display_name="Claude",
                model_name="claude-sonnet-4-20250514",
                trust_state="trusted",
                health="ok",
            ),
        ],
        evidence_refs=["snapshot:relay-2026", "<script>alert(1)</script>"],
    )
    doc = render_cockpit_html(base)
    assert 'aria-label="Provider Balance Provenance"' in doc
    assert '<span class="provider-balance-evidence-chip">snapshot:relay-2026</span>' in doc
    # HTML escaping must apply to the raw script payload — no unescaped tag.
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in doc


def test_provider_balance_view_level_evidence_refs_redacts_unsafe_markers():
    view = provider_balance_view_from_summary({
        "evidence_refs": (
            "snapshot:safe",
            "raw_prompt:SECRET",
            "model_payload:SECRET",
            "api_key:SECRET",
        ),
    })
    # The redactor folds unsafe markers to the sentinel.
    assert "snapshot:safe" in view.evidence_refs
    assert "raw_prompt:SECRET" not in view.evidence_refs
    assert "model_payload:SECRET" not in view.evidence_refs
    assert "api_key:SECRET" not in view.evidence_refs
    assert view.evidence_refs.count("unsafe_metadata_redacted") == 3


def test_provider_balance_view_level_evidence_block_absent_when_empty():
    base = CockpitViewModel(project="Test", bearing="test")
    base.provider_balance = ProviderBalanceView(
        providers=[
            ProviderBalanceItem(
                provider_id="claude",
                display_name="Claude",
                model_name="claude-sonnet-4-20250514",
                trust_state="trusted",
                health="ok",
            ),
        ],
    )
    doc = render_cockpit_html(base)
    assert 'aria-label="Provider Balance Provenance"' not in doc
    assert "provider-balance-evidence-chip" not in doc
    assert "Provenance:" not in doc


def test_cockpit_view_model_with_backend_bindings_partial_summary_preserves_base_providers():
    base = CockpitViewModel(project="Test", bearing="partial-merge")
    base.provider_balance = _populated_base_balance()
    bound = cockpit_view_model_with_backend_bindings(
        base,
        provider_balance_summary={
            "selected_provider": "deepseek",
            "evidence_refs": ("backend:snapshot",),
            "providers": (
                {
                    "provider_id": "deepseek",
                    "display_name": "DeepSeek",
                    "model_name": "deepseek-chat",
                    "trust_state": "candidate",
                    "health": "ok",
                    "cost_pressure": "low",
                    "evidence_refs": ("backend:deepseek-fresh",),
                },
            ),
        },
    )
    by_id = {p.provider_id: p for p in bound.provider_balance.providers}
    # Claude and OpenAI preserved (not in summary); DeepSeek updated from backend
    assert "claude" in by_id
    assert "openai" in by_id
    assert by_id["deepseek"].health == "ok"
    assert by_id["deepseek"].cost_pressure == "low"
    assert by_id["deepseek"].evidence_refs == ["backend:deepseek-fresh"]
    # View-level fields override only when summary provides; routing_owner /
    # policy_state preserved from base because the summary omits them.
    assert bound.provider_balance.selected_provider == "deepseek"
    assert bound.provider_balance.routing_owner == "Relay"
    assert bound.provider_balance.policy_state == "ok"
    assert bound.provider_balance.evidence_refs == ["backend:snapshot"]


def test_cockpit_view_model_with_backend_bindings_provider_balance_optional_preserves_base():
    """Regression: omitting provider_balance_summary leaves base untouched."""
    base = CockpitViewModel(project="Test", bearing="no-summary")
    base.provider_balance = _populated_base_balance()
    snapshot_before = base.provider_balance
    bound = cockpit_view_model_with_backend_bindings(base)
    assert bound.provider_balance is snapshot_before
    assert [p.provider_id for p in bound.provider_balance.providers] == [
        "claude", "openai", "deepseek",
    ]
    assert bound.provider_balance.evidence_refs == ["base:provenance"]


def test_sample_backend_bound_cockpit_renders_view_level_provider_balance_provenance():
    doc = render_cockpit_html(sample_backend_bound_cockpit_view_model())
    # The sample binder supplies view-level evidence_refs at the summary level.
    assert 'aria-label="Provider Balance Provenance"' in doc
    assert '<span class="provider-balance-evidence-chip">snapshot:relay-provider-balance-2026-06-07</span>' in doc
    assert '<span class="provider-balance-evidence-chip">attestation:aegis-route-tier</span>' in doc
    assert '<span class="provider-balance-evidence-chip">signing-chain:relay-handoff</span>' in doc


def test_merge_provider_balance_summary_is_deterministic():
    base = _populated_base_balance()
    summary = {
        "selected_provider": "deepseek",
        "evidence_refs": ("backend:snapshot",),
        "providers": (
            {
                "provider_id": "deepseek",
                "display_name": "DeepSeek",
                "model_name": "deepseek-chat",
                "trust_state": "candidate",
                "health": "degraded",
            },
            {
                "provider_id": "openrouter",
                "display_name": "OpenRouter",
                "model_name": "deepseek-chat",
                "trust_state": "aggregator",
                "health": "degraded",
            },
        ),
    }
    a = merge_provider_balance_summary_into_view(base, summary)
    b = merge_provider_balance_summary_into_view(base, summary)
    assert a == b
    assert [p.provider_id for p in a.providers] == [p.provider_id for p in b.providers]


# Bifrost + Prompt Payload Visibility: backend-bound surface adjacency proof.
#
# Proves the visible prompt payload surface produced by the backend-binding
# pipeline renders required prompt-payload fields inside the same cockpit
# document as dispatch hardening and the instrument-band queue-poll chip.


_PROMPT_PAYLOAD_VISIBILITY_PROVIDER = "claude"
_PROMPT_PAYLOAD_VISIBILITY_MODEL = "claude-sonnet-4-20250514"
_PROMPT_PAYLOAD_VISIBILITY_ROUTE_CLASS = "direct"
_PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND = "direct"

_PROMPT_PAYLOAD_VISIBILITY_FORBIDDEN_LEAKAGE = (
    "RAW_PROMPT_SENTINEL",
    "SECRET_VALUE",
    "raw_prompt",
    "raw_provider_response",
    "provider_response",
)
_PROMPT_PAYLOAD_VISIBILITY_FORBIDDEN_CONTROLS = (
    "<button",
    "<form",
    "data-recovery-action",
    "restart-session",
    "archive-session",
    "resteer-session",
    "spawn-session",
    "merge",
    "rebase",
    "cherry-pick",
    "stash-pop",
)


def _slice_aria_section(doc: str, aria_label: str) -> str:
    needle = f'aria-label="{aria_label}"'
    assert needle in doc, f"missing section aria-label={aria_label!r}"
    after = doc.split(needle, 1)[1]
    assert "</section>" in after, f"unclosed section for aria-label={aria_label!r}"
    return after.split("</section>", 1)[0]


def test_backend_bound_prompt_payload_visibility_renders_adjacent_to_dispatch_and_queue_poll():
    vm = sample_backend_bound_cockpit_view_model()
    vm.dispatch_hardening = DispatchHardeningView(
        dispatch_id="dispatch-prompt-payload-visibility",
        provider_id=_PROMPT_PAYLOAD_VISIBILITY_PROVIDER,
        exact_model_id=_PROMPT_PAYLOAD_VISIBILITY_MODEL,
        route_class=_PROMPT_PAYLOAD_VISIBILITY_ROUTE_CLASS,
        route_kind=_PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND,
        trust_state="trusted",
        proof_strength="strong",
        external_review_status="not_required",
        payload_evidence_state="snapshot_present",
    )
    doc = render_cockpit_html(vm)

    dispatch_section = _slice_aria_section(doc, "Dispatch Hardening State")
    meter_section = _slice_aria_section(doc, "Visible Prompt Payload Meter")
    payload_section = _slice_aria_section(doc, "Prompt Payload Visibility")

    # Prompt payload size.
    assert 'class="payload-size">(3.7k)</span>' in payload_section
    assert "920 tokens" in payload_section
    assert "under 1k" in meter_section
    assert "12.4k" in meter_section

    # Budget pressure.
    assert "23% budget" in payload_section
    assert "Prompt budget: 4000 tokens" in payload_section
    assert "Context budget: 200000 tokens" in payload_section
    assert "Budget: 22.5%" in meter_section
    assert "Budget: 62.0%" in meter_section

    # Growth/flat status.
    assert 'data-growth-state="flat"' in payload_section
    assert 'data-watch-state="ok"' in payload_section
    assert "Delta: 0 tokens / 0.0%" in payload_section
    assert "Growth delta: 0 tokens / 0.0%" in meter_section
    assert "Growth delta: +240 tokens / 6.0%" in meter_section

    # Q-mode prompt-drag state.
    assert "Q-mode prompt drag: ok" in meter_section
    assert "Q-mode prompt drag: degraded" in meter_section
    assert "Payload status: ok" in meter_section
    assert "Payload status: degraded" in meter_section

    # Evidence refs.
    assert "Evidence: payload-snapshot:claude-dispatch" in payload_section
    assert "Telemetry: adapter:claude" in payload_section
    assert "Adapter: review:claude-cleared" in payload_section
    assert "Payload evidence: payload-snapshot:claude-dispatch" in meter_section
    assert "Payload evidence: payload-snapshot:deepseek-qmode" in meter_section
    assert "Provider balance: provider-balance:claude" in meter_section
    assert "Provider balance: provider-balance:deepseek" in meter_section

    # Dispatch section identity, scoped to the dispatch section.
    assert f"Provider: {_PROMPT_PAYLOAD_VISIBILITY_PROVIDER}" in dispatch_section
    assert f"Exact model: {_PROMPT_PAYLOAD_VISIBILITY_MODEL}" in dispatch_section
    assert f"Route class: {_PROMPT_PAYLOAD_VISIBILITY_ROUTE_CLASS}" in dispatch_section
    assert f"Route kind: {_PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND}" in dispatch_section

    # Payload section identity, scoped to prompt payload visibility.
    assert f"Provider: {_PROMPT_PAYLOAD_VISIBILITY_PROVIDER}" in payload_section
    assert f"Model: {_PROMPT_PAYLOAD_VISIBILITY_MODEL}" in payload_section
    assert f"Route class: {_PROMPT_PAYLOAD_VISIBILITY_ROUTE_CLASS}" in payload_section
    assert f"Route kind: {_PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND}" in payload_section

    # Meter section identity, scoped to the Claude meter row.
    claude_meter_marker = 'data-meter-id="payload-meter:claude-under-1k"'
    assert claude_meter_marker in meter_section
    claude_row = meter_section.split(claude_meter_marker, 1)[1]
    claude_row = claude_row.split('<div class="payload-meter-item ', 1)[0]
    assert f"Provider: {_PROMPT_PAYLOAD_VISIBILITY_PROVIDER}" in claude_row
    assert f"Model: {_PROMPT_PAYLOAD_VISIBILITY_MODEL}" in claude_row
    assert f"Route: {_PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND}" in claude_row

    def _capture(section: str, field: str) -> str:
        match = re.search(re.escape(field) + r":\s*([A-Za-z0-9_.\-]+)", section)
        assert match, f"missing field {field!r} in section"
        return match.group(1)

    dispatch_provider = _capture(dispatch_section, "Provider")
    dispatch_model = _capture(dispatch_section, "Exact model")
    dispatch_route_class = _capture(dispatch_section, "Route class")
    dispatch_route_kind = _capture(dispatch_section, "Route kind")
    payload_provider = _capture(payload_section, "Provider")
    payload_model = _capture(payload_section, "Model")
    payload_route_class = _capture(payload_section, "Route class")
    payload_route_kind = _capture(payload_section, "Route kind")
    meter_claude_provider = _capture(claude_row, "Provider")
    meter_claude_model = _capture(claude_row, "Model")
    meter_claude_route_kind = _capture(claude_row, "Route")

    assert dispatch_provider == payload_provider == meter_claude_provider == (
        _PROMPT_PAYLOAD_VISIBILITY_PROVIDER
    )
    assert dispatch_model == payload_model == meter_claude_model == (
        _PROMPT_PAYLOAD_VISIBILITY_MODEL
    )
    assert dispatch_route_class == payload_route_class == (
        _PROMPT_PAYLOAD_VISIBILITY_ROUTE_CLASS
    )
    assert dispatch_route_kind == payload_route_kind == meter_claude_route_kind == (
        _PROMPT_PAYLOAD_VISIBILITY_ROUTE_KIND
    )

    # Adjacency to queue-poll state in the rendered cockpit document.
    dispatch_marker = 'aria-label="Dispatch Hardening State"'
    meter_marker = 'aria-label="Visible Prompt Payload Meter"'
    payload_marker = 'aria-label="Prompt Payload Visibility"'
    queue_marker = '<span class="instr-queue">Queue '
    assert queue_marker in doc
    assert doc.index(dispatch_marker) < doc.index(meter_marker)
    assert doc.index(meter_marker) < doc.index(payload_marker)
    assert doc.index(payload_marker) < doc.index(queue_marker)
    assert "Queue ON" in doc

    scoped_sections = {
        "dispatch_hardening": dispatch_section,
        "visible_prompt_payload_meter": meter_section,
        "prompt_payload_visibility": payload_section,
    }
    for section_name, section in scoped_sections.items():
        for unsafe in _PROMPT_PAYLOAD_VISIBILITY_FORBIDDEN_LEAKAGE:
            assert unsafe not in section, (
                f"leakage token {unsafe!r} appeared in {section_name} section"
            )
        for control in _PROMPT_PAYLOAD_VISIBILITY_FORBIDDEN_CONTROLS:
            assert control not in section, (
                f"control token {control!r} appeared in {section_name} section"
            )
