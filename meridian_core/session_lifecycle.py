"""Session Lifecycle: Session state and command planning for Prime.

Defines typed state and commands for session lifecycle management.
Sessions progress through lifecycle states (STARTING → POLLING → RUNNING → STOPPED → ARCHIVED)
and Prime coordinates state transitions via typed command plans.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SessionStatus(Enum):
    """Session lifecycle state."""

    STARTING = "starting"
    POLLING = "polling"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    REVIEW_GATED = "review_gated"
    CAPACITY_LIMITED = "capacity_limited"
    STALE = "stale"
    STOPPED = "stopped"
    ARCHIVED = "archived"


class HarnessRole(Enum):
    """Role of the session."""

    BUILD = "build"
    REVIEW = "review"
    UI = "ui"
    ARCHITECTURE = "architecture"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class CommandIntent(Enum):
    """Intent of a session command."""

    SPAWN = "spawn"
    WATCH = "watch"
    POLL_QUEUE = "poll_queue"
    STEER = "steer"
    STOP_REQUEST = "stop_request"
    TRANSFER = "transfer"
    ARCHIVE = "archive"
    RESTART = "restart"
    RESTEER = "resteer"
    RECOVER_FROM_LIMIT = "recover_from_limit"
    REQUEST_HUMAN_GATE = "request_human_gate"


class ReviewCadenceState(Enum):
    """Review cadence gate state."""

    NONE = "none"
    PENDING = "pending"
    REVIEW_GATED = "review_gated"
    CLEARED = "cleared"
    FAILED = "failed"


class ProofState(Enum):
    """Evidence collection state."""

    NO_PROOF = "no_proof"
    QUEUE_READ = "queue_read"
    WORKTREE_VERIFIED = "worktree_verified"
    PERMISSION_VALIDATED = "permission_validated"
    COMMAND_STAGED = "command_staged"
    EXECUTED = "executed"
    ROLLBACK_READY = "rollback_ready"


class HealthState(Enum):
    """Session health indicator."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILED = "failed"


class SessionAction(Enum):
    """Relay routing decision: what to do with a session."""

    REUSE = "reuse"
    START_NEW = "start_new"
    SUMMARIZE_RESET = "summarize_reset"
    TRANSFER = "transfer"
    ARCHIVE = "archive"
    REQUEST_HUMAN_GATE = "request_human_gate"
    AVOID = "avoid"


class SessionActionReason(Enum):
    """Why Relay chose a particular session action."""

    CONTEXT_FILL = "context_fill"
    REASONING_SHIFT = "reasoning_shift"
    PROJECT_SCOPE = "project_scope"
    STALE_HEARTBEAT = "stale_heartbeat"
    REVIEW_GATE = "review_gate"
    PERMISSION_BOUNDARY = "permission_boundary"
    CONTEXT_HEALTHY = "context_healthy"
    CONTEXT_POLLUTION = "context_pollution"
    TOOL_MISMATCH = "tool_mismatch"
    SURFACE_MODE = "surface_mode"
    PAYLOAD_BUDGET = "payload_budget"
    DEFECT_FOUND = "defect_found"
    DUAL_LANE_NEEDED = "dual_lane_needed"


class PermissionState(Enum):
    """Branch/worktree permission lock state."""

    LOCKED_BY_DEFAULT = "locked_by_default"
    UNLOCKED_TEMPORARY = "unlocked_temporary"
    UNLOCKED_PERMANENT = "unlocked_permanent"


class OperationScope(Enum):
    """Types of operations requiring permission control."""

    BRANCH_MOVE = "branch_move"
    WORKTREE_CREATE = "worktree_create"
    ARCHIVE = "archive"
    RESTART = "restart"
    RESTEER = "resteer"
    RECOVER_FROM_LIMIT = "recover_from_limit"


class FindingType(Enum):
    """Types of Beacon staleness/blocker findings."""

    RESTART = "restart"
    RESTEER = "resteer"


