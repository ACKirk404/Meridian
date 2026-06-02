"""Prime Autonomy domain model for next-action decisions.

Frozen dataclasses and helpers for representing Prime's next deterministic action,
independent of UI/runtime integration. Used for decision logging, audit trails,
and deterministic fallback action selection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, List, FrozenSet

from meridian_core.session_lifecycle import (
    FindingType,
    OperationScope,
    PrimeAutonomyInput as SessionPrimeAutonomyInput,
    ReviewCadenceState,
    SessionCommandPlan,
    SessionPermissionSummary,
    SessionStatus,
)


class PrimeActionType(Enum):
    """Type of action Prime can direct."""
    POLL_SESSION = "poll_session"  # Check session state
    ADVISE_SESSION_RECOVERY = "advise_session_recovery"  # Stage recovery advice only
    ADVANCE_COGNITION = "advance_cognition"  # Run cognition policy evaluation
    RUN_WORKFLOW = "run_workflow"  # Execute workflow sub-agent
    PAUSE_AND_WAIT = "pause_and_wait"  # Wait for human input or external signal
    ESCALATE_ERROR = "escalate_error"  # Report blocker or error state
    NO_OP = "no_op"  # Safe default: do nothing


class PrimeActionConfidence(Enum):
    """Confidence in action selection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"  # Default safe action when uncertain


class PrimeActionRiskTier(Enum):
    """Risk level of the action."""
    SAFE = "safe"  # Read-only, no state changes
    LOW = "low"  # Minor state changes, easily reversible
    MEDIUM = "medium"  # Significant changes, requires audit trail
    HIGH = "high"  # Major changes, human gate required


class PrimeActionSource(Enum):
    """Source of the action decision."""
    COGNITION_POLICY = "cognition_policy"
    WORKFLOW_RESULT = "workflow_result"
    SESSION_STATE = "session_state"
    ERROR_RECOVERY = "error_recovery"
    HUMAN_OVERRIDE = "human_override"


@dataclass(frozen=True)
class PrimeNextAction:
    """Immutable representation of Prime's next deterministic action.

    Fields define the action type, target scope, decision quality, risk level,
    blockers, human-gate requirement, rationale, and evidence references.
    """

    action_type: PrimeActionType
    confidence: PrimeActionConfidence
    risk_tier: PrimeActionRiskTier
    source: PrimeActionSource

    # Target scope: which harness/lane/project this action targets
    target_harness: Optional[str] = None  # e.g., "Echo", "Atlas", "Relay"
    target_lane: Optional[str] = None      # e.g., "cognition", "workflow"
    target_project: Optional[str] = None   # e.g., "Meridian", external

    # Decision context
    rationale: str = ""  # Why this action was chosen
    evidence: FrozenSet[str] = field(default_factory=frozenset)  # References to proof/audit log entries

    # Constraints
    human_gate_required: bool = False  # Must wait for human approval before executing
    blockers: FrozenSet[str] = field(default_factory=frozenset)  # Blocking conditions preventing execution

    def is_blocked(self) -> bool:
        """Return True if any blockers prevent execution."""
        return bool(self.blockers)

    def is_executable(self) -> bool:
        """Return True only when no blocker or pending human gate prevents execution."""
        return not self.is_blocked() and not self.human_gate_required


