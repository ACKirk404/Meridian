"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
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
    route_class: str | None = None
    route_kind: str | None = None
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
            "route_class": self.route_class,
            "route_kind": self.route_kind,
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
    dispatch_envelope: RelayDispatchEnvelope | None = None
    packet_hash: str | None = None
    prompt_budget_ref: str | None = None
    source_lineage_compliant: bool | None = None
    packet_proof_metadata_ref: str | None = None
    packet_proof_blocked_tags: tuple[str, ...] = ()


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
    dispatch_envelope: RelayDispatchEnvelope | None = None


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
class RelayExecutionSummary:
    """Immutable collection of per-lane results and errors from one plan execution."""

    results: tuple[RelayExecutionResult, ...]
    errors: tuple[RelayExecutionError, ...]
    decision_record: RelayDecisionRecord | None = None

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
                summary=f"{role} lane failed: {error.error}",
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


def _build_payload_evidence(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
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
        route_class=audit.route_class.value if audit.route_class else None,
        route_kind=audit.route_kind.value,
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


def _proof_trail_evidence_ids(proof_trail: ProofTrail | None) -> tuple[str, ...]:
    if proof_trail is None:
        return ()
    return tuple(evidence.id for evidence in proof_trail.evidence)


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


def _build_decision_record(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
    route_metadata: ModelRouteMetadataBinding | None = None,
    payload_evidence: RelayPromptPayloadEvidence | None = None,
    dispatch_envelope: RelayDispatchEnvelope | None = None,
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
        dispatch_envelope=dispatch_envelope,
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

    for lane, snapshot, payload_evidence, dispatch_envelope in zip(
        plan.lanes,
        snapshots,
        payload_evidences,
        dispatch_envelopes,
    ):
        try:
            output = model_call(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    payload_evidence=payload_evidence,
                    dispatch_envelope=dispatch_envelope,
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
        decision_record = _build_decision_record(
            plan,
            first_snapshot,
            payload_evidence=first_payload_evidence,
            dispatch_envelope=dispatch_envelopes[0] if dispatch_envelopes else None,
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
            lane_id=f"{lane.role.value}:{lane.preferred_model}",
        )
        for lane, adapter, snapshot in zip(plan.lanes, resolved_adapters, snapshots)
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

    for lane, adapter, snapshot, route_metadata, payload_evidence, dispatch_envelope in zip(
        plan.lanes,
        resolved_adapters,
        snapshots,
        resolved_route_metadata,
        payload_evidences,
        dispatch_envelopes,
    ):
        try:
            output = adapter(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    adapter_metadata=adapter.metadata,
                    route_metadata=route_metadata,
                    payload_evidence=payload_evidence,
                    dispatch_envelope=dispatch_envelope,
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
        decision_record = _build_decision_record(
            plan,
            first_snapshot,
            first_adapter_metadata,
            first_route_metadata,
            first_payload_evidence,
            dispatch_envelopes[0] if dispatch_envelopes else None,
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

    return execute_relay_dispatch_plan(
        plan, model_call, proof_trail, payload_snapshots, include_decision_record
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