@dataclass(frozen=True)
class PermissionContext:
    """Approval scope and escalation state for session operations."""

    approved_by: str
    approval_scope: frozenset[OperationScope]
    escalation_gate: bool
    escalation_reason: Optional[str]
    branch_permission_state: PermissionState
    approved_by_secondary: Optional[str]
    unlock_expiry: Optional[datetime]
    task_scope: Optional[str]
    last_permission_change: datetime

    def __post_init__(self) -> None:
        """Enforce construction-time invariants for permission states."""
        if self.branch_permission_state == PermissionState.UNLOCKED_TEMPORARY:
            if self.unlock_expiry is None:
                raise ValueError("UNLOCKED_TEMPORARY requires unlock_expiry to be set")
            if self.task_scope is None:
                raise ValueError("UNLOCKED_TEMPORARY requires task_scope to be set")
        elif self.branch_permission_state == PermissionState.UNLOCKED_PERMANENT:
            if self.approved_by_secondary is None:
                raise ValueError("UNLOCKED_PERMANENT requires approved_by_secondary (dual approval)")

    def is_operation_approved(self, operation: OperationScope) -> bool:
        """True if operation is in approval scope."""
        return operation in self.approval_scope

    def is_permission_locked(self) -> bool:
        """True if branch is currently locked."""
        return self.branch_permission_state == PermissionState.LOCKED_BY_DEFAULT

    def is_unlock_expired(self) -> bool:
        """True if temporary unlock has expired."""
        if self.unlock_expiry is None:
            return False
        return datetime.now(timezone.utc) > self.unlock_expiry.replace(tzinfo=timezone.utc)

    def is_unlock_task_scoped(self, current_task_id: Optional[str]) -> bool:
        """True if unlock is restricted to specific task and current task matches."""
        if self.task_scope is None:
            return True
        return self.task_scope == current_task_id

    def requires_approval_for_operation(self, operation: OperationScope) -> bool:
        """True if operation requires explicit approval."""
        return self.is_permission_locked() and not self.is_operation_approved(operation)

    def can_execute_operation(self, operation: OperationScope, current_task_id: Optional[str] = None) -> bool:
        """True if operation can execute without further approval."""
        if self.is_unlock_expired():
            return False
        if not self.is_unlock_task_scoped(current_task_id):
            return False
        return self.is_operation_approved(operation) and not self.escalation_gate

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "approved_by": self.approved_by,
            "approval_scope": [op.value for op in self.approval_scope],
            "escalation_gate": self.escalation_gate,
            "escalation_reason": self.escalation_reason,
            "branch_permission_state": self.branch_permission_state.value,
            "approved_by_secondary": self.approved_by_secondary,
            "unlock_expiry": self.unlock_expiry.isoformat() if self.unlock_expiry else None,
            "task_scope": self.task_scope,
            "last_permission_change": self.last_permission_change.isoformat(),
        }