def select_prime_next_action(
    action_type: Optional[PrimeActionType] = None,
    confidence: Optional[PrimeActionConfidence] = None,
    risk_tier: Optional[PrimeActionRiskTier] = None,
    source: Optional[PrimeActionSource] = None,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Deterministic helper to construct a Prime next-action with fallback defaults.

    Any None input falls back to a safe default, ensuring a valid action always returns.
    Returns a frozen immutable PrimeNextAction ready for decision logging.
    """

    # Safe defaults for each field
    final_action_type = action_type or PrimeActionType.PAUSE_AND_WAIT
    final_confidence = confidence or PrimeActionConfidence.FALLBACK
    final_risk_tier = risk_tier or PrimeActionRiskTier.SAFE
    final_source = source or PrimeActionSource.ERROR_RECOVERY

    # Convert lists to frozen sets
    final_evidence = frozenset(evidence or [])
    final_blockers = frozenset(blockers or [])

    return PrimeNextAction(
        action_type=final_action_type,
        confidence=final_confidence,
        risk_tier=final_risk_tier,
        source=final_source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=final_evidence,
        human_gate_required=human_gate_required,
        blockers=final_blockers,
    )


def make_prime_next_action(
    action_type: PrimeActionType,
    confidence: PrimeActionConfidence,
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE,
    source: PrimeActionSource = PrimeActionSource.ERROR_RECOVERY,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Strict constructor for Prime next-action: requires action_type and confidence.

    Falls back only on optional fields. Use this when you have explicit action intent.
    """

    return select_prime_next_action(
        action_type=action_type,
        confidence=confidence,
        risk_tier=risk_tier,
        source=source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=evidence,
        human_gate_required=human_gate_required,
        blockers=blockers,
    )


# Review cadence gate: require Codex review after this many task-changing commits.
_REVIEW_GATE_COMMIT_LIMIT = 3


@dataclass(frozen=True)
class ProjectStateSignal:
    """Plain data snapshot of project/backlog/lane state for the Prime selector.

    All inputs are plain data — no model, Echo, or Atlas calls are made
    inside this class or the selector that consumes it.
    """

    active_task: Optional[str] = None        # current active task ID, or None if queue is idle
    candidate_task: Optional[str] = None     # next candidate task ID, or None
    review_gate_open: bool = True            # False when cadence gate explicitly blocks new work
    commits_since_review: int = 0            # commits since last accepted Codex review
    human_gate_required: bool = False        # must wait for human approval before proceeding
    blockers: FrozenSet[str] = field(default_factory=frozenset)  # active blocking conditions
    lane_id: Optional[str] = None            # which build lane (e.g. "build-1")
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE
    echo_signal: Optional[str] = None        # Echo memory context placeholder (plain data)
    atlas_signal: Optional[str] = None       # Atlas retrieval context placeholder (plain data)


def select_next_action_from_project_state(
    state: Optional[ProjectStateSignal] = None,
) -> PrimeNextAction:
    """Select the next Prime action deterministically from project/backlog/lane state.

    Priority (most restrictive first):
      1. Missing state (None)  → PAUSE_AND_WAIT, FALLBACK confidence
      2. Human gate required   → PAUSE_AND_WAIT, human_gate_required=True
      3. Active blockers       → ESCALATE_ERROR
      4. HIGH risk tier        → PAUSE_AND_WAIT, human_gate_required=True
      5. Review gate tripped   → PAUSE_AND_WAIT (cadence gate or explicit close)
      6. No active task        → POLL_SESSION
      7. Active task present   → ADVANCE_COGNITION

    No model calls, filesystem reads, or network access are performed.
    """
    if state is None:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            rationale="No project state available; cannot determine next action safely.",
        )

    # Priority 2: Human gate
    if state.human_gate_required:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.SESSION_STATE,
            target_lane=state.lane_id,
            rationale="Human gate is required before proceeding.",
            blockers=list(state.blockers),
            human_gate_required=True,
        )

    # Priority 3: Blockers
    if state.blockers:
        return make_prime_next_action(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_lane=state.lane_id,
            rationale=f"Blockers prevent execution: {'; '.join(sorted(state.blockers))}",
            blockers=list(state.blockers),
        )

    # Priority 4: HIGH risk tier auto-gates to human approval
    if state.risk_tier == PrimeActionRiskTier.HIGH:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.COGNITION_POLICY,
            target_lane=state.lane_id,
            rationale="High risk tier requires human gate before execution.",
            human_gate_required=True,
        )

    # Priority 5: Review gate (explicit close or commit-count limit)
    review_gate_tripped = (
        not state.review_gate_open
        or state.commits_since_review >= _REVIEW_GATE_COMMIT_LIMIT
    )
    if review_gate_tripped:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.COGNITION_POLICY,
            target_lane=state.lane_id,
            rationale=(
                f"Review gate: {state.commits_since_review} commit(s) since last review, "
                f"gate_open={state.review_gate_open}."
            ),
        )

    # Priority 6: No active task — poll for new assignment
    if state.active_task is None:
        return make_prime_next_action(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_lane=state.lane_id,
            rationale="No active task; polling queue for new assignment.",
        )

    # Priority 7: Active task — advance cognition
    return make_prime_next_action(
        action_type=PrimeActionType.ADVANCE_COGNITION,
        confidence=PrimeActionConfidence.HIGH,
        risk_tier=state.risk_tier,
        source=PrimeActionSource.COGNITION_POLICY,
        target_lane=state.lane_id,
        rationale=f"Active task '{state.active_task}' is ready; advancing cognition.",
    )


