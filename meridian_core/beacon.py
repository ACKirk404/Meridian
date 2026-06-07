"""Beacon liveness checks for Meridian harnesses.

V0 Beacon is intentionally small: it turns flat-file queue or sentinel file
freshness into the existing Heartbeat domain model. Process supervision,
session spawning, and restart/resteer actions belong to later Prime slices.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model_adapter import DeepSeekValidationDisposition
from .models import Heartbeat, HeartbeatStatus
from .session_lifecycle import (
    SessionAction,
    SessionCommandPlan,
    SessionLiveControlCommandPlanStagingRecord,
    SessionLiveStateAdvisoryProjection,
    SessionPermissionSummary,
    SessionRecoveryReadinessSummary,
    SessionRuntimeStateExport,
    V2CommandPlanPreviewProof,
    WorkflowWorkOrderRecoverySummary,
)


@dataclass(frozen=True)
class LivenessTarget:
    """A file-backed liveness target for one harness or worker lane."""

    harness_id: str
    path: Path
    stale_after_seconds: int = 300


@dataclass(frozen=True)
class BeaconAdvisoryEvidence:
    """Display-safe advisory evidence derived from a Session command plan."""

    harness_id: str
    advisory_type: str
    evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    human_gate_required: bool
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize advisory evidence without live control state."""
        return {
            "harness_id": self.harness_id,
            "advisory_type": self.advisory_type,
            "evidence": list(self.evidence),
            "blockers": list(self.blockers),
            "human_gate_required": self.human_gate_required,
            "generated_at": self.generated_at.isoformat(),
        }


