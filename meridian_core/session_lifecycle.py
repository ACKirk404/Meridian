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


class WorkflowHeartbeatStatus(Enum):
    """Display-safe workflow work-order heartbeat status."""

    FRESH = "fresh"
    WARNING = "warning"
    STALE = "stale"
    MISSING = "missing"


class WorkflowResultKind(Enum):
    """Display-safe workflow work-order result/error kind."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMEOUT = "timeout"
    TOOL_DENIED = "tool_denied"
    GATE_REQUIRED = "gate_required"
    RESTEER_REQUESTED = "resteer_requested"
    INTERNAL_ERROR = "internal_error"


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
class SessionPermissionSummary:
    """Display-safe permission/advisory summary for Prime and Beacon."""

    session_id: str
    session_name: str
    permission_state: PermissionState
    approved_operations: tuple[OperationScope, ...]
    blockers: tuple[str, ...]
    approvals_pending: tuple[str, ...]
    review_gate_blockers: tuple[str, ...]
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    evidence: tuple[str, ...]
    can_accept_work: bool
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe advisory metadata."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "permission_state": self.permission_state.value,
            "approved_operations": [
                operation.value for operation in self.approved_operations
            ],
            "blockers": list(self.blockers),
            "approvals_pending": list(self.approvals_pending),
            "review_gate_blockers": list(self.review_gate_blockers),
            "restart_resteer_findings": [
                finding.to_dict() for finding in self.restart_resteer_findings
            ],
            "evidence": list(self.evidence),
            "can_accept_work": self.can_accept_work,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class WorkflowWorkOrderRecoverySummary:
    """Advisory heartbeat/result summary for bounded workflow recovery."""

    work_order_id: str
    target_session_id: str
    heartbeat_age_seconds: Optional[int]
    heartbeat_status: WorkflowHeartbeatStatus
    result_kind: WorkflowResultKind
    error_kind: Optional[str]
    retry_resteer_recommendation: Optional[str]
    recovery_action: SessionAction
    permission_blockers: tuple[str, ...]
    review_gate_blockers: tuple[str, ...]
    stale_session_recovery_rationale: str
    evidence: tuple[str, ...]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize workflow recovery advice to display-safe metadata."""
        return {
            "work_order_id": self.work_order_id,
            "target_session_id": self.target_session_id,
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "heartbeat_status": self.heartbeat_status.value,
            "result_kind": self.result_kind.value,
            "error_kind": self.error_kind,
            "retry_resteer_recommendation": self.retry_resteer_recommendation,
            "recovery_action": self.recovery_action.value,
            "permission_blockers": list(self.permission_blockers),
            "review_gate_blockers": list(self.review_gate_blockers),
            "stale_session_recovery_rationale": self.stale_session_recovery_rationale,
            "evidence": list(self.evidence),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SessionRuntimeStateExport:
    """Display-safe runtime state export for workflow recovery advice."""

    state_id: str
    session_id: str
    session_name: str
    status: SessionStatus
    health_state: HealthState
    current_task_id: str
    active_command_kind: Optional[CommandIntent]
    target_session_id: Optional[str]
    recommended_recovery_action: Optional[SessionAction]
    heartbeat_status: Optional[WorkflowHeartbeatStatus]
    heartbeat_age_seconds: Optional[int]
    result_kind: Optional[WorkflowResultKind]
    permission_state: PermissionState
    permission_blockers: tuple[str, ...]
    review_gate_blockers: tuple[str, ...]
    human_gate_blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize runtime-state export to JSON-safe advisory metadata."""
        return {
            "state_id": self.state_id,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "status": self.status.value,
            "health_state": self.health_state.value,
            "current_task_id": self.current_task_id,
            "active_command_kind": (
                self.active_command_kind.value if self.active_command_kind else None
            ),
            "target_session_id": self.target_session_id,
            "recommended_recovery_action": (
                self.recommended_recovery_action.value
                if self.recommended_recovery_action
                else None
            ),
            "heartbeat_status": (
                self.heartbeat_status.value if self.heartbeat_status else None
            ),
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "result_kind": self.result_kind.value if self.result_kind else None,
            "permission_state": self.permission_state.value,
            "permission_blockers": list(self.permission_blockers),
            "review_gate_blockers": list(self.review_gate_blockers),
            "human_gate_blockers": list(self.human_gate_blockers),
            "evidence_refs": list(self.evidence_refs),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SessionLiveControlPermissionGate:
    """Advisory permission gate for future live-control execution readiness."""

    gate_id: str
    target_session_id: str
    command_kind: Optional[CommandIntent]
    recommended_action: Optional[SessionAction]
    required_operation: Optional[OperationScope]
    ready_for_execution: bool
    human_gate_required: bool
    human_gate_rationale: str
    blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize permission-gate advice to display-safe metadata."""
        return {
            "gate_id": self.gate_id,
            "target_session_id": self.target_session_id,
            "command_kind": self.command_kind.value if self.command_kind else None,
            "recommended_action": (
                self.recommended_action.value if self.recommended_action else None
            ),
            "required_operation": (
                self.required_operation.value if self.required_operation else None
            ),
            "ready_for_execution": self.ready_for_execution,
            "human_gate_required": self.human_gate_required,
            "human_gate_rationale": self.human_gate_rationale,
            "blockers": list(self.blockers),
            "evidence_refs": list(self.evidence_refs),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(frozen=True)
class SessionRecoveryReadinessSummary:
    """Display-safe recovery readiness summary for Prime/Beacon consumers."""

    summary_id: str
    state_id: str
    gate_id: str
    target_session_id: str
    command_kind: Optional[CommandIntent]
    recommended_action: Optional[SessionAction]
    required_operation: Optional[OperationScope]
    readiness_status: str
    ready_for_execution: bool
    human_gate_required: bool
    human_gate_rationale: str
    heartbeat_status: Optional[WorkflowHeartbeatStatus]
    result_kind: Optional[WorkflowResultKind]
    permission_state: PermissionState
    blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialize readiness advice to JSON-safe metadata."""
        return {
            "summary_id": self.summary_id,
            "state_id": self.state_id,
            "gate_id": self.gate_id,
            "target_session_id": self.target_session_id,
            "command_kind": self.command_kind.value if self.command_kind else None,
            "recommended_action": (
                self.recommended_action.value if self.recommended_action else None
            ),
            "required_operation": (
                self.required_operation.value if self.required_operation else None
            ),
            "readiness_status": self.readiness_status,
            "ready_for_execution": self.ready_for_execution,
            "human_gate_required": self.human_gate_required,
            "human_gate_rationale": self.human_gate_rationale,
            "heartbeat_status": (
                self.heartbeat_status.value if self.heartbeat_status else None
            ),
            "result_kind": self.result_kind.value if self.result_kind else None,
            "permission_state": self.permission_state.value,
            "blockers": list(self.blockers),
            "evidence_refs": list(self.evidence_refs),
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
    permission_summaries: tuple[SessionPermissionSummary, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        return {
            "current_sessions": [s.to_dict() for s in self.current_sessions],
            "queues_by_harness": {k: list(v) for k, v in self.queues_by_harness},
            "approvals_pending": list(self.approvals_pending),
            "restart_resteer_findings": [f.to_dict() for f in self.restart_resteer_findings],
            "recent_completions": list(self.recent_completions),
            "timestamp": self.timestamp.isoformat(),
            "permission_summaries": [
                summary.to_dict() for summary in self.permission_summaries
            ],
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

    # Permission advisory evidence
    permission_state: Optional[PermissionState] = None
    permission_task_scope: Optional[str] = None
    permission_unlock_expiry: Optional[datetime] = None
    permission_approved_operations: tuple[OperationScope, ...] = ()
    permission_operation: Optional[OperationScope] = None
    permission_operation_allowed: bool = False
    permission_evidence: Optional[str] = None

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

    def permission_blocker(self) -> Optional[str]:
        """Return the display-safe permission blocker for this command, if any."""
        if self.permission_operation is None or self.permission_operation_allowed:
            return None
        return f"permission_required_for_{self.permission_operation.value}"

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

    def audit_evidence(self) -> dict[str, Any]:
        """Return display-safe audit metadata for Prime/Bifrost."""
        blockers: list[str] = []
        if self.human_approval_required:
            blockers.append("human_approval_required")
        if not self.is_executable_now:
            blockers.append("not_executable_now")
        if self.proof_requirement == ProofState.NO_PROOF:
            blockers.append("proof_missing")
        if self.approval_context:
            blockers.append(self.approval_context)
        permission_blocker = self.permission_blocker()
        if permission_blocker:
            blockers.append(permission_blocker)

        return {
            "plan": {
                "action": self.command_intent.value,
                "reason": self.reason,
                "expected_transition": [
                    self.expected_state_transition[0].value,
                    self.expected_state_transition[1].value,
                ],
                "is_executable": self.is_executable(),
            },
            "blockers": blockers,
            "permission": {
                "proof_requirement": self.proof_requirement.value,
                "aegis_gate_result": self.aegis_gate_result,
                "branch_affected": self.branch_affected,
                "worktree_path_affected": self.worktree_path_affected,
                "permission_state": (
                    self.permission_state.value if self.permission_state else None
                ),
                "task_scope": self.permission_task_scope,
                "unlock_expiry": (
                    self.permission_unlock_expiry.isoformat()
                    if self.permission_unlock_expiry
                    else None
                ),
                "approved_operations": [
                    operation.value for operation in self.permission_approved_operations
                ],
                "operation": (
                    self.permission_operation.value if self.permission_operation else None
                ),
                "operation_allowed": self.permission_operation_allowed,
                "evidence": self.permission_evidence,
            },
            "review_gate": {
                "cadence_gate_required": self.cadence_gate_required,
                "cadence_gate_status": self.cadence_gate_status.value,
                "review_gate_evidence": self.review_gate_evidence,
                "human_approval_required": self.human_approval_required,
            },
            "recovery": {
                "rollback_or_recovery_note": self.rollback_or_recovery_note,
                "queue_file_affected": self.queue_file_affected,
            },
        }

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
            "permission_state": (
                self.permission_state.value if self.permission_state else None
            ),
            "permission_task_scope": self.permission_task_scope,
            "permission_unlock_expiry": (
                self.permission_unlock_expiry.isoformat()
                if self.permission_unlock_expiry
                else None
            ),
            "permission_approved_operations": [
                operation.value for operation in self.permission_approved_operations
            ],
            "permission_operation": (
                self.permission_operation.value if self.permission_operation else None
            ),
            "permission_operation_allowed": self.permission_operation_allowed,
            "permission_evidence": self.permission_evidence,
            "audit_evidence": self.audit_evidence(),
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


def _approval_reasons_for_session(
    session_id: str,
    approvals_pending: tuple[tuple[str, str], ...] | list[tuple[str, str]],
) -> tuple[str, ...]:
    return tuple(reason for pending_session_id, reason in approvals_pending if pending_session_id == session_id)


def _findings_for_session(
    session: SessionLifecycleState,
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    | list[RestartResteerFinding],
    stale_threshold_seconds: int,
    timestamp: datetime,
) -> tuple[RestartResteerFinding, ...]:
    findings = [
        finding
        for finding in restart_resteer_findings
        if finding.session_id == session.session_id
    ]
    existing_types = {finding.finding_type for finding in findings}

    if FindingType.RESTART not in existing_types:
        restart_finding = generate_restart_finding(
            session,
            threshold_seconds=stale_threshold_seconds,
            timestamp=timestamp,
        )
        if restart_finding is not None:
            findings.append(restart_finding)

    if FindingType.RESTEER not in existing_types:
        resteer_finding = generate_resteer_finding(session, timestamp=timestamp)
        if resteer_finding is not None:
            findings.append(resteer_finding)

    return tuple(findings)


def _permission_unlock_expired_at(
    permission: PermissionContext,
    observed_at: datetime,
) -> bool:
    if permission.unlock_expiry is None:
        return False
    return _as_utc(observed_at) > _as_utc(permission.unlock_expiry)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _session_can_accept_work_at(
    session: SessionLifecycleState,
    observed_at: datetime,
) -> bool:
    if session.status in (
        SessionStatus.BLOCKED,
        SessionStatus.STALE,
        SessionStatus.ARCHIVED,
        SessionStatus.CAPACITY_LIMITED,
    ):
        return False
    if not session.is_healthy():
        return False
    if session.permission_context.is_permission_locked():
        return False
    if _permission_unlock_expired_at(session.permission_context, observed_at):
        return False
    if not session.permission_context.is_unlock_task_scoped(session.current_task_id):
        return False
    return True


def summarize_session_permission_state(
    session: SessionLifecycleState,
    approvals_pending: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    | list[RestartResteerFinding] = (),
    stale_threshold_seconds: int = 1800,
    timestamp: Optional[datetime] = None,
) -> SessionPermissionSummary:
    """Summarize one session's permission state for Prime/Beacon advice.

    The summary is display-safe and serializable. It does not execute or stage
    session control, branch movement, or worktree movement.
    """
    observed_at = timestamp or datetime.now(timezone.utc)
    permission = session.permission_context
    approved_operations = tuple(
        sorted(permission.approval_scope, key=lambda operation: operation.value)
    )
    can_accept_work = _session_can_accept_work_at(session, observed_at)
    blockers: list[str] = []
    if permission.is_permission_locked():
        blockers.append("permission.locked")
    if _permission_unlock_expired_at(permission, observed_at):
        blockers.append("permission.unlock_expired")
    if not permission.is_unlock_task_scoped(session.current_task_id):
        blockers.append("permission.out_of_scope")
    if permission.escalation_gate:
        blockers.append(
            "permission.escalation_gate"
            if permission.escalation_reason is None
            else f"permission.escalation_gate:{permission.escalation_reason}"
        )

    approval_reasons = _approval_reasons_for_session(session.session_id, approvals_pending)
    blockers.extend(f"approval.pending:{reason}" for reason in approval_reasons)

    review_gate_blockers: list[str] = []
    if session.status == SessionStatus.REVIEW_GATED:
        review_gate_blockers.append("review_gate.status=review_gated")
    if session.review_cadence_state in (
        ReviewCadenceState.PENDING,
        ReviewCadenceState.REVIEW_GATED,
        ReviewCadenceState.FAILED,
    ):
        review_gate_blockers.append(
            f"review_gate.cadence={session.review_cadence_state.value}"
        )
    blockers.extend(review_gate_blockers)

    findings = _findings_for_session(
        session,
        restart_resteer_findings,
        stale_threshold_seconds,
        observed_at,
    )

    evidence = [
        f"session.id={session.session_id}",
        f"session.status={session.status.value}",
        f"session.health={session.health_state.value}",
        f"permission.state={permission.branch_permission_state.value}",
        "permission.approved_operations="
        + (",".join(operation.value for operation in approved_operations) or "none"),
        f"permission.task_scope={permission.task_scope or 'none'}",
        "permission.unlock_expiry="
        + (permission.unlock_expiry.isoformat() if permission.unlock_expiry else "none"),
        f"permission.can_accept_work={can_accept_work}",
    ]
    evidence.extend(f"approval.pending={reason}" for reason in approval_reasons)
    evidence.extend(review_gate_blockers)
    evidence.extend(f"blocker={blocker}" for blocker in blockers)
    evidence.extend(
        f"finding.{finding.finding_type.value}=stale_seconds:{finding.evidence_stale_seconds}"
        for finding in findings
    )
    evidence.extend(
        f"finding.{finding.finding_type.value}.recommendation={finding.recommended_action}"
        for finding in findings
    )

    return SessionPermissionSummary(
        session_id=session.session_id,
        session_name=session.session_name,
        permission_state=permission.branch_permission_state,
        approved_operations=approved_operations,
        blockers=tuple(blockers),
        approvals_pending=approval_reasons,
        review_gate_blockers=tuple(review_gate_blockers),
        restart_resteer_findings=findings,
        evidence=tuple(evidence),
        can_accept_work=can_accept_work,
        timestamp=observed_at,
    )


def summarize_session_permission_states(
    sessions: tuple[SessionLifecycleState, ...] | list[SessionLifecycleState],
    approvals_pending: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    | list[RestartResteerFinding] = (),
    stale_threshold_seconds: int = 1800,
    timestamp: Optional[datetime] = None,
) -> tuple[SessionPermissionSummary, ...]:
    """Aggregate permission summaries in session order for advisory consumers."""
    observed_at = timestamp or datetime.now(timezone.utc)
    return tuple(
        summarize_session_permission_state(
            session,
            approvals_pending=approvals_pending,
            restart_resteer_findings=restart_resteer_findings,
            stale_threshold_seconds=stale_threshold_seconds,
            timestamp=observed_at,
        )
        for session in sessions
    )


def summarize_workflow_work_order_recovery(
    session: SessionLifecycleState,
    work_order_id: str,
    heartbeat_emitted_at: Optional[datetime] = None,
    result_kind: WorkflowResultKind = WorkflowResultKind.PENDING,
    error_kind: Optional[str] = None,
    retry_resteer_recommendation: Optional[str] = None,
    heartbeat_stale_after_seconds: int = 300,
    timestamp: Optional[datetime] = None,
) -> WorkflowWorkOrderRecoverySummary:
    """Summarize workflow work-order heartbeat/result state for recovery advice.

    This is a pure advisory surface. It does not restart, resteer, archive, gate,
    inspect, or mutate workflow or session runtime state.
    """
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    heartbeat_age_seconds = _workflow_heartbeat_age_seconds(
        heartbeat_emitted_at,
        observed_at,
    )
    heartbeat_status = _workflow_heartbeat_status(
        heartbeat_age_seconds,
        heartbeat_stale_after_seconds,
    )
    permission_summary = summarize_session_permission_state(
        session,
        timestamp=observed_at,
    )
    permission_blockers = tuple(
        blocker
        for blocker in permission_summary.blockers
        if blocker.startswith(
            (
                "permission.",
                "approval.pending",
            )
        )
    )
    review_gate_blockers = permission_summary.review_gate_blockers
    recovery_action = _workflow_recovery_action(
        heartbeat_status,
        result_kind,
        permission_blockers,
        review_gate_blockers,
    )
    rationale = _workflow_recovery_rationale(
        heartbeat_status,
        result_kind,
        recovery_action,
    )
    evidence = [
        f"work_order.id={work_order_id}",
        f"target_session.id={session.session_id}",
        f"heartbeat.status={heartbeat_status.value}",
        "heartbeat.age_seconds="
        + ("unknown" if heartbeat_age_seconds is None else str(heartbeat_age_seconds)),
        f"result.kind={result_kind.value}",
        f"recovery.action={recovery_action.value}",
        f"recovery.rationale={rationale}",
    ]
    if error_kind is not None:
        evidence.append(f"error.kind={error_kind}")
    if retry_resteer_recommendation is not None:
        evidence.append(
            f"retry_resteer.recommendation={retry_resteer_recommendation}"
        )
    evidence.extend(f"blocker={blocker}" for blocker in permission_blockers)
    evidence.extend(f"blocker={blocker}" for blocker in review_gate_blockers)

    return WorkflowWorkOrderRecoverySummary(
        work_order_id=work_order_id,
        target_session_id=session.session_id,
        heartbeat_age_seconds=heartbeat_age_seconds,
        heartbeat_status=heartbeat_status,
        result_kind=result_kind,
        error_kind=error_kind,
        retry_resteer_recommendation=retry_resteer_recommendation,
        recovery_action=recovery_action,
        permission_blockers=permission_blockers,
        review_gate_blockers=review_gate_blockers,
        stale_session_recovery_rationale=rationale,
        evidence=tuple(evidence),
        timestamp=observed_at,
    )


def export_session_runtime_state_for_workflow_recovery(
    session: SessionLifecycleState,
    command_plan: Optional[SessionCommandPlan] = None,
    permission_summary: Optional[SessionPermissionSummary] = None,
    workflow_recovery_summary: Optional[WorkflowWorkOrderRecoverySummary] = None,
    approvals_pending: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    restart_resteer_findings: tuple[RestartResteerFinding, ...]
    | list[RestartResteerFinding] = (),
    stale_threshold_seconds: int = 1800,
    timestamp: Optional[datetime] = None,
) -> SessionRuntimeStateExport:
    """Export deterministic runtime-state advice for Prime/Beacon recovery views.

    This combines already-typed Session Lifecycle surfaces into serializable
    advisory fields only. It does not spawn, inspect, move, restart, or steer.
    """
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    summary = permission_summary or summarize_session_permission_state(
        session,
        approvals_pending=approvals_pending,
        restart_resteer_findings=restart_resteer_findings,
        stale_threshold_seconds=stale_threshold_seconds,
        timestamp=observed_at,
    )
    workflow = workflow_recovery_summary

    permission_blockers = tuple(
        blocker
        for blocker in summary.blockers
        if blocker.startswith(("permission.", "approval.pending"))
    )
    review_gate_blockers = summary.review_gate_blockers
    human_gate_blockers = list(permission_blockers)
    human_gate_blockers.extend(review_gate_blockers)

    evidence_refs = [
        f"state.id={session.session_id}:{session.status.value}:{observed_at.isoformat()}",
        f"session.id={session.session_id}",
        f"session.status={session.status.value}",
        f"session.health={session.health_state.value}",
        f"session.current_task_id={session.current_task_id}",
        f"permission.summary.session_id={summary.session_id}",
        f"permission.state={summary.permission_state.value}",
    ]
    evidence_refs.extend(f"permission.blocker={blocker}" for blocker in permission_blockers)
    evidence_refs.extend(f"review.blocker={blocker}" for blocker in review_gate_blockers)

    if command_plan is not None:
        audit = command_plan.audit_evidence()
        evidence_refs.extend(
            [
                f"command.kind={command_plan.command_intent.value}",
                f"command.target_session_id={command_plan.session_id}",
                f"command.executable={audit['plan']['is_executable']}",
            ]
        )
        human_gate_blockers.extend(str(blocker) for blocker in audit["blockers"])
        if command_plan.session_id != session.session_id:
            human_gate_blockers.append("command.target_session_mismatch")
            evidence_refs.append("command.target_session_mismatch=True")
    else:
        evidence_refs.append("command.kind=none")

    if workflow is not None:
        evidence_refs.extend(
            [
                f"workflow.work_order_id={workflow.work_order_id}",
                f"workflow.target_session_id={workflow.target_session_id}",
                f"workflow.heartbeat_status={workflow.heartbeat_status.value}",
                "workflow.heartbeat_age_seconds="
                + (
                    "unknown"
                    if workflow.heartbeat_age_seconds is None
                    else str(workflow.heartbeat_age_seconds)
                ),
                f"workflow.result_kind={workflow.result_kind.value}",
                f"workflow.recovery_action={workflow.recovery_action.value}",
            ]
        )
        evidence_refs.extend(f"workflow.evidence={item}" for item in workflow.evidence)
        if workflow.target_session_id != session.session_id:
            human_gate_blockers.append("workflow.target_session_mismatch")
            evidence_refs.append("workflow.target_session_mismatch=True")
    else:
        evidence_refs.append("workflow.summary=none")

    return SessionRuntimeStateExport(
        state_id=f"{session.session_id}:{session.status.value}:{observed_at.isoformat()}",
        session_id=session.session_id,
        session_name=session.session_name,
        status=session.status,
        health_state=session.health_state,
        current_task_id=session.current_task_id,
        active_command_kind=command_plan.command_intent if command_plan else None,
        target_session_id=workflow.target_session_id if workflow else None,
        recommended_recovery_action=workflow.recovery_action if workflow else None,
        heartbeat_status=workflow.heartbeat_status if workflow else None,
        heartbeat_age_seconds=workflow.heartbeat_age_seconds if workflow else None,
        result_kind=workflow.result_kind if workflow else None,
        permission_state=summary.permission_state,
        permission_blockers=permission_blockers,
        review_gate_blockers=review_gate_blockers,
        human_gate_blockers=tuple(dict.fromkeys(human_gate_blockers)),
        evidence_refs=tuple(evidence_refs),
        timestamp=observed_at,
    )


def evaluate_live_control_permission_gate(
    session: SessionLifecycleState,
    runtime_export: SessionRuntimeStateExport,
    timestamp: Optional[datetime] = None,
) -> SessionLiveControlPermissionGate:
    """Evaluate permission readiness for future restart/resteer/archive control.

    This is pure advisory metadata. It does not execute recovery, spawn or
    inspect processes, move branches/worktrees/sessions, call models, or write UI.
    """
    observed_at = _as_utc(timestamp or datetime.now(timezone.utc))
    target_session_id = runtime_export.target_session_id or runtime_export.session_id
    command_kind = _live_control_command_kind(runtime_export)
    required_operation = (
        _operation_for_command_intent(command_kind) if command_kind else None
    )
    permission = session.permission_context

    blockers = list(runtime_export.human_gate_blockers)
    if target_session_id != session.session_id:
        blockers.append("target_session_mismatch")
    if command_kind is None:
        blockers.append("command_kind_missing")
    elif command_kind not in (
        CommandIntent.RESTART,
        CommandIntent.RESTEER,
        CommandIntent.ARCHIVE,
    ):
        blockers.append(f"command_kind_unsupported:{command_kind.value}")
    if required_operation is None:
        blockers.append("required_operation_missing")
    elif not permission.is_operation_approved(required_operation):
        blockers.append(f"permission.operation_not_approved:{required_operation.value}")
    if permission.is_permission_locked():
        blockers.append("permission.locked")
    if _permission_unlock_expired_at(permission, observed_at):
        blockers.append("permission.unlock_expired")
    if not permission.is_unlock_task_scoped(session.current_task_id):
        blockers.append("permission.out_of_scope")
    if permission.escalation_gate:
        blockers.append(
            "permission.escalation_gate"
            if permission.escalation_reason is None
            else f"permission.escalation_gate:{permission.escalation_reason}"
        )

    deduped_blockers = tuple(dict.fromkeys(blockers))
    ready_for_execution = (
        required_operation is not None
        and command_kind
        in (CommandIntent.RESTART, CommandIntent.RESTEER, CommandIntent.ARCHIVE)
        and not deduped_blockers
    )
    human_gate_required = not ready_for_execution
    rationale = (
        "Permission gate cleared for future live-control command staging."
        if ready_for_execution
        else "Human or Aegis gate required before future live-control command staging."
    )

    evidence_refs = list(runtime_export.evidence_refs)
    evidence_refs.extend(
        [
            f"gate.target_session_id={target_session_id}",
            "gate.command_kind=" + (command_kind.value if command_kind else "none"),
            "gate.recommended_action="
            + (
                runtime_export.recommended_recovery_action.value
                if runtime_export.recommended_recovery_action
                else "none"
            ),
            "gate.required_operation="
            + (required_operation.value if required_operation else "none"),
            f"gate.ready_for_execution={ready_for_execution}",
            f"gate.human_gate_required={human_gate_required}",
            f"permission.state={permission.branch_permission_state.value}",
            "permission.approved_operations="
            + (
                ",".join(
                    operation.value
                    for operation in sorted(
                        permission.approval_scope,
                        key=lambda operation: operation.value,
                    )
                )
                or "none"
            ),
            "permission.unlock_expiry="
            + (permission.unlock_expiry.isoformat() if permission.unlock_expiry else "none"),
            f"permission.task_scope={permission.task_scope or 'none'}",
        ]
    )
    evidence_refs.extend(f"gate.blocker={blocker}" for blocker in deduped_blockers)

    return SessionLiveControlPermissionGate(
        gate_id=f"{target_session_id}:{command_kind.value if command_kind else 'none'}:{observed_at.isoformat()}",
        target_session_id=target_session_id,
        command_kind=command_kind,
        recommended_action=runtime_export.recommended_recovery_action,
        required_operation=required_operation,
        ready_for_execution=ready_for_execution,
        human_gate_required=human_gate_required,
        human_gate_rationale=rationale,
        blockers=deduped_blockers,
        evidence_refs=tuple(evidence_refs),
        timestamp=observed_at,
    )


def summarize_recovery_readiness(
    runtime_export: SessionRuntimeStateExport,
    permission_gate: SessionLiveControlPermissionGate,
    timestamp: Optional[datetime] = None,
) -> SessionRecoveryReadinessSummary:
    """Combine runtime export and permission gate into recovery readiness advice.

    This is a serializable advisory summary only. It does not execute restart,
    resteer, archive, process/model/UI work, session movement, or branch changes.
    """
    observed_at = _as_utc(timestamp or permission_gate.timestamp)
    target_session_id = (
        permission_gate.target_session_id
        or runtime_export.target_session_id
        or runtime_export.session_id
    )
    blockers = list(runtime_export.human_gate_blockers)
    blockers.extend(permission_gate.blockers)
    if runtime_export.target_session_id and (
        runtime_export.target_session_id != permission_gate.target_session_id
    ):
        blockers.append("readiness.target_session_mismatch")
    if runtime_export.recommended_recovery_action != permission_gate.recommended_action:
        blockers.append("readiness.recommended_action_mismatch")

    deduped_blockers = tuple(dict.fromkeys(blockers))
    ready_for_execution = permission_gate.ready_for_execution and not deduped_blockers
    human_gate_required = (
        permission_gate.human_gate_required
        or runtime_export.recommended_recovery_action == SessionAction.REQUEST_HUMAN_GATE
        or bool(deduped_blockers)
    )
    readiness_status = _recovery_readiness_status(
        ready_for_execution,
        human_gate_required,
        runtime_export.recommended_recovery_action,
    )
    human_gate_rationale = (
        permission_gate.human_gate_rationale
        if human_gate_required
        else "Recovery readiness advisory is clear for future command staging."
    )

    evidence_refs = list(runtime_export.evidence_refs)
    evidence_refs.extend(permission_gate.evidence_refs)
    evidence_refs.extend(
        [
            f"readiness.state_id={runtime_export.state_id}",
            f"readiness.gate_id={permission_gate.gate_id}",
            f"readiness.target_session_id={target_session_id}",
            "readiness.command_kind="
            + (
                permission_gate.command_kind.value
                if permission_gate.command_kind
                else "none"
            ),
            "readiness.recommended_action="
            + (
                runtime_export.recommended_recovery_action.value
                if runtime_export.recommended_recovery_action
                else "none"
            ),
            "readiness.required_operation="
            + (
                permission_gate.required_operation.value
                if permission_gate.required_operation
                else "none"
            ),
            f"readiness.status={readiness_status}",
            f"readiness.ready_for_execution={ready_for_execution}",
            f"readiness.human_gate_required={human_gate_required}",
        ]
    )
    evidence_refs.extend(f"readiness.blocker={blocker}" for blocker in deduped_blockers)

    return SessionRecoveryReadinessSummary(
        summary_id=f"{target_session_id}:{readiness_status}:{observed_at.isoformat()}",
        state_id=runtime_export.state_id,
        gate_id=permission_gate.gate_id,
        target_session_id=target_session_id,
        command_kind=permission_gate.command_kind,
        recommended_action=runtime_export.recommended_recovery_action,
        required_operation=permission_gate.required_operation,
        readiness_status=readiness_status,
        ready_for_execution=ready_for_execution,
        human_gate_required=human_gate_required,
        human_gate_rationale=human_gate_rationale,
        heartbeat_status=runtime_export.heartbeat_status,
        result_kind=runtime_export.result_kind,
        permission_state=runtime_export.permission_state,
        blockers=deduped_blockers,
        evidence_refs=tuple(dict.fromkeys(evidence_refs)),
        timestamp=observed_at,
    )


def _workflow_heartbeat_age_seconds(
    heartbeat_emitted_at: Optional[datetime],
    observed_at: datetime,
) -> Optional[int]:
    if heartbeat_emitted_at is None:
        return None
    return max(0, int((observed_at - _as_utc(heartbeat_emitted_at)).total_seconds()))


def _live_control_command_kind(
    runtime_export: SessionRuntimeStateExport,
) -> Optional[CommandIntent]:
    if runtime_export.active_command_kind in (
        CommandIntent.RESTART,
        CommandIntent.RESTEER,
        CommandIntent.ARCHIVE,
    ):
        return runtime_export.active_command_kind
    action_to_command = {
        SessionAction.START_NEW: CommandIntent.RESTART,
        SessionAction.TRANSFER: CommandIntent.RESTEER,
        SessionAction.ARCHIVE: CommandIntent.ARCHIVE,
    }
    return action_to_command.get(runtime_export.recommended_recovery_action)


def _recovery_readiness_status(
    ready_for_execution: bool,
    human_gate_required: bool,
    recommended_action: Optional[SessionAction],
) -> str:
    if ready_for_execution:
        return "ready"
    if human_gate_required:
        return "blocked"
    if recommended_action is None or recommended_action == SessionAction.REUSE:
        return "watch"
    return "advisory"


def _workflow_heartbeat_status(
    heartbeat_age_seconds: Optional[int],
    heartbeat_stale_after_seconds: int,
) -> WorkflowHeartbeatStatus:
    if heartbeat_age_seconds is None:
        return WorkflowHeartbeatStatus.MISSING
    if heartbeat_age_seconds > heartbeat_stale_after_seconds:
        return WorkflowHeartbeatStatus.STALE
    if heartbeat_age_seconds >= int(heartbeat_stale_after_seconds * 0.8):
        return WorkflowHeartbeatStatus.WARNING
    return WorkflowHeartbeatStatus.FRESH


def _workflow_recovery_action(
    heartbeat_status: WorkflowHeartbeatStatus,
    result_kind: WorkflowResultKind,
    permission_blockers: tuple[str, ...],
    review_gate_blockers: tuple[str, ...],
) -> SessionAction:
    if permission_blockers or review_gate_blockers:
        return SessionAction.REQUEST_HUMAN_GATE
    if result_kind == WorkflowResultKind.SUCCEEDED:
        return SessionAction.ARCHIVE
    if result_kind == WorkflowResultKind.RESTEER_REQUESTED:
        return SessionAction.TRANSFER
    if result_kind in (
        WorkflowResultKind.GATE_REQUIRED,
        WorkflowResultKind.TOOL_DENIED,
        WorkflowResultKind.INTERNAL_ERROR,
    ):
        return SessionAction.REQUEST_HUMAN_GATE
    if result_kind == WorkflowResultKind.TIMEOUT:
        return SessionAction.START_NEW
    if heartbeat_status in (
        WorkflowHeartbeatStatus.MISSING,
        WorkflowHeartbeatStatus.STALE,
    ):
        return SessionAction.START_NEW
    return SessionAction.REUSE


def _workflow_recovery_rationale(
    heartbeat_status: WorkflowHeartbeatStatus,
    result_kind: WorkflowResultKind,
    recovery_action: SessionAction,
) -> str:
    if result_kind == WorkflowResultKind.SUCCEEDED:
        return "Workflow completed; archive or record the typed result summary."
    if result_kind == WorkflowResultKind.RESTEER_REQUESTED:
        return "Workflow requested resteer; issue a new bounded work order from structured guidance."
    if result_kind == WorkflowResultKind.TIMEOUT:
        return "Workflow timed out; restart the same work order in a fresh bounded context."
    if result_kind in (
        WorkflowResultKind.GATE_REQUIRED,
        WorkflowResultKind.TOOL_DENIED,
        WorkflowResultKind.INTERNAL_ERROR,
    ):
        return "Workflow result needs human/Aegis gate review before recovery proceeds."
    if heartbeat_status in (
        WorkflowHeartbeatStatus.MISSING,
        WorkflowHeartbeatStatus.STALE,
    ):
        return "Workflow heartbeat is stale or missing; restart the same work order in a fresh bounded context."
    if recovery_action == SessionAction.REQUEST_HUMAN_GATE:
        return "Workflow recovery is blocked by permission or review gates."
    return "Workflow heartbeat is current; continue watching the bounded work order."


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
    observed_at = timestamp or datetime.now(timezone.utc)
    immutable_sessions = tuple(sessions)
    immutable_approvals = tuple(approvals_pending)
    immutable_findings = tuple(restart_resteer_findings)
    immutable_queues = frozenset(
        (harness, tuple(queue_files))
        for harness, queue_files in queues_by_harness.items()
    )
    return PrimeAutonomyInput(
        current_sessions=immutable_sessions,
        queues_by_harness=immutable_queues,
        approvals_pending=immutable_approvals,
        restart_resteer_findings=immutable_findings,
        recent_completions=tuple(recent_completions),
        timestamp=observed_at,
        permission_summaries=summarize_session_permission_states(
            immutable_sessions,
            approvals_pending=immutable_approvals,
            restart_resteer_findings=immutable_findings,
            timestamp=observed_at,
        ),
    )


def _operation_for_command_intent(command_intent: CommandIntent) -> Optional[OperationScope]:
    """Map command intent to the permission operation it would need."""
    operation_by_intent = {
        CommandIntent.SPAWN: OperationScope.WORKTREE_CREATE,
        CommandIntent.TRANSFER: OperationScope.BRANCH_MOVE,
        CommandIntent.ARCHIVE: OperationScope.ARCHIVE,
        CommandIntent.RESTART: OperationScope.RESTART,
        CommandIntent.RESTEER: OperationScope.RESTEER,
        CommandIntent.RECOVER_FROM_LIMIT: OperationScope.RECOVER_FROM_LIMIT,
    }
    return operation_by_intent.get(command_intent)


def plan_command_from_session_action(
    session: Optional[SessionLifecycleState],
    action: SessionAction,
    reason: SessionActionReason,
    evidence: tuple[str, ...] | list[str] = (),
) -> Optional[SessionCommandPlan]:
    """Map a routing/recovery decision into a pure advisory command plan.

    This does not execute control. It only gives Prime a typed, auditable plan
    that can be reviewed, gated, or discarded by a caller.
    """
    if session is None:
        return None

    evidence_refs = tuple(evidence)
    current_state_evidence = "; ".join(evidence_refs) or (
        f"SessionLifecycleState:{session.session_id}:{session.status.value}"
    )
    review_gate_evidence = None
    proof_requirement = ProofState.COMMAND_STAGED
    command_intent = CommandIntent.WATCH
    expected_transition = (session.status, session.status)
    is_executable_now = False
    human_approval_required = False
    approval_context = None
    rollback_or_recovery_note = "Advisory only; no live session control is executed."

    if action == SessionAction.SUMMARIZE_RESET:
        command_intent = CommandIntent.STEER
        expected_transition = (session.status, session.status)
        is_executable_now = session.status == SessionStatus.RUNNING
    elif action == SessionAction.TRANSFER:
        command_intent = CommandIntent.TRANSFER
        expected_transition = (session.status, SessionStatus.WAITING)
        human_approval_required = True
        approval_context = "Transfer requires human/Aegis approval."
    elif action == SessionAction.START_NEW:
        if reason == SessionActionReason.STALE_HEARTBEAT or session.status == SessionStatus.STALE:
            command_intent = CommandIntent.RESTART
            expected_transition = (SessionStatus.STALE, SessionStatus.RUNNING)
            human_approval_required = True
            approval_context = "Stale recovery requires human/Aegis approval."
        else:
            command_intent = CommandIntent.SPAWN
            expected_transition = (SessionStatus.STARTING, SessionStatus.POLLING)
            human_approval_required = True
            approval_context = "Starting a new session requires staged approval."
    elif action == SessionAction.ARCHIVE:
        command_intent = CommandIntent.ARCHIVE
        expected_transition = (session.status, SessionStatus.ARCHIVED)
        human_approval_required = True
        approval_context = "Archive requires human/Aegis approval."
    elif action == SessionAction.REQUEST_HUMAN_GATE:
        command_intent = CommandIntent.REQUEST_HUMAN_GATE
        expected_transition = (session.status, session.status)
        human_approval_required = True
        approval_context = "Human gate required before session recovery proceeds."
        if reason == SessionActionReason.REVIEW_GATE:
            review_gate_evidence = "review gate pending"
        if reason == SessionActionReason.PERMISSION_BOUNDARY:
            proof_requirement = ProofState.PERMISSION_VALIDATED
    elif action == SessionAction.REUSE:
        command_intent = CommandIntent.WATCH
        expected_transition = (session.status, session.status)
        is_executable_now = True
        proof_requirement = ProofState.QUEUE_READ
    elif action == SessionAction.AVOID:
        command_intent = CommandIntent.REQUEST_HUMAN_GATE
        expected_transition = (session.status, session.status)
        human_approval_required = True
        approval_context = "Avoided session requires human review before reuse."

    if human_approval_required:
        is_executable_now = False

    permission_operation = _operation_for_command_intent(command_intent)
    permission_operation_allowed = (
        session.can_execute_operation(permission_operation)
        if permission_operation is not None
        else False
    )
    permission_evidence = (
        f"{session.permission_context.branch_permission_state.value}:"
        f"{session.current_task_id or 'no_task'}"
    )

    return SessionCommandPlan(
        session_id=session.session_id,
        session_name=session.session_name,
        command_intent=command_intent,
        reason=reason.value,
        expected_state_transition=expected_transition,
        current_state_evidence=current_state_evidence,
        queue_file_evidence=session.assigned_queue_file,
        worktree_evidence=session.worktree_path,
        review_gate_evidence=review_gate_evidence,
        proof_requirement=proof_requirement,
        queue_file_affected=session.assigned_queue_file,
        worktree_path_affected=session.worktree_path,
        branch_affected=session.branch_name,
        aegis_gate_result=None,
        cadence_gate_required=reason == SessionActionReason.REVIEW_GATE,
        cadence_gate_status=session.review_cadence_state,
        is_executable_now=is_executable_now,
        human_approval_required=human_approval_required,
        approval_context=approval_context,
        rollback_or_recovery_note=rollback_or_recovery_note,
        permission_state=session.permission_context.branch_permission_state,
        permission_task_scope=session.permission_context.task_scope,
        permission_unlock_expiry=session.permission_context.unlock_expiry,
        permission_approved_operations=tuple(
            sorted(
                session.permission_context.approval_scope,
                key=lambda operation: operation.value,
            )
        ),
        permission_operation=permission_operation,
        permission_operation_allowed=permission_operation_allowed,
        permission_evidence=permission_evidence,
    )
