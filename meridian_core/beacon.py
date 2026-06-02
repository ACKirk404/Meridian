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

from .models import Heartbeat, HeartbeatStatus
from .session_lifecycle import (
    SessionAction,
    SessionCommandPlan,
    SessionPermissionSummary,
    SessionRuntimeStateExport,
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