def command_plan_advisory_evidence(
    command_plan: SessionCommandPlan,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a command plan into Beacon advisory evidence only.

    This never executes restart, resteer, branch movement, or worktree movement.
    """
    audit = command_plan.audit_evidence()
    plan = _audit_section(audit, "plan")
    permission = _audit_section(audit, "permission")
    review_gate = _audit_section(audit, "review_gate")
    recovery = _audit_section(audit, "recovery")
    blockers = tuple(_audit_list(audit, "blockers"))

    evidence = [
        f"plan.action={plan.get('action', 'unknown')}",
        f"plan.reason={plan.get('reason', 'unknown')}",
        f"permission.proof={permission.get('proof_requirement', 'unknown')}",
        f"permission.state={permission.get('permission_state', 'unknown')}",
        f"permission.operation={permission.get('operation', 'unknown')}",
        f"permission.operation_allowed={_audit_bool(permission.get('operation_allowed'))}",
        f"review.human_gate={_audit_bool(review_gate.get('human_approval_required'))}",
        f"recovery.note={recovery.get('rollback_or_recovery_note', 'unknown')}",
    ]
    if permission.get("evidence") is not None:
        evidence.append(f"permission.evidence={permission.get('evidence')}")

    return BeaconAdvisoryEvidence(
        harness_id=command_plan.session_id,
        advisory_type=str(plan.get("action") or "unknown"),
        evidence=tuple(evidence),
        blockers=blockers,
        human_gate_required=_audit_bool(review_gate.get("human_approval_required"))
        or bool(blockers),
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def permission_summary_advisory_evidence(
    summary: SessionPermissionSummary,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a Session permission summary into Beacon advisory evidence only."""
    advisory_type = (
        summary.restart_resteer_findings[0].finding_type.value
        if summary.restart_resteer_findings
        else "permission_summary"
    )
    evidence = list(summary.evidence)
    evidence.extend(
        f"recovery.rationale={finding.recommended_action}"
        for finding in summary.restart_resteer_findings
    )

    return BeaconAdvisoryEvidence(
        harness_id=summary.session_id,
        advisory_type=advisory_type,
        evidence=tuple(evidence),
        blockers=tuple(summary.blockers),
        human_gate_required=bool(summary.blockers or summary.restart_resteer_findings),
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def workflow_recovery_advisory_evidence(
    summary: WorkflowWorkOrderRecoverySummary,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a workflow recovery summary into Beacon advisory evidence only."""
    blockers = tuple(summary.permission_blockers + summary.review_gate_blockers)
    evidence = list(summary.evidence)
    evidence.append(f"workflow.recovery_action={summary.recovery_action.value}")

    return BeaconAdvisoryEvidence(
        harness_id=summary.target_session_id,
        advisory_type=f"workflow_{summary.recovery_action.value}",
        evidence=tuple(evidence),
        blockers=blockers,
        human_gate_required=(
            summary.recovery_action == SessionAction.REQUEST_HUMAN_GATE
            or bool(blockers)
        ),
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def runtime_state_advisory_evidence(
    runtime_export: SessionRuntimeStateExport,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a runtime-state export into Beacon advisory evidence only."""
    recovery_action = runtime_export.recommended_recovery_action
    advisory_type = (
        f"runtime_{recovery_action.value}"
        if recovery_action is not None
        else "runtime_state_export"
    )
    evidence = list(runtime_export.evidence_refs)
    evidence.extend(
        [
            f"runtime.state_id={runtime_export.state_id}",
            "runtime.command_kind="
            + (
                runtime_export.active_command_kind.value
                if runtime_export.active_command_kind
                else "none"
            ),
            "runtime.recovery_action="
            + (recovery_action.value if recovery_action else "none"),
            "runtime.heartbeat_status="
            + (
                runtime_export.heartbeat_status.value
                if runtime_export.heartbeat_status
                else "none"
            ),
        ]
    )
    blockers = tuple(runtime_export.human_gate_blockers)

    return BeaconAdvisoryEvidence(
        harness_id=runtime_export.target_session_id or runtime_export.session_id,
        advisory_type=advisory_type,
        evidence=tuple(evidence),
        blockers=blockers,
        human_gate_required=(
            recovery_action == SessionAction.REQUEST_HUMAN_GATE or bool(blockers)
        ),
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def recovery_readiness_advisory_evidence(
    readiness_summary: SessionRecoveryReadinessSummary,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert recovery readiness summary into Beacon advisory evidence only."""
    evidence = list(readiness_summary.evidence_refs)
    evidence.extend(
        [
            f"readiness.summary_id={readiness_summary.summary_id}",
            f"readiness.status={readiness_summary.readiness_status}",
            "readiness.command_kind="
            + (
                readiness_summary.command_kind.value
                if readiness_summary.command_kind
                else "none"
            ),
            "readiness.recommended_action="
            + (
                readiness_summary.recommended_action.value
                if readiness_summary.recommended_action
                else "none"
            ),
            "readiness.required_operation="
            + (
                readiness_summary.required_operation.value
                if readiness_summary.required_operation
                else "none"
            ),
            f"readiness.ready_for_execution={readiness_summary.ready_for_execution}",
        ]
    )

    return BeaconAdvisoryEvidence(
        harness_id=readiness_summary.target_session_id,
        advisory_type=f"readiness_{readiness_summary.readiness_status}",
        evidence=tuple(evidence),
        blockers=readiness_summary.blockers,
        human_gate_required=(
            readiness_summary.human_gate_required
            or bool(readiness_summary.blockers)
        ),
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def command_plan_staging_advisory_evidence(
    staging_record: SessionLiveControlCommandPlanStagingRecord,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert non-executable command-plan staging into Beacon evidence only."""
    command_kind = (
        staging_record.command_kind.value
        if staging_record.command_kind
        else "unknown"
    )
    evidence = list(staging_record.evidence_refs)
    evidence.extend(
        [
            f"staging.id={staging_record.staging_id}",
            f"staging.target_session_id={staging_record.target_session_id}",
            f"staging.command_kind={command_kind}",
            "staging.recommended_action="
            + (
                staging_record.recommended_action.value
                if staging_record.recommended_action
                else "none"
            ),
            "staging.required_operation="
            + (
                staging_record.required_operation.value
                if staging_record.required_operation
                else "none"
            ),
            f"staging.ready_for_execution={staging_record.ready_for_execution}",
            f"staging.is_executable_now={staging_record.is_executable_now}",
            f"staging.ui_review_required={staging_record.ui_review_required}",
            f"permission.state={staging_record.permission_state.value}",
        ]
    )

    return BeaconAdvisoryEvidence(
        harness_id=staging_record.target_session_id,
        advisory_type=f"staging_{command_kind}",
        evidence=tuple(evidence),
        blockers=staging_record.blockers,
        human_gate_required=True,
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def live_state_advisory_evidence(
    projection: SessionLiveStateAdvisoryProjection,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a SessionLiveStateAdvisoryProjection into Beacon advisory evidence.

    Display-safety is preserved end-to-end: the projection already redacts
    raw paths and raw blocker text, so the Beacon evidence carries only
    bounded labels and presence indicators. This is advisory-only — no
    session control, no process inspection, no model calls.

    Fail-closed advisory contract: ``human_gate_required`` is forced True
    and the Beacon advisory always carries the universal advisory blocker
    ``advisory_only.requires_human_gate`` inherited from the projection,
    so no downstream consumer can read this evidence as executable.
    """
    evidence = list(projection.evidence_refs)
    evidence.extend(
        [
            f"live_state.projection_id={projection.projection_id}",
            f"live_state.session_id={projection.session_id}",
            f"live_state.status={projection.status.value}",
            f"live_state.health={projection.health_state.value}",
            f"live_state.proof_state={projection.proof_state.value}",
            f"live_state.blocker_present={projection.blocker_present}",
            f"live_state.project_path_present={projection.project_path_present}",
            f"live_state.worktree_path_present={projection.worktree_path_present}",
            f"live_state.is_executable_now={projection.is_executable_now}",
            "live_state.advisory_only=True",
        ]
    )

    return BeaconAdvisoryEvidence(
        harness_id=projection.session_id,
        advisory_type=f"live_state_{projection.status.value}",
        evidence=tuple(evidence),
        blockers=projection.advisory_blockers,
        # Fail-closed: never report executable state for a live-state advisory,
        # independent of any future projection-field drift.
        human_gate_required=True,
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def v2_command_plan_preview_advisory_evidence(
    proof: V2CommandPlanPreviewProof,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Convert a V2 command-plan preview proof into Beacon advisory evidence.

    Display-safety is preserved end-to-end: the proof already redacts raw
    paths, raw reason text, and raw rollback text, so the Beacon evidence
    carries only bounded labels and presence indicators. This is advisory
    /proof-only — no command execution, no process inspection, no model
    calls.

    Fail-closed advisory contract: ``human_gate_required`` is forced True
    and the Beacon advisory always carries the universal advisory blocker
    ``v2_command_plan_preview.advisory_only.requires_human_gate`` inherited
    from the proof, so no downstream consumer can read this evidence as
    executable.
    """
    evidence = list(proof.evidence_refs)
    evidence.extend(
        [
            f"v2_preview.preview_id={proof.preview_id}",
            f"v2_preview.target_session_id={proof.target_session_id}",
            "v2_preview.command_kind="
            + (proof.command_kind.value if proof.command_kind else "none"),
            f"v2_preview.aegis_gate_result={proof.aegis_gate_result}",
            f"v2_preview.aegis_gate_status={proof.aegis_gate_status}",
            f"v2_preview.is_executable_now={proof.is_executable_now}",
            f"v2_preview.human_gate_state={proof.human_gate_state}",
            f"v2_preview.review_cadence_state={proof.review_cadence_state.value}",
            f"v2_preview.permission_state={proof.permission_state.value}",
            "v2_preview.advisory_only=True",
        ]
    )

    return BeaconAdvisoryEvidence(
        harness_id=proof.target_session_id,
        advisory_type=(
            f"v2_command_plan_preview_"
            f"{proof.command_kind.value if proof.command_kind else 'unknown'}"
        ),
        evidence=tuple(evidence),
        blockers=proof.advisory_blockers,
        # Fail-closed: never report executable state for a V2 preview proof.
        human_gate_required=True,
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


_DEEPSEEK_BEACON_HARNESS_ID = "relay-model-deepseek"
_DEEPSEEK_ADVISORY_NON_AUTHORITY_BLOCKERS: tuple[str, ...] = (
    "deepseek_advisory_only_no_autonomous_implementation",
    "deepseek_advisory_only_no_review_clearing",
    "deepseek_advisory_only_no_branch_movement",
    "deepseek_advisory_only_no_live_coding",
    "deepseek_advisory_only_no_relay_bypass",
)


def deepseek_validation_disposition_advisory_evidence(
    disposition: DeepSeekValidationDisposition,
    *,
    now: datetime | None = None,
) -> BeaconAdvisoryEvidence:
    """Project reviewed DeepSeek validation disposition into Beacon advisory evidence.

    Display/advisory only. Surfaces validation level, direct dispatch id,
    variant labels, transport_cleared, blocked-authority tags, and evidence
    refs. The disposition's hard-coded non-authority bits surface as explicit
    advisory evidence and blockers. Never authorizes autonomous implementation,
    review clearing, branch movement, live coding, or relay bypass.
    """
    evidence: list[str] = [
        f"deepseek.validation_level={disposition.validation_level}",
        f"deepseek.direct_dispatch_id={disposition.direct_dispatch_id}",
        "deepseek.variant_labels=" + ",".join(disposition.variant_labels),
        f"deepseek.transport_cleared={disposition.transport_cleared}",
        f"deepseek.validation_evidence_ref={disposition.validation_evidence_ref}",
        "deepseek.blocked_authority_tags=" + ",".join(disposition.blocked_authority_tags),
        f"deepseek.autonomous_implementation_authorized={disposition.autonomous_implementation_authorized}",
        f"deepseek.review_clearing_authorized={disposition.review_clearing_authorized}",
        f"deepseek.branch_movement_authorized={disposition.branch_movement_authorized}",
        f"deepseek.live_coding_authority_authorized={disposition.live_coding_authority_authorized}",
        f"deepseek.relay_bypass_authorized={disposition.relay_bypass_authorized}",
        f"deepseek.serialization_only={disposition.serialization_only}",
    ]
    if disposition.direct_endpoint_evidence_ref is not None:
        evidence.append(
            f"deepseek.direct_endpoint_evidence_ref={disposition.direct_endpoint_evidence_ref}"
        )
    if disposition.external_review_evidence_ref is not None:
        evidence.append(
            f"deepseek.external_review_evidence_ref={disposition.external_review_evidence_ref}"
        )

    blockers: list[str] = list(_DEEPSEEK_ADVISORY_NON_AUTHORITY_BLOCKERS)
    blockers.extend(f"blocked_authority:{tag}" for tag in disposition.blocked_authority_tags)
    if not disposition.transport_cleared:
        blockers.append("deepseek_transport_not_cleared")
    if disposition.validation_level == "level-unknown":
        blockers.append("deepseek_validation_level_unknown")

    return BeaconAdvisoryEvidence(
        harness_id=_DEEPSEEK_BEACON_HARNESS_ID,
        advisory_type=f"deepseek_validation_{disposition.validation_level}",
        evidence=tuple(evidence),
        blockers=tuple(blockers),
        human_gate_required=True,
        generated_at=_as_utc(now or datetime.now(timezone.utc)),
    )


def check_harness_liveness(
    targets: list[LivenessTarget] | tuple[LivenessTarget, ...],
    *,
    now: datetime | None = None,
) -> tuple[Heartbeat, ...]:
    """Return one Heartbeat per target based on file freshness."""
    checked_at = _as_utc(now or datetime.now(timezone.utc))
    heartbeats: list[Heartbeat] = []
    for target in targets:
        heartbeats.append(_check_target(target, checked_at))
    return tuple(heartbeats)


def _check_target(target: LivenessTarget, checked_at: datetime) -> Heartbeat:
    if target.stale_after_seconds < 0:
        raise ValueError("stale_after_seconds must be zero or greater")

    if not target.path.exists():
        return Heartbeat(
            harness_id=target.harness_id,
            status=HeartbeatStatus.FAILED,
            current_work=str(target.path),
            last_event="liveness sentinel missing",
            blockers=[f"missing sentinel: {target.path}"],
            updated_at=checked_at,
        )

    modified_at = datetime.fromtimestamp(target.path.stat().st_mtime, timezone.utc)
    age_seconds = max(0, int((checked_at - modified_at).total_seconds()))
    status = (
        HeartbeatStatus.ALIVE
        if age_seconds <= target.stale_after_seconds
        else HeartbeatStatus.STALE
    )
    blockers = (
        [f"stale for {age_seconds}s; threshold {target.stale_after_seconds}s"]
        if status is HeartbeatStatus.STALE
        else []
    )
    return Heartbeat(
        harness_id=target.harness_id,
        status=status,
        current_work=str(target.path),
        last_event=f"sentinel updated {age_seconds}s ago",
        blockers=blockers,
        updated_at=checked_at,
    )


def _audit_section(audit_evidence: dict[str, Any], section: str) -> dict[str, Any]:
    value = audit_evidence.get(section, {})
    return value if isinstance(value, dict) else {}


def _audit_list(audit_evidence: dict[str, Any], section: str) -> list[str]:
    value = audit_evidence.get(section, [])
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _audit_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
