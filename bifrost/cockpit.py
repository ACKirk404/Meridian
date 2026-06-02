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
from typing import TYPE_CHECKING, Mapping

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
    route_kind: str = ""
    context_budget_tokens: int = 0
    prompt_budget_tokens: int = 0
    current_prompt_tokens: int = 0
    prompt_budget_percent: float = 0.0
    prompt_delta_tokens: int = 0
    cost_pressure: str = "none"
    quota_state: str = "unknown"
    remaining_credit_label: str = ""
    credit_status: str = "unknown"
    estimated_spend_label: str = ""
    notes: str = ""


@dataclass
class ProviderBalanceView:
    providers: list[ProviderBalanceItem] = field(default_factory=list)
    selected_provider: str = ""
    routing_owner: str = "unknown"
    policy_state: str = "ok"


@dataclass
class ModelCapabilityItem:
    provider_id: str
    exact_model_id: str
    route_kind: str
    trust_state: str
    candidate_trust_state: str = "trusted"
    context_window_tokens: int = 0
    cost_posture: str = "unknown"
    latency_tier: str = "unknown"
    tokenizer_family: str = "unknown"
    supports_streaming: bool = False
    q_mode_flat: bool = False
    external_review_required: bool = False
    external_review_status: str = "not_required"
    proof_strength: str = "unknown"
    blocked_authorities: list[str] = field(default_factory=list)
    allowed_task_hints: list[str] = field(default_factory=list)
    blocked_task_hints: list[str] = field(default_factory=list)
    prompt_budget_status: str = "unknown"
    prompt_growth_state: str = "unknown"
    prompt_delta_tokens: int = 0
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class ModelCapabilityMetadataView:
    items: list[ModelCapabilityItem] = field(default_factory=list)
    selected_model_id: str = ""
    metadata_source: str = "sample"


@dataclass
class ModelValidationEnvelopeItem:
    envelope_id: str
    provider_id: str
    exact_model_id: str
    dispatch_id: str
    route_kind: str
    validation_state: str
    fail_closed_reason: str = "none"
    candidate_trust_state: str = "trusted"
    external_review_status: str = "not_required"
    proof_strength: str = "unknown"
    prompt_budget_status: str = "unknown"
    prompt_growth_state: str = "unknown"
    prompt_budget_percent: float = 0.0
    prompt_delta_tokens: int = 0
    prompt_delta_percent: float = 0.0
    route_proof_refs: list[str] = field(default_factory=list)
    blocker_tags: list[str] = field(default_factory=list)
    warning_tags: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class ModelValidationEnvelopeView:
    envelopes: list[ModelValidationEnvelopeItem] = field(default_factory=list)
    source: str = "sample"


@dataclass
class PromptPayloadView:
    size_label: str = ""
    estimated_tokens: int = 0
    prompt_budget_tokens: int = 0
    context_budget_tokens: int = 0
    budget_percent: float = 0.0
    delta_tokens: int = 0
    delta_percent: float = 0.0
    growth_state: str = "flat"
    watch_state: str = "ok"
    source: str = ""
    provider_id: str = ""
    model_name: str = ""
    trust_state: str = "unknown"
    route_class: str = ""
    route_kind: str = ""
    evidence_ref: str = ""
    telemetry_ref: str = ""
    adapter_metadata_ref: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class DispatchHardeningView:
    dispatch_id: str = ""
    provider_id: str = ""
    exact_model_id: str = ""
    route_class: str = ""
    route_kind: str = ""
    trust_state: str = "unknown"
    proof_strength: str = "unknown"
    external_review_status: str = "unknown"
    blocked_authorities: list[str] = field(default_factory=list)
    payload_evidence_state: str = "unknown"
    fallback_blockers: list[str] = field(default_factory=list)
    dispatch_error_tags: list[str] = field(default_factory=list)


@dataclass
class PromptPacketProofView:
    packet_id: str = ""
    packet_hash: str = ""
    source_lineage_compliance: str = "unknown"
    prompt_budget_ref: str = ""
    aegis_evidence_ids: list[str] = field(default_factory=list)
    proof_requirement: str = "unknown"
    snapshot_hash_gaps: list[str] = field(default_factory=list)
    proof_state: str = "warn"
    missing_metadata_warnings: list[str] = field(default_factory=list)


@dataclass
class AegisPromptPacketPolicyView:
    packet_id: str = ""
    policy_id: str = ""
    decision: str = "warn"
    human_gate_state: str = "not_required"
    proof_requirement: str = "unknown"
    aegis_evidence_ids: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    reason_tags: list[str] = field(default_factory=list)


@dataclass
class RelayAegisPolicyHandoffView:
    decision: str = ""
    severity: str = "info"
    packet_id: str = ""
    packet_hash_status: str = "unknown"
    proof_requirement: str = "unknown"
    aegis_evidence_ids: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    demotion_target: str = ""
    human_gate_state: str = "not_required"
    missing_metadata_fail_closed: bool = False
    missing_metadata_fields: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class ProofGateStatus:
    gate_id: str
    gate_name: str
    status: str  # "pass" | "warning" | "block"
    reason: str = ""


@dataclass
class ProofPreviewItem:
    proof_id: str
    label: str
    state: str  # "pending" | "blocked" | "passed" | "needs-human-review"
    owner: str
    evidence_ref: str = ""
    summary: str = ""


@dataclass
class ProofStateView:
    proof_status: str = "no_proof"  # "no_proof" | "queue_read" | "verified" | "executed"
    gates: list[ProofGateStatus] = field(default_factory=list)
    preview_items: list[ProofPreviewItem] = field(default_factory=list)
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
    model_capabilities: ModelCapabilityMetadataView = field(default_factory=ModelCapabilityMetadataView)
    model_validation_envelopes: ModelValidationEnvelopeView = field(default_factory=ModelValidationEnvelopeView)
    prompt_payload: PromptPayloadView = field(default_factory=PromptPayloadView)
    dispatch_hardening: DispatchHardeningView = field(default_factory=DispatchHardeningView)
    prompt_packet_proof: PromptPacketProofView = field(default_factory=PromptPacketProofView)
    aegis_prompt_packet_policy: AegisPromptPacketPolicyView = field(default_factory=AegisPromptPacketPolicyView)
    relay_aegis_policy_handoff: RelayAegisPolicyHandoffView = field(default_factory=RelayAegisPolicyHandoffView)
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