@dataclass(frozen=True)
class RestartResteerFinding:
    """Advisory finding for stale or blocked sessions."""

    session_id: str
    finding_type: FindingType
    reason: str
    evidence_stale_seconds: int
    evidence_last_queue_read_at: datetime
    evidence_blocker_summary: Optional[str]
    recommended_action: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "session_id": self.session_id,
            "finding_type": self.finding_type.value,
            "reason": self.reason,
            "evidence_stale_seconds": self.evidence_stale_seconds,
            "evidence_last_queue_read_at": self.evidence_last_queue_read_at.isoformat(),
            "evidence_blocker_summary": self.evidence_blocker_summary,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class PrimeAutonomyInput:
    """What Prime receives when selecting next action."""

    current_sessions: tuple["SessionLifecycleState", ...]
    queues_by_harness: frozenset[tuple[str, tuple[str, ...]]]
    approvals_pending: tuple[tuple[str, str], ...]
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    recent_completions: tuple[str, ...]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "current_sessions": [s.to_dict() for s in self.current_sessions],
            "queues_by_harness": {k: list(v) for k, v in self.queues_by_harness},
            "approvals_pending": list(self.approvals_pending),
            "restart_resteer_findings": [f.to_dict() for f in self.restart_resteer_findings],
            "recent_completions": list(self.recent_completions),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SessionLifecycleState:
    """Authoritative snapshot of a session.

    All fields are immutable. Use with_* methods or construct a new instance to update state.
    """

    # Identity
    session_id: str
    session_name: str

    # Context
    project_name: str
    project_path: Optional[str]

    # Role and Queue
    harness_role: HarnessRole
    assigned_queue_file: str

    # Model and Provider
    model_provider: str
    model_name: str

    # Execution State
    status: SessionStatus
    worktree_path: str
    branch_name: str

    # Task Context
    current_task_id: Optional[str]

    # Heartbeat and Metrics
    last_queue_read_at: datetime
    last_queue_write_at: datetime
    last_prompt_sent_at: datetime
    last_prompt_payload_size: int

    # Review and Proof
    review_cadence_state: ReviewCadenceState
    proof_state: ProofState

    # Health
    health_state: HealthState
    blocker_summary: Optional[str]

    # Permissions
    permission_context: PermissionContext

    # Relay Routing Decisions
    routing_action: Optional[SessionAction] = None
    routing_reason: Optional[SessionActionReason] = None

    def is_idle(self) -> bool:
        """True if waiting for work: POLLING, WAITING, or REVIEW_GATED."""
        return self.status in (
            SessionStatus.POLLING,
            SessionStatus.WAITING,
            SessionStatus.REVIEW_GATED,
        )

    def is_healthy(self) -> bool:
        """True if health_state is HEALTHY and no blocker."""
        return self.health_state == HealthState.HEALTHY and self.blocker_summary is None

    def can_accept_work(self) -> bool:
        """True if able to transition to RUNNING."""
        if self.status in (
            SessionStatus.BLOCKED,
            SessionStatus.STALE,
            SessionStatus.ARCHIVED,
            SessionStatus.CAPACITY_LIMITED,
        ):
            return False
        if not self.is_healthy():
            return False
        if self.permission_context.is_permission_locked():
            return False
        if self.permission_context.is_unlock_expired():
            return False
        if not self.permission_context.is_unlock_task_scoped(self.current_task_id):
            return False
        return True

    def heartbeat_stale(self, threshold_seconds: int = 1800) -> bool:
        """True if last_prompt_sent_at is older than threshold (in seconds)."""
        elapsed = datetime.now(timezone.utc) - self.last_prompt_sent_at.replace(
            tzinfo=timezone.utc
        )
        return elapsed.total_seconds() > threshold_seconds

    def suggest_routing_action(
        self,
        context_health_degraded: bool = False,
        payload_near_limit: bool = False,
        reasoning_mode_shifted: bool = False,
        project_changed: bool = False,
        surface_mode_changed: bool = False,
        tool_or_auth_broken: bool = False,
        defect_found: bool = False,
        tier_3_needs_independence: bool = False,
        context_needs_fill: bool = False,
        review_gate_pending: bool = False,
        permission_boundary_crossed: bool = False,
        should_archive: bool = False,
    ) -> tuple[SessionAction, SessionActionReason]:
        """Suggest routing action based on session state signals.

        Returns tuple of (SessionAction, SessionActionReason).
        """
        if tool_or_auth_broken:
            return (SessionAction.AVOID, SessionActionReason.TOOL_MISMATCH)
        if permission_boundary_crossed:
            return (SessionAction.REQUEST_HUMAN_GATE, SessionActionReason.PERMISSION_BOUNDARY)
        if review_gate_pending:
            return (SessionAction.REQUEST_HUMAN_GATE, SessionActionReason.REVIEW_GATE)
        if should_archive:
            return (SessionAction.ARCHIVE, SessionActionReason.CONTEXT_FILL)
        if context_needs_fill:
            return (SessionAction.START_NEW, SessionActionReason.CONTEXT_FILL)
        if payload_near_limit:
            return (SessionAction.SUMMARIZE_RESET, SessionActionReason.PAYLOAD_BUDGET)
        if context_health_degraded or self.heartbeat_stale():
            return (SessionAction.START_NEW, SessionActionReason.STALE_HEARTBEAT)
        if reasoning_mode_shifted:
            return (SessionAction.START_NEW, SessionActionReason.REASONING_SHIFT)
        if project_changed:
            return (SessionAction.START_NEW, SessionActionReason.PROJECT_SCOPE)
        if surface_mode_changed:
            return (SessionAction.START_NEW, SessionActionReason.SURFACE_MODE)
        if defect_found:
            return (SessionAction.START_NEW, SessionActionReason.DEFECT_FOUND)
        if tier_3_needs_independence:
            return (SessionAction.TRANSFER, SessionActionReason.DUAL_LANE_NEEDED)
        if self.is_healthy() and not context_health_degraded:
            return (SessionAction.REUSE, SessionActionReason.CONTEXT_HEALTHY)
        return (SessionAction.START_NEW, SessionActionReason.CONTEXT_POLLUTION)

    def is_permission_locked(self) -> bool:
        """True if branch is currently locked."""
        return self.permission_context.is_permission_locked()

    def requires_approval_for_operation(self, operation: OperationScope) -> bool:
        """True if operation requires explicit approval."""
        return self.permission_context.requires_approval_for_operation(operation)

    def can_execute_operation(self, operation: OperationScope) -> bool:
        """True if operation can execute without escalation."""
        return self.permission_context.can_execute_operation(operation, self.current_task_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict for Bifrost."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "harness_role": self.harness_role.value,
            "assigned_queue_file": self.assigned_queue_file,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "status": self.status.value,
            "worktree_path": self.worktree_path,
            "branch_name": self.branch_name,
            "current_task_id": self.current_task_id,
            "last_queue_read_at": self.last_queue_read_at.isoformat(),
            "last_queue_write_at": self.last_queue_write_at.isoformat(),
            "last_prompt_sent_at": self.last_prompt_sent_at.isoformat(),
            "last_prompt_payload_size": self.last_prompt_payload_size,
            "review_cadence_state": self.review_cadence_state.value,
            "proof_state": self.proof_state.value,
            "health_state": self.health_state.value,
            "blocker_summary": self.blocker_summary,
            "permission_context": self.permission_context.to_dict(),
            "routing_action": self.routing_action.value if self.routing_action else None,
            "routing_reason": self.routing_reason.value if self.routing_reason else None,
        }


