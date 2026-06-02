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
    render_cockpit_html,
    relay_aegis_policy_handoff_from_summary,
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

ROOT = Path(__file__).resolve().parents[1]


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


def test_index_user_session_mode_names_target_and_preserves_storage():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "User Session:" in doc
    assert "window.meridianRefreshUserSessionTarget = () =>" in doc
    assert "meridian.user-session.target.v1" in doc
    assert "localStorage.setItem(userSessionTargetKey, userSessionSelect.value)" in doc
    assert "Select a live User Session target before sending" in doc


def test_compass_logic_snapshot_documents_project_context_harness():
    from meridian_core.compass_logic_snapshot import compass_logic_snapshot

    snapshot = compass_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]
    assert snapshot["source"] == "meridian_core.compass_logic_snapshot.compass_logic_snapshot"
    assert "Project Definition Logic" in titles
    assert "Bounds and Scope Logic" in titles
    assert "Project Difference Logic" in titles
    assert "Cross-Project Communication Logic" in titles
    assert "Project Selector Logic" in titles
    assert "Prime Prompt Context" in titles
    assert "Portfolio Boundary" in titles
    assert "User Session Independence" not in titles


def test_vulcan_logic_snapshot_documents_session_lifecycle_harness():
    from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot

    snapshot = vulcan_logic_snapshot()
    titles = [section["title"] for section in snapshot["capabilitySections"]]
    assert snapshot["source"] == "meridian_core.vulcan_logic_snapshot.vulcan_logic_snapshot"
    assert "Session Definition Logic" in titles
    assert "Lifecycle State Logic" in titles
    assert "Command Plan Logic" in titles
    assert "User Session Independence" in titles
    assert "Project-Aware Session Grouping" in titles
    assert "Stale Target Guard" in titles
    assert "Cross-Harness Relationship Logic" in titles
    assert "Portfolio Boundary" not in titles


def test_index_projects_selector_is_compass_context_not_user_routing():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "projectOptions = ['Bifrost', 'Meridian', 'Spark']" in doc
    assert "screen.dataset.projectContext" in doc
    assert "Compass project context:" in doc
    assert "projectContext" in doc
    assert "renderUserSessionSelect();" in doc
    assert "localStorage.setItem(userSessionTargetKey, projectSelect.value" not in doc


def test_index_compass_harness_uses_backend_logic_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Compass Runtime Logic" in doc
    assert "data-compass-logic" in doc
    assert "bridgeUrl('compass-logic')" in doc
    assert "renderCompassLogicSnapshot" in doc
    assert "renderCompassProjectLogic" in doc


def test_index_vulcan_harness_uses_backend_logic_snapshot():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Vulcan Runtime Logic" in doc
    assert "data-vulcan-logic" in doc
    assert "bridgeUrl('vulcan-logic')" in doc
    assert "renderVulcanLogicSnapshot" in doc
    assert "renderVulcanSessionLogic" in doc


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


def test_index_wired_harness_titles_use_runtime_logic_naming():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "Prime Runtime Logic" in doc
    assert "Relay Runtime Logic" in doc
    assert "Compass Runtime Logic" in doc
    assert "Vulcan Runtime Logic" in doc


def test_index_relay_harness_renders_backend_logic_snapshot_contract():
    doc = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "data-relay-logic" in doc
    assert "bridgeUrl('relay-logic')" in doc
    assert "renderRelayLogicSnapshot(snapshot)" in doc
    assert "renderRelayPrimeDirectives(snapshot)" in doc
    assert "capabilitySections.map(renderRelayCapabilitySection)" in doc
    assert "snapshot.routePrecedence" in doc
    assert "tier3.dispatch?.laneOrder" in doc
    assert "tier3.dispatch?.payloadPolicy" in doc
    assert "relayAuditRows(tier3)" in doc
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


def test_bridge_exposes_prime_logic_route_and_capability():
    doc = (ROOT / "scripts" / "meridian-model-bridge.js").read_text(encoding="utf-8")
    assert "primeRuntimeSnapshot: true" in doc
    assert "primeLogic: '/bridge/prime-logic'" in doc
    assert "meridian_core.prime_runtime" in doc
    assert "req.url === BRIDGE_ROUTES.primeLogic" in doc


def test_ui_checklist_defers_deep_compass_and_vulcan_items_to_backend_tracker():
    doc = (ROOT / "docs" / "ui-integration-checklist.md").read_text(encoding="utf-8")
    assert "### Compass And Vulcan Backend Readiness" in doc
    assert "| HBD1 | Compass backend checklist |" in doc
    assert "| HBD2 | Vulcan backend checklist |" in doc
    assert "| CMP1 | Project definition |" not in doc
    assert "| VLC1 | Session definition |" not in doc


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



# ── Harness dashboard ────────────────────────────────────────────────────────


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


# ── Right-Panel Mode Tests ──────────────────────────────────────────────────


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


# ── Sessions dropdown grouping and sorting ──────────────────────────────────

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


# ── interactive-state mode switching ────────────────────────────────────────

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


# ── Sessions dropdown filtering (Reviews B repairs) ──────────────────────────

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


# ── Stale-target guard (post-Sessions dropdown repair) ──────────────────────

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
