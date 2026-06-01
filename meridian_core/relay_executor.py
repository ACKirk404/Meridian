"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

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
)
from .prompt_payload_meter import PromptPayloadSnapshot
from .relay import ModelRole
from .relay_dispatch import RelayDispatchPlan


ModelCallFn = ModelAdapter


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


@dataclass(frozen=True)
class RelayExecutionResult:
    """Successful output for one lane with optional payload snapshot and adapter metadata."""

    role: ModelRole
    preferred_model: str
    output: str
    payload_snapshot: PromptPayloadSnapshot | None = None
    adapter_metadata: ModelHarnessMetadata | None = None


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


def _build_decision_record(
    plan: RelayDispatchPlan,
    payload_snapshot: PromptPayloadSnapshot | None = None,
    adapter_metadata: ModelHarnessMetadata | None = None,
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
    lanes = plan.lanes

    fallback_blockers = list(audit.fallback_blockers)
    fallback_allowed = len(fallback_blockers) == 0

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

    # Populate vendor from adapter metadata or mark unknown for nontrivial tiers
    vendor = None
    if adapter_metadata is not None:
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
    if payload_snapshot is not None:
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
        proof_required=tuple(audit.proof_required),
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
        aegis_explanation=aegis_explanation,
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

    for lane, snapshot in zip(plan.lanes, snapshots):
        try:
            output = model_call(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
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
        decision_record = _build_decision_record(plan, first_snapshot)

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

    for lane, adapter, snapshot in zip(plan.lanes, resolved_adapters, snapshots):
        try:
            output = adapter(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    adapter_metadata=adapter.metadata,
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
        decision_record = _build_decision_record(plan, first_snapshot, first_adapter_metadata)

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