def select_next_action_from_session_lifecycle_advisory(
    advisory_input: Optional[SessionPrimeAutonomyInput] = None,
) -> PrimeNextAction:
    """Convert Session Lifecycle Prime/Beacon input into a safe Prime advisory.

    The returned action can advise, pause, or escalate, but it never executes
    restart/resteer control. Live recovery still requires a separate command plan.
    """
    if advisory_input is None:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_harness="Session Lifecycle",
            rationale="No Session Lifecycle advisory input available.",
        )

    sessions_by_id = {
        session.session_id: session for session in advisory_input.current_sessions
    }
    summaries_by_id = {
        summary.session_id: summary for summary in advisory_input.permission_summaries
    }

    if advisory_input.approvals_pending:
        blockers = [
            f"{session_id}: {reason}"
            for session_id, reason in advisory_input.approvals_pending
        ]
        evidence = list(blockers)
        for session_id, _reason in advisory_input.approvals_pending:
            evidence.extend(_permission_summary_evidence(summaries_by_id.get(session_id)))
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.SESSION_STATE,
            target_harness="Session Lifecycle",
            rationale="Session recovery advisory is waiting on approval.",
            evidence=evidence,
            human_gate_required=True,
            blockers=blockers,
        )

    for session in advisory_input.current_sessions:
        if (
            session.status == SessionStatus.REVIEW_GATED
            or session.review_cadence_state == ReviewCadenceState.REVIEW_GATED
        ):
            evidence = [
                f"{session.session_id}: status={session.status.value}",
                f"{session.session_id}: review={session.review_cadence_state.value}",
            ]
            summary = summaries_by_id.get(session.session_id)
            evidence.extend(_permission_summary_evidence(summary))
            blockers = ["review gate requires human approval"]
            blockers.extend(_permission_summary_review_blockers(summary))
            return make_prime_next_action(
                action_type=PrimeActionType.PAUSE_AND_WAIT,
                confidence=PrimeActionConfidence.HIGH,
                risk_tier=PrimeActionRiskTier.HIGH,
                source=PrimeActionSource.SESSION_STATE,
                target_harness="Session Lifecycle",
                target_lane=session.session_id,
                rationale="Review gate blocks session recovery advice from execution.",
                evidence=evidence,
                human_gate_required=True,
                blockers=blockers,
            )

    for finding in _advisory_findings(advisory_input):
        session = sessions_by_id.get(finding.session_id)
        summary = summaries_by_id.get(finding.session_id)
        operation = (
            OperationScope.RESTART
            if finding.finding_type == FindingType.RESTART
            else OperationScope.RESTEER
        )
        evidence = [
            f"{finding.session_id}: finding={finding.finding_type.value}",
            f"{finding.session_id}: stale_seconds={finding.evidence_stale_seconds}",
            f"{finding.session_id}: recommendation={finding.recommended_action}",
        ]
        evidence.extend(_permission_summary_evidence(summary))

        permission_blockers = _permission_summary_permission_blockers(summary)
        if (
            permission_blockers
            or (
                session is not None
                and not session.can_execute_operation(operation)
            )
        ):
            blockers = [
                f"{finding.session_id}: permission boundary blocks {operation.value}"
            ]
            blockers.extend(permission_blockers)
            return make_prime_next_action(
                action_type=PrimeActionType.PAUSE_AND_WAIT,
                confidence=PrimeActionConfidence.HIGH,
                risk_tier=PrimeActionRiskTier.HIGH,
                source=PrimeActionSource.SESSION_STATE,
                target_harness="Session Lifecycle",
                target_lane=finding.session_id,
                rationale="Permission boundary blocks session recovery advice.",
                evidence=evidence,
                human_gate_required=True,
                blockers=blockers,
            )

        return make_prime_next_action(
            action_type=PrimeActionType.ADVISE_SESSION_RECOVERY,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.SESSION_STATE,
            target_harness="Session Lifecycle",
            target_lane=finding.session_id,
            rationale=f"Advise {finding.finding_type.value} recovery: {finding.reason}",
            evidence=evidence,
            human_gate_required=True,
            blockers=["advisory only; command plan approval required before execution"],
        )

    session_ids = [session.session_id for session in advisory_input.current_sessions]
    evidence = list(session_ids)
    for summary in advisory_input.permission_summaries:
        evidence.extend(_permission_summary_evidence(summary))
    return make_prime_next_action(
        action_type=PrimeActionType.POLL_SESSION,
        confidence=PrimeActionConfidence.MEDIUM,
        risk_tier=PrimeActionRiskTier.SAFE,
        source=PrimeActionSource.SESSION_STATE,
        target_harness="Session Lifecycle",
        rationale="No restart/resteer findings; continue watching session state.",
        evidence=evidence,
    )


def _advisory_findings(
    advisory_input: SessionPrimeAutonomyInput,
) -> tuple[Any, ...]:
    findings = list(advisory_input.restart_resteer_findings)
    seen = {(finding.session_id, finding.finding_type) for finding in findings}
    for summary in advisory_input.permission_summaries:
        for finding in summary.restart_resteer_findings:
            key = (finding.session_id, finding.finding_type)
            if key not in seen:
                findings.append(finding)
                seen.add(key)
    return tuple(findings)


def _permission_summary_evidence(
    summary: Optional[SessionPermissionSummary],
) -> list[str]:
    if summary is None:
        return []
    return [f"{summary.session_id}: {item}" for item in summary.evidence]


