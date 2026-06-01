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
    permission_context: dict[str, Any]

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
        return (
            self.status
            not in (
                SessionStatus.BLOCKED,
                SessionStatus.STALE,
                SessionStatus.ARCHIVED,
                SessionStatus.CAPACITY_LIMITED,
            )
            and self.is_healthy()
        )

    def heartbeat_stale(self, threshold_minutes: int = 30) -> bool:
        """True if last_queue_read_at is older than threshold."""
        elapsed = datetime.now(timezone.utc) - self.last_queue_read_at.replace(
            tzinfo=timezone.utc
        )
        return elapsed.total_seconds() > (threshold_minutes * 60)

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
            "permission_context": self.permission_context,
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
