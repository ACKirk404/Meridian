"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from .aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    PromptPacketProofDecision,
    PromptPacketProofMetadata as AegisPromptPacketProofMetadata,
    PromptPacketProofPolicyResult,
    ProofTrail,
    evaluate_prompt_packet_proof_policy,
)
from .cognition_policy import evaluate_cognition_policy
from .model_adapter import (
    AdapterRegistry,
    MissingAdapterError,
    ModelAdapter,
    ModelHarnessMetadata,
    ModelRouteMetadataBinding,
    bind_model_route_metadata,
)
from .prompt_payload_meter import PromptPayloadSnapshot
from .relay import ModelRole
from .relay_dispatch import RelayDispatchPlan


ModelCallFn = ModelAdapter


@dataclass(frozen=True)
class RelayPromptPayloadEvidence:
    """Structured prompt payload evidence captured before the model-call boundary.

    This record carries only sizing, route, and telemetry capability facts. It never
    stores raw prompt text, credentials, raw model responses, or transcripts.
    """

    prompt_source: str = "relay"
    heartbeat_id: str | None = None
    route_id: str | None = None
    project: str | None = None
    lane_id: str | None = None
    selected_provider: str | None = None
    selected_model: str | None = None
    capability_tier: str | None = None
    route_class: str | None = None
    route_kind: str | None = None
    provider_route_kind: str = "unknown"
    trust_state: str = "unknown"
    requires_external_review: bool = False
    external_review_status: str = "not_required"
    model_metadata_ref: str | None = None
    external_review_evidence_ref: str | None = None
    estimated_prompt_tokens: int | None = None
    prompt_budget_tokens: int | None = None
    model_context_window_tokens: int | None = None
    max_output_tokens: int | None = None
    remaining_context_tokens: int | None = None
    budget_percent: float | None = None
    budget_status: str = "unknown"
    budget_compliant: bool | None = None
    over_budget_reason: str | None = None
    previous_prompt_tokens: int | None = None
    delta_tokens: int | None = None
    delta_percent: float | None = None
    comparison_scope: str = "dispatch"
    growth_state: str = "unknown"
    prompt_drag_tags: tuple[str, ...] = ()
    expected_growth_reason: str | None = None
    prompt_payload_snapshot_hash: str | None = None
    response_payload_snapshot_hash: str | None = None
    adapter_supports_snapshot: bool = False
    supports_completion_tokens: bool = False
    supports_latency_ms: bool = False
    supports_payload_snapshot: bool = False
    supports_response_hash: bool = False
    tokenizer_family: str = "unknown"
    telemetry_error_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a stable serializable shape for downstream evidence handoff."""
        return {
            "prompt_source": self.prompt_source,
            "heartbeat_id": self.heartbeat_id,
            "route_id": self.route_id,
            "project": self.project,
            "lane_id": self.lane_id,
            "selected_provider": self.selected_provider,
            "selected_model": self.selected_model,
            "capability_tier": self.capability_tier,
            "route_class": self.route_class,
            "route_kind": self.route_kind,
            "provider_route_kind": self.provider_route_kind,
            "trust_state": self.trust_state,
            "requires_external_review": self.requires_external_review,
            "external_review_status": self.external_review_status,
            "model_metadata_ref": self.model_metadata_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "prompt_budget_tokens": self.prompt_budget_tokens,
            "model_context_window_tokens": self.model_context_window_tokens,
            "max_output_tokens": self.max_output_tokens,
            "remaining_context_tokens": self.remaining_context_tokens,
            "budget_percent": self.budget_percent,
            "budget_status": self.budget_status,
            "budget_compliant": self.budget_compliant,
            "over_budget_reason": self.over_budget_reason,
            "previous_prompt_tokens": self.previous_prompt_tokens,
            "delta_tokens": self.delta_tokens,
            "delta_percent": self.delta_percent,
            "comparison_scope": self.comparison_scope,
            "growth_state": self.growth_state,
            "prompt_drag_tags": self.prompt_drag_tags,
            "expected_growth_reason": self.expected_growth_reason,
            "prompt_payload_snapshot_hash": self.prompt_payload_snapshot_hash,
            "response_payload_snapshot_hash": self.response_payload_snapshot_hash,
            "adapter_supports_snapshot": self.adapter_supports_snapshot,
            "supports_completion_tokens": self.supports_completion_tokens,
            "supports_latency_ms": self.supports_latency_ms,
            "supports_payload_snapshot": self.supports_payload_snapshot,
            "supports_response_hash": self.supports_response_hash,
            "tokenizer_family": self.tokenizer_family,
            "telemetry_error_tags": self.telemetry_error_tags,
        }


@dataclass(frozen=True)
class RelayPromptPayloadMeterEvidence:
    """Display-safe visible prompt payload meter data for Relay lanes."""

    meter_evidence_id: str
    heartbeat_id: str | None = None
    lane_id: str | None = None
    route_id: str | None = None
    selected_provider: str | None = None
    exact_model_id: str | None = None
    provider_route_kind: str = "unknown"
    trust_state: str = "unknown"
    capability_tier: str | None = None
    display_label: str = "(unknown)"
    estimated_prompt_tokens: int | None = None
    prompt_budget_tokens: int | None = None
    budget_percent: float | None = None
    payload_status: str = "unknown"
    growth_delta_tokens: int | None = None
    growth_delta_percent: float | None = None
    q_mode: bool = False
    growth_state: str = "unknown"
    prompt_drag_tags: tuple[str, ...] = ()
    warning_tags: tuple[str, ...] = ()
    blocker_tags: tuple[str, ...] = ()
    payload_evidence_ref: str | None = None
    prompt_payload_snapshot_hash: str | None = None
    model_metadata_ref: str | None = None
    external_review_evidence_ref: str | None = None
    serialization_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return stable meter data without prompt text or provider responses."""
        return {
            "meter_evidence_id": self.meter_evidence_id,
            "heartbeat_id": self.heartbeat_id,
            "lane_id": self.lane_id,
            "route_id": self.route_id,
            "selected_provider": self.selected_provider,
            "exact_model_id": self.exact_model_id,
            "provider_route_kind": self.provider_route_kind,
            "trust_state": self.trust_state,
            "capability_tier": self.capability_tier,
            "display_label": self.display_label,
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "prompt_budget_tokens": self.prompt_budget_tokens,
            "budget_percent": self.budget_percent,
            "payload_status": self.payload_status,
            "growth_delta_tokens": self.growth_delta_tokens,
            "growth_delta_percent": self.growth_delta_percent,
            "q_mode": self.q_mode,
            "growth_state": self.growth_state,
            "prompt_drag_tags": self.prompt_drag_tags,
            "warning_tags": self.warning_tags,
            "blocker_tags": self.blocker_tags,
            "payload_evidence_ref": self.payload_evidence_ref,
            "prompt_payload_snapshot_hash": self.prompt_payload_snapshot_hash,
            "model_metadata_ref": self.model_metadata_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "serialization_only": self.serialization_only,
        }


@dataclass(frozen=True)
class RelayDispatchEnvelope:
    """Safe audit envelope built before dispatch without raw transport payloads."""

    envelope_id: str
    heartbeat_id: str
    role: str | None = None
    requested_model_id: str | None = None
    exact_model_id: str | None = None
    selected_provider: str | None = None
    route_id: str | None = None
    route_class: str | None = None
    route_kind: str | None = None
    risk_tier: int = 0
    trust_state: str = "unknown"
    capability_tier: str | None = None
    payload_evidence_ref: str | None = None
    payload_snapshot_hash: str | None = None
    packet_hash: str | None = None
    prompt_budget_ref: str | None = None
    source_lineage_compliant: bool | None = None
    packet_proof_metadata_ref: str | None = None
    aegis_gate_decision: str | None = None
    aegis_evidence_ids: tuple[str, ...] = ()
    proof_required: tuple[str, ...] = ()
    human_gate_required: bool = False
    blocked_error_tags: tuple[str, ...] = ()
    safe_to_dispatch: bool = False
    transport_payload_kind: str = "approved_prompt_text"
    audit_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic serializable envelope for audit handoff."""
        return {
            "envelope_id": self.envelope_id,
            "heartbeat_id": self.heartbeat_id,
            "role": self.role,
            "requested_model_id": self.requested_model_id,
            "exact_model_id": self.exact_model_id,
            "selected_provider": self.selected_provider,
            "route_id": self.route_id,
            "route_class": self.route_class,
            "route_kind": self.route_kind,
            "risk_tier": self.risk_tier,
            "trust_state": self.trust_state,
            "capability_tier": self.capability_tier,
            "payload_evidence_ref": self.payload_evidence_ref,
            "payload_snapshot_hash": self.payload_snapshot_hash,
            "packet_hash": self.packet_hash,
            "prompt_budget_ref": self.prompt_budget_ref,
            "source_lineage_compliant": self.source_lineage_compliant,
            "packet_proof_metadata_ref": self.packet_proof_metadata_ref,
            "aegis_gate_decision": self.aegis_gate_decision,
            "aegis_evidence_ids": self.aegis_evidence_ids,
            "proof_required": self.proof_required,
            "human_gate_required": self.human_gate_required,
            "blocked_error_tags": self.blocked_error_tags,
            "safe_to_dispatch": self.safe_to_dispatch,
            "transport_payload_kind": self.transport_payload_kind,
            "audit_fields": self.audit_fields,
        }


@dataclass(frozen=True)
class RelayDispatchMetadataEnvelope:
    """Provider-neutral metadata envelope for future transport binding."""

    envelope_id: str
    heartbeat_id: str
    lane_id: str | None = None
    role: str | None = None
    requested_model_id: str | None = None
    exact_model_id: str | None = None
    selected_provider: str | None = None
    provider_route_kind: str = "unknown"
    trust_mode: str = "unknown"
    trust_state: str = "unknown"
    proof_strength: str = "unknown"
    capability_tier: str | None = None
    direct_endpoint_evidence_ref: str | None = None
    aggregator_evidence_ref: str | None = None
    validation_evidence_ref: str | None = None
    allowed_task_types: tuple[str, ...] = ()
    blocked_task_types: tuple[str, ...] = ()
    blocked_authority_tags: tuple[str, ...] = ()
    max_risk_tier: int | None = None
    context_window_tokens: int | None = None
    prompt_payload_budget_tokens: int | None = None
    prompt_payload_status: str = "unknown"
    estimated_prompt_tokens: int | None = None
    prompt_budget_percent: float | None = None
    prompt_growth_tokens: int | None = None
    prompt_growth_percent: float | None = None
    growth_state: str = "unknown"
    prompt_drag_tags: tuple[str, ...] = ()
    requires_external_review: bool = False
    external_review_status: str = "not_required"
    model_metadata_ref: str | None = None
    external_review_evidence_ref: str | None = None
    payload_evidence_ref: str | None = None
    payload_snapshot_hash: str | None = None
    dispatch_envelope_ref: str | None = None
    packet_proof_metadata_ref: str | None = None
    supports_completion_tokens: bool = False
    supports_latency_ms: bool = False
    supports_payload_snapshot: bool = False
    supports_response_hash: bool = False
    validation_tags: tuple[str, ...] = ()
    fail_closed_advisory: bool = False
    fail_closed_tags: tuple[str, ...] = ()
    metadata_transport_allowed: bool = False
    retry_requires_fresh_metadata: bool = False
    transport_payload_kind: str = "metadata_only"
    serialization_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return stable display-safe metadata for future provider transport handoff."""
        return {
            "envelope_id": self.envelope_id,
            "heartbeat_id": self.heartbeat_id,
            "lane_id": self.lane_id,
            "role": self.role,
            "requested_model_id": self.requested_model_id,
            "exact_model_id": self.exact_model_id,
            "selected_provider": self.selected_provider,
            "provider_route_kind": self.provider_route_kind,
            "trust_mode": self.trust_mode,
            "trust_state": self.trust_state,
            "proof_strength": self.proof_strength,
            "capability_tier": self.capability_tier,
            "direct_endpoint_evidence_ref": self.direct_endpoint_evidence_ref,
            "aggregator_evidence_ref": self.aggregator_evidence_ref,
            "validation_evidence_ref": self.validation_evidence_ref,
            "allowed_task_types": self.allowed_task_types,
            "blocked_task_types": self.blocked_task_types,
            "blocked_authority_tags": self.blocked_authority_tags,
            "max_risk_tier": self.max_risk_tier,
            "context_window_tokens": self.context_window_tokens,
            "prompt_payload_budget_tokens": self.prompt_payload_budget_tokens,
            "prompt_payload_status": self.prompt_payload_status,
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "prompt_budget_percent": self.prompt_budget_percent,
            "prompt_growth_tokens": self.prompt_growth_tokens,
            "prompt_growth_percent": self.prompt_growth_percent,
            "growth_state": self.growth_state,
            "prompt_drag_tags": self.prompt_drag_tags,
            "requires_external_review": self.requires_external_review,
            "external_review_status": self.external_review_status,
            "model_metadata_ref": self.model_metadata_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "payload_evidence_ref": self.payload_evidence_ref,
            "payload_snapshot_hash": self.payload_snapshot_hash,
            "dispatch_envelope_ref": self.dispatch_envelope_ref,
            "packet_proof_metadata_ref": self.packet_proof_metadata_ref,
            "supports_completion_tokens": self.supports_completion_tokens,
            "supports_latency_ms": self.supports_latency_ms,
            "supports_payload_snapshot": self.supports_payload_snapshot,
            "supports_response_hash": self.supports_response_hash,
            "validation_tags": self.validation_tags,
            "fail_closed_advisory": self.fail_closed_advisory,
            "fail_closed_tags": self.fail_closed_tags,
            "metadata_transport_allowed": self.metadata_transport_allowed,
            "retry_requires_fresh_metadata": self.retry_requires_fresh_metadata,
            "transport_payload_kind": self.transport_payload_kind,
            "serialization_only": self.serialization_only,
        }