def _permission_summary_permission_blockers(
    summary: Optional[SessionPermissionSummary],
) -> list[str]:
    if summary is None:
        return []
    permission_prefixes = (
        "permission.locked",
        "permission.unlock_expired",
        "permission.out_of_scope",
        "permission.escalation_gate",
    )
    return [
        f"{summary.session_id}: {blocker}"
        for blocker in summary.blockers
        if blocker.startswith(permission_prefixes)
    ]


def _permission_summary_review_blockers(
    summary: Optional[SessionPermissionSummary],
) -> list[str]:
    if summary is None:
        return []
    return [f"{summary.session_id}: {blocker}" for blocker in summary.review_gate_blockers]


def _audit_section(audit_evidence: dict[str, Any], section: str) -> dict[str, Any]:
    if not isinstance(audit_evidence, dict):
        return {}
    value = audit_evidence.get(section, {})
    return value if isinstance(value, dict) else {}


def _audit_list(audit_evidence: dict[str, Any], section: str) -> list[str]:
    if not isinstance(audit_evidence, dict):
        return []
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


def _prime_evidence_from_command_audit(audit_evidence: dict[str, Any]) -> list[str]:
    plan = _audit_section(audit_evidence, "plan")
    permission = _audit_section(audit_evidence, "permission")
    review_gate = _audit_section(audit_evidence, "review_gate")
    recovery = _audit_section(audit_evidence, "recovery")
    blockers = _audit_list(audit_evidence, "blockers")

    evidence = [
        f"plan.action={plan.get('action', 'unknown')}",
        f"plan.reason={plan.get('reason', 'unknown')}",
        f"plan.executable={_audit_bool(plan.get('is_executable'))}",
        f"permission.proof={permission.get('proof_requirement', 'unknown')}",
        f"permission.branch={permission.get('branch_affected', 'unknown')}",
        f"review.required={_audit_bool(review_gate.get('cadence_gate_required'))}",
        f"review.status={review_gate.get('cadence_gate_status', 'unknown')}",
        f"recovery.note={recovery.get('rollback_or_recovery_note', 'unknown')}",
    ]
    if permission.get("permission_state") is not None:
        evidence.append(f"permission.state={permission.get('permission_state')}")
    if permission.get("task_scope") is not None:
        evidence.append(f"permission.task_scope={permission.get('task_scope')}")
    if permission.get("operation") is not None:
        evidence.append(f"permission.operation={permission.get('operation')}")
        evidence.append(
            f"permission.operation_allowed="
            f"{_audit_bool(permission.get('operation_allowed'))}"
        )
    if permission.get("evidence") is not None:
        evidence.append(f"permission.evidence={permission.get('evidence')}")
    evidence.extend(f"blocker={blocker}" for blocker in blockers)
    return evidence


def select_next_action_from_command_plan_audit(
    command_plan: Optional[SessionCommandPlan] = None,
    audit_evidence: Optional[dict[str, Any]] = None,
) -> PrimeNextAction:
    """Convert SessionCommandPlan audit evidence into a Prime advisory action.

    Accepts either the command plan object or its serialized audit_evidence dict.
    The result is advisory-only and does not execute session control.
    """
    if command_plan is not None:
        audit = command_plan.audit_evidence()
        target_lane = command_plan.session_id
    else:
        audit = audit_evidence
        target_lane = None

    if audit is None:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_harness="Session Lifecycle",
            rationale="No SessionCommandPlan audit evidence available.",
        )

    plan = _audit_section(audit, "plan")
    review_gate = _audit_section(audit, "review_gate")
    blockers = _audit_list(audit, "blockers")
    evidence = _prime_evidence_from_command_audit(audit)
    action_name = str(plan.get("action") or "unknown")
    reason = str(plan.get("reason") or "no reason supplied")
    executable = _audit_bool(plan.get("is_executable"))
    human_gate_required = _audit_bool(review_gate.get("human_approval_required"))
    is_blocked = bool(blockers) or human_gate_required or not executable
    if is_blocked and not blockers:
        blockers = ["not_executable_now"]

    if action_name == "poll_queue" and executable:
        return make_prime_next_action(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_harness="Session Lifecycle",
            target_lane=target_lane,
            rationale=f"Command audit permits safe poll: {reason}",
            evidence=evidence,
        )

    return make_prime_next_action(
        action_type=(
            PrimeActionType.PAUSE_AND_WAIT
            if is_blocked
            else PrimeActionType.ADVISE_SESSION_RECOVERY
        ),
        confidence=PrimeActionConfidence.HIGH,
        risk_tier=PrimeActionRiskTier.HIGH if is_blocked else PrimeActionRiskTier.MEDIUM,
        source=PrimeActionSource.SESSION_STATE,
        target_harness="Session Lifecycle",
        target_lane=target_lane,
        rationale=f"Command audit advisory for {action_name}: {reason}",
        evidence=evidence,
        human_gate_required=human_gate_required,
        blockers=blockers,
    )