def sample_cockpit_view_model(
    relay_aegis_policy_handoff_summary: Mapping[str, object] | None = None,
) -> CockpitViewModel:
    """Return deterministic sample data for previewing the cockpit."""
    handoff_summary = relay_aegis_policy_handoff_summary or {
        "aegis_gate_decision": "demote",
        "aegis_gate_severity": "warning",
        "packet_id_ref": "prompt-packet-001",
        "packet_hash_ref": "present",
        "proof_requirement": "tier2_payload_snapshot",
        "evidence_ids": (
            "aegis:route-tier",
            "aegis:payload-proof",
        ),
        "fallback_blockers": (
            "demotion_route_required",
        ),
        "warning_tags": (
            "response_payload_hash_pending",
        ),
        "demotion_target_tier": "tier1:account-first",
        "human_gate_state": "not_required",
        "missing_metadata_fail_closed": False,
        "missing_metadata_fields": (),
        "aegis_explanation": "Relay accepted Aegis demotion target with proof snapshot warning.",
    }
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
                    model_name="claude-sonnet-4-20250514",
                    trust_state="trusted",
                    health="ok",
                    route_kind="direct",
                    context_budget_tokens=200000,
                    prompt_budget_tokens=4000,
                    current_prompt_tokens=1240,
                    prompt_budget_percent=31.0,
                    prompt_delta_tokens=0,
                    cost_pressure="low",
                    quota_state="available",
                    remaining_credit_label="credit: available",
                    credit_status="available",
                    estimated_spend_label="$0.18 estimated",
                    notes="Primary provider ready",
                ),
                ProviderBalanceItem(
                    provider_id="openai",
                    display_name="OpenAI",
                    model_name="gpt-4o",
                    trust_state="trusted",
                    health="ok",
                    route_kind="direct",
                    context_budget_tokens=128000,
                    prompt_budget_tokens=3000,
                    current_prompt_tokens=890,
                    prompt_budget_percent=29.7,
                    prompt_delta_tokens=50,
                    cost_pressure="medium",
                    quota_state="available",
                    remaining_credit_label="quota: normal",
                    credit_status="available",
                    estimated_spend_label="$0.12 estimated",
                    notes="Secondary provider with minor growth",
                ),
                ProviderBalanceItem(
                    provider_id="deepseek",
                    display_name="DeepSeek",
                    model_name="deepseek-chat",
                    trust_state="candidate",
                    health="degraded",
                    route_kind="direct",
                    context_budget_tokens=256000,
                    prompt_budget_tokens=5000,
                    current_prompt_tokens=2450,
                    prompt_budget_percent=49.0,
                    prompt_delta_tokens=240,
                    cost_pressure="high",
                    quota_state="limited",
                    remaining_credit_label="credit: limited",
                    credit_status="limited",
                    estimated_spend_label="$0.03 estimated",
                    notes="Q-mode prompt drag detected",
                ),
                ProviderBalanceItem(
                    provider_id="openrouter",
                    display_name="OpenRouter",
                    model_name="deepseek-chat",
                    trust_state="aggregator",
                    health="degraded",
                    route_kind="aggregator",
                    context_budget_tokens=64000,
                    prompt_budget_tokens=1800,
                    current_prompt_tokens=1600,
                    prompt_budget_percent=88.9,
                    prompt_delta_tokens=360,
                    cost_pressure="degraded",
                    quota_state="metered",
                    remaining_credit_label="credit: provider-hidden",
                    credit_status="unknown",
                    estimated_spend_label="$0.02 estimated",
                    notes="Aggregator route lacks payload snapshot proof",
                ),
                ProviderBalanceItem(
                    provider_id="local",
                    display_name="Local",
                    model_name="local-deterministic",
                    trust_state="local",
                    health="offline",
                    route_kind="local",
                    context_budget_tokens=32000,
                    prompt_budget_tokens=1200,
                    current_prompt_tokens=0,
                    prompt_budget_percent=0.0,
                    prompt_delta_tokens=0,
                    cost_pressure="blocked",
                    quota_state="unavailable",
                    remaining_credit_label="credit: n/a",
                    credit_status="unavailable",
                    estimated_spend_label="$0.00 estimated",
                    notes="Local deterministic route unavailable",
                ),
            ],
            selected_provider="claude",
            routing_owner="Relay",
            policy_state="warning",
        ),
        model_capabilities=ModelCapabilityMetadataView(
            selected_model_id="claude-sonnet-4-20250514",
            metadata_source="model-harness-sample",
            items=[
                ModelCapabilityItem(
                    provider_id="claude",
                    exact_model_id="claude-sonnet-4-20250514",
                    route_kind="direct",
                    trust_state="trusted",
                    candidate_trust_state="trusted",
                    context_window_tokens=200000,
                    cost_posture="premium",
                    latency_tier="fast",
                    tokenizer_family="claude",
                    supports_streaming=True,
                    q_mode_flat=False,
                    external_review_required=False,
                    external_review_status="not_required",
                    proof_strength="strong",
                    blocked_authorities=[],
                    allowed_task_hints=["build", "review", "explain"],
                    blocked_task_hints=[],
                    prompt_budget_status="within_budget",
                    prompt_growth_state="flat",
                    prompt_delta_tokens=0,
                    evidence_refs=["adapter:claude", "telemetry:claude-payload"],
                ),
                ModelCapabilityItem(
                    provider_id="openai",
                    exact_model_id="gpt-4o",
                    route_kind="direct",
                    trust_state="trusted",
                    candidate_trust_state="trusted",
                    context_window_tokens=128000,
                    cost_posture="premium",
                    latency_tier="fast",
                    tokenizer_family="openai",
                    supports_streaming=True,
                    q_mode_flat=False,
                    external_review_required=False,
                    external_review_status="not_required",
                    proof_strength="standard",
                    blocked_authorities=[],
                    allowed_task_hints=["build", "verify", "explain"],
                    blocked_task_hints=["tier4_human_gate"],
                    prompt_budget_status="within_budget",
                    prompt_growth_state="expected_growth",
                    prompt_delta_tokens=50,
                    evidence_refs=["adapter:openai", "telemetry:openai-payload"],
                ),
                ModelCapabilityItem(
                    provider_id="deepseek",
                    exact_model_id="deepseek-chat",
                    route_kind="direct",
                    trust_state="candidate",
                    candidate_trust_state="candidate",
                    context_window_tokens=256000,
                    cost_posture="minimal",
                    latency_tier="normal",
                    tokenizer_family="deepseek",
                    supports_streaming=True,
                    q_mode_flat=True,
                    external_review_required=True,
                    external_review_status="pending",
                    proof_strength="weak",
                    blocked_authorities=["external_review_required"],
                    allowed_task_hints=["verify", "explain"],
                    blocked_task_hints=["build", "review_clearing"],
                    prompt_budget_status="watch",
                    prompt_growth_state="unexpected_growth",
                    prompt_delta_tokens=240,
                    evidence_refs=["adapter:deepseek", "validation:pending"],
                ),
                ModelCapabilityItem(
                    provider_id="deepseek-reviewed",
                    exact_model_id="deepseek-chat",
                    route_kind="direct",
                    trust_state="trusted",
                    candidate_trust_state="external_review_cleared",
                    context_window_tokens=256000,
                    cost_posture="minimal",
                    latency_tier="normal",
                    tokenizer_family="deepseek",
                    supports_streaming=True,
                    q_mode_flat=True,
                    external_review_required=True,
                    external_review_status="passed",
                    proof_strength="strong",
                    blocked_authorities=[],
                    allowed_task_hints=["verify", "explain"],
                    blocked_task_hints=[],
                    prompt_budget_status="within_budget",
                    prompt_growth_state="flat",
                    prompt_delta_tokens=0,
                    evidence_refs=["review:codex-b", "validation:deepseek-direct-passed"],
                ),
                ModelCapabilityItem(
                    provider_id="openrouter",
                    exact_model_id="deepseek-chat",
                    route_kind="aggregator",
                    trust_state="degraded",
                    candidate_trust_state="validation_blocked",
                    context_window_tokens=64000,
                    cost_posture="unknown",
                    latency_tier="unknown",
                    tokenizer_family="deepseek",
                    supports_streaming=True,
                    q_mode_flat=False,
                    external_review_required=True,
                    external_review_status="pending",
                    proof_strength="weak",
                    blocked_authorities=["aggregator_without_proof", "payload_snapshot_missing"],
                    allowed_task_hints=["explain"],
                    blocked_task_hints=["payload_snapshot", "tier2_plus"],
                    prompt_budget_status="near_limit",
                    prompt_growth_state="degraded",
                    prompt_delta_tokens=360,
                    evidence_refs=["adapter:openrouter", "snapshot:unavailable"],
                ),
            ],
        ),
        model_validation_envelopes=ModelValidationEnvelopeView(
            source="model-harness-runtime-validation-sample",
            envelopes=[
                ModelValidationEnvelopeItem(
                    envelope_id="validation:claude-direct-ready",
                    provider_id="claude",
                    exact_model_id="claude-sonnet-4-20250514",
                    dispatch_id="claude-sonnet-4-20250514",
                    route_kind="direct",
                    validation_state="allowed",
                    fail_closed_reason="none",
                    candidate_trust_state="trusted",
                    external_review_status="not_required",
                    proof_strength="strong",
                    prompt_budget_status="within_budget",
                    prompt_growth_state="flat",
                    prompt_budget_percent=23.0,
                    prompt_delta_tokens=0,
                    prompt_delta_percent=0.0,
                    route_proof_refs=["metadata:claude-direct", "snapshot:claude-payload"],
                    blocker_tags=[],
                    warning_tags=[],
                    evidence_refs=["validation:claude-direct-ready", "payload:dispatch-latest"],
                ),
                ModelValidationEnvelopeItem(
                    envelope_id="validation:deepseek-review-pending",
                    provider_id="deepseek",
                    exact_model_id="deepseek-chat",
                    dispatch_id="deepseek-chat",
                    route_kind="direct",
                    validation_state="fail_closed",
                    fail_closed_reason="external_review_required",
                    candidate_trust_state="candidate",
                    external_review_status="pending",
                    proof_strength="weak",
                    prompt_budget_status="watch",
                    prompt_growth_state="unexpected_growth",
                    prompt_budget_percent=72.0,
                    prompt_delta_tokens=240,
                    prompt_delta_percent=6.0,
                    route_proof_refs=["endpoint:https://api.deepseek.com/v1/chat/completions"],
                    blocker_tags=["external_review_required", "review_clearing_blocked"],
                    warning_tags=["prompt_growth_watch"],
                    evidence_refs=["adapter:deepseek", "validation:pending", "budget:deepseek-watch"],
                ),
                ModelValidationEnvelopeItem(
                    envelope_id="validation:openrouter-aggregator-blocked",
                    provider_id="openrouter",
                    exact_model_id="deepseek-chat",
                    dispatch_id="deepseek-chat",
                    route_kind="aggregator",
                    validation_state="fail_closed",
                    fail_closed_reason="blocked_authority",
                    candidate_trust_state="validation_blocked",
                    external_review_status="pending",
                    proof_strength="weak",
                    prompt_budget_status="near_limit",
                    prompt_growth_state="degraded",
                    prompt_budget_percent=88.9,
                    prompt_delta_tokens=360,
                    prompt_delta_percent=12.0,
                    route_proof_refs=["aggregator:openrouter", "direct-proof:unavailable"],
                    blocker_tags=["aggregator_without_proof", "payload_snapshot_missing"],
                    warning_tags=["aggregator_route_capped", "prompt_drag_degraded"],
                    evidence_refs=["adapter:openrouter", "snapshot:unavailable"],
                ),
            ],
        ),
        prompt_payload=PromptPayloadView(
            size_label="(under 1k)",
            estimated_tokens=920,
            prompt_budget_tokens=4000,
            context_budget_tokens=200000,
            budget_percent=23.0,
            delta_tokens=0,
            delta_percent=0.0,
            growth_state="flat",
            watch_state="ok",
            source="relay",
            provider_id="claude",
            model_name="claude-opus-4-7",
            trust_state="trusted",
            route_class="direct_api",
            route_kind="account-first",
            evidence_ref="payload-snapshot:dispatch-latest",
            telemetry_ref="telemetry:prompt-payload",
            adapter_metadata_ref="adapter:claude",
            warnings=[],
        ),
        dispatch_hardening=DispatchHardeningView(
            dispatch_id="dispatch-sample-001",
            provider_id="claude",
            exact_model_id="claude-opus-4-7",
            route_class="direct_api",
            route_kind="account-first",
            trust_state="trusted",
            proof_strength="strong",
            external_review_status="not_required",
            blocked_authorities=["branch_movement", "review_clearing"],
            payload_evidence_state="snapshot_present",
            fallback_blockers=[
                "silent_fallback_blocked",
                "aggregator_identity_required",
            ],
            dispatch_error_tags=[
                "fallback_not_authorized",
                "auto_routing_disabled",
            ],
        ),
        prompt_packet_proof=PromptPacketProofView(
            packet_id="prompt-packet-001",
            packet_hash="sha256:packet-proof-sample",
            source_lineage_compliance="compliant",
            prompt_budget_ref="budget:relay-dispatch-4000",
            aegis_evidence_ids=[
                "aegis:route-tier",
                "aegis:payload-proof",
            ],
            proof_requirement="tier2_payload_snapshot",
            snapshot_hash_gaps=[
                "response_payload_hash_pending",
            ],
            proof_state="warn",
            missing_metadata_warnings=[
                "completion_tokens_missing",
                "latency_ms_missing",
            ],
        ),
        aegis_prompt_packet_policy=AegisPromptPacketPolicyView(
            packet_id="prompt-packet-001",
            policy_id="aegis-policy-packet-001",
            decision="warn",
            human_gate_state="not_required",
            proof_requirement="tier2_payload_snapshot",
            aegis_evidence_ids=[
                "aegis:route-tier",
                "aegis:payload-proof",
            ],
            missing_fields=[
                "completion_tokens",
                "latency_ms",
            ],
            reason_tags=[
                "payload_snapshot_present",
                "response_hash_pending",
            ],
        ),
        relay_aegis_policy_handoff=relay_aegis_policy_handoff_from_summary(handoff_summary),
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
            preview_items=[
                ProofPreviewItem(
                    proof_id="queue-proof-pending",
                    label="Queue Proof",
                    state="pending",
                    owner="Session Lifecycle",
                    evidence_ref="queue:build-5",
                    summary="Awaiting next proof write after local tests",
                ),
                ProofPreviewItem(
                    proof_id="relay-proof-blocked",
                    label="Relay Route Proof",
                    state="blocked",
                    owner="Relay",
                    evidence_ref="route:auto-disabled",
                    summary="Auto routing remains blocked until checklist gates clear",
                ),
                ProofPreviewItem(
                    proof_id="cockpit-proof-passed",
                    label="Cockpit Render Proof",
                    state="passed",
                    owner="Bifrost",
                    evidence_ref="pytest:bifrost-cockpit",
                    summary="Static render tests passed for current preview",
                ),
                ProofPreviewItem(
                    proof_id="human-review-needed",
                    label="Human Review Gate",
                    state="needs-human-review",
                    owner="Aegis",
                    evidence_ref="review:codex",
                    summary="External review required before promotion",
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
        pressure_class = f"provider-pressure-{_e(provider.cost_pressure)}"
        credit_class = f"provider-credit-{_e(provider.credit_status)}"
        selected_attr = ' data-selected="true"' if provider.provider_id == balance.selected_provider else ""
        trust_label = f"[{_e(provider.trust_state)}]"
        provider_items.append(
            f'<div class="provider-item {status_class} {pressure_class} {credit_class}" data-provider="{_e(provider.provider_id)}"{selected_attr}>'
            f'<div class="provider-header">'
            f'<span class="provider-name">{_e(provider.display_name)}</span>'
            f'<span class="provider-trust">{trust_label}</span>'
            f'<span class="provider-model">{_e(provider.model_name)}</span>'
            f'<span class="provider-route">Route: {_e(provider.route_kind)}</span>'
            f"</div>"
            f'<div class="provider-metrics">'
            f'<span class="metric">Budget: {provider.prompt_budget_percent:.0f}%</span>'
            f'<span class="metric">Tokens: {provider.current_prompt_tokens}/{provider.prompt_budget_tokens}</span>'
            f'<span class="metric">Context: {provider.context_budget_tokens}</span>'
            f'<span class="metric">Delta: {provider.prompt_delta_tokens}</span>'
            f'<span class="metric">Pressure: {_e(provider.cost_pressure)}</span>'
            f'<span class="metric">Quota: {_e(provider.quota_state)}</span>'
            f'<span class="metric provider-credit-label">Remaining: {_e(provider.remaining_credit_label or provider.credit_status)}</span>'
            f'<span class="metric provider-spend">Spend: {_e(provider.estimated_spend_label or "unknown")}</span>'
            f"</div>"
            f'<span class="provider-notes">{_e(provider.notes)}</span>'
            f"</div>"
        )

    return (
        '<section class="provider-balance" aria-label="Provider Balance">'
        '<div class="provider-header-main">'
        '<h3>Provider Balance</h3>'
        f'<span class="routing-owner">{_e(balance.routing_owner)}</span>'
        f'<span class="selected-provider">Selected: {_e(balance.selected_provider or "none")}</span>'
        f'<span class="policy-state policy-{_e(balance.policy_state)}">{_e(balance.policy_state)}</span>'
        "</div>"
        '<div class="provider-items">'
        + "".join(provider_items)
        + "</div>"
        + "</section>"
    )


def _render_model_capabilities(metadata: ModelCapabilityMetadataView) -> str:
    if not metadata.items:
        return ""

    item_markup = []
    for item in metadata.items:
        selected_attr = ' data-selected="true"' if item.exact_model_id == metadata.selected_model_id else ""
        candidate_trust_state = item.candidate_trust_state or item.trust_state
        external_review_status = item.external_review_status or (
            "required" if item.external_review_required else "not_required"
        )
        allowed = "".join(
            f'<span class="capability-chip capability-allowed">{_e(hint)}</span>'
            for hint in item.allowed_task_hints
        ) or '<span class="capability-chip capability-empty">none</span>'
        blocked = "".join(
            f'<span class="capability-chip capability-blocked">{_e(hint)}</span>'
            for hint in item.blocked_task_hints
        ) or '<span class="capability-chip capability-empty">none</span>'
        blocked_authorities = "".join(
            f'<span class="capability-chip capability-authority">{_e(authority)}</span>'
            for authority in item.blocked_authorities
        ) or '<span class="capability-chip capability-empty">none</span>'
        evidence = "".join(
            f'<span class="capability-chip capability-evidence">{_e(ref)}</span>'
            for ref in item.evidence_refs
        ) or '<span class="capability-chip capability-empty">no_evidence_refs</span>'
        item_markup.append(
            f'<div class="model-capability-item capability-route-{_e(item.route_kind)} capability-trust-{_e(item.trust_state)}" data-model="{_e(item.exact_model_id)}" data-provider="{_e(item.provider_id)}"{selected_attr}>'
            '<div class="capability-header">'
            f'<span class="capability-provider">{_e(item.provider_id)}</span>'
            f'<span class="capability-model">Exact model: {_e(item.exact_model_id)}</span>'
            f'<span class="capability-route">Route: {_e(item.route_kind)}</span>'
            f'<span class="capability-trust">Trust: {_e(item.trust_state)}</span>'
            "</div>"
            '<div class="capability-badges" aria-label="Candidate Trust and External Review Badges">'
            f'<span class="capability-badge capability-candidate-{_e(candidate_trust_state)}">Candidate trust: {_e(candidate_trust_state)}</span>'
            f'<span class="capability-badge capability-review-{_e(external_review_status)}">External review status: {_e(external_review_status)}</span>'
            f'<span class="capability-badge capability-proof-{_e(item.proof_strength)}">Proof: {_e(item.proof_strength)}</span>'
            "</div>"
            '<div class="capability-grid">'
            f'<span>Context window: {item.context_window_tokens}</span>'
            f'<span>Cost posture: {_e(item.cost_posture)}</span>'
            f'<span>Latency: {_e(item.latency_tier)}</span>'
            f'<span>Tokenizer: {_e(item.tokenizer_family)}</span>'
            f'<span>Streaming: {"yes" if item.supports_streaming else "no"}</span>'
            f'<span>Q-mode flat: {"yes" if item.q_mode_flat else "no"}</span>'
            f'<span>External review: {"required" if item.external_review_required else "not_required"}</span>'
            f'<span>Prompt budget: {_e(item.prompt_budget_status)}</span>'
            f'<span>Prompt growth: {_e(item.prompt_growth_state)}</span>'
            f'<span>Prompt delta: {item.prompt_delta_tokens}</span>'
            "</div>"
            '<div class="capability-lists">'
            '<div class="capability-list capability-allowed-tasks" aria-label="Allowed Task Hints"><span class="capability-list-title">Allowed</span>'
            + allowed
            + "</div>"
            '<div class="capability-list capability-blocked-tasks" aria-label="Blocked Task Hints"><span class="capability-list-title">Blocked</span>'
            + blocked
            + "</div>"
            '<div class="capability-list capability-blocked-authorities" aria-label="Blocked Authorities"><span class="capability-list-title">Authorities</span>'
            + blocked_authorities
            + "</div>"
            '<div class="capability-list capability-evidence-refs" aria-label="Model Capability Evidence Refs"><span class="capability-list-title">Evidence</span>'
            + evidence
            + "</div>"
            + "</div>"
            + "</div>"
        )

    return (
        '<section class="model-capabilities" aria-label="Model Harness Capability Metadata">'
        '<div class="capability-header-main">'
        '<h3>Model Harness Capability Metadata</h3>'
        f'<span class="capability-source">Source: {_e(metadata.metadata_source)}</span>'
        f'<span class="capability-selected">Selected model: {_e(metadata.selected_model_id or "none")}</span>'
        "</div>"
        '<div class="model-capability-items">'
        + "".join(item_markup)
        + "</div>"
        + "</section>"
    )


def _render_model_validation_envelopes(validation: ModelValidationEnvelopeView) -> str:
    if not validation.envelopes:
        return ""

    envelope_markup = []
    for envelope in validation.envelopes:
        route_proofs = "".join(
            f'<span class="validation-chip validation-proof-ref">{_e(ref)}</span>'
            for ref in envelope.route_proof_refs
        ) or '<span class="validation-chip validation-empty">no_route_proof_refs</span>'
        blockers = "".join(
            f'<span class="validation-chip validation-blocker">{_e(tag)}</span>'
            for tag in envelope.blocker_tags
        ) or '<span class="validation-chip validation-empty">none</span>'
        warnings = "".join(
            f'<span class="validation-chip validation-warning">{_e(tag)}</span>'
            for tag in envelope.warning_tags
        ) or '<span class="validation-chip validation-empty">none</span>'
        evidence = "".join(
            f'<span class="validation-chip validation-evidence">{_e(ref)}</span>'
            for ref in envelope.evidence_refs
        ) or '<span class="validation-chip validation-empty">no_evidence_refs</span>'
        envelope_markup.append(
            f'<div class="validation-envelope validation-state-{_e(envelope.validation_state)}" data-envelope="{_e(envelope.envelope_id)}" data-model="{_e(envelope.exact_model_id)}" data-provider="{_e(envelope.provider_id)}">'
            '<div class="validation-envelope-header">'
            f'<span class="validation-envelope-id">{_e(envelope.envelope_id)}</span>'
            f'<span class="validation-state">Validation: {_e(envelope.validation_state)}</span>'
            f'<span class="validation-fail-reason">Fail closed: {_e(envelope.fail_closed_reason)}</span>'
            "</div>"
            '<div class="validation-badges" aria-label="Validation Envelope Candidate Trust Badges">'
            f'<span class="capability-badge capability-candidate-{_e(envelope.candidate_trust_state)}">Candidate trust: {_e(envelope.candidate_trust_state)}</span>'
            f'<span class="capability-badge capability-review-{_e(envelope.external_review_status)}">External review status: {_e(envelope.external_review_status)}</span>'
            f'<span class="capability-badge capability-proof-{_e(envelope.proof_strength)}">Proof: {_e(envelope.proof_strength)}</span>'
            "</div>"
            '<div class="validation-grid">'
            f'<span>Provider: {_e(envelope.provider_id)}</span>'
            f'<span>Exact model: {_e(envelope.exact_model_id)}</span>'
            f'<span>Dispatch id: {_e(envelope.dispatch_id)}</span>'
            f'<span>Route: {_e(envelope.route_kind)}</span>'
            f'<span>Prompt budget: {_e(envelope.prompt_budget_status)}</span>'
            f'<span>Prompt growth: {_e(envelope.prompt_growth_state)}</span>'
            f'<span>Budget percent: {envelope.prompt_budget_percent:.1f}%</span>'
            f'<span>Prompt delta: {envelope.prompt_delta_tokens}</span>'
            f'<span>Delta percent: {envelope.prompt_delta_percent:.1f}%</span>'
            "</div>"
            '<div class="validation-lists">'
            '<div class="validation-list validation-route-proofs" aria-label="Validation Envelope Route Proof Refs"><span class="validation-list-title">Route Proofs</span>'
            + route_proofs
            + "</div>"
            '<div class="validation-list validation-blockers" aria-label="Validation Envelope Blockers"><span class="validation-list-title">Blockers</span>'
            + blockers
            + "</div>"
            '<div class="validation-list validation-warnings" aria-label="Validation Envelope Warnings"><span class="validation-list-title">Warnings</span>'
            + warnings
            + "</div>"
            '<div class="validation-list validation-evidence-refs" aria-label="Validation Envelope Evidence Refs"><span class="validation-list-title">Evidence</span>'
            + evidence
            + "</div>"
            + "</div>"
            + "</div>"
        )

    return (
        '<section class="model-validation-envelopes" aria-label="Model Harness Runtime Validation Envelopes">'
        '<div class="validation-header-main">'
        '<h3>Runtime Validation Envelopes</h3>'
        f'<span class="validation-source">Source: {_e(validation.source)}</span>'
        "</div>"
        '<div class="validation-envelope-items">'
        + "".join(envelope_markup)
        + "</div>"
        + "</section>"
    )


def _render_prompt_payload(payload: PromptPayloadView) -> str:
    if not payload.size_label:
        return ""

    growth_class = f"payload-growth-{_e(payload.growth_state)}"
    watch_class = f"payload-watch-{_e(payload.watch_state)}"
    delta_display = f"+{payload.delta_tokens}" if payload.delta_tokens > 0 else f"{payload.delta_tokens}"
    warning_items = "".join(
        f'<span class="payload-warning" data-warning="{_e(warning)}">{_e(warning)}</span>'
        for warning in payload.warnings
    )

    return (
        '<section class="prompt-payload" aria-label="Prompt Payload Visibility">'
        '<div class="payload-header">'
        f'<span class="payload-size">{_e(payload.size_label)}</span>'
        f'<span class="payload-tokens">{payload.estimated_tokens} tokens</span>'
        f'<span class="payload-budget">{payload.budget_percent:.0f}% budget</span>'
        f'<span class="payload-prompt-budget">Prompt budget: {payload.prompt_budget_tokens} tokens</span>'
        f'<span class="payload-context-budget">Context budget: {payload.context_budget_tokens} tokens</span>'
        "</div>"
        f'<div class="payload-status {growth_class} {watch_class}" data-growth-state="{_e(payload.growth_state)}" data-watch-state="{_e(payload.watch_state)}">'
        f'<span class="status-indicator">{_e(payload.growth_state)}</span>'
        f'<span class="watch-indicator">{_e(payload.watch_state)}</span>'
        f'<span class="delta">Delta: {delta_display} tokens / {payload.delta_percent:.1f}%</span>'
        f'<span class="source">From: {_e(payload.source)}</span>'
        f"</div>"
        '<div class="payload-route-context">'
        f'<span class="payload-provider">Provider: {_e(payload.provider_id)}</span>'
        f'<span class="payload-model">Model: {_e(payload.model_name)}</span>'
        f'<span class="payload-trust">Trust: {_e(payload.trust_state)}</span>'
        f'<span class="payload-route-class">Route class: {_e(payload.route_class)}</span>'
        f'<span class="payload-route-kind">Route kind: {_e(payload.route_kind)}</span>'
        "</div>"
        '<div class="payload-evidence">'
        f'<span class="payload-evidence-ref">Evidence: {_e(payload.evidence_ref)}</span>'
        f'<span class="payload-telemetry-ref">Telemetry: {_e(payload.telemetry_ref)}</span>'
        f'<span class="payload-adapter-ref">Adapter: {_e(payload.adapter_metadata_ref)}</span>'
        f'<span class="payload-warnings">{warning_items}</span>'
        "</div>"
        + "</section>"
    )


def _render_dispatch_hardening(dispatch: DispatchHardeningView) -> str:
    if not dispatch.dispatch_id:
        return ""

    blocked_authorities = "".join(
        f'<span class="dispatch-chip dispatch-authority">{_e(authority)}</span>'
        for authority in dispatch.blocked_authorities
    )
    fallback_blockers = "".join(
        f'<span class="dispatch-chip dispatch-fallback-blocker">{_e(blocker)}</span>'
        for blocker in dispatch.fallback_blockers
    )
    error_tags = "".join(
        f'<span class="dispatch-chip dispatch-error-tag">{_e(tag)}</span>'
        for tag in dispatch.dispatch_error_tags
    )

    return (
        '<section class="dispatch-hardening" aria-label="Dispatch Hardening State">'
        '<div class="dispatch-header-main">'
        '<h3>Dispatch Hardening</h3>'
        f'<span class="dispatch-id">{_e(dispatch.dispatch_id)}</span>'
        f'<span class="dispatch-trust dispatch-trust-{_e(dispatch.trust_state)}">{_e(dispatch.trust_state)}</span>'
        "</div>"
        '<div class="dispatch-route-grid">'
        f'<span class="dispatch-field dispatch-provider">Provider: {_e(dispatch.provider_id)}</span>'
        f'<span class="dispatch-field dispatch-model">Exact model: {_e(dispatch.exact_model_id)}</span>'
        f'<span class="dispatch-field dispatch-route-class">Route class: {_e(dispatch.route_class)}</span>'
        f'<span class="dispatch-field dispatch-route-kind">Route kind: {_e(dispatch.route_kind)}</span>'
        f'<span class="dispatch-field dispatch-proof-strength">Proof strength: {_e(dispatch.proof_strength)}</span>'
        f'<span class="dispatch-field dispatch-external-review">External review: {_e(dispatch.external_review_status)}</span>'
        f'<span class="dispatch-field dispatch-payload-evidence">Payload evidence: {_e(dispatch.payload_evidence_state)}</span>'
        "</div>"
        '<div class="dispatch-hardening-lists">'
        '<div class="dispatch-list dispatch-blocked-authorities" aria-label="Blocked Authorities">'
        '<span class="dispatch-list-title">Blocked authorities</span>'
        + blocked_authorities
        + "</div>"
        '<div class="dispatch-list dispatch-fallback-blockers" aria-label="Fallback Blockers">'
        '<span class="dispatch-list-title">Fallback blockers</span>'
        + fallback_blockers
        + "</div>"
        '<div class="dispatch-list dispatch-error-tags" aria-label="Dispatch Error Tags">'
        '<span class="dispatch-list-title">Dispatch error tags</span>'
        + error_tags
        + "</div>"
        + "</div>"
        + "</section>"
    )


def _render_prompt_packet_proof(packet: PromptPacketProofView) -> str:
    if not packet.packet_id:
        return ""

    evidence_items = "".join(
        f'<span class="packet-chip packet-evidence">{_e(evidence_id)}</span>'
        for evidence_id in packet.aegis_evidence_ids
    )
    gap_items = "".join(
        f'<span class="packet-chip packet-gap">{_e(gap)}</span>'
        for gap in packet.snapshot_hash_gaps
    )
    warning_items = "".join(
        f'<span class="packet-chip packet-warning">{_e(warning)}</span>'
        for warning in packet.missing_metadata_warnings
    )

    return (
        '<section class="prompt-packet-proof" aria-label="PromptPacket Proof Metadata">'
        '<div class="packet-header-main">'
        '<h3>PromptPacket Proof</h3>'
        f'<span class="packet-id">{_e(packet.packet_id)}</span>'
        f'<span class="packet-state packet-state-{_e(packet.proof_state)}">{_e(packet.proof_state)}</span>'
        "</div>"
        '<div class="packet-proof-grid">'
        f'<span class="packet-field packet-hash">Packet hash: {_e(packet.packet_hash)}</span>'
        f'<span class="packet-field packet-lineage">Source lineage: {_e(packet.source_lineage_compliance)}</span>'
        f'<span class="packet-field packet-budget-ref">Prompt budget ref: {_e(packet.prompt_budget_ref)}</span>'
        f'<span class="packet-field packet-requirement">Proof requirement: {_e(packet.proof_requirement)}</span>'
        "</div>"
        '<div class="packet-proof-lists">'
        '<div class="packet-list packet-aegis-evidence" aria-label="Aegis Evidence IDs">'
        '<span class="packet-list-title">Aegis evidence IDs</span>'
        + evidence_items
        + "</div>"
        '<div class="packet-list packet-snapshot-gaps" aria-label="Snapshot Hash Gaps">'
        '<span class="packet-list-title">Snapshot/hash gaps</span>'
        + gap_items
        + "</div>"
        '<div class="packet-list packet-metadata-warnings" aria-label="Missing Metadata Warnings">'
        '<span class="packet-list-title">Missing metadata warnings</span>'
        + warning_items
        + "</div>"
        + "</div>"
        + "</section>"
    )


def _render_aegis_prompt_packet_policy(policy: AegisPromptPacketPolicyView) -> str:
    if not policy.packet_id:
        return ""

    policy_id = policy.policy_id or "policy_id_missing"
    proof_requirement = policy.proof_requirement or "proof_requirement_missing"
    human_gate_state = policy.human_gate_state or "unknown"
    evidence_items = "".join(
        f'<span class="aegis-policy-chip aegis-policy-evidence">{_e(evidence_id)}</span>'
        for evidence_id in policy.aegis_evidence_ids
    ) or '<span class="aegis-policy-chip aegis-policy-empty">no_evidence_ids</span>'
    missing_items = "".join(
        f'<span class="aegis-policy-chip aegis-policy-missing-field">{_e(field_name)}</span>'
        for field_name in policy.missing_fields
    ) or '<span class="aegis-policy-chip aegis-policy-empty">no_missing_fields</span>'
    reason_items = "".join(
        f'<span class="aegis-policy-chip aegis-policy-reason">{_e(reason_tag)}</span>'
        for reason_tag in policy.reason_tags
    ) or '<span class="aegis-policy-chip aegis-policy-empty">no_reason_tags</span>'

    return (
        '<section class="aegis-packet-policy" aria-label="Aegis PromptPacket Policy Decision">'
        '<div class="aegis-policy-header-main">'
        '<h3>Aegis PromptPacket Policy</h3>'
        f'<span class="aegis-policy-id">{_e(policy_id)}</span>'
        f'<span class="aegis-policy-decision aegis-policy-decision-{_e(policy.decision)}">{_e(policy.decision)}</span>'
        "</div>"
        '<div class="aegis-policy-grid">'
        f'<span class="aegis-policy-field aegis-policy-packet-id">Packet id: {_e(policy.packet_id)}</span>'
        f'<span class="aegis-policy-field aegis-policy-human-gate aegis-policy-human-gate-{_e(human_gate_state)}">Human gate: {_e(human_gate_state)}</span>'
        f'<span class="aegis-policy-field aegis-policy-requirement">Proof requirement: {_e(proof_requirement)}</span>'
        "</div>"
        '<div class="aegis-policy-lists">'
        '<div class="aegis-policy-list aegis-policy-evidence-ids" aria-label="Aegis Policy Evidence IDs">'
        '<span class="aegis-policy-list-title">Evidence IDs</span>'
        + evidence_items
        + "</div>"
        '<div class="aegis-policy-list aegis-policy-missing-fields" aria-label="Aegis Policy Missing Fields">'
        '<span class="aegis-policy-list-title">Missing fields</span>'
        + missing_items
        + "</div>"
        '<div class="aegis-policy-list aegis-policy-reason-tags" aria-label="Aegis Policy Reason Tags">'
        '<span class="aegis-policy-list-title">Reason tags</span>'
        + reason_items
        + "</div>"
        + "</div>"
        + "</section>"
    )


def _safe_handoff_value(value: object) -> str:
    text = str(value)
    lowered = text.lower()
    unsafe_markers = (
        "raw_prompt",
        "serialized_prompt",
        "model_payload",
        "secret",
        "api_key",
        "bearer ",
        "authorization",
        "provider_request",
        "raw_provider_response",
        "process_id",
    )
    if any(marker in lowered for marker in unsafe_markers):
        return "unsafe_metadata_redacted"
    return text


def _handoff_summary_value(
    summary: Mapping[str, object],
    *keys: str,
    default: object = "",
) -> object:
    for key in keys:
        value = summary.get(key)
        if value is not None and value != "":
            return value
    return default


def _handoff_summary_bool(summary: Mapping[str, object], *keys: str) -> bool:
    value = _handoff_summary_value(summary, *keys, default=False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "blocked", "fail_closed"}
    return bool(value)


def _handoff_summary_list(summary: Mapping[str, object], *keys: str) -> list[str]:
    value = _handoff_summary_value(summary, *keys, default=())
    if value is None or value == "":
        return []
    if isinstance(value, Mapping):
        return [_safe_handoff_value(key) for key in sorted(value.keys(), key=str)]
    if isinstance(value, set):
        return [_safe_handoff_value(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [_safe_handoff_value(item) for item in value]
    return [_safe_handoff_value(value)]


def relay_aegis_policy_handoff_from_summary(
    summary: Mapping[str, object],
) -> RelayAegisPolicyHandoffView:
    """Build Bifrost's display view from a structured Relay/Aegis handoff summary."""
    fail_closed = _handoff_summary_bool(
        summary,
        "missing_metadata_fail_closed",
        "fail_closed",
        "metadata_fail_closed",
    )
    decision_default = "block" if fail_closed else "unknown"
    severity_default = "error" if fail_closed else "info"
    return RelayAegisPolicyHandoffView(
        decision=_safe_handoff_value(_handoff_summary_value(
            summary,
            "decision",
            "aegis_gate_decision",
            default=decision_default,
        )),
        severity=_safe_handoff_value(_handoff_summary_value(
            summary,
            "severity",
            "aegis_gate_severity",
            default=severity_default,
        )),
        packet_id=_safe_handoff_value(_handoff_summary_value(
            summary,
            "packet_id",
            "packet_id_ref",
            default="packet_id_missing",
        )),
        packet_hash_status=_safe_handoff_value(_handoff_summary_value(
            summary,
            "packet_hash_status",
            "packet_hash_ref",
            default="unknown",
        )),
        proof_requirement=_safe_handoff_value(_handoff_summary_value(
            summary,
            "proof_requirement",
            default="proof_requirement_missing",
        )),
        aegis_evidence_ids=_handoff_summary_list(
            summary,
            "aegis_evidence_ids",
            "evidence_ids",
        ),
        blockers=_handoff_summary_list(
            summary,
            "blockers",
            "fallback_blockers",
        ),
        warnings=_handoff_summary_list(
            summary,
            "warnings",
            "warning_tags",
            "policy_warning_tags",
        ),
        demotion_target=_safe_handoff_value(_handoff_summary_value(
            summary,
            "demotion_target",
            "demotion_target_tier",
            "demotion_route",
            default="not_applicable",
        )),
        human_gate_state=_safe_handoff_value(_handoff_summary_value(
            summary,
            "human_gate_state",
            default="unknown" if fail_closed else "not_required",
        )),
        missing_metadata_fail_closed=fail_closed,
        missing_metadata_fields=_handoff_summary_list(
            summary,
            "missing_metadata_fields",
            "missing_fields",
        ),
        explanation=_safe_handoff_value(_handoff_summary_value(
            summary,
            "explanation",
            "aegis_explanation",
            default="",
        )),
    )


def _render_relay_aegis_policy_handoff(handoff: RelayAegisPolicyHandoffView) -> str:
    if not handoff.decision:
        return ""

    packet_id = _safe_handoff_value(handoff.packet_id or "packet_id_missing")
    packet_hash_status = _safe_handoff_value(handoff.packet_hash_status or "unknown")
    proof_requirement = _safe_handoff_value(handoff.proof_requirement or "proof_requirement_missing")
    human_gate_state = _safe_handoff_value(handoff.human_gate_state or "unknown")
    demotion_target = _safe_handoff_value(handoff.demotion_target or "not_applicable")
    fail_closed = "yes" if handoff.missing_metadata_fail_closed else "no"
    evidence_items = "".join(
        f'<span class="handoff-chip handoff-evidence">{_e(_safe_handoff_value(evidence_id))}</span>'
        for evidence_id in handoff.aegis_evidence_ids
    ) or '<span class="handoff-chip handoff-empty">no_evidence_ids</span>'
    blocker_items = "".join(
        f'<span class="handoff-chip handoff-blocker">{_e(_safe_handoff_value(blocker))}</span>'
        for blocker in handoff.blockers
    ) or '<span class="handoff-chip handoff-empty">no_blockers</span>'
    warning_items = "".join(
        f'<span class="handoff-chip handoff-warning">{_e(_safe_handoff_value(warning))}</span>'
        for warning in handoff.warnings
    ) or '<span class="handoff-chip handoff-empty">no_warnings</span>'
    missing_metadata_items = "".join(
        f'<span class="handoff-chip handoff-missing-metadata">{_e(_safe_handoff_value(field_name))}</span>'
        for field_name in handoff.missing_metadata_fields
    ) or '<span class="handoff-chip handoff-empty">no_missing_metadata_fields</span>'

    return (
        '<section class="relay-aegis-handoff" aria-label="Relay Aegis Policy Handoff Summary">'
        '<div class="handoff-header-main">'
        '<h3>Relay/Aegis Handoff</h3>'
        f'<span class="handoff-severity handoff-severity-{_e(handoff.severity)}">{_e(_safe_handoff_value(handoff.severity))}</span>'
        f'<span class="handoff-decision handoff-decision-{_e(handoff.decision)}">{_e(_safe_handoff_value(handoff.decision))}</span>'
        "</div>"
        '<div class="handoff-grid">'
        f'<span class="handoff-field handoff-packet-id">Packet id: {_e(packet_id)}</span>'
        f'<span class="handoff-field handoff-packet-hash">Packet hash status: {_e(packet_hash_status)}</span>'
        f'<span class="handoff-field handoff-requirement">Proof requirement: {_e(proof_requirement)}</span>'
        f'<span class="handoff-field handoff-demotion-target">Demotion target: {_e(demotion_target)}</span>'
        f'<span class="handoff-field handoff-human-gate handoff-human-gate-{_e(human_gate_state)}">Human gate: {_e(human_gate_state)}</span>'
        f'<span class="handoff-field handoff-fail-closed">Missing metadata fail closed: {fail_closed}</span>'
        f'<span class="handoff-field handoff-explanation">Explanation: {_e(_safe_handoff_value(handoff.explanation))}</span>'
        "</div>"
        '<div class="handoff-lists">'
        '<div class="handoff-list handoff-evidence-ids" aria-label="Relay Aegis Handoff Evidence IDs">'
        '<span class="handoff-list-title">Evidence IDs</span>'
        + evidence_items
        + "</div>"
        '<div class="handoff-list handoff-blockers" aria-label="Relay Aegis Handoff Blockers">'
        '<span class="handoff-list-title">Blockers</span>'
        + blocker_items
        + "</div>"
        '<div class="handoff-list handoff-warnings" aria-label="Relay Aegis Handoff Warnings">'
        '<span class="handoff-list-title">Warnings</span>'
        + warning_items
        + "</div>"
        '<div class="handoff-list handoff-missing-metadata-fields" aria-label="Relay Aegis Missing Metadata Fields">'
        '<span class="handoff-list-title">Missing metadata</span>'
        + missing_metadata_items
        + "</div>"
        + "</div>"
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

    preview_items = []
    for item in proof.preview_items:
        state_class = f"proof-preview-{_e(item.state)}"
        preview_items.append(
            f'<div class="proof-preview-item {state_class}" data-proof-id="{_e(item.proof_id)}" data-proof-state="{_e(item.state)}">'
            f'<span class="proof-preview-label">{_e(item.label)}</span>'
            f'<span class="proof-preview-state">{_e(item.state)}</span>'
            f'<span class="proof-preview-owner">{_e(item.owner)}</span>'
            f'<span class="proof-preview-evidence">{_e(item.evidence_ref)}</span>'
            f'<span class="proof-preview-summary">{_e(item.summary)}</span>'
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
            '<div class="proof-preview-list" aria-label="Proof State Preview">'
            + "".join(preview_items)
            + "</div>"
            if preview_items
            else ""
        )
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

    # Filter to open sessions only (exclude blocked and done)
    open_statuses = {"live", "hidden", "waiting"}
    open_sessions = [s for s in mode.sessions if s.status in open_statuses]

    if not open_sessions:
        return ""

    # Group sessions by project, sorting projects and sessions alphabetically
    sessions_by_project: dict[str, list[SessionItem]] = {}
    for session in open_sessions:
        if session.project_name not in sessions_by_project:
            sessions_by_project[session.project_name] = []
        sessions_by_project[session.project_name].append(session)

    # Sort projects alphabetically, sort sessions within each project alphabetically
    sorted_projects = sorted(sessions_by_project.keys())
    for project in sessions_by_project:
        sessions_by_project[project].sort(key=lambda s: s.session_name)

    # Find currently selected session for title display and routing target
    selected_session_name = ""
    selected_session_id = ""
    selected_session_is_stale = False

    # Check if selected session is in the open sessions (available)
    for session in open_sessions:
        if session.session_id == mode.selected_session_id:
            selected_session_name = session.session_name
            selected_session_id = session.session_id
            break

    # If selected_session_id doesn't match any open session, it's stale
    if mode.selected_session_id and not selected_session_id:
        selected_session_id = mode.selected_session_id
        selected_session_is_stale = True
        # Try to find the session in all sessions to get its name
        for session in mode.sessions:
            if session.session_id == mode.selected_session_id:
                selected_session_name = session.session_name
                break
        if not selected_session_name:
            selected_session_name = mode.selected_session_id

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

    # Build routing target state indicator or stale-target guard
    routing_target_html = ""
    if selected_session_id:
        if selected_session_is_stale:
            recovery_actions = (
                (
                    "restart-session",
                    "restart",
                    "Restart session",
                    "Ask coordinator to restart the stale workflow from its last safe checkpoint.",
                    "evidence:session-restart-request",
                ),
                (
                    "resteer-session",
                    "resteer",
                    "Resteer session",
                    "Route recovery through Prime with the stale target and blocker summary visible.",
                    "evidence:prime-resteer-required",
                ),
                (
                    "archive-session",
                    "archive",
                    "Archive stale session",
                    "Preserve the stale context as archive-only without closing or deleting live work.",
                    "evidence:archive-context-preserved",
                ),
                (
                    "poll-watch-session",
                    "poll_watch",
                    "Poll/watch",
                    "Keep watching for lifecycle recovery before any prompt routing resumes.",
                    "evidence:lifecycle-watch-only",
                ),
                (
                    "human-gated-blocked",
                    "human_gate_blocked",
                    "Human gate blocked",
                    "Block automated recovery until Scott or a review lane clears the gate.",
                    "evidence:human-gate-required",
                ),
            )
            recovery_action_markup = "".join(
                '<button type="button" class="recovery-action"'
                f' data-recovery-action="{_e(action_id)}"'
                f' data-recovery-state="{_e(state)}"'
                f' data-evidence-ref="{_e(evidence_ref)}">'
                f'<span class="recovery-action-label">{_e(label)}</span>'
                f'<span class="recovery-action-summary">{_e(summary)}</span>'
                f'<span class="recovery-action-evidence">{_e(evidence_ref)}</span>'
                "</button>"
                for action_id, state, label, summary, evidence_ref in recovery_actions
            )
            # Show stale-target guard warning
            routing_target_html = (
                f'<div class="stale-target-guard" data-stale-session-id="{_e(selected_session_id)}">'
                f'<span class="stale-warning">⚠ Target unavailable: {_e(selected_session_name)}</span>'
                f'<span class="stale-message">Session is closed, blocked, or no longer routable. Prompts will not be sent.</span>'
                '<div class="stale-recovery-actions" aria-label="Stale session recovery actions">'
                + recovery_action_markup
                + "</div>"
                + "</div>"
            )
        else:
            # Show normal routing target state
            routing_target_html = (
                f'<div class="routing-target-state" data-target-session-id="{_e(selected_session_id)}">'
                f'<span class="routing-label">Next prompt target: {_e(selected_session_name)}</span>'
                "</div>"
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
        f'{routing_target_html}'
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
    model_capabilities = _render_model_capabilities(vm.model_capabilities)
    model_validation_envelopes = _render_model_validation_envelopes(vm.model_validation_envelopes)
    prompt_payload = _render_prompt_payload(vm.prompt_payload)
    dispatch_hardening = _render_dispatch_hardening(vm.dispatch_hardening)
    prompt_packet_proof = _render_prompt_packet_proof(vm.prompt_packet_proof)
    aegis_packet_policy = _render_aegis_prompt_packet_policy(vm.aegis_prompt_packet_policy)
    relay_aegis_handoff = _render_relay_aegis_policy_handoff(vm.relay_aegis_policy_handoff)
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
        f"{dispatch_hardening}\n"
        f"{prompt_packet_proof}\n"
        f"{aegis_packet_policy}\n"
        f"{relay_aegis_handoff}\n"
        f"{provider_balance}\n"
        f"{model_capabilities}\n"
        f"{model_validation_envelopes}\n"
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