@dataclass(frozen=True)
class RelayProviderResultValidationEvidence:
    """Display-safe post-adapter result validation metadata."""

    result_evidence_id: str
    heartbeat_id: str | None = None
    lane_id: str | None = None
    role: str | None = None
    route_id: str | None = None
    selected_provider: str | None = None
    exact_model_id: str | None = None
    provider_route_kind: str = "unknown"
    trust_mode: str = "unknown"
    trust_state: str = "unknown"
    proof_strength: str = "unknown"
    capability_tier: str | None = None
    direct_endpoint_evidence_ref: str | None = None
    aggregator_evidence_ref: str | None = None
    model_metadata_ref: str | None = None
    validation_evidence_ref: str | None = None
    external_review_evidence_ref: str | None = None
    requires_external_review: bool = False
    external_review_status: str = "not_required"
    dispatch_metadata_envelope_ref: str | None = None
    payload_evidence_ref: str | None = None
    payload_snapshot_hash: str | None = None
    packet_hash: str | None = None
    prompt_budget_ref: str | None = None
    prompt_payload_status: str = "unknown"
    prompt_budget_percent: float | None = None
    prompt_growth_tokens: int | None = None
    prompt_growth_percent: float | None = None
    prompt_drag_tags: tuple[str, ...] = ()
    output_length: int | None = None
    normalized_output_hash: str | None = None
    response_hash_status: str = "unknown"
    completion_tokens_status: str = "unknown"
    total_tokens_status: str = "unknown"
    latency_bucket: str = "unknown"
    supports_completion_tokens: bool = False
    supports_latency_ms: bool = False
    supports_response_hash: bool = False
    result_validation_status: str = "unknown"
    warning_tags: tuple[str, ...] = ()
    blocker_tags: tuple[str, ...] = ()
    retry_requires_fresh_validation: bool = False
    demotion_required: bool = False
    human_gate_required: bool = False
    usable_for_lane: bool = False
    serialization_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return stable result metadata without raw output or provider bodies."""
        return {
            "result_evidence_id": self.result_evidence_id,
            "heartbeat_id": self.heartbeat_id,
            "lane_id": self.lane_id,
            "role": self.role,
            "route_id": self.route_id,
            "selected_provider": self.selected_provider,
            "exact_model_id": self.exact_model_id,
            "provider_route_kind": self.provider_route_kind,
            "trust_mode": self.trust_mode,
            "trust_state": self.trust_state,
            "proof_strength": self.proof_strength,
            "capability_tier": self.capability_tier,
            "direct_endpoint_evidence_ref": self.direct_endpoint_evidence_ref,
            "aggregator_evidence_ref": self.aggregator_evidence_ref,
            "model_metadata_ref": self.model_metadata_ref,
            "validation_evidence_ref": self.validation_evidence_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "requires_external_review": self.requires_external_review,
            "external_review_status": self.external_review_status,
            "dispatch_metadata_envelope_ref": self.dispatch_metadata_envelope_ref,
            "payload_evidence_ref": self.payload_evidence_ref,
            "payload_snapshot_hash": self.payload_snapshot_hash,
            "packet_hash": self.packet_hash,
            "prompt_budget_ref": self.prompt_budget_ref,
            "prompt_payload_status": self.prompt_payload_status,
            "prompt_budget_percent": self.prompt_budget_percent,
            "prompt_growth_tokens": self.prompt_growth_tokens,
            "prompt_growth_percent": self.prompt_growth_percent,
            "prompt_drag_tags": self.prompt_drag_tags,
            "output_length": self.output_length,
            "normalized_output_hash": self.normalized_output_hash,
            "response_hash_status": self.response_hash_status,
            "completion_tokens_status": self.completion_tokens_status,
            "total_tokens_status": self.total_tokens_status,
            "latency_bucket": self.latency_bucket,
            "supports_completion_tokens": self.supports_completion_tokens,
            "supports_latency_ms": self.supports_latency_ms,
            "supports_response_hash": self.supports_response_hash,
            "result_validation_status": self.result_validation_status,
            "warning_tags": self.warning_tags,
            "blocker_tags": self.blocker_tags,
            "retry_requires_fresh_validation": self.retry_requires_fresh_validation,
            "demotion_required": self.demotion_required,
            "human_gate_required": self.human_gate_required,
            "usable_for_lane": self.usable_for_lane,
            "serialization_only": self.serialization_only,
        }


@dataclass(frozen=True)
class RelayAegisProviderResultValidationAdvisory:
    """Advisory post-result validation facts for future Aegis policy input."""

    advisory_id: str | None = None
    heartbeat_id: str | None = None
    advisory_kind: str = "provider_result_validation"
    timing: str = "post_adapter_return"
    execution_mode: str = "display_advisory_only"
    result_evidence_ids: tuple[str, ...] = ()
    exact_model_ids: tuple[str, ...] = ()
    provider_route_kinds: tuple[str, ...] = ()
    trust_states: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    external_review_statuses: tuple[str, ...] = ()
    result_validation_statuses: tuple[str, ...] = ()
    response_hash_statuses: tuple[str, ...] = ()
    blocker_tags: tuple[str, ...] = ()
    warning_tags: tuple[str, ...] = ()
    retry_requires_fresh_validation: bool = False
    demotion_required: bool = False
    human_gate_required: bool = False
    fail_closed_advisory: bool = False
    usable_for_future_retry: bool = False
    adapter_boundary_unchanged: bool = True
    aegis_execution_timing_unchanged: bool = True
    serialization_only: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return deterministic advisory data without invoking Aegis."""
        return {
            "advisory_id": self.advisory_id,
            "heartbeat_id": self.heartbeat_id,
            "advisory_kind": self.advisory_kind,
            "timing": self.timing,
            "execution_mode": self.execution_mode,
            "result_evidence_ids": self.result_evidence_ids,
            "exact_model_ids": self.exact_model_ids,
            "provider_route_kinds": self.provider_route_kinds,
            "trust_states": self.trust_states,
            "proof_refs": self.proof_refs,
            "external_review_statuses": self.external_review_statuses,
            "result_validation_statuses": self.result_validation_statuses,
            "response_hash_statuses": self.response_hash_statuses,
            "blocker_tags": self.blocker_tags,
            "warning_tags": self.warning_tags,
            "retry_requires_fresh_validation": self.retry_requires_fresh_validation,
            "demotion_required": self.demotion_required,
            "human_gate_required": self.human_gate_required,
            "fail_closed_advisory": self.fail_closed_advisory,
            "usable_for_future_retry": self.usable_for_future_retry,
            "adapter_boundary_unchanged": self.adapter_boundary_unchanged,
            "aegis_execution_timing_unchanged": self.aegis_execution_timing_unchanged,
            "serialization_only": self.serialization_only,
        }