@dataclass(frozen=True)
class SessionCommandPlan:
    """Prime's proposed action for a session.

    Must be typed and auditable before execution.
    """

    # Target
    session_id: str
    session_name: str

    # Intent and Reason
    command_intent: CommandIntent
    reason: str

    # Expected Outcome
    expected_state_transition: tuple[SessionStatus, SessionStatus]

    # Evidence References
    current_state_evidence: str
    queue_file_evidence: str
    worktree_evidence: str
    review_gate_evidence: Optional[str]
    proof_requirement: ProofState

    # Affected Resources
    queue_file_affected: str
    worktree_path_affected: str
    branch_affected: str

    # Safety Gates
    aegis_gate_result: Optional[str]
    cadence_gate_required: bool
    cadence_gate_status: ReviewCadenceState

    # Executability
    is_executable_now: bool
    human_approval_required: bool
    approval_context: Optional[str]

    # Recovery
    rollback_or_recovery_note: Optional[str]

    def is_executable(self) -> bool:
        """True if command can execute immediately.

        Checks: is_executable_now, human_approval_required, proof requirement.
        """
        return (
            self.is_executable_now
            and not self.human_approval_required
            and self.proof_requirement != ProofState.NO_PROOF
        )

    def requires_aegis_approval(self) -> bool:
        """True if this command needs Aegis gate verification."""
        high_risk_intents = {
            CommandIntent.TRANSFER,
            CommandIntent.ARCHIVE,
            CommandIntent.RESTART,
            CommandIntent.RECOVER_FROM_LIMIT,
        }
        return self.command_intent in high_risk_intents

    def is_legal(self, current_state: SessionLifecycleState) -> bool:
        """True if this command is legal given current session state."""
        legal_transitions = {
            CommandIntent.SPAWN: {SessionStatus.STARTING},
            CommandIntent.WATCH: {SessionStatus.RUNNING, SessionStatus.POLLING},
            CommandIntent.POLL_QUEUE: {
                SessionStatus.STARTING,
                SessionStatus.POLLING,
                SessionStatus.RUNNING,
                SessionStatus.WAITING,
                SessionStatus.BLOCKED,
                SessionStatus.REVIEW_GATED,
                SessionStatus.CAPACITY_LIMITED,
                SessionStatus.STALE,
                SessionStatus.STOPPED,
            },
            CommandIntent.STEER: {SessionStatus.RUNNING},
            CommandIntent.STOP_REQUEST: {
                SessionStatus.STARTING,
                SessionStatus.POLLING,
                SessionStatus.RUNNING,
                SessionStatus.WAITING,
                SessionStatus.BLOCKED,
                SessionStatus.REVIEW_GATED,
                SessionStatus.CAPACITY_LIMITED,
                SessionStatus.STALE,
            },
            CommandIntent.TRANSFER: {SessionStatus.RUNNING, SessionStatus.WAITING},
            CommandIntent.ARCHIVE: {SessionStatus.STOPPED, SessionStatus.ARCHIVED},
            CommandIntent.RESTART: {SessionStatus.STOPPED, SessionStatus.STALE},
            CommandIntent.RESTEER: {SessionStatus.RUNNING},
            CommandIntent.RECOVER_FROM_LIMIT: {SessionStatus.CAPACITY_LIMITED},
            CommandIntent.REQUEST_HUMAN_GATE: {s for s in SessionStatus},
        }

        allowed_states = legal_transitions.get(self.command_intent, set())
        return current_state.status in allowed_states

    def verify_state_transition_legal(self) -> bool:
        """True if expected_state_transition matches contract rules."""
        from_state, to_state = self.expected_state_transition

        legal_transitions = {
            (SessionStatus.STARTING, SessionStatus.POLLING),
            (SessionStatus.POLLING, SessionStatus.POLLING),
            (SessionStatus.POLLING, SessionStatus.RUNNING),
            (SessionStatus.RUNNING, SessionStatus.WAITING),
            (SessionStatus.RUNNING, SessionStatus.BLOCKED),
            (SessionStatus.WAITING, SessionStatus.RUNNING),
            (SessionStatus.WAITING, SessionStatus.BLOCKED),
            (SessionStatus.BLOCKED, SessionStatus.WAITING),
            (SessionStatus.BLOCKED, SessionStatus.POLLING),
            (SessionStatus.REVIEW_GATED, SessionStatus.RUNNING),
            (SessionStatus.REVIEW_GATED, SessionStatus.BLOCKED),
            (SessionStatus.CAPACITY_LIMITED, SessionStatus.RUNNING),
            (SessionStatus.CAPACITY_LIMITED, SessionStatus.WAITING),
            (SessionStatus.STALE, SessionStatus.RUNNING),
            (SessionStatus.STALE, SessionStatus.ARCHIVED),
            (SessionStatus.STOPPED, SessionStatus.ARCHIVED),
            (SessionStatus.ARCHIVED, SessionStatus.ARCHIVED),
        }

        return (from_state, to_state) in legal_transitions

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict for Bifrost preview."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "command_intent": self.command_intent.value,
            "reason": self.reason,
            "expected_state_transition": [
                self.expected_state_transition[0].value,
                self.expected_state_transition[1].value,
            ],
            "current_state_evidence": self.current_state_evidence,
            "queue_file_evidence": self.queue_file_evidence,
            "worktree_evidence": self.worktree_evidence,
            "review_gate_evidence": self.review_gate_evidence,
            "proof_requirement": self.proof_requirement.value,
            "queue_file_affected": self.queue_file_affected,
            "worktree_path_affected": self.worktree_path_affected,
            "branch_affected": self.branch_affected,
            "aegis_gate_result": self.aegis_gate_result,
            "cadence_gate_required": self.cadence_gate_required,
            "cadence_gate_status": self.cadence_gate_status.value,
            "is_executable_now": self.is_executable_now,
            "human_approval_required": self.human_approval_required,
            "approval_context": self.approval_context,
            "rollback_or_recovery_note": self.rollback_or_recovery_note,
        }