@dataclass(frozen=True)
class RelayPromptPacketPolicyEvidence:
    """Display-safe Relay record of Aegis PromptPacket policy evaluation."""

    decision: str
    severity: str
    reason: str
    evidence_ids: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    demote_to_tier: int | None = None
    packet_id: str | None = None
    packet_hash: str | None = None
    prompt_budget_ref: str | None = None
    packet_proof_metadata_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic policy evidence without prompt or transport payloads."""
        return {
            "decision": self.decision,
            "severity": self.severity,
            "reason": self.reason,
            "evidence_ids": self.evidence_ids,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "demote_to_tier": self.demote_to_tier,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "prompt_budget_ref": self.prompt_budget_ref,
            "packet_proof_metadata_ref": self.packet_proof_metadata_ref,
        }


@dataclass(frozen=True)
class RelayPromptPacketPolicyDisposition:
    """Relay transport disposition derived from evaluated PromptPacket policy."""

    transport_allowed: bool
    transport_action: str
    fail_closed: bool = False
    retry_requires_fresh_evaluation: bool = False
    demotion_target_tier: int | None = None
    demotion_authorized: bool = False
    fallback_allowed: bool = False
    blockers: tuple[str, ...] = ()
    audit_tags: tuple[str, ...] = ()
    explanation: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return deterministic advisory data for decision/audit handoff."""
        return {
            "transport_allowed": self.transport_allowed,
            "transport_action": self.transport_action,
            "fail_closed": self.fail_closed,
            "retry_requires_fresh_evaluation": self.retry_requires_fresh_evaluation,
            "demotion_target_tier": self.demotion_target_tier,
            "demotion_authorized": self.demotion_authorized,
            "fallback_allowed": self.fallback_allowed,
            "blockers": self.blockers,
            "audit_tags": self.audit_tags,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class RelayDecisionRecord:
    """Provider-neutral decision record capturing route selection rationale for Prime explanation.

    Exposes the audit fields needed for Prime to understand: route class, session action,
    context health, dual-lane requirement, trust/proof blockers, account-vs-API precedence,
    cost/privacy pressure, fallback blockers, and explanation for Prime.

    Optional Aegis gate evidence fields (populated when Aegis validation occurs):
    - aegis_gate_decision: gate outcome (allow/demote/block/human_gate)
    - aegis_evidence_ids: tuple of evidence ids from gate validation
    - aegis_waiver_present: whether a waiver was applied to this gate
    - aegis_gate_severity: severity level of gate outcome
    - aegis_explanation: explanation text from gate evaluation
    """

    heartbeat_id: str  # from packet.packet_id
    project: str | None = None  # context-dependent metadata
    surface_mode: str | None = None  # context-dependent metadata
    intent: str | None = None  # context-dependent metadata
    role: str = "builder"  # primary builder role
    risk_tier: int = 0
    session_action: str = "no_session"
    route_class: str | None = None
    vendor: str | None = None  # provider-neutral: always None
    model_id: str | None = None  # provider-neutral: always None
    account_or_api_source: str = "unknown"
    context_health: str = "unknown"
    prompt_payload_status: str | None = None
    dual_lane_required: bool = False
    lane_independence_reason: str = ""
    trust_state: str = "unknown"
    proof_required: tuple[str, ...] = ()
    human_gate_required: bool = False
    cost_posture: str = "standard"
    latency_posture: str = "standard"
    privacy_notes: str = "unknown"
    fallback_allowed: bool = True
    fallback_blockers: tuple[str, ...] = ()
    observability_fields: tuple[str, ...] = ()
    telemetry_required: tuple[str, ...] = ()
    explanation_for_prime: str = ""
    aegis_gate_decision: str | None = None  # gate outcome: allow/demote/block/human_gate
    aegis_evidence_ids: tuple[str, ...] = ()  # evidence ids from gate validation
    aegis_waiver_present: bool = False  # whether waiver was applied
    aegis_gate_severity: str | None = None  # severity level from gate
    aegis_explanation: str = ""  # gate evaluation explanation
    route_metadata: ModelRouteMetadataBinding | None = None
    payload_evidence: RelayPromptPayloadEvidence | None = None
    payload_meter_evidence: RelayPromptPayloadMeterEvidence | None = None
    dispatch_envelope: RelayDispatchEnvelope | None = None
    dispatch_metadata_envelope: RelayDispatchMetadataEnvelope | None = None
    provider_result_validation_evidence: RelayProviderResultValidationEvidence | None = None
    packet_hash: str | None = None
    prompt_budget_ref: str | None = None
    source_lineage_compliant: bool | None = None
    packet_proof_metadata_ref: str | None = None
    packet_proof_blocked_tags: tuple[str, ...] = ()
    prompt_packet_policy_evidence: RelayPromptPacketPolicyEvidence | None = None
    prompt_packet_policy_disposition: RelayPromptPacketPolicyDisposition | None = None


@dataclass(frozen=True)
class RelayExecutionResult:
    """Successful output for one lane with optional payload snapshot and adapter metadata."""

    role: ModelRole
    preferred_model: str
    output: str
    payload_snapshot: PromptPayloadSnapshot | None = None
    adapter_metadata: ModelHarnessMetadata | None = None
    route_metadata: ModelRouteMetadataBinding | None = None
    payload_evidence: RelayPromptPayloadEvidence | None = None
    payload_meter_evidence: RelayPromptPayloadMeterEvidence | None = None
    dispatch_envelope: RelayDispatchEnvelope | None = None
    dispatch_metadata_envelope: RelayDispatchMetadataEnvelope | None = None
    provider_result_validation_evidence: RelayProviderResultValidationEvidence | None = None


@dataclass(frozen=True)
class RelayExecutionError:
    """Captured exception for one lane."""

    role: ModelRole
    preferred_model: str
    error: str


@dataclass(frozen=True)
class AegisGateEvidenceSummary:
    """Serializable summary of Aegis gate evidence for downstream Bifrost/Prime surfaces.

    Exposes gate decision, severity, evidence ids, waiver presence, explanation, and
    any Relay fallback blockers generated from Aegis evidence. Provider-neutral and
    deterministic; no external Aegis calls or model invocations.
    """

    gate_decision: str | None = None  # gate outcome: allow/demote/block/human_gate
    severity: str | None = None  # severity level from gate
    evidence_ids: tuple[str, ...] = ()  # evidence ids from gate validation
    waiver_present: bool = False  # whether waiver was applied
    explanation: str = ""  # gate evaluation explanation
    fallback_blockers_from_aegis: tuple[str, ...] = ()  # Relay blockers generated from Aegis decisions

    def to_dict(self) -> dict[str, object]:
        """Serialize to stable dictionary for Bifrost/Prime consumption.

        Returns a deterministic dict with stable keys that downstream surfaces can
        rely on. All values are immutable (None, str, bool, tuple). No external calls.
        """
        return {
            "gate_decision": self.gate_decision,
            "severity": self.severity,
            "evidence_ids": self.evidence_ids,
            "waiver_present": self.waiver_present,
            "explanation": self.explanation,
            "fallback_blockers_from_aegis": self.fallback_blockers_from_aegis,
        }


@dataclass(frozen=True)
class RelayAegisPromptPacketHandoffSummary:
    """Display-safe PromptPacket policy summary for Bifrost handoff."""

    decision: str | None = None
    severity: str | None = None
    packet_id: str | None = None
    packet_hash_status: str = "missing"
    packet_hash: str | None = None
    proof_requirement: str | None = None
    aegis_evidence_ids: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    missing_metadata_fields: tuple[str, ...] = ()
    reason_tags: tuple[str, ...] = ()
    demotion_target_tier: int | None = None
    human_gate_state: str = "not_required"
    fail_closed: bool = False
    missing_metadata: bool = False
    prompt_budget_ref: str | None = None
    packet_proof_metadata_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return deterministic handoff keys without prompt or transport payloads."""
        return {
            "decision": self.decision,
            "severity": self.severity,
            "packet_id": self.packet_id,
            "packet_hash_status": self.packet_hash_status,
            "packet_hash": self.packet_hash,
            "proof_requirement": self.proof_requirement,
            "aegis_evidence_ids": self.aegis_evidence_ids,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "missing_metadata_fields": self.missing_metadata_fields,
            "reason_tags": self.reason_tags,
            "demotion_target_tier": self.demotion_target_tier,
            "human_gate_state": self.human_gate_state,
            "fail_closed": self.fail_closed,
            "missing_metadata": self.missing_metadata,
            "prompt_budget_ref": self.prompt_budget_ref,
            "packet_proof_metadata_ref": self.packet_proof_metadata_ref,
        }


_SAFE_PROMPT_PACKET_REASON_TEXT = (
    "PromptPacket proof metadata satisfies Aegis policy",
    "human approval required before dispatch",
)

_SAFE_PROMPT_PACKET_HANDOFF_TAGS = frozenset(
    {
        "aegis_clean_proof_trail",
        "aegis_demotion_requires_fresh_policy_evaluation",
        "aegis_demotion_target_unauthorized",
        "aegis_human_gate_required",
        "aegis_prompt_packet_policy_allow",
        "aegis_prompt_packet_policy_blocked",
        "aegis_prompt_packet_policy_warn",
        "human_gate_approval",
        "human_gate_approval_missing",
        "independent_dual_model_lanes",
        "independent_review_when_meaningful",
        "missing_metadata_fail_closed",
        "packet_hash_missing",
        "packet_hash_required_unavailable",
        "packet_hash_unavailable",
        "packet_proof_metadata_missing",
        "prompt_payload_snapshot",
        "unknown_prompt_packet_policy_decision",
        "unknown_proof_requirement",
    }
)

_SAFE_PROMPT_PACKET_EVIDENCE_PREFIXES = (
    "aegis-proof-",
    "packet-proof-",
)


def _display_safe_handoff_tags(
    tags: tuple[str, ...],
    *,
    fallback: str,
) -> tuple[str, ...]:
    """Return structured handoff tags without arbitrary free-text leakage."""
    safe_tags: list[str] = []
    for tag in tags:
        if tag in _SAFE_PROMPT_PACKET_REASON_TEXT:
            safe_tags.append(tag)
        elif tag in _SAFE_PROMPT_PACKET_HANDOFF_TAGS:
            safe_tags.append(tag)
        elif tag.startswith(_SAFE_PROMPT_PACKET_EVIDENCE_PREFIXES):
            safe_tags.append(tag)
        else:
            safe_tags.append(fallback)
    return tuple(dict.fromkeys(safe_tags))


@dataclass(frozen=True)
class RelayModelCapabilityLaneSummary:
    """Display-safe model capability metadata for one Relay lane."""

    lane_id: str | None = None
    selected_provider: str | None = None
    exact_model_id: str | None = None
    capability_tier: str | None = None
    provider_route_kind: str = "unknown"
    trust_state: str = "unknown"
    context_window_tokens: int | None = None
    prompt_payload_budget_tokens: int | None = None
    prompt_payload_status: str = "unknown"
    estimated_prompt_tokens: int | None = None
    prompt_budget_percent: float | None = None
    growth_state: str = "unknown"
    prompt_drag_tags: tuple[str, ...] = ()
    requires_external_review: bool = False
    external_review_status: str = "not_required"
    model_metadata_ref: str | None = None
    external_review_evidence_ref: str | None = None
    payload_evidence_ref: str | None = None
    telemetry_error_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "lane_id": self.lane_id,
            "selected_provider": self.selected_provider,
            "exact_model_id": self.exact_model_id,
            "capability_tier": self.capability_tier,
            "provider_route_kind": self.provider_route_kind,
            "trust_state": self.trust_state,
            "context_window_tokens": self.context_window_tokens,
            "prompt_payload_budget_tokens": self.prompt_payload_budget_tokens,
            "prompt_payload_status": self.prompt_payload_status,
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "prompt_budget_percent": self.prompt_budget_percent,
            "growth_state": self.growth_state,
            "prompt_drag_tags": self.prompt_drag_tags,
            "requires_external_review": self.requires_external_review,
            "external_review_status": self.external_review_status,
            "model_metadata_ref": self.model_metadata_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "payload_evidence_ref": self.payload_evidence_ref,
            "telemetry_error_tags": self.telemetry_error_tags,
        }


@dataclass(frozen=True)
class RelayModelCapabilityMetadataSummary:
    """Deterministic collection of display-safe Model Harness lane metadata."""

    lanes: tuple[RelayModelCapabilityLaneSummary, ...] = ()
    missing_metadata_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "lanes": tuple(lane.to_dict() for lane in self.lanes),
            "missing_metadata_tags": self.missing_metadata_tags,
        }


@dataclass(frozen=True)
class RelayExecutionSummary:
    """Immutable collection of per-lane results and errors from one plan execution."""

    results: tuple[RelayExecutionResult, ...]
    errors: tuple[RelayExecutionError, ...]
    decision_record: RelayDecisionRecord | None = None
    prompt_packet_policy_evidence: RelayPromptPacketPolicyEvidence | None = None
    prompt_packet_policy_disposition: RelayPromptPacketPolicyDisposition | None = None

    def aegis_gate_evidence_summary(self) -> AegisGateEvidenceSummary:
        """Extract Aegis gate evidence from decision record for downstream serialization.

        Returns a provider-neutral summary of gate decision, severity, evidence ids,
        waiver presence, explanation, and Relay fallback blockers from Aegis evidence.
        If no decision record present, returns empty summary.
        """
        if self.decision_record is None:
            return AegisGateEvidenceSummary()

        record = self.decision_record
        # Extract Aegis blockers from fallback_blockers that were generated by Aegis evidence
        aegis_blockers = tuple(
            blocker
            for blocker in record.fallback_blockers
            if blocker.startswith("aegis_")
        )

        return AegisGateEvidenceSummary(
            gate_decision=record.aegis_gate_decision,
            severity=record.aegis_gate_severity,
            evidence_ids=record.aegis_evidence_ids,
            waiver_present=record.aegis_waiver_present,
            explanation=record.aegis_explanation,
            fallback_blockers_from_aegis=aegis_blockers,
        )

    def aegis_prompt_packet_policy_handoff(self) -> RelayAegisPromptPacketHandoffSummary:
        """Project evaluated PromptPacket policy evidence into Bifrost-safe data."""
        policy = self.prompt_packet_policy_evidence
        if policy is None and self.decision_record is not None:
            policy = self.decision_record.prompt_packet_policy_evidence
        if policy is None:
            return RelayAegisPromptPacketHandoffSummary()

        record = self.decision_record
        envelope = record.dispatch_envelope if record is not None else None
        proof_required = (
            envelope.proof_required
            if envelope is not None
            else (record.proof_required if record is not None else ())
        )
        if "human_gate_approval" in proof_required:
            proof_requirement = "human_gate_approval"
        elif "independent_dual_model_lanes" in proof_required:
            proof_requirement = "independent_dual_model_lanes"
        elif "independent_review_when_meaningful" in proof_required:
            proof_requirement = "independent_review_when_meaningful"
        elif "aegis_clean_proof_trail" in proof_required:
            proof_requirement = "aegis_clean_proof_trail"
        else:
            proof_requirement = proof_required[0] if proof_required else None
        packet_hash = (
            policy.packet_hash
            if policy.packet_hash is not None
            else (envelope.packet_hash if envelope is not None else None)
        )
        prompt_budget_ref = (
            policy.prompt_budget_ref
            if policy.prompt_budget_ref is not None
            else (envelope.prompt_budget_ref if envelope is not None else None)
        )
        packet_proof_metadata_ref = (
            policy.packet_proof_metadata_ref
            if policy.packet_proof_metadata_ref is not None
            else (envelope.packet_proof_metadata_ref if envelope is not None else None)
        )
        human_gate_required = bool(
            envelope.human_gate_required
            if envelope is not None
            else (record.human_gate_required if record is not None else False)
        )
        if policy.decision == PromptPacketProofDecision.HUMAN_GATE.value:
            human_gate_state = "required"
        elif human_gate_required:
            human_gate_state = "approved"
        else:
            human_gate_state = "not_required"

        missing_metadata_fields = []
        if policy.packet_id is None:
            missing_metadata_fields.append("packet_id")
        if packet_hash is None:
            missing_metadata_fields.append("packet_hash")
        if prompt_budget_ref is None:
            missing_metadata_fields.append("prompt_budget_ref")
        if packet_proof_metadata_ref is None:
            missing_metadata_fields.append("packet_proof_metadata_ref")
        if proof_requirement is None:
            missing_metadata_fields.append("proof_requirement")
        if not policy.evidence_ids:
            missing_metadata_fields.append("aegis_evidence_ids")

        evidence_ids = _display_safe_handoff_tags(
            policy.evidence_ids,
            fallback="redacted_evidence_id",
        )
        blockers = _display_safe_handoff_tags(
            policy.blockers,
            fallback="redacted_policy_blocker",
        )
        warnings = _display_safe_handoff_tags(
            policy.warnings,
            fallback="redacted_policy_warning",
        )
        tags = _display_safe_handoff_tags(
            tuple(policy.blockers or policy.warnings or (policy.reason,)),
            fallback="redacted_policy_reason",
        )
        fail_closed = policy.decision in (
            PromptPacketProofDecision.BLOCK.value,
            PromptPacketProofDecision.HUMAN_GATE.value,
        )
        missing_metadata = bool(missing_metadata_fields)

        return RelayAegisPromptPacketHandoffSummary(
            decision=policy.decision,
            severity=policy.severity,
            packet_id=policy.packet_id,
            packet_hash_status="present" if packet_hash else "missing",
            packet_hash=packet_hash,
            proof_requirement=proof_requirement,
            aegis_evidence_ids=evidence_ids,
            blockers=blockers,
            warnings=warnings,
            missing_metadata_fields=tuple(missing_metadata_fields),
            reason_tags=tags,
            demotion_target_tier=policy.demote_to_tier,
            human_gate_state=human_gate_state,
            fail_closed=fail_closed,
            missing_metadata=missing_metadata,
            prompt_budget_ref=prompt_budget_ref,
            packet_proof_metadata_ref=packet_proof_metadata_ref,
        )

    def model_capability_metadata_summary(self) -> RelayModelCapabilityMetadataSummary:
        """Return display-safe provider-neutral Model Harness metadata by lane."""
        lane_summaries: list[RelayModelCapabilityLaneSummary] = []
        missing_tags: list[str] = []

        for result in self.results:
            evidence = result.payload_evidence
            route_metadata = result.route_metadata
            lane_id = (
                evidence.lane_id
                if evidence is not None
                else f"{result.role.value}:{result.preferred_model}"
            )
            payload_ref = _payload_evidence_ref(evidence)
            if route_metadata is None and evidence is None:
                missing_tags.append(f"model_metadata_missing:{lane_id}")
            lane_summaries.append(
                RelayModelCapabilityLaneSummary(
                    lane_id=lane_id,
                    selected_provider=(
                        route_metadata.provider_name
                        if route_metadata is not None
                        else (evidence.selected_provider if evidence is not None else None)
                    ),
                    exact_model_id=(
                        route_metadata.model_name
                        if route_metadata is not None
                        else (evidence.selected_model if evidence is not None else None)
                    ),
                    capability_tier=(
                        route_metadata.capability_tier
                        if route_metadata is not None
                        else (evidence.capability_tier if evidence is not None else None)
                    ),
                    provider_route_kind=(
                        route_metadata.provider_route_kind
                        if route_metadata is not None
                        else (evidence.provider_route_kind if evidence is not None else "unknown")
                    ),
                    trust_state=(
                        route_metadata.trust_state
                        if route_metadata is not None
                        else (evidence.trust_state if evidence is not None else "unknown")
                    ),
                    context_window_tokens=(
                        route_metadata.context_budget
                        if route_metadata is not None
                        else (
                            evidence.model_context_window_tokens
                            if evidence is not None
                            else None
                        )
                    ),
                    prompt_payload_budget_tokens=(
                        route_metadata.prompt_payload_budget
                        if route_metadata is not None
                        else (evidence.prompt_budget_tokens if evidence is not None else None)
                    ),
                    prompt_payload_status=(
                        route_metadata.prompt_payload_status
                        if route_metadata is not None
                        and route_metadata.prompt_payload_status is not None
                        else (evidence.budget_status if evidence is not None else "unknown")
                    ),
                    estimated_prompt_tokens=(
                        route_metadata.prompt_payload_estimated_tokens
                        if route_metadata is not None
                        and route_metadata.prompt_payload_estimated_tokens is not None
                        else (
                            evidence.estimated_prompt_tokens
                            if evidence is not None
                            else None
                        )
                    ),
                    prompt_budget_percent=(
                        route_metadata.prompt_payload_budget_percent
                        if route_metadata is not None
                        and route_metadata.prompt_payload_budget_percent is not None
                        else (evidence.budget_percent if evidence is not None else None)
                    ),
                    growth_state=evidence.growth_state if evidence is not None else "unknown",
                    prompt_drag_tags=(
                        evidence.prompt_drag_tags if evidence is not None else ()
                    ),
                    requires_external_review=(
                        route_metadata.requires_external_review
                        if route_metadata is not None
                        else (
                            evidence.requires_external_review
                            if evidence is not None
                            else False
                        )
                    ),
                    external_review_status=(
                        route_metadata.external_review_status
                        if route_metadata is not None
                        else (
                            evidence.external_review_status
                            if evidence is not None
                            else "not_required"
                        )
                    ),
                    model_metadata_ref=(
                        route_metadata.model_metadata_ref
                        if route_metadata is not None
                        else (evidence.model_metadata_ref if evidence is not None else None)
                    ),
                    external_review_evidence_ref=(
                        route_metadata.external_review_evidence_ref
                        if route_metadata is not None
                        else (
                            evidence.external_review_evidence_ref
                            if evidence is not None
                            else None
                        )
                    ),
                    payload_evidence_ref=payload_ref,
                    telemetry_error_tags=(
                        evidence.telemetry_error_tags if evidence is not None else ()
                    ),
                )
            )

        if not lane_summaries and self.decision_record is not None:
            evidence = self.decision_record.payload_evidence
            if evidence is None:
                missing_tags.append("model_metadata_missing:decision_record")
            else:
                lane_summaries.append(
                    RelayModelCapabilityLaneSummary(
                        lane_id=evidence.lane_id,
                        selected_provider=evidence.selected_provider,
                        exact_model_id=evidence.selected_model,
                        capability_tier=evidence.capability_tier,
                        provider_route_kind=evidence.provider_route_kind,
                        trust_state=evidence.trust_state,
                        context_window_tokens=evidence.model_context_window_tokens,
                        prompt_payload_budget_tokens=evidence.prompt_budget_tokens,
                        prompt_payload_status=evidence.budget_status,
                        estimated_prompt_tokens=evidence.estimated_prompt_tokens,
                        prompt_budget_percent=evidence.budget_percent,
                        growth_state=evidence.growth_state,
                        prompt_drag_tags=evidence.prompt_drag_tags,
                        requires_external_review=evidence.requires_external_review,
                        external_review_status=evidence.external_review_status,
                        model_metadata_ref=evidence.model_metadata_ref,
                        external_review_evidence_ref=evidence.external_review_evidence_ref,
                        payload_evidence_ref=_payload_evidence_ref(evidence),
                        telemetry_error_tags=evidence.telemetry_error_tags,
                    )
                )

        return RelayModelCapabilityMetadataSummary(
            lanes=tuple(lane_summaries),
            missing_metadata_tags=tuple(dict.fromkeys(missing_tags)),
        )

    def prompt_payload_meter_evidence(
        self,
    ) -> tuple[RelayPromptPayloadMeterEvidence, ...]:
        """Return display-safe visible prompt payload meter evidence."""
        evidence = [result.payload_meter_evidence for result in self.results]
        return tuple(item for item in evidence if item is not None)

    def prompt_payload_meter_consumer_view(self) -> dict[str, object]:
        """Return deterministic prompt payload meter data for Relay consumers."""
        evidence = self.prompt_payload_meter_evidence()
        decision_evidence = (
            self.decision_record.payload_meter_evidence
            if self.decision_record is not None
            else None
        )
        if not evidence and decision_evidence is not None:
            evidence = (decision_evidence,)
        blocker_tags = tuple(
            dict.fromkeys(
                tag
                for item in (*evidence, decision_evidence)
                if item is not None
                for tag in item.blocker_tags
            )
        )
        warning_tags = tuple(
            dict.fromkeys(
                tag
                for item in (*evidence, decision_evidence)
                if item is not None
                for tag in item.warning_tags
            )
        )
        heartbeat_id = None
        if decision_evidence is not None:
            heartbeat_id = decision_evidence.heartbeat_id
        elif evidence:
            heartbeat_id = evidence[0].heartbeat_id
        elif self.decision_record is not None:
            heartbeat_id = self.decision_record.heartbeat_id
        return {
            "heartbeat_id": heartbeat_id,
            "consumer_view_kind": "relay_prompt_payload_meter",
            "serialization_only": True,
            "meter_evidence": tuple(item.to_dict() for item in evidence),
            "decision_record_meter_evidence": (
                decision_evidence.to_dict() if decision_evidence is not None else None
            ),
            "prompt_drag_blocked": bool(blocker_tags),
            "blocker_tags": blocker_tags,
            "warning_tags": warning_tags,
        }

    def dispatch_metadata_envelopes(self) -> tuple[RelayDispatchMetadataEnvelope, ...]:
        """Return display-safe metadata envelopes without provider payloads."""
        envelopes = [result.dispatch_metadata_envelope for result in self.results]
        return tuple(envelope for envelope in envelopes if envelope is not None)

    def dispatch_metadata_consumer_view(self) -> dict[str, object]:
        """Return deterministic metadata-only consumer data for Relay decisions."""
        envelopes = self.dispatch_metadata_envelopes()
        decision_envelope = (
            self.decision_record.dispatch_metadata_envelope
            if self.decision_record is not None
            else None
        )
        if not envelopes and decision_envelope is not None:
            envelopes = (decision_envelope,)
        fail_closed_tags = tuple(
            dict.fromkeys(
                tag
                for envelope in (*envelopes, decision_envelope)
                if envelope is not None
                for tag in envelope.fail_closed_tags
            )
        )
        heartbeat_id = None
        if decision_envelope is not None:
            heartbeat_id = decision_envelope.heartbeat_id
        elif envelopes:
            heartbeat_id = envelopes[0].heartbeat_id
        elif self.decision_record is not None:
            heartbeat_id = self.decision_record.heartbeat_id
        return {
            "heartbeat_id": heartbeat_id,
            "consumer_view_kind": "relay_dispatch_metadata",
            "serialization_only": True,
            "envelopes": tuple(envelope.to_dict() for envelope in envelopes),
            "decision_record_envelope": (
                decision_envelope.to_dict() if decision_envelope is not None else None
            ),
            "fail_closed_advisory": bool(fail_closed_tags),
            "fail_closed_tags": fail_closed_tags,
        }

    def provider_result_validation_evidence(
        self,
    ) -> tuple[RelayProviderResultValidationEvidence, ...]:
        """Return display-safe post-adapter result validation evidence."""
        evidence = [
            result.provider_result_validation_evidence for result in self.results
        ]
        return tuple(item for item in evidence if item is not None)

    def provider_result_validation_consumer_view(self) -> dict[str, object]:
        """Return deterministic result-validation data for downstream consumers."""
        evidence = self.provider_result_validation_evidence()
        decision_evidence = (
            self.decision_record.provider_result_validation_evidence
            if self.decision_record is not None
            else None
        )
        if not evidence and decision_evidence is not None:
            evidence = (decision_evidence,)
        blocker_tags = tuple(
            dict.fromkeys(
                tag
                for item in (*evidence, decision_evidence)
                if item is not None
                for tag in item.blocker_tags
            )
        )
        warning_tags = tuple(
            dict.fromkeys(
                tag
                for item in (*evidence, decision_evidence)
                if item is not None
                for tag in item.warning_tags
            )
        )
        heartbeat_id = None
        if decision_evidence is not None:
            heartbeat_id = decision_evidence.heartbeat_id
        elif evidence:
            heartbeat_id = evidence[0].heartbeat_id
        elif self.decision_record is not None:
            heartbeat_id = self.decision_record.heartbeat_id
        return {
            "heartbeat_id": heartbeat_id,
            "consumer_view_kind": "relay_provider_result_validation",
            "serialization_only": True,
            "result_evidence": tuple(item.to_dict() for item in evidence),
            "decision_record_result_evidence": (
                decision_evidence.to_dict() if decision_evidence is not None else None
            ),
            "fail_closed": bool(blocker_tags),
            "blocker_tags": blocker_tags,
            "warning_tags": warning_tags,
        }

    def aegis_provider_result_validation_advisory(
        self,
    ) -> RelayAegisProviderResultValidationAdvisory:
        """Project post-result validation evidence into Aegis advisory input."""
        evidence = self.provider_result_validation_evidence()
        decision_evidence = (
            self.decision_record.provider_result_validation_evidence
            if self.decision_record is not None
            else None
        )
        if not evidence and decision_evidence is not None:
            evidence = (decision_evidence,)
        heartbeat_id = None
        if decision_evidence is not None:
            heartbeat_id = decision_evidence.heartbeat_id
        elif evidence:
            heartbeat_id = evidence[0].heartbeat_id
        elif self.decision_record is not None:
            heartbeat_id = self.decision_record.heartbeat_id

        proof_refs = []
        for item in evidence:
            proof_refs.extend(
                ref
                for ref in (
                    item.model_metadata_ref,
                    item.validation_evidence_ref,
                    item.external_review_evidence_ref,
                    item.dispatch_metadata_envelope_ref,
                    item.payload_evidence_ref,
                    item.packet_hash,
                    item.prompt_budget_ref,
                )
                if ref is not None
            )
        blocker_tags = tuple(
            dict.fromkeys(tag for item in evidence for tag in item.blocker_tags)
        )
        warning_tags = tuple(
            dict.fromkeys(tag for item in evidence for tag in item.warning_tags)
        )
        fail_closed = bool(blocker_tags) or any(
            item.result_validation_status == "blocked" for item in evidence
        )
        advisory_id = (
            f"relay-aegis-provider-result:{heartbeat_id}"
            if heartbeat_id is not None
            else None
        )
        return RelayAegisProviderResultValidationAdvisory(
            advisory_id=advisory_id,
            heartbeat_id=heartbeat_id,
            result_evidence_ids=tuple(
                item.result_evidence_id for item in evidence
            ),
            exact_model_ids=tuple(
                dict.fromkeys(
                    item.exact_model_id
                    for item in evidence
                    if item.exact_model_id is not None
                )
            ),
            provider_route_kinds=tuple(
                dict.fromkeys(item.provider_route_kind for item in evidence)
            ),
            trust_states=tuple(dict.fromkeys(item.trust_state for item in evidence)),
            proof_refs=tuple(dict.fromkeys(proof_refs)),
            external_review_statuses=tuple(
                dict.fromkeys(item.external_review_status for item in evidence)
            ),
            result_validation_statuses=tuple(
                dict.fromkeys(item.result_validation_status for item in evidence)
            ),
            response_hash_statuses=tuple(
                dict.fromkeys(item.response_hash_status for item in evidence)
            ),
            blocker_tags=blocker_tags,
            warning_tags=warning_tags,
            retry_requires_fresh_validation=any(
                item.retry_requires_fresh_validation for item in evidence
            ),
            demotion_required=any(item.demotion_required for item in evidence),
            human_gate_required=any(item.human_gate_required for item in evidence),
            fail_closed_advisory=fail_closed,
            usable_for_future_retry=bool(evidence) and not fail_closed,
        )


class RelayProofGateError(RuntimeError):
    """Raised when Aegis proof blocks a high-risk Relay dispatch."""


def _snapshot_severity(snapshot: PromptPayloadSnapshot) -> EvidenceSeverity:
    """Map payload snapshot status to Aegis evidence severity."""
    from .prompt_payload_meter import PayloadStatus

    status = snapshot.status
    if status == PayloadStatus.DEGRADED:
        return EvidenceSeverity.WARNING
    elif status == PayloadStatus.WATCH:
        return EvidenceSeverity.INFO
    else:
        return EvidenceSeverity.INFO


def relay_execution_summary_to_proof_trail(
    summary: RelayExecutionSummary,
) -> ProofTrail:
    """Convert Relay execution output into Aegis evidence.

    Successful lane outputs become non-blocking BUILD_OUTPUT evidence. Lane
    errors become proof-blocking BUILD_OUTPUT evidence with ERROR severity.
    Payload snapshot evidence is added for lanes with snapshot metadata.
    """
    trail = ProofTrail()
    for index, result in enumerate(summary.results):
        role = result.role.value
        trail.add(
            AegisEvidence(
                id=f"relay-result-{index}-{role}",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.INFO,
                status=EvidenceStatus.OPEN,
                source="relay_executor",
                target=f"{role}:{result.preferred_model}",
                summary=f"{role} lane completed; output length {len(result.output)} characters",
            )
        )
        if result.payload_snapshot is not None:
            snapshot = result.payload_snapshot
            trail.add(
                AegisEvidence(
                    id=f"relay-payload-{index}-{role}",
                    evidence_type=EvidenceType.BUILD_OUTPUT,
                    severity=_snapshot_severity(snapshot),
                    status=EvidenceStatus.OPEN,
                    source="relay_executor",
                    target=f"{role}:{result.preferred_model}",
                    summary=f"Payload snapshot: {snapshot.display_label} "
                    f"({snapshot.estimated_tokens} tokens, "
                    f"{snapshot.budget_percent:.1f}% of budget); status: {snapshot.status.value}",
                )
            )
    for index, error in enumerate(summary.errors):
        role = error.role.value
        trail.add(
            AegisEvidence(
                id=f"relay-error-{index}-{role}",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="relay_executor",
                target=f"{role}:{error.preferred_model}",
                summary=f"{role} lane failed; error length {len(error.error)} characters",
            )
        )
    return trail


def _payload_evidence_growth_state(snapshot: PromptPayloadSnapshot | None) -> str:
    if snapshot is None:
        return "unknown"
    if snapshot.budget_tokens is not None and snapshot.estimated_tokens > snapshot.budget_tokens:
        return "over_budget"
    if snapshot.growth_tokens == 0:
        return "flat"
    if snapshot.queue_mode and snapshot.status.value == "degraded":
        return "growing_unexpected"
    return "growing_expected"


def _payload_evidence_prompt_drag_tags(
    snapshot: PromptPayloadSnapshot | None,
    *,
    over_budget: bool,
) -> tuple[str, ...]:
    tags: list[str] = []
    if snapshot is None:
        return ()
    if over_budget:
        tags.append("prompt_drag_over_budget")
    if snapshot.queue_mode and snapshot.status.value == "degraded":
        tags.append("prompt_drag_degraded")
    if snapshot.growth_tokens > 0:
        tags.append("prompt_drag_growth")
    elif snapshot.growth_tokens == 0:
        tags.append("prompt_drag_flat")
    return tuple(tags)


def _adapter_metadata_candidate_value(
    adapter_metadata: ModelHarnessMetadata | None,
    key: str,
) -> str | None:
    if adapter_metadata is None or adapter_metadata.deepseek_candidate_state is None:
        return None
    value = adapter_metadata.deepseek_candidate_state.get(key)
    return str(value) if value is not None else None


def _adapter_metadata_candidate_tuple(
    adapter_metadata: ModelHarnessMetadata | None,
    key: str,
) -> tuple[str, ...]:
    value = _adapter_metadata_candidate_value(adapter_metadata, key)
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _adapter_metadata_candidate_int(
    adapter_metadata: ModelHarnessMetadata | None,
    key: str,
) -> int | None:
    value = _adapter_metadata_candidate_value(adapter_metadata, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _adapter_external_review_status(
    adapter_metadata: ModelHarnessMetadata | None,
) -> str:
    if adapter_metadata is None:
        return "unknown"
    status = _adapter_metadata_candidate_value(adapter_metadata, "external_review_status")
    if status:
        return status
    return "required_unknown" if adapter_metadata.requires_external_review else "not_required"


def _adapter_model_metadata_ref(
    adapter_metadata: ModelHarnessMetadata | None,
) -> str | None:
    if adapter_metadata is None:
        return None
    return f"model-harness-metadata:{adapter_metadata.provider_name}:{adapter_metadata.model_name}"


def _build_payload_evidence(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
    route_metadata: ModelRouteMetadataBinding | None = None,
    *,
    prompt_source: str = "relay",
    lane_id: str | None = None,
    comparison_scope: str = "dispatch",
    expected_growth_reason: str | None = None,
) -> RelayPromptPayloadEvidence:
    """Build prompt payload evidence before dispatch without storing prompt text."""
    route = plan.route
    audit = route.audit
    packet = plan.packet
    packet_proof = getattr(packet, "proof_metadata", None)

    provider = adapter_metadata.provider_name if adapter_metadata else None
    selected_model = adapter_metadata.model_name if adapter_metadata else None
    context_window = adapter_metadata.context_budget if adapter_metadata else None
    capability_tier = adapter_metadata.capability_tier if adapter_metadata else None
    trust_state = adapter_metadata.trust_state if adapter_metadata else audit.trust_state.value
    requires_external_review = (
        adapter_metadata.requires_external_review if adapter_metadata else False
    )
    provider_route_kind = _adapter_metadata_candidate_value(adapter_metadata, "api_mode") or "unknown"
    external_review_status = _adapter_external_review_status(adapter_metadata)
    model_metadata_ref = _adapter_model_metadata_ref(adapter_metadata)
    external_review_evidence_ref = (
        f"external-review:{provider}:{selected_model}:{external_review_status}"
        if requires_external_review and provider is not None and selected_model is not None
        else None
    )
    if route_metadata is not None:
        provider = route_metadata.provider_name
        selected_model = route_metadata.model_name
        context_window = route_metadata.context_budget
        capability_tier = route_metadata.capability_tier
        trust_state = route_metadata.trust_state
        requires_external_review = route_metadata.requires_external_review
        provider_route_kind = route_metadata.provider_route_kind
        external_review_status = route_metadata.external_review_status
        model_metadata_ref = route_metadata.model_metadata_ref
        external_review_evidence_ref = route_metadata.external_review_evidence_ref
    prompt_budget = (
        payload_snapshot.budget_tokens
        if payload_snapshot is not None and payload_snapshot.budget_tokens is not None
        else (adapter_metadata.prompt_payload_budget if adapter_metadata else None)
    )
    estimated_tokens = (
        payload_snapshot.estimated_tokens if payload_snapshot is not None else packet.prompt_tokens
    )
    remaining_context = (
        context_window - estimated_tokens if context_window is not None else None
    )
    over_budget = (
        prompt_budget is not None and prompt_budget > 0 and estimated_tokens > prompt_budget
    )

    telemetry_tags: list[str] = []
    if adapter_metadata is None:
        telemetry_tags.append("telemetry_unavailable")
        telemetry_tags.append("provider_metadata_missing")
    else:
        if not adapter_metadata.supports_completion_tokens:
            telemetry_tags.append("completion_tokens_unavailable")
        if not adapter_metadata.supports_latency_ms:
            telemetry_tags.append("latency_ms_unavailable")
        if not adapter_metadata.supports_payload_snapshot:
            telemetry_tags.append("prompt_snapshot_missing")
        if not adapter_metadata.supports_response_hash:
            telemetry_tags.append("response_hash_unavailable")
    if over_budget:
        telemetry_tags.append("budget_exceeded")
    if context_window is None:
        telemetry_tags.append("context_window_unknown")

    prompt_hash = None
    if adapter_metadata is not None and adapter_metadata.supports_payload_snapshot:
        prompt_hash = hashlib.sha256(packet.serialized_prompt.encode("utf-8")).hexdigest()

    return RelayPromptPayloadEvidence(
        prompt_source=prompt_source,
        heartbeat_id=packet.packet_id,
        route_id=f"tier-{route.risk_tier}:{route.mode.value}",
        lane_id=lane_id,
        selected_provider=provider,
        selected_model=selected_model,
        capability_tier=capability_tier,
        route_class=audit.route_class.value if audit.route_class else None,
        route_kind=audit.route_kind.value,
        provider_route_kind=provider_route_kind,
        trust_state=trust_state,
        requires_external_review=requires_external_review,
        external_review_status=external_review_status,
        model_metadata_ref=model_metadata_ref,
        external_review_evidence_ref=external_review_evidence_ref,
        estimated_prompt_tokens=estimated_tokens,
        prompt_budget_tokens=prompt_budget,
        model_context_window_tokens=context_window,
        max_output_tokens=adapter_metadata.max_output_tokens if adapter_metadata else None,
        remaining_context_tokens=remaining_context,
        budget_percent=(
            payload_snapshot.budget_percent
            if payload_snapshot is not None
            else ((estimated_tokens / prompt_budget) * 100 if prompt_budget else None)
        ),
        budget_status=payload_snapshot.status.value if payload_snapshot is not None else "unknown",
        budget_compliant=(not over_budget if prompt_budget is not None else None),
        over_budget_reason="prompt_tokens_exceed_budget" if over_budget else None,
        previous_prompt_tokens=payload_snapshot.prior_estimated_tokens if payload_snapshot else None,
        delta_tokens=payload_snapshot.growth_tokens if payload_snapshot else None,
        delta_percent=payload_snapshot.growth_percent if payload_snapshot else None,
        comparison_scope=comparison_scope,
        growth_state=_payload_evidence_growth_state(payload_snapshot),
        prompt_drag_tags=_payload_evidence_prompt_drag_tags(
            payload_snapshot,
            over_budget=over_budget,
        ),
        expected_growth_reason=expected_growth_reason,
        prompt_payload_snapshot_hash=prompt_hash,
        response_payload_snapshot_hash=None,
        adapter_supports_snapshot=(
            adapter_metadata.supports_payload_snapshot if adapter_metadata else False
        ),
        supports_completion_tokens=(
            adapter_metadata.supports_completion_tokens if adapter_metadata else False
        ),
        supports_latency_ms=adapter_metadata.supports_latency_ms if adapter_metadata else False,
        supports_payload_snapshot=(
            adapter_metadata.supports_payload_snapshot if adapter_metadata else False
        ),
        supports_response_hash=(
            adapter_metadata.supports_response_hash if adapter_metadata else False
        ),
        tokenizer_family=adapter_metadata.tokenizer_family if adapter_metadata else "unknown",
        telemetry_error_tags=tuple(telemetry_tags),
    )


def _dedupe_tags(*tag_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    tags: list[str] = []
    for group in tag_groups:
        for tag in group:
            if tag and tag not in tags:
                tags.append(tag)
    return tuple(tags)


def _payload_evidence_ref(payload_evidence: RelayPromptPayloadEvidence | None) -> str | None:
    if payload_evidence is None:
        return None
    heartbeat_id = payload_evidence.heartbeat_id or "unknown-heartbeat"
    lane_id = payload_evidence.lane_id or "unknown-lane"
    return f"relay-payload-evidence:{heartbeat_id}:{lane_id}"


def _round_meter_percent(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)


def _build_prompt_payload_meter_evidence(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    *,
    lane_id: str | None = None,
) -> RelayPromptPayloadMeterEvidence:
    """Build visible prompt payload meter data without exposing prompt text."""
    packet = plan.packet
    snapshot = payload_snapshot
    snapshot_missing = snapshot is None
    estimated_tokens_missing = (
        payload_evidence is not None and payload_evidence.estimated_prompt_tokens is None
    )
    if snapshot is None:
        snapshot = PromptPayloadSnapshot(
            raw_prompt_chars=len(packet.serialized_prompt),
            estimated_tokens=(
                payload_evidence.estimated_prompt_tokens
                if payload_evidence is not None
                and payload_evidence.estimated_prompt_tokens is not None
                else packet.prompt_tokens
            ),
            budget_tokens=(
                payload_evidence.prompt_budget_tokens
                if payload_evidence is not None
                else None
            ),
        )
    lane_label = (
        lane_id
        or (payload_evidence.lane_id if payload_evidence is not None else None)
        or "unknown-lane"
    )
    prompt_drag_tags = (
        payload_evidence.prompt_drag_tags
        if payload_evidence is not None
        else _payload_evidence_prompt_drag_tags(
            snapshot,
            over_budget=(
                snapshot.budget_tokens is not None
                and snapshot.budget_tokens > 0
                and snapshot.estimated_tokens > snapshot.budget_tokens
            ),
        )
    )
    warning_tags: list[str] = []
    blocker_tags: list[str] = []
    if snapshot_missing:
        warning_tags.append("prompt_payload_snapshot_missing")
    if estimated_tokens_missing:
        warning_tags.append("prompt_tokens_fallback_from_packet")
    if snapshot.budget_tokens is None:
        warning_tags.append("prompt_budget_unknown")
    if snapshot.status.value == "watch":
        warning_tags.append("prompt_payload_watch")
    elif snapshot.status.value == "degraded":
        blocker_tags.append("prompt_payload_degraded")
    for tag in prompt_drag_tags:
        if "over_budget" in tag or "degraded" in tag:
            blocker_tags.append(tag)
        elif "watch" in tag or "growth" in tag:
            warning_tags.append(tag)
    return RelayPromptPayloadMeterEvidence(
        meter_evidence_id=f"relay-prompt-meter:{packet.packet_id}:{lane_label}",
        heartbeat_id=packet.packet_id,
        lane_id=lane_label,
        route_id=(
            payload_evidence.route_id
            if payload_evidence is not None
            else f"tier-{plan.route.risk_tier}:{plan.route.mode.value}"
        ),
        selected_provider=(
            payload_evidence.selected_provider if payload_evidence is not None else None
        ),
        exact_model_id=(
            payload_evidence.selected_model if payload_evidence is not None else None
        ),
        provider_route_kind=(
            payload_evidence.provider_route_kind
            if payload_evidence is not None
            else "unknown"
        ),
        trust_state=payload_evidence.trust_state if payload_evidence else "unknown",
        capability_tier=payload_evidence.capability_tier if payload_evidence else None,
        display_label=snapshot.display_label,
        estimated_prompt_tokens=snapshot.estimated_tokens,
        prompt_budget_tokens=snapshot.budget_tokens,
        budget_percent=_round_meter_percent(snapshot.budget_percent),
        payload_status=snapshot.status.value,
        growth_delta_tokens=snapshot.growth_tokens,
        growth_delta_percent=_round_meter_percent(snapshot.growth_percent),
        q_mode=snapshot.queue_mode,
        growth_state=_payload_evidence_growth_state(snapshot),
        prompt_drag_tags=prompt_drag_tags,
        warning_tags=tuple(dict.fromkeys(warning_tags)),
        blocker_tags=tuple(dict.fromkeys(blocker_tags)),
        payload_evidence_ref=_payload_evidence_ref(payload_evidence),
        prompt_payload_snapshot_hash=(
            payload_evidence.prompt_payload_snapshot_hash if payload_evidence else None
        ),
        model_metadata_ref=payload_evidence.model_metadata_ref if payload_evidence else None,
        external_review_evidence_ref=(
            payload_evidence.external_review_evidence_ref if payload_evidence else None
        ),
    )


def _proof_trail_evidence_ids(proof_trail: ProofTrail | None) -> tuple[str, ...]:
    if proof_trail is None:
        return ()
    return tuple(evidence.id for evidence in proof_trail.evidence)


def _relay_proof_requirement_for_aegis(plan: RelayDispatchPlan) -> str:
    proof_required = tuple(plan.packet.proof_required or plan.route.audit.proof_required)
    if plan.route.requires_human_gate or "human_gate_approval" in proof_required:
        return "human_gate"
    if plan.route.requires_independence:
        if any(
            proof in proof_required
            for proof in ("independent_dual_model_lanes", "independent_review_when_meaningful")
        ):
            return "dual_review"
    if not proof_required:
        return "none"
    if "aegis_clean_proof_trail" in proof_required:
        return "security_review" if plan.route.risk_tier >= 3 else "code_review"
    if "prompt_payload_snapshot" in proof_required:
        return "telemetry"
    return proof_required[0]


def _build_aegis_prompt_packet_policy_metadata(
    plan: RelayDispatchPlan,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
    *,
    proof_trail: ProofTrail | None = None,
    human_gate_approved: bool = False,
    demotion_target_tier: int | None = None,
) -> AegisPromptPacketProofMetadata:
    """Adapt sealed Relay packet/envelope facts into Aegis policy metadata."""
    packet = plan.packet
    packet_proof = getattr(packet, "proof_metadata", None)
    evidence_ids = (
        dispatch_envelope.aegis_evidence_ids
        if dispatch_envelope and dispatch_envelope.aegis_evidence_ids
        else _proof_trail_evidence_ids(proof_trail)
    )
    packet_hash = (
        dispatch_envelope.packet_hash
        if dispatch_envelope and dispatch_envelope.packet_hash is not None
        else (packet_proof.packet_hash if packet_proof else None)
    )
    packet_hash_status = "present" if packet_hash else (
        "unavailable" if packet_proof else "missing"
    )
    snapshot_hash = (
        dispatch_envelope.payload_snapshot_hash
        if dispatch_envelope and dispatch_envelope.payload_snapshot_hash is not None
        else (
            packet_proof.prompt_payload_snapshot_hash
            if packet_proof and packet_proof.snapshot_hash_available
            else None
        )
    )
    snapshot_status = "present" if snapshot_hash else "unavailable"
    proof_requirement = _relay_proof_requirement_for_aegis(plan)

    return AegisPromptPacketProofMetadata(
        packet_id=getattr(packet, "packet_id", None),
        packet_hash_status=packet_hash_status,
        packet_hash=packet_hash,
        prompt_tokens=getattr(packet, "prompt_tokens", -1),
        max_context_tokens=packet.budget.max_context_tokens,
        budget_ref=(
            dispatch_envelope.prompt_budget_ref
            if dispatch_envelope and dispatch_envelope.prompt_budget_ref is not None
            else (packet_proof.prompt_budget_ref if packet_proof else None)
        ),
        source_lineage=dict(packet.source_lineage),
        allowed_sources=tuple(packet.budget.allowed_sources),
        aegis_evidence_ids=evidence_ids,
        risk_tier=plan.route.risk_tier,
        proof_requirement=proof_requirement,
        selected_model_id=dispatch_envelope.exact_model_id if dispatch_envelope else None,
        model_trust_state=(
            dispatch_envelope.trust_state
            if dispatch_envelope
            else plan.route.audit.trust_state.value
        ),
        snapshot_requirement="required" if plan.route.risk_tier >= 2 else "not_required",
        snapshot_status=snapshot_status,
        human_gate_required=plan.route.requires_human_gate,
        human_approval_present=human_gate_approved,
        dual_lane_required=plan.route.requires_independence,
        dual_lane_proof_present=bool(evidence_ids) if plan.route.requires_independence else False,
        demotion_target_tier=demotion_target_tier,
    )


def _relay_prompt_packet_policy_evidence(
    result: PromptPacketProofPolicyResult,
    metadata: AegisPromptPacketProofMetadata,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
) -> RelayPromptPacketPolicyEvidence:
    return RelayPromptPacketPolicyEvidence(
        decision=result.decision.value,
        severity=result.severity,
        reason=result.reason,
        evidence_ids=result.evidence_ids,
        blockers=result.blockers,
        warnings=result.warnings,
        demote_to_tier=result.demote_to_tier,
        packet_id=metadata.packet_id,
        packet_hash=metadata.packet_hash,
        prompt_budget_ref=metadata.budget_ref,
        packet_proof_metadata_ref=(
            dispatch_envelope.packet_proof_metadata_ref if dispatch_envelope else None
        ),
    )


def _relay_prompt_packet_policy_disposition(
    plan: RelayDispatchPlan,
    evidence: RelayPromptPacketPolicyEvidence,
) -> RelayPromptPacketPolicyDisposition:
    """Map evaluated policy evidence into a conservative Relay transport action."""
    decision = evidence.decision
    if decision in (
        PromptPacketProofDecision.ALLOW.value,
        PromptPacketProofDecision.WARN.value,
    ):
        audit_tags = (
            ("aegis_prompt_packet_policy_warn",)
            if decision == PromptPacketProofDecision.WARN.value
            else ("aegis_prompt_packet_policy_allow",)
        )
        return RelayPromptPacketPolicyDisposition(
            transport_allowed=True,
            transport_action="dispatch",
            fallback_allowed=True,
            audit_tags=audit_tags,
            explanation=evidence.reason,
        )

    if decision == PromptPacketProofDecision.DEMOTE.value:
        target = evidence.demote_to_tier
        demotion_authorized = (
            target is not None
            and isinstance(target, int)
            and 0 <= target < plan.route.risk_tier
        )
        blockers = (
            "aegis_demotion_requires_fresh_policy_evaluation",
        )
        if not demotion_authorized:
            blockers = blockers + ("aegis_demotion_target_unauthorized",)
        return RelayPromptPacketPolicyDisposition(
            transport_allowed=False,
            transport_action="demote_requires_fresh_evaluation",
            retry_requires_fresh_evaluation=True,
            demotion_target_tier=target,
            demotion_authorized=demotion_authorized,
            blockers=blockers,
            audit_tags=(
                "rebuild_prompt_packet_for_demoted_route",
                "rerun_aegis_before_transport",
                "no_silent_fallback",
            ),
            explanation=evidence.reason,
        )

    if decision == PromptPacketProofDecision.HUMAN_GATE.value:
        blockers = evidence.blockers or ("aegis_human_gate_required",)
        if "aegis_human_gate_required" not in blockers:
            blockers = blockers + ("aegis_human_gate_required",)
        return RelayPromptPacketPolicyDisposition(
            transport_allowed=False,
            transport_action="human_gate_required",
            fail_closed=True,
            retry_requires_fresh_evaluation=True,
            blockers=blockers,
            audit_tags=(
                "wait_for_review_console_approval",
                "rerun_aegis_before_transport",
            ),
            explanation=evidence.reason,
        )

    if decision == PromptPacketProofDecision.BLOCK.value:
        blockers = evidence.blockers or ("aegis_prompt_packet_policy_blocked",)
        if any("missing" in blocker for blocker in blockers):
            blockers = blockers + ("missing_metadata_fail_closed",)
        return RelayPromptPacketPolicyDisposition(
            transport_allowed=False,
            transport_action="block",
            fail_closed=True,
            retry_requires_fresh_evaluation=True,
            blockers=tuple(dict.fromkeys(blockers)),
            audit_tags=(
                "correct_metadata_before_retry",
                "rerun_aegis_before_transport",
            ),
            explanation=evidence.reason,
        )

    return RelayPromptPacketPolicyDisposition(
        transport_allowed=False,
        transport_action="block",
        fail_closed=True,
        retry_requires_fresh_evaluation=True,
        blockers=("unknown_prompt_packet_policy_decision",),
        audit_tags=(
            "correct_metadata_before_retry",
            "rerun_aegis_before_transport",
        ),
        explanation=evidence.reason,
    )


def _evaluate_relay_prompt_packet_policy(
    plan: RelayDispatchPlan,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
    *,
    proof_trail: ProofTrail | None = None,
    human_gate_approved: bool = False,
    demotion_target_tier: int | None = None,
) -> RelayPromptPacketPolicyEvidence:
    metadata = _build_aegis_prompt_packet_policy_metadata(
        plan,
        dispatch_envelope,
        proof_trail=proof_trail,
        human_gate_approved=human_gate_approved,
        demotion_target_tier=demotion_target_tier,
    )
    result = evaluate_prompt_packet_proof_policy(metadata)
    return _relay_prompt_packet_policy_evidence(result, metadata, dispatch_envelope)


def _dispatch_blocking_tags(
    tags: tuple[str, ...],
    *,
    risk_tier: int,
) -> tuple[str, ...]:
    blocking_prefixes = ("aegis_",)
    blocking_tags = {
        "budget_exceeded",
        "context_window_unknown",
        "provider_metadata_missing",
        "packet_proof_metadata_missing",
        "prompt_budget_exceeded",
        "source_lineage_noncompliant",
        "telemetry_unavailable",
        "unknown_route_class",
        "unknown_session_action",
        "vendor_unknown",
        "model_id_unknown",
        "tier3_dual_lane_independence_missing",
        "human_gate_proof_missing",
    }
    if risk_tier >= 2:
        blocking_tags.update(
            {
                "completion_tokens_unavailable",
                "latency_ms_unavailable",
                "prompt_snapshot_missing",
                "response_hash_unavailable",
            }
        )
    return tuple(
        tag
        for tag in tags
        if tag in blocking_tags or tag.startswith(blocking_prefixes)
    )


def _build_dispatch_envelope(
    plan: RelayDispatchPlan,
    *,
    lane_role: ModelRole | None = None,
    requested_model_id: str | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
    route_metadata: ModelRouteMetadataBinding | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    fallback_blockers: tuple[str, ...] = (),
    aegis_gate_decision: str | None = None,
    aegis_evidence_ids: tuple[str, ...] = (),
) -> RelayDispatchEnvelope:
    """Build the safe Relay dispatch envelope used for audit/transport hardening."""
    route = plan.route
    audit = route.audit
    packet = plan.packet
    packet_proof = getattr(packet, "proof_metadata", None)

    selected_provider = None
    exact_model_id = requested_model_id
    capability_tier = None
    trust_state = audit.trust_state.value
    if route_metadata is not None:
        selected_provider = route_metadata.provider_name
        exact_model_id = route_metadata.model_name
        capability_tier = route_metadata.capability_tier
        trust_state = route_metadata.trust_state
    elif adapter_metadata is not None:
        selected_provider = adapter_metadata.provider_name
        exact_model_id = adapter_metadata.model_name
        capability_tier = adapter_metadata.capability_tier
        trust_state = adapter_metadata.trust_state

    tags = _dedupe_tags(
        payload_evidence.telemetry_error_tags if payload_evidence else (),
        packet_proof.blocked_tags if packet_proof else ("packet_proof_metadata_missing",),
        fallback_blockers,
    )
    blocking_tags = _dispatch_blocking_tags(tags, risk_tier=route.risk_tier)
    if route.risk_tier >= 2 and selected_provider is None:
        blocking_tags = _dedupe_tags(blocking_tags, ("vendor_unknown",))
    if route.risk_tier >= 2 and exact_model_id is None:
        blocking_tags = _dedupe_tags(blocking_tags, ("model_id_unknown",))

    lane_label = lane_role.value if lane_role else "no-lane"
    model_label = exact_model_id or requested_model_id or "unknown-model"

    return RelayDispatchEnvelope(
        envelope_id=f"relay-dispatch:{packet.packet_id}:{lane_label}:{model_label}",
        heartbeat_id=packet.packet_id,
        role=lane_role.value if lane_role else None,
        requested_model_id=requested_model_id,
        exact_model_id=exact_model_id,
        selected_provider=selected_provider,
        route_id=f"tier-{route.risk_tier}:{route.mode.value}",
        route_class=audit.route_class.value if audit.route_class else None,
        route_kind=audit.route_kind.value,
        risk_tier=route.risk_tier,
        trust_state=trust_state,
        capability_tier=capability_tier,
        payload_evidence_ref=_payload_evidence_ref(payload_evidence),
        payload_snapshot_hash=(
            payload_evidence.prompt_payload_snapshot_hash if payload_evidence else None
        ),
        packet_hash=packet_proof.packet_hash if packet_proof else None,
        prompt_budget_ref=packet_proof.prompt_budget_ref if packet_proof else None,
        source_lineage_compliant=(
            packet_proof.source_lineage_compliant if packet_proof else None
        ),
        packet_proof_metadata_ref=(
            f"prompt-packet-proof:{packet_proof.packet_id}" if packet_proof else None
        ),
        aegis_gate_decision=aegis_gate_decision,
        aegis_evidence_ids=(
            aegis_evidence_ids or (packet_proof.aegis_evidence_ids if packet_proof else ())
        ),
        proof_required=(
            packet_proof.proof_required if packet_proof else tuple(audit.proof_required)
        ),
        human_gate_required=route.requires_human_gate,
        blocked_error_tags=blocking_tags,
        safe_to_dispatch=not blocking_tags,
        transport_payload_kind="approved_prompt_text" if lane_role else "none",
        audit_fields=(
            "heartbeat_id",
            "role",
            "requested_model_id",
            "exact_model_id",
            "selected_provider",
            "route_id",
            "route_class",
            "route_kind",
            "risk_tier",
            "trust_state",
            "capability_tier",
            "payload_evidence_ref",
            "packet_hash",
            "prompt_budget_ref",
            "source_lineage_compliant",
            "packet_proof_metadata_ref",
            "proof_required",
            "blocked_error_tags",
            "safe_to_dispatch",
        ),
    )


def _build_dispatch_metadata_envelope(
    plan: RelayDispatchPlan,
    *,
    lane_role: ModelRole | None = None,
    requested_model_id: str | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
    route_metadata: ModelRouteMetadataBinding | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
) -> RelayDispatchMetadataEnvelope:
    """Serialize already-bound model metadata for future provider transports."""
    route = plan.route
    packet = plan.packet
    lane_id = (
        payload_evidence.lane_id
        if payload_evidence is not None
        else (f"{lane_role.value}:{requested_model_id}" if lane_role else None)
    )
    role = lane_role.value if lane_role else (dispatch_envelope.role if dispatch_envelope else None)
    exact_model_id = (
        route_metadata.model_name
        if route_metadata is not None
        else (
            payload_evidence.selected_model
            if payload_evidence is not None and payload_evidence.selected_model is not None
            else (dispatch_envelope.exact_model_id if dispatch_envelope else requested_model_id)
        )
    )
    selected_provider = (
        route_metadata.provider_name
        if route_metadata is not None
        else (
            payload_evidence.selected_provider
            if payload_evidence is not None
            else (dispatch_envelope.selected_provider if dispatch_envelope else None)
        )
    )
    provider_route_kind = (
        route_metadata.provider_route_kind
        if route_metadata is not None
        else (
            payload_evidence.provider_route_kind
            if payload_evidence is not None
            else "unknown"
        )
    )
    trust_mode = _adapter_metadata_candidate_value(adapter_metadata, "trust_mode")
    if trust_mode is None:
        trust_mode = provider_route_kind if provider_route_kind != "unknown" else "unknown"
    trust_state = (
        route_metadata.trust_state
        if route_metadata is not None
        else (
            payload_evidence.trust_state
            if payload_evidence is not None
            else (dispatch_envelope.trust_state if dispatch_envelope else "unknown")
        )
    )
    proof_strength = _adapter_metadata_candidate_value(
        adapter_metadata,
        "proof_strength",
    ) or "unknown"
    direct_endpoint_evidence_ref = _adapter_metadata_candidate_value(
        adapter_metadata,
        "direct_endpoint_evidence_ref",
    )
    aggregator_evidence_ref = _adapter_metadata_candidate_value(
        adapter_metadata,
        "aggregator_evidence_ref",
    )
    validation_evidence_ref = _adapter_metadata_candidate_value(
        adapter_metadata,
        "validation_evidence_ref",
    )
    allowed_task_types = _adapter_metadata_candidate_tuple(
        adapter_metadata,
        "allowed_task_types",
    )
    blocked_task_types = _adapter_metadata_candidate_tuple(
        adapter_metadata,
        "blocked_task_types",
    )
    blocked_authority_tags = _adapter_metadata_candidate_tuple(
        adapter_metadata,
        "blocked_authorities",
    )
    max_risk_tier = _adapter_metadata_candidate_int(adapter_metadata, "max_risk_tier")
    context_window = (
        route_metadata.context_budget
        if route_metadata is not None
        else (
            payload_evidence.model_context_window_tokens
            if payload_evidence is not None
            else None
        )
    )
    prompt_budget = (
        route_metadata.prompt_payload_budget
        if route_metadata is not None
        else (payload_evidence.prompt_budget_tokens if payload_evidence is not None else None)
    )
    prompt_status = (
        route_metadata.prompt_payload_status
        if route_metadata is not None and route_metadata.prompt_payload_status is not None
        else (payload_evidence.budget_status if payload_evidence is not None else "unknown")
    )
    requires_external_review = (
        route_metadata.requires_external_review
        if route_metadata is not None
        else (
            payload_evidence.requires_external_review
            if payload_evidence is not None
            else False
        )
    )
    external_review_status = (
        route_metadata.external_review_status
        if route_metadata is not None
        else (
            payload_evidence.external_review_status
            if payload_evidence is not None
            else "not_required"
        )
    )

    validation_tags: list[str] = []
    if route_metadata is None:
        validation_tags.append("model_metadata_missing")
    if selected_provider is None:
        validation_tags.append("selected_provider_missing")
    if exact_model_id is None:
        validation_tags.append("exact_model_id_missing")
    if provider_route_kind == "unknown":
        validation_tags.append("provider_route_kind_unknown")
    if trust_mode == "unknown":
        validation_tags.append("trust_mode_unknown")
    if trust_state == "unknown":
        validation_tags.append("trust_state_unknown")
    if provider_route_kind == "direct" and not direct_endpoint_evidence_ref:
        validation_tags.append("direct_endpoint_evidence_missing")
    if provider_route_kind == "aggregator" and direct_endpoint_evidence_ref:
        validation_tags.append("aggregator_direct_endpoint_mismatch")
    if provider_route_kind == "aggregator" and not aggregator_evidence_ref:
        validation_tags.append("aggregator_evidence_missing")
    if context_window is None:
        validation_tags.append("context_window_unknown")
    if prompt_budget is None:
        validation_tags.append("prompt_payload_budget_unknown")
    if prompt_status == "unknown":
        validation_tags.append("prompt_payload_status_unknown")
    if requires_external_review and external_review_status != "passed":
        validation_tags.append(f"external_review_{external_review_status}")
    if dispatch_envelope is not None and dispatch_envelope.blocked_error_tags:
        validation_tags.extend(dispatch_envelope.blocked_error_tags)

    fail_closed_tags = tuple(
        tag
        for tag in dict.fromkeys(validation_tags)
        if tag.endswith("_missing")
        or tag.endswith("_unknown")
        or tag.startswith("external_review_")
        or tag.endswith("_mismatch")
        or tag in {"vendor_unknown", "model_id_unknown", "packet_proof_metadata_missing"}
    )
    fail_closed_advisory = bool(fail_closed_tags) or (
        dispatch_envelope is not None and not dispatch_envelope.safe_to_dispatch
    )

    lane_label = role or "no-lane"
    model_label = exact_model_id or requested_model_id or "unknown-model"
    return RelayDispatchMetadataEnvelope(
        envelope_id=f"relay-dispatch-metadata:{packet.packet_id}:{lane_label}:{model_label}",
        heartbeat_id=packet.packet_id,
        lane_id=lane_id,
        role=role,
        requested_model_id=requested_model_id,
        exact_model_id=exact_model_id,
        selected_provider=selected_provider,
        provider_route_kind=provider_route_kind,
        trust_mode=trust_mode,
        trust_state=trust_state,
        proof_strength=proof_strength,
        capability_tier=(
            route_metadata.capability_tier
            if route_metadata is not None
            else (
                payload_evidence.capability_tier
                if payload_evidence is not None
                else (dispatch_envelope.capability_tier if dispatch_envelope else None)
            )
        ),
        direct_endpoint_evidence_ref=direct_endpoint_evidence_ref,
        aggregator_evidence_ref=aggregator_evidence_ref,
        validation_evidence_ref=validation_evidence_ref,
        allowed_task_types=allowed_task_types,
        blocked_task_types=blocked_task_types,
        blocked_authority_tags=blocked_authority_tags,
        max_risk_tier=max_risk_tier,
        context_window_tokens=context_window,
        prompt_payload_budget_tokens=prompt_budget,
        prompt_payload_status=prompt_status,
        estimated_prompt_tokens=(
            route_metadata.prompt_payload_estimated_tokens
            if route_metadata is not None
            else (
                payload_evidence.estimated_prompt_tokens
                if payload_evidence is not None
                else None
            )
        ),
        prompt_budget_percent=(
            route_metadata.prompt_payload_budget_percent
            if route_metadata is not None
            else (payload_evidence.budget_percent if payload_evidence is not None else None)
        ),
        prompt_growth_tokens=(
            payload_evidence.delta_tokens if payload_evidence is not None else None
        ),
        prompt_growth_percent=(
            payload_evidence.delta_percent if payload_evidence is not None else None
        ),
        growth_state=payload_evidence.growth_state if payload_evidence is not None else "unknown",
        prompt_drag_tags=payload_evidence.prompt_drag_tags if payload_evidence is not None else (),
        requires_external_review=requires_external_review,
        external_review_status=external_review_status,
        model_metadata_ref=(
            route_metadata.model_metadata_ref
            if route_metadata is not None
            else (payload_evidence.model_metadata_ref if payload_evidence is not None else None)
        ),
        external_review_evidence_ref=(
            route_metadata.external_review_evidence_ref
            if route_metadata is not None
            else (
                payload_evidence.external_review_evidence_ref
                if payload_evidence is not None
                else None
            )
        ),
        payload_evidence_ref=_payload_evidence_ref(payload_evidence),
        payload_snapshot_hash=(
            payload_evidence.prompt_payload_snapshot_hash if payload_evidence else None
        ),
        dispatch_envelope_ref=dispatch_envelope.envelope_id if dispatch_envelope else None,
        packet_proof_metadata_ref=(
            dispatch_envelope.packet_proof_metadata_ref if dispatch_envelope else None
        ),
        supports_completion_tokens=(
            adapter_metadata.supports_completion_tokens if adapter_metadata else False
        ),
        supports_latency_ms=adapter_metadata.supports_latency_ms if adapter_metadata else False,
        supports_payload_snapshot=(
            adapter_metadata.supports_payload_snapshot if adapter_metadata else False
        ),
        supports_response_hash=(
            adapter_metadata.supports_response_hash if adapter_metadata else False
        ),
        validation_tags=tuple(dict.fromkeys(validation_tags)),
        fail_closed_advisory=fail_closed_advisory,
        fail_closed_tags=fail_closed_tags,
        metadata_transport_allowed=not fail_closed_advisory,
        retry_requires_fresh_metadata=fail_closed_advisory,
    )


def _build_provider_result_validation_evidence(
    plan: RelayDispatchPlan,
    output: object,
    *,
    lane_role: ModelRole | None = None,
    requested_model_id: str | None = None,
    dispatch_metadata_envelope: RelayDispatchMetadataEnvelope | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
) -> RelayProviderResultValidationEvidence:
    """Build display-safe post-adapter validation evidence from metadata only."""
    packet = plan.packet
    route = plan.route
    lane_id = (
        dispatch_metadata_envelope.lane_id
        if dispatch_metadata_envelope is not None
        else (
            payload_evidence.lane_id
            if payload_evidence is not None
            else (f"{lane_role.value}:{requested_model_id}" if lane_role else None)
        )
    )
    role = (
        dispatch_metadata_envelope.role
        if dispatch_metadata_envelope is not None
        else (lane_role.value if lane_role else None)
    )
    warnings: list[str] = []
    blockers: list[str] = []

    if dispatch_metadata_envelope is None:
        blockers.append("dispatch_metadata_envelope_missing")
    else:
        blockers.extend(dispatch_metadata_envelope.fail_closed_tags)
        if dispatch_metadata_envelope.requires_external_review and (
            dispatch_metadata_envelope.external_review_status != "passed"
        ):
            blockers.append(
                f"external_review_{dispatch_metadata_envelope.external_review_status}"
            )

    output_text = output if isinstance(output, str) else None
    output_length = len(output_text) if output_text is not None else None
    normalized_output_hash = (
        hashlib.sha256(output_text.strip().encode("utf-8")).hexdigest()
        if output_text is not None
        else None
    )
    if output_text is None:
        blockers.append("adapter_result_non_string")
        response_hash_status = "unavailable"
    elif output_text == "":
        blockers.append("adapter_result_empty")
        response_hash_status = "empty"
    else:
        response_hash_status = "computed"

    supports_response_hash = (
        dispatch_metadata_envelope.supports_response_hash
        if dispatch_metadata_envelope is not None
        else False
    )
    supports_completion_tokens = (
        dispatch_metadata_envelope.supports_completion_tokens
        if dispatch_metadata_envelope is not None
        else False
    )
    supports_latency_ms = (
        dispatch_metadata_envelope.supports_latency_ms
        if dispatch_metadata_envelope is not None
        else False
    )
    if not supports_response_hash:
        warnings.append("response_hash_telemetry_unavailable")
    if not supports_completion_tokens:
        warnings.append("completion_token_telemetry_unavailable")
        warnings.append("total_token_telemetry_unavailable")
    if not supports_latency_ms:
        warnings.append("latency_telemetry_unavailable")

    prompt_status = (
        dispatch_metadata_envelope.prompt_payload_status
        if dispatch_metadata_envelope is not None
        else (payload_evidence.budget_status if payload_evidence else "unknown")
    )
    prompt_drag_tags = (
        dispatch_metadata_envelope.prompt_drag_tags
        if dispatch_metadata_envelope is not None
        else (payload_evidence.prompt_drag_tags if payload_evidence else ())
    )
    if prompt_status in {"degraded", "over_budget"}:
        blockers.append(f"prompt_payload_{prompt_status}")
    elif prompt_status == "watch":
        warnings.append("prompt_payload_watch")
    for tag in prompt_drag_tags:
        if "over_budget" in tag or "degraded" in tag:
            blockers.append(tag)
        elif "watch" in tag or "warning" in tag:
            warnings.append(tag)

    blockers_tuple = tuple(dict.fromkeys(blockers))
    warnings_tuple = tuple(dict.fromkeys(warnings))
    if blockers_tuple:
        validation_status = "blocked"
    elif prompt_status == "degraded":
        validation_status = "degraded"
    elif warnings_tuple:
        validation_status = "warning"
    elif output_text is None:
        validation_status = "unknown"
    else:
        validation_status = "valid"

    return RelayProviderResultValidationEvidence(
        result_evidence_id=f"relay-provider-result:{packet.packet_id}:{lane_id or 'no-lane'}",
        heartbeat_id=packet.packet_id,
        lane_id=lane_id,
        role=role,
        route_id=f"tier-{route.risk_tier}:{route.mode.value}",
        selected_provider=(
            dispatch_metadata_envelope.selected_provider
            if dispatch_metadata_envelope is not None
            else (payload_evidence.selected_provider if payload_evidence else None)
        ),
        exact_model_id=(
            dispatch_metadata_envelope.exact_model_id
            if dispatch_metadata_envelope is not None
            else (
                payload_evidence.selected_model
                if payload_evidence and payload_evidence.selected_model
                else requested_model_id
            )
        ),
        provider_route_kind=(
            dispatch_metadata_envelope.provider_route_kind
            if dispatch_metadata_envelope is not None
            else (payload_evidence.provider_route_kind if payload_evidence else "unknown")
        ),
        trust_mode=(
            dispatch_metadata_envelope.trust_mode
            if dispatch_metadata_envelope is not None
            else "unknown"
        ),
        trust_state=(
            dispatch_metadata_envelope.trust_state
            if dispatch_metadata_envelope is not None
            else (payload_evidence.trust_state if payload_evidence else "unknown")
        ),
        proof_strength=(
            dispatch_metadata_envelope.proof_strength
            if dispatch_metadata_envelope is not None
            else "unknown"
        ),
        capability_tier=(
            dispatch_metadata_envelope.capability_tier
            if dispatch_metadata_envelope is not None
            else (payload_evidence.capability_tier if payload_evidence else None)
        ),
        direct_endpoint_evidence_ref=(
            dispatch_metadata_envelope.direct_endpoint_evidence_ref
            if dispatch_metadata_envelope is not None
            else None
        ),
        aggregator_evidence_ref=(
            dispatch_metadata_envelope.aggregator_evidence_ref
            if dispatch_metadata_envelope is not None
            else None
        ),
        model_metadata_ref=(
            dispatch_metadata_envelope.model_metadata_ref
            if dispatch_metadata_envelope is not None
            else (payload_evidence.model_metadata_ref if payload_evidence else None)
        ),
        validation_evidence_ref=(
            dispatch_metadata_envelope.validation_evidence_ref
            if dispatch_metadata_envelope is not None
            else None
        ),
        external_review_evidence_ref=(
            dispatch_metadata_envelope.external_review_evidence_ref
            if dispatch_metadata_envelope is not None
            else (
                payload_evidence.external_review_evidence_ref
                if payload_evidence
                else None
            )
        ),
        requires_external_review=(
            dispatch_metadata_envelope.requires_external_review
            if dispatch_metadata_envelope is not None
            else (payload_evidence.requires_external_review if payload_evidence else False)
        ),
        external_review_status=(
            dispatch_metadata_envelope.external_review_status
            if dispatch_metadata_envelope is not None
            else (
                payload_evidence.external_review_status
                if payload_evidence
                else "not_required"
            )
        ),
        dispatch_metadata_envelope_ref=(
            dispatch_metadata_envelope.envelope_id
            if dispatch_metadata_envelope is not None
            else None
        ),
        payload_evidence_ref=(
            dispatch_metadata_envelope.payload_evidence_ref
            if dispatch_metadata_envelope is not None
            else _payload_evidence_ref(payload_evidence)
        ),
        payload_snapshot_hash=(
            dispatch_metadata_envelope.payload_snapshot_hash
            if dispatch_metadata_envelope is not None
            else (
                payload_evidence.prompt_payload_snapshot_hash
                if payload_evidence
                else None
            )
        ),
        packet_hash=dispatch_envelope.packet_hash if dispatch_envelope else None,
        prompt_budget_ref=(
            dispatch_envelope.prompt_budget_ref if dispatch_envelope else None
        ),
        prompt_payload_status=prompt_status,
        prompt_budget_percent=(
            dispatch_metadata_envelope.prompt_budget_percent
            if dispatch_metadata_envelope is not None
            else (payload_evidence.budget_percent if payload_evidence else None)
        ),
        prompt_growth_tokens=(
            dispatch_metadata_envelope.prompt_growth_tokens
            if dispatch_metadata_envelope is not None
            else (payload_evidence.delta_tokens if payload_evidence else None)
        ),
        prompt_growth_percent=(
            dispatch_metadata_envelope.prompt_growth_percent
            if dispatch_metadata_envelope is not None
            else (payload_evidence.delta_percent if payload_evidence else None)
        ),
        prompt_drag_tags=prompt_drag_tags,
        output_length=output_length,
        normalized_output_hash=normalized_output_hash,
        response_hash_status=response_hash_status,
        completion_tokens_status=(
            "supported_unreported"
            if supports_completion_tokens
            else "unsupported"
        ),
        total_tokens_status=(
            "supported_unreported"
            if supports_completion_tokens
            else "unsupported"
        ),
        latency_bucket="supported_unreported" if supports_latency_ms else "unsupported",
        supports_completion_tokens=supports_completion_tokens,
        supports_latency_ms=supports_latency_ms,
        supports_response_hash=supports_response_hash,
        result_validation_status=validation_status,
        warning_tags=warnings_tuple,
        blocker_tags=blockers_tuple,
        retry_requires_fresh_validation=bool(blockers_tuple),
        demotion_required=bool(blockers_tuple),
        human_gate_required=bool(blockers_tuple),
        usable_for_lane=not blockers_tuple,
    )


def _build_decision_record(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
    route_metadata: ModelRouteMetadataBinding | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
    dispatch_metadata_envelope: RelayDispatchMetadataEnvelope | None = None,
    payload_meter_evidence: RelayPromptPayloadMeterEvidence | None = None,
    prompt_packet_policy_evidence: RelayPromptPacketPolicyEvidence | None = None,
    aegis_gate_decision: str | None = None,
    aegis_explanation: str = "",
) -> RelayDecisionRecord:
    """Generate a provider-neutral decision record from a dispatch plan.

    Exposes audit fields for Prime to understand route selection rationale:
    route class, session action, context health, dual-lane requirement,
    trust/proof blockers, account-vs-API precedence, cost/privacy, and
    fallback blockers. Populates vendor/model_id from adapter metadata when
    available, or marks as unknown stop conditions.

    Optional Aegis gate evidence (aegis_gate_decision, aegis_explanation):
    - "block" decision adds explicit fallback blocker and explanation
    - "human_gate" decision adds human gate requirement blocker and explanation
    - "demote" decision adds non-silent demotion note to explanation
    """
    from .prompt_payload_meter import PayloadStatus

    route = plan.route
    audit = route.audit
    packet = plan.packet
    packet_proof = getattr(packet, "proof_metadata", None)
    lanes = plan.lanes

    fallback_blockers = list(audit.fallback_blockers)
    fallback_allowed = len(fallback_blockers) == 0
    if packet_proof is None:
        fallback_blockers.append("packet_proof_metadata_missing")
        fallback_allowed = False
    elif packet_proof.blocked_tags:
        fallback_blockers.extend(packet_proof.blocked_tags)
        fallback_allowed = False

    # Check for stop conditions
    if audit.route_class is None and route.risk_tier >= 1:
        fallback_blockers.append("unknown_route_class")
        fallback_allowed = False

    if audit.session_action is None and route.risk_tier >= 1:
        fallback_blockers.append("unknown_session_action")
        fallback_allowed = False

    if route.risk_tier == 3 and route.requires_independence:
        if not any(lane.independent for lane in lanes):
            fallback_blockers.append("tier3_dual_lane_independence_missing")
            fallback_allowed = False

    if route.requires_human_gate and not audit.proof_required:
        fallback_blockers.append("human_gate_proof_missing")
        fallback_allowed = False

    if route_metadata is None and adapter_metadata is not None:
        route_metadata = bind_model_route_metadata(
            adapter_metadata,
            route_risk_tier=route.risk_tier,
            route_cost_posture=route.cost_posture,
            route_latency_posture=route.latency_posture,
            payload_snapshot=payload_snapshot,
        )
    if payload_evidence is None:
        payload_evidence = _build_payload_evidence(
            plan,
            payload_snapshot,
            adapter_metadata,
            route_metadata,
        )

    # Populate vendor from adapter metadata or mark unknown for nontrivial tiers
    vendor = None
    if route_metadata is not None:
        vendor = route_metadata.provider_name
    elif adapter_metadata is not None:
        vendor = adapter_metadata.provider_name
    elif route.risk_tier >= 2:
        vendor = "unknown"
        # Treat vendor identity unknown as explicit blocker for Tier 2+
        fallback_blockers.append("vendor_unknown")
        fallback_allowed = False

    # Populate model_id from preferred_model of first builder lane or mark unknown
    model_id = None
    if lanes:
        for lane in lanes:
            if lane.role.value == "builder":
                model_id = lane.preferred_model
                break
    if model_id is None and route.risk_tier >= 2:
        model_id = "unknown"
        # Treat model identity unknown as explicit blocker for Tier 2+
        fallback_blockers.append("model_id_unknown")
        fallback_allowed = False

    lane_independence_reason = ""
    if route.requires_independence and len(fallback_blockers) > 0:
        if "dual_lane_independence_required" in fallback_blockers or "tier3_dual_lane_independence_missing" in fallback_blockers:
            lane_independence_reason = (
                "Tier 3 dual-lane independence required for meaningful decisions"
            )

    # Handle Aegis gate evidence: block and human_gate add explicit fallback blockers
    if aegis_gate_decision == "block":
        fallback_blockers.append("aegis_gate_blocked")
        fallback_allowed = False
    elif aegis_gate_decision == "human_gate":
        fallback_blockers.append("aegis_human_gate_required")
        fallback_allowed = False

    prompt_payload_status = None
    if route_metadata is not None and route_metadata.prompt_payload_status is not None:
        prompt_payload_status = route_metadata.prompt_payload_status
    elif payload_snapshot is not None:
        prompt_payload_status = payload_snapshot.status.value

    account_or_api_source = "unknown"
    if audit.route_precedence:
        account_or_api_source = audit.route_precedence[0].value

    explanation = (
        f"Risk tier {route.risk_tier}: {route.reason}. "
        f"Route: {audit.route_class.value if audit.route_class else 'unknown'}. "
        f"Context: {route.context_health.value}. "
        f"Session: {audit.session_action.value}. "
        f"Vendor: {vendor or 'not yet bound'}."
    )

    # Append Aegis gate explanation if provided
    if aegis_gate_decision:
        if aegis_gate_decision == "demote":
            explanation += f" Aegis: demoted per gate decision (details: {aegis_explanation})."
        elif aegis_gate_decision in ("block", "human_gate"):
            explanation += f" Aegis: {aegis_gate_decision} gate decision ({aegis_explanation})."

    first_builder_lane = None
    if lanes:
        first_builder_lane = next(
            (lane for lane in lanes if lane.role.value == "builder"),
            lanes[0],
        )
    prior_envelope = dispatch_envelope
    if dispatch_envelope is None or fallback_blockers or aegis_gate_decision:
        dispatch_envelope = _build_dispatch_envelope(
            plan,
            lane_role=first_builder_lane.role if first_builder_lane else None,
            requested_model_id=(
                first_builder_lane.preferred_model if first_builder_lane else model_id
            ),
            adapter_metadata=adapter_metadata,
            route_metadata=route_metadata,
            payload_evidence=payload_evidence,
            fallback_blockers=tuple(fallback_blockers),
            aegis_gate_decision=aegis_gate_decision,
            aegis_evidence_ids=prior_envelope.aegis_evidence_ids if prior_envelope else (),
        )
    packet_aegis_evidence_ids = (
        dispatch_envelope.aegis_evidence_ids
        if dispatch_envelope and dispatch_envelope.aegis_evidence_ids
        else (packet_proof.aegis_evidence_ids if packet_proof else ())
    )
    if dispatch_metadata_envelope is None:
        dispatch_metadata_envelope = _build_dispatch_metadata_envelope(
            plan,
            lane_role=first_builder_lane.role if first_builder_lane else None,
            requested_model_id=(
                first_builder_lane.preferred_model if first_builder_lane else model_id
            ),
            route_metadata=route_metadata,
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )
    if payload_meter_evidence is None:
        payload_meter_evidence = _build_prompt_payload_meter_evidence(
            plan,
            payload_snapshot,
            payload_evidence,
            lane_id=(
                payload_evidence.lane_id
                if payload_evidence is not None and payload_evidence.lane_id
                else (
                    f"{first_builder_lane.role.value}:{first_builder_lane.preferred_model}"
                    if first_builder_lane
                    else None
                )
            ),
        )

    return RelayDecisionRecord(
        heartbeat_id=packet.packet_id,
        project=None,
        surface_mode=None,
        intent=None,
        role="builder",
        risk_tier=route.risk_tier,
        session_action=audit.session_action.value,
        route_class=audit.route_class.value if audit.route_class else None,
        vendor=vendor,
        model_id=model_id,
        account_or_api_source=account_or_api_source,
        context_health=route.context_health.value,
        prompt_payload_status=prompt_payload_status,
        dual_lane_required=route.requires_independence,
        lane_independence_reason=lane_independence_reason,
        trust_state=audit.trust_state.value,
        proof_required=(
            packet_proof.proof_required if packet_proof else tuple(audit.proof_required)
        ),
        human_gate_required=route.requires_human_gate,
        cost_posture=route.cost_posture.value,
        latency_posture=route.latency_posture.value,
        privacy_notes=route.privacy_level.value,
        fallback_allowed=fallback_allowed,
        fallback_blockers=tuple(fallback_blockers),
        observability_fields=audit.telemetry_required,
        telemetry_required=audit.telemetry_required,
        explanation_for_prime=explanation,
        aegis_gate_decision=aegis_gate_decision,
        aegis_evidence_ids=packet_aegis_evidence_ids,
        aegis_explanation=aegis_explanation,
        route_metadata=route_metadata,
        payload_evidence=payload_evidence,
        payload_meter_evidence=payload_meter_evidence,
        dispatch_envelope=dispatch_envelope,
        dispatch_metadata_envelope=dispatch_metadata_envelope,
        packet_hash=packet_proof.packet_hash if packet_proof else None,
        prompt_budget_ref=packet_proof.prompt_budget_ref if packet_proof else None,
        source_lineage_compliant=(
            packet_proof.source_lineage_compliant if packet_proof else None
        ),
        packet_proof_metadata_ref=(
            f"prompt-packet-proof:{packet_proof.packet_id}" if packet_proof else None
        ),
        packet_proof_blocked_tags=(
            packet_proof.blocked_tags
            if packet_proof
            else ("packet_proof_metadata_missing",)
        ),
        prompt_packet_policy_evidence=prompt_packet_policy_evidence,
    )


def execute_relay_dispatch_plan(
    plan: RelayDispatchPlan,
    model_call: ModelCallFn,
    proof_trail: ProofTrail | None = None,
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
    include_decision_record: bool = False,
) -> RelayExecutionSummary:
    """
    Execute every lane in *plan* by calling model_call(lane.payload).

    Only the lane payload is forwarded to model_call — no role, model name,
    or metadata. Exceptions are caught per-lane and converted to
    RelayExecutionError entries; successful outputs become RelayExecutionResult
    entries. Lane order matches plan.lanes.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane
    for inclusion in execution results and proof trail evidence.

    If include_decision_record is True, generates a RelayDecisionRecord exposing
    audit fields for Prime to explain the route selection.
    """
    _assert_proof_gate_clear(plan, proof_trail)

    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []
    snapshots = payload_snapshots or tuple(None for _ in plan.lanes)
    payload_evidences = tuple(
        _build_payload_evidence(
            plan,
            snapshot,
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
        )
        for lane, snapshot in zip(plan.lanes, snapshots)
    )
    payload_meter_evidences = tuple(
        _build_prompt_payload_meter_evidence(
            plan,
            snapshot,
            payload_evidence,
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
        )
        for lane, snapshot, payload_evidence in zip(
            plan.lanes,
            snapshots,
            payload_evidences,
        )
    )
    dispatch_envelopes = tuple(
        _build_dispatch_envelope(
            plan,
            lane_role=lane.role,
            requested_model_id=lane.preferred_model,
            payload_evidence=payload_evidence,
            aegis_evidence_ids=_proof_trail_evidence_ids(proof_trail),
        )
        for lane, payload_evidence in zip(plan.lanes, payload_evidences)
    )
    dispatch_metadata_envelopes = tuple(
        _build_dispatch_metadata_envelope(
            plan,
            lane_role=lane.role,
            requested_model_id=lane.preferred_model,
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )
        for lane, payload_evidence, dispatch_envelope in zip(
            plan.lanes,
            payload_evidences,
            dispatch_envelopes,
        )
    )

    for lane, snapshot, payload_evidence, payload_meter_evidence, dispatch_envelope, dispatch_metadata_envelope in zip(
        plan.lanes,
        snapshots,
        payload_evidences,
        payload_meter_evidences,
        dispatch_envelopes,
        dispatch_metadata_envelopes,
    ):
        try:
            output = model_call(lane.payload)
            result_validation_evidence = _build_provider_result_validation_evidence(
                plan,
                output,
                lane_role=lane.role,
                requested_model_id=lane.preferred_model,
                dispatch_metadata_envelope=dispatch_metadata_envelope,
                payload_evidence=payload_evidence,
                dispatch_envelope=dispatch_envelope,
            )
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    payload_evidence=payload_evidence,
                    payload_meter_evidence=payload_meter_evidence,
                    dispatch_envelope=dispatch_envelope,
                    dispatch_metadata_envelope=dispatch_metadata_envelope,
                    provider_result_validation_evidence=result_validation_evidence,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                RelayExecutionError(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    error=str(exc),
                )
            )

    decision_record = None
    if include_decision_record:
        first_snapshot = snapshots[0] if snapshots else None
        first_payload_evidence = payload_evidences[0] if payload_evidences else None
        first_payload_meter_evidence = (
            payload_meter_evidences[0] if payload_meter_evidences else None
        )
        decision_record = _build_decision_record(
            plan,
            first_snapshot,
            payload_evidence=first_payload_evidence,
            dispatch_envelope=dispatch_envelopes[0] if dispatch_envelopes else None,
            dispatch_metadata_envelope=(
                dispatch_metadata_envelopes[0] if dispatch_metadata_envelopes else None
            ),
        )
        if results:
            decision_record = replace(
                decision_record,
                payload_meter_evidence=first_payload_meter_evidence,
                provider_result_validation_evidence=(
                    results[0].provider_result_validation_evidence
                ),
            )

    return RelayExecutionSummary(
        results=tuple(results),
        errors=tuple(errors),
        decision_record=decision_record,
    )


def execute_relay_plan_with_registry(
    plan: RelayDispatchPlan,
    registry: AdapterRegistry,
    proof_trail: ProofTrail | None = None,
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
    include_decision_record: bool = False,
) -> RelayExecutionSummary:
    """
    Execute a plan with per-lane adapter resolution from the registry.

    Pre-resolves all adapters before any call — raises MissingAdapterError
    before the first model call if any lane's adapter is missing. The Aegis
    proof gate is checked first; blocking evidence prevents resolution.
    Only lane.payload crosses to the adapter; role and metadata are not forwarded.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane
    for inclusion in execution results and proof trail evidence.

    If include_decision_record is True, generates a RelayDecisionRecord exposing
    audit fields for Prime to explain the route selection.
    """
    _assert_proof_gate_clear(plan, proof_trail)

    resolved_adapters = [
        registry.resolve(lane.role, lane.preferred_model) for lane in plan.lanes
    ]

    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []
    snapshots = payload_snapshots or tuple(None for _ in plan.lanes)
    resolved_route_metadata = tuple(
        bind_model_route_metadata(
            adapter.metadata,
            route_risk_tier=plan.route.risk_tier,
            route_cost_posture=plan.route.cost_posture,
            route_latency_posture=plan.route.latency_posture,
            payload_snapshot=snapshot,
        )
        for adapter, snapshot in zip(resolved_adapters, snapshots)
    )
    payload_evidences = tuple(
        _build_payload_evidence(
            plan,
            snapshot,
            adapter.metadata,
            route_metadata,
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
        )
        for lane, adapter, route_metadata, snapshot in zip(
            plan.lanes,
            resolved_adapters,
            resolved_route_metadata,
            snapshots,
        )
    )
    payload_meter_evidences = tuple(
        _build_prompt_payload_meter_evidence(
            plan,
            snapshot,
            payload_evidence,
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
        )
        for lane, snapshot, payload_evidence in zip(
            plan.lanes,
            snapshots,
            payload_evidences,
        )
    )
    dispatch_envelopes = tuple(
        _build_dispatch_envelope(
            plan,
            lane_role=lane.role,
            requested_model_id=lane.preferred_model,
            adapter_metadata=adapter.metadata,
            route_metadata=route_metadata,
            payload_evidence=payload_evidence,
            aegis_evidence_ids=_proof_trail_evidence_ids(proof_trail),
        )
        for lane, adapter, route_metadata, payload_evidence in zip(
            plan.lanes,
            resolved_adapters,
            resolved_route_metadata,
            payload_evidences,
        )
    )
    dispatch_metadata_envelopes = tuple(
        _build_dispatch_metadata_envelope(
            plan,
            lane_role=lane.role,
            requested_model_id=lane.preferred_model,
            adapter_metadata=adapter.metadata,
            route_metadata=route_metadata,
            payload_evidence=payload_evidence,
            dispatch_envelope=dispatch_envelope,
        )
        for lane, adapter, route_metadata, payload_evidence, dispatch_envelope in zip(
            plan.lanes,
            resolved_adapters,
            resolved_route_metadata,
            payload_evidences,
            dispatch_envelopes,
        )
    )

    for lane, adapter, snapshot, route_metadata, payload_evidence, payload_meter_evidence, dispatch_envelope, dispatch_metadata_envelope in zip(
        plan.lanes,
        resolved_adapters,
        snapshots,
        resolved_route_metadata,
        payload_evidences,
        payload_meter_evidences,
        dispatch_envelopes,
        dispatch_metadata_envelopes,
    ):
        try:
            output = adapter(lane.payload)
            result_validation_evidence = _build_provider_result_validation_evidence(
                plan,
                output,
                lane_role=lane.role,
                requested_model_id=lane.preferred_model,
                dispatch_metadata_envelope=dispatch_metadata_envelope,
                payload_evidence=payload_evidence,
                dispatch_envelope=dispatch_envelope,
            )
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    adapter_metadata=adapter.metadata,
                    route_metadata=route_metadata,
                    payload_evidence=payload_evidence,
                    payload_meter_evidence=payload_meter_evidence,
                    dispatch_envelope=dispatch_envelope,
                    dispatch_metadata_envelope=dispatch_metadata_envelope,
                    provider_result_validation_evidence=result_validation_evidence,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                RelayExecutionError(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    error=str(exc),
                )
            )

    decision_record = None
    if include_decision_record:
        first_snapshot = snapshots[0] if snapshots else None
        first_adapter_metadata = resolved_adapters[0].metadata if resolved_adapters else None
        first_route_metadata = resolved_route_metadata[0] if resolved_route_metadata else None
        first_payload_evidence = payload_evidences[0] if payload_evidences else None
        first_payload_meter_evidence = (
            payload_meter_evidences[0] if payload_meter_evidences else None
        )
        decision_record = _build_decision_record(
            plan,
            first_snapshot,
            first_adapter_metadata,
            first_route_metadata,
            first_payload_evidence,
            dispatch_envelopes[0] if dispatch_envelopes else None,
            dispatch_metadata_envelopes[0] if dispatch_metadata_envelopes else None,
        )
        if results:
            decision_record = replace(
                decision_record,
                payload_meter_evidence=first_payload_meter_evidence,
                provider_result_validation_evidence=(
                    results[0].provider_result_validation_evidence
                ),
            )

    return RelayExecutionSummary(
        results=tuple(results),
        errors=tuple(errors),
        decision_record=decision_record,
    )


def execute_relay_dispatch_plan_with_policy(
    plan: RelayDispatchPlan,
    model_call: ModelCallFn,
    proof_trail: ProofTrail | None = None,
    human_gate_approved: bool = False,
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
    include_decision_record: bool = False,
    demotion_target_tier: int | None = None,
) -> RelayExecutionSummary:
    """
    Execute a plan after evaluating V2 CognitionPolicy against the risk tier.

    Evaluates cognition_policy for plan.route.risk_tier before any model call.
    If policy blocks dispatch, raises RelayProofGateError with blocking reasons
    before calling model_call. Otherwise delegates to execute_relay_dispatch_plan.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane.

    If include_decision_record is True, generates a RelayDecisionRecord exposing
    audit fields for Prime to explain the route selection.
    """
    policy_result = evaluate_cognition_policy(
        plan.route.risk_tier,
        proof_trail=proof_trail,
        human_gate_approved=human_gate_approved,
    )

    if not policy_result.can_dispatch:
        reasons = "; ".join(policy_result.blocking_reasons)
        raise RelayProofGateError(
            f"Relay dispatch blocked by cognition policy: {reasons}"
        )

    first_lane = plan.lanes[0] if plan.lanes else None
    first_snapshot = payload_snapshots[0] if payload_snapshots else None
    first_payload_evidence = (
        _build_payload_evidence(
            plan,
            first_snapshot,
            lane_id=f"{first_lane.role.value}:{first_lane.preferred_model}",
        )
        if first_lane
        else None
    )
    first_dispatch_envelope = (
        _build_dispatch_envelope(
            plan,
            lane_role=first_lane.role,
            requested_model_id=first_lane.preferred_model,
            payload_evidence=first_payload_evidence,
            aegis_evidence_ids=_proof_trail_evidence_ids(proof_trail),
        )
        if first_lane
        else None
    )
    prompt_packet_policy_evidence = _evaluate_relay_prompt_packet_policy(
        plan,
        first_dispatch_envelope,
        proof_trail=proof_trail,
        human_gate_approved=human_gate_approved,
        demotion_target_tier=demotion_target_tier,
    )
    prompt_packet_policy_disposition = _relay_prompt_packet_policy_disposition(
        plan,
        prompt_packet_policy_evidence,
    )
    if not prompt_packet_policy_disposition.transport_allowed:
        blockers = ", ".join(prompt_packet_policy_disposition.blockers)
        raise RelayProofGateError(
            "Relay dispatch blocked by PromptPacket proof policy: "
            f"{prompt_packet_policy_evidence.reason}; "
            f"action={prompt_packet_policy_disposition.transport_action}; "
            f"blockers={blockers}"
        )

    summary = execute_relay_dispatch_plan(
        plan,
        model_call,
        proof_trail,
        payload_snapshots,
        include_decision_record or prompt_packet_policy_evidence is not None,
    )
    decision_record = summary.decision_record
    if decision_record is not None:
        decision_record = replace(
            decision_record,
            prompt_packet_policy_evidence=prompt_packet_policy_evidence,
            prompt_packet_policy_disposition=prompt_packet_policy_disposition,
        )
    return replace(
        summary,
        decision_record=decision_record,
        prompt_packet_policy_evidence=prompt_packet_policy_evidence,
        prompt_packet_policy_disposition=prompt_packet_policy_disposition,
    )


def _assert_proof_gate_clear(
    plan: RelayDispatchPlan,
    proof_trail: ProofTrail | None,
) -> None:
    if proof_trail is None or plan.route.risk_tier < 3:
        return
    blocking = proof_trail.blocking()
    if not blocking:
        return
    evidence_ids = ", ".join(evidence.id for evidence in blocking)
    raise RelayProofGateError(
        f"Relay dispatch blocked by Aegis proof evidence: {evidence_ids}"
    )