def generate_restart_finding(
    session: SessionLifecycleState,
    threshold_seconds: int = 1800,
    timestamp: Optional[datetime] = None,
) -> Optional[RestartResteerFinding]:
    """Create a Beacon restart advisory for a stale session.

    This is pure advisory state. It does not restart, inspect, or mutate a live session.
    """
    observed_at = timestamp or datetime.now(timezone.utc)
    stale_seconds = int(
        (
            observed_at.replace(tzinfo=timezone.utc)
            - session.last_prompt_sent_at.replace(tzinfo=timezone.utc)
        ).total_seconds()
    )
    if stale_seconds <= threshold_seconds:
        return None

    return RestartResteerFinding(
        session_id=session.session_id,
        finding_type=FindingType.RESTART,
        reason="Session heartbeat exceeded stale threshold",
        evidence_stale_seconds=stale_seconds,
        evidence_last_queue_read_at=session.last_queue_read_at,
        evidence_blocker_summary=session.blocker_summary,
        recommended_action="Stage restart recovery through a human/Aegis-gated command plan",
        timestamp=observed_at,
    )


def generate_resteer_finding(
    session: SessionLifecycleState,
    blocker: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Optional[RestartResteerFinding]:
    """Create a Beacon resteer advisory for a blocked or review-gated session.

    This is pure advisory state. It records evidence but does not steer a session.
    """
    blocker_summary = blocker or session.blocker_summary
    if not blocker_summary and session.status not in (
        SessionStatus.BLOCKED,
        SessionStatus.REVIEW_GATED,
    ):
        return None

    observed_at = timestamp or datetime.now(timezone.utc)
    stale_seconds = int(
        (
            observed_at.replace(tzinfo=timezone.utc)
            - session.last_prompt_sent_at.replace(tzinfo=timezone.utc)
        ).total_seconds()
    )

    return RestartResteerFinding(
        session_id=session.session_id,
        finding_type=FindingType.RESTEER,
        reason=blocker_summary or "Session requires resteer review",
        evidence_stale_seconds=stale_seconds,
        evidence_last_queue_read_at=session.last_queue_read_at,
        evidence_blocker_summary=blocker_summary,
        recommended_action="Stage resteer recovery through a human/Aegis-gated command plan",
        timestamp=observed_at,
    )


def gather_prime_autonomy_input(
    sessions: tuple[SessionLifecycleState, ...] | list[SessionLifecycleState],
    queues_by_harness: dict[str, tuple[str, ...] | list[str]],
    approvals_pending: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    | list[RestartResteerFinding] = (),
    recent_completions: tuple[str, ...] | list[str] = (),
    timestamp: Optional[datetime] = None,
) -> PrimeAutonomyInput:
    """Collect immutable Prime advisory input from Session Lifecycle snapshots."""
    immutable_queues = frozenset(
        (harness, tuple(queue_files))
        for harness, queue_files in queues_by_harness.items()
    )
    return PrimeAutonomyInput(
        current_sessions=tuple(sessions),
        queues_by_harness=immutable_queues,
        approvals_pending=tuple(approvals_pending),
        restart_resteer_findings=tuple(restart_resteer_findings),
        recent_completions=tuple(recent_completions),
        timestamp=timestamp or datetime.now(timezone.utc),
    )
