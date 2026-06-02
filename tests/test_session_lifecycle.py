"""Tests for Session Lifecycle domain objects."""

import pytest
from datetime import datetime, timezone

from meridian_core.session_lifecycle import (
    SessionStatus,
    HarnessRole,
    CommandIntent,
    ReviewCadenceState,
    ProofState,
    HealthState,
    SessionAction,
    SessionActionReason,
    PermissionState,
    OperationScope,
    FindingType,
    PermissionContext,
    RestartResteerFinding,
    PrimeAutonomyInput,
    SessionLifecycleState,
    SessionCommandPlan,
)


class TestSessionLifecycleState:
    """Tests for SessionLifecycleState dataclass."""

    @pytest.fixture
    def healthy_state(self):
        """Create a healthy session state."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-1",
            session_name="Build 2",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.POLLING,
            worktree_path="/worktree/build-2",
            branch_name="main",
            current_task_id=None,
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=5000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.QUEUE_READ,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_immutability(self, healthy_state):
        """Verify that state is frozen (immutable)."""
        with pytest.raises((AttributeError, TypeError)):
            healthy_state.status = SessionStatus.RUNNING

    def test_is_idle(self, healthy_state):
        """Test is_idle() method."""
        assert healthy_state.is_idle()

    def test_is_healthy(self, healthy_state):
        """Test is_healthy() method."""
        assert healthy_state.is_healthy()

    def test_can_accept_work(self, healthy_state):
        """Test can_accept_work() method."""
        assert healthy_state.can_accept_work()

    def test_heartbeat_stale_fresh(self, healthy_state):
        """Test heartbeat_stale() with recent read."""
        assert not healthy_state.heartbeat_stale(threshold_minutes=30)

    def test_to_dict(self, healthy_state):
        """Test serialization to dict."""
        serialized = healthy_state.to_dict()
        assert serialized["session_id"] == "session-1"
        assert serialized["status"] == "polling"

    def test_suggest_routing_action_reuse_healthy(self, healthy_state):
        """Test routing suggests REUSE for healthy sessions."""
        action, reason = healthy_state.suggest_routing_action()
        assert action == SessionAction.REUSE
        assert reason == SessionActionReason.CONTEXT_HEALTHY

    def test_suggest_routing_action_avoid_broken_tool(self, healthy_state):
        """Test routing suggests AVOID when tool/auth broken."""
        action, reason = healthy_state.suggest_routing_action(tool_or_auth_broken=True)
        assert action == SessionAction.AVOID
        assert reason == SessionActionReason.TOOL_MISMATCH

    def test_suggest_routing_action_summarize_payload_limit(self, healthy_state):
        """Test routing suggests SUMMARIZE when payload near limit."""
        action, reason = healthy_state.suggest_routing_action(payload_near_limit=True)
        assert action == SessionAction.SUMMARIZE_RESET
        assert reason == SessionActionReason.PAYLOAD_BUDGET

    def test_suggest_routing_action_new_stale_heartbeat(self, healthy_state):
        """Test routing suggests START_NEW for stale sessions."""
        action, reason = healthy_state.suggest_routing_action(
            context_health_degraded=True
        )
        assert action == SessionAction.START_NEW
        assert reason == SessionActionReason.STALE_HEARTBEAT

    def test_suggest_routing_action_new_reasoning_shift(self, healthy_state):
        """Test routing suggests START_NEW when reasoning mode shifts."""
        action, reason = healthy_state.suggest_routing_action(reasoning_mode_shifted=True)
        assert action == SessionAction.START_NEW
        assert reason == SessionActionReason.REASONING_SHIFT

    def test_suggest_routing_action_new_project_changed(self, healthy_state):
        """Test routing suggests START_NEW when project changes."""
        action, reason = healthy_state.suggest_routing_action(project_changed=True)
        assert action == SessionAction.START_NEW
        assert reason == SessionActionReason.PROJECT_SCOPE

    def test_suggest_routing_action_transfer_dual_lane(self, healthy_state):
        """Test routing suggests TRANSFER for dual-lane Tier 3."""
        action, reason = healthy_state.suggest_routing_action(
            tier_3_needs_independence=True
        )
        assert action == SessionAction.TRANSFER
        assert reason == SessionActionReason.DUAL_LANE_NEEDED

    def test_suggest_routing_action_archive_context_fill(self, healthy_state):
        """Test routing suggests ARCHIVE when context should be filled."""
        action, reason = healthy_state.suggest_routing_action(should_archive=True)
        assert action == SessionAction.ARCHIVE
        assert reason == SessionActionReason.CONTEXT_FILL

    def test_suggest_routing_action_human_gate_review_pending(self, healthy_state):
        """Test routing suggests REQUEST_HUMAN_GATE when review is gated."""
        action, reason = healthy_state.suggest_routing_action(review_gate_pending=True)
        assert action == SessionAction.REQUEST_HUMAN_GATE
        assert reason == SessionActionReason.REVIEW_GATE

    def test_suggest_routing_action_human_gate_permission_boundary(self, healthy_state):
        """Test routing suggests REQUEST_HUMAN_GATE at permission boundary."""
        action, reason = healthy_state.suggest_routing_action(
            permission_boundary_crossed=True
        )
        assert action == SessionAction.REQUEST_HUMAN_GATE
        assert reason == SessionActionReason.PERMISSION_BOUNDARY

    def test_suggest_routing_action_start_new_context_fill(self, healthy_state):
        """Test routing suggests START_NEW when context needs filling."""
        action, reason = healthy_state.suggest_routing_action(context_needs_fill=True)
        assert action == SessionAction.START_NEW
        assert reason == SessionActionReason.CONTEXT_FILL

    def test_routing_fields_in_serialization(self, healthy_state):
        """Test routing fields are included in to_dict()."""
        state_with_routing = SessionLifecycleState(
            **{
                **healthy_state.__dict__,
                "routing_action": SessionAction.REUSE,
                "routing_reason": SessionActionReason.CONTEXT_HEALTHY,
            }
        )
        serialized = state_with_routing.to_dict()
        assert serialized["routing_action"] == "reuse"
        assert serialized["routing_reason"] == "context_healthy"


class TestSessionCommandPlan:
    """Tests for SessionCommandPlan dataclass."""

    @pytest.fixture
    def poll_command(self):
        """Create a POLL_QUEUE command."""
        return SessionCommandPlan(
            session_id="session-1",
            session_name="Build 2",
            command_intent=CommandIntent.POLL_QUEUE,
            reason="Check for new tasks in queue",
            expected_state_transition=(SessionStatus.POLLING, SessionStatus.POLLING),
            current_state_evidence="SessionLifecycleState at 2026-06-05 03:40",
            queue_file_evidence="docs/live-build-2.md (read 03:40)",
            worktree_evidence="/worktree/build-2 verified",
            review_gate_evidence=None,
            proof_requirement=ProofState.QUEUE_READ,
            queue_file_affected="docs/live-build-2.md",
            worktree_path_affected="/worktree/build-2",
            branch_affected="main",
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=True,
            human_approval_required=False,
            approval_context=None,
            rollback_or_recovery_note=None,
        )

    def test_immutability(self, poll_command):
        """Verify that command is frozen."""
        with pytest.raises((AttributeError, TypeError)):
            poll_command.is_executable_now = False

    def test_is_executable(self, poll_command):
        """Test is_executable() method."""
        assert poll_command.is_executable()

    def test_is_executable_human_gate(self, poll_command):
        """Test is_executable() respects human_approval_required."""
        human_gated = poll_command.__class__(
            **{**poll_command.__dict__, "human_approval_required": True}
        )
        assert not human_gated.is_executable()

    def test_requires_aegis_approval(self, poll_command):
        """Test requires_aegis_approval() method."""
        assert not poll_command.requires_aegis_approval()

        archive_cmd = poll_command.__class__(
            **{**poll_command.__dict__, "command_intent": CommandIntent.ARCHIVE}
        )
        assert archive_cmd.requires_aegis_approval()

    def test_verify_state_transition_legal(self, poll_command):
        """Test verify_state_transition_legal() method."""
        assert poll_command.verify_state_transition_legal()

    def test_to_dict(self, poll_command):
        """Test serialization to dict."""
        serialized = poll_command.to_dict()
        assert serialized["session_id"] == "session-1"
        assert serialized["command_intent"] == "poll_queue"

    def test_archive_command_for_context_fill(self, poll_command):
        """Test ARCHIVE command when routing suggests context fill."""
        archive_cmd = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.ARCHIVE,
                "reason": "Archive session due to context fill requirement",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.ARCHIVED),
                "is_executable_now": False,
                "human_approval_required": True,
            }
        )
        assert archive_cmd.command_intent == CommandIntent.ARCHIVE
        assert archive_cmd.requires_aegis_approval()
        assert not archive_cmd.is_executable()

    def test_human_gate_command_for_review_gate(self, poll_command):
        """Test REQUEST_HUMAN_GATE command when review gate is pending."""
        human_gate_cmd = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "reason": "Request human approval due to review gate",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.REVIEW_GATED),
                "is_executable_now": False,
                "human_approval_required": True,
            }
        )
        assert human_gate_cmd.command_intent == CommandIntent.REQUEST_HUMAN_GATE
        assert not human_gate_cmd.is_executable()
        assert human_gate_cmd.human_approval_required

    def test_summarize_reset_command_for_payload_limit(self, poll_command):
        """Test STEER command for context summarization near payload limit."""
        summarize_cmd = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.STEER,
                "reason": "Reset context due to prompt payload near limit",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.RUNNING),
                "is_executable_now": True,
                "human_approval_required": False,
            }
        )
        assert summarize_cmd.command_intent == CommandIntent.STEER
        assert summarize_cmd.is_executable()

    def test_transfer_command_for_dual_lane(self, poll_command):
        """Test TRANSFER command for Tier 3 dual-lane independence."""
        transfer_cmd = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.TRANSFER,
                "reason": "Transfer session for dual-lane Tier 3 independence",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.WAITING),
                "is_executable_now": False,
                "human_approval_required": True,
            }
        )
        assert transfer_cmd.command_intent == CommandIntent.TRANSFER
        assert transfer_cmd.requires_aegis_approval()
        assert not transfer_cmd.is_executable()

    def test_archive_command_legal_from_stopped(self, poll_command):
        """Test ARCHIVE command legal state transition from STOPPED."""
        archive_from_stopped = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.ARCHIVE,
                "expected_state_transition": (SessionStatus.STOPPED, SessionStatus.ARCHIVED),
            }
        )
        assert archive_from_stopped.verify_state_transition_legal()

    def test_human_gate_command_works_from_any_status(self, poll_command):
        """Test REQUEST_HUMAN_GATE works from any session status."""
        for status in [SessionStatus.POLLING, SessionStatus.RUNNING, SessionStatus.WAITING]:
            human_gate = poll_command.__class__(
                **{
                    **poll_command.__dict__,
                    "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                    "expected_state_transition": (status, status),
                }
            )
            assert human_gate.command_intent == CommandIntent.REQUEST_HUMAN_GATE

    def test_routing_action_archive_requires_aegis(self, poll_command):
        """Test archive routing action requires Aegis approval."""
        archive_decision = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.ARCHIVE,
                "aegis_gate_result": None,
            }
        )
        assert archive_decision.requires_aegis_approval()
        assert archive_decision.aegis_gate_result is None

    def test_routing_action_transfer_requires_aegis(self, poll_command):
        """Test transfer routing action requires Aegis approval."""
        transfer_decision = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.TRANSFER,
                "aegis_gate_result": None,
            }
        )
        assert transfer_decision.requires_aegis_approval()

    def test_human_gate_decision_blocks_execution(self, poll_command):
        """Test that human gate decision blocks immediate execution."""
        human_gated = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "is_executable_now": True,
                "human_approval_required": True,
            }
        )
        assert not human_gated.is_executable()

    def test_context_fill_routing_triggers_archive(self, poll_command):
        """Test context fill routing reason leads to ARCHIVE command."""
        archive_for_fill = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.ARCHIVE,
                "reason": "Session context should be archived for fill by new session",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.ARCHIVED),
            }
        )
        assert archive_for_fill.command_intent == CommandIntent.ARCHIVE


class TestPermissionContext:
    """Tests for PermissionContext dataclass."""

    @pytest.fixture
    def locked_context(self):
        """Create a locked permission context."""
        now = datetime.now(timezone.utc)
        return PermissionContext(
            approved_by="scott",
            approval_scope=frozenset(),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            last_permission_change=now,
        )

    @pytest.fixture
    def unlocked_context(self):
        """Create an unlocked permission context."""
        now = datetime.now(timezone.utc)
        return PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE, OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            last_permission_change=now,
        )

    def test_permission_context_immutability(self, locked_context):
        """Verify permission context is frozen."""
        with pytest.raises((AttributeError, TypeError)):
            locked_context.approval_scope = frozenset([OperationScope.BRANCH_MOVE])

    def test_is_operation_approved_true(self, unlocked_context):
        """Test is_operation_approved when operation is in scope."""
        assert unlocked_context.is_operation_approved(OperationScope.BRANCH_MOVE)

    def test_is_operation_approved_false(self, unlocked_context):
        """Test is_operation_approved when operation is not in scope."""
        assert not unlocked_context.is_operation_approved(OperationScope.ARCHIVE)

    def test_is_permission_locked_true(self, locked_context):
        """Test is_permission_locked for locked state."""
        assert locked_context.is_permission_locked()

    def test_is_permission_locked_false(self, unlocked_context):
        """Test is_permission_locked for unlocked state."""
        assert not unlocked_context.is_permission_locked()

    def test_requires_approval_locked_approved(self, unlocked_context):
        """Test requires_approval when unlocked and approved."""
        assert not unlocked_context.requires_approval_for_operation(OperationScope.BRANCH_MOVE)

    def test_requires_approval_locked_not_approved(self, locked_context):
        """Test requires_approval when locked and not approved."""
        assert locked_context.requires_approval_for_operation(OperationScope.BRANCH_MOVE)

    def test_permission_context_to_dict(self, unlocked_context):
        """Test serialization to dict."""
        serialized = unlocked_context.to_dict()
        assert serialized["approved_by"] == "prime"
        assert "branch_move" in serialized["approval_scope"]
        assert serialized["branch_permission_state"] == "unlocked_temporary"


class TestRestartResteerFinding:
    """Tests for RestartResteerFinding dataclass."""

    @pytest.fixture
    def restart_finding(self):
        """Create a restart finding."""
        now = datetime.now(timezone.utc)
        return RestartResteerFinding(
            session_id="session-1",
            finding_type=FindingType.RESTART,
            reason="Session idle for 45 minutes",
            evidence_stale_seconds=2700,
            evidence_last_queue_read_at=now,
            evidence_blocker_summary=None,
            recommended_action="Restart with existing worktree",
            timestamp=now,
        )

    def test_restart_finding_immutability(self, restart_finding):
        """Verify restart finding is frozen."""
        with pytest.raises((AttributeError, TypeError)):
            restart_finding.finding_type = FindingType.RESTEER

    def test_restart_finding_to_dict(self, restart_finding):
        """Test serialization to dict."""
        serialized = restart_finding.to_dict()
        assert serialized["session_id"] == "session-1"
        assert serialized["finding_type"] == "restart"
        assert serialized["evidence_stale_seconds"] == 2700


class TestPrimeAutonomyInput:
    """Tests for PrimeAutonomyInput dataclass."""

    @pytest.fixture
    def prime_input(self):
        """Create Prime autonomy input."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            last_permission_change=now,
        )
        session = SessionLifecycleState(
            session_id="session-1",
            session_name="Build 2",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.POLLING,
            worktree_path="/worktree/build-2",
            branch_name="main",
            current_task_id=None,
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=5000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.QUEUE_READ,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )
        return PrimeAutonomyInput(
            current_sessions=[session],
            queues_by_harness={"build": ["docs/live-build-2.md"]},
            approvals_pending=[("session-1", "branch merge requires approval")],
            restart_resteer_findings=[],
            recent_completions=["commit-abc123"],
            timestamp=now,
        )

    def test_prime_input_immutability(self, prime_input):
        """Verify prime input is frozen."""
        with pytest.raises((AttributeError, TypeError)):
            prime_input.current_sessions = []

    def test_prime_input_to_dict(self, prime_input):
        """Test serialization to dict."""
        serialized = prime_input.to_dict()
        assert len(serialized["current_sessions"]) == 1
        assert serialized["queues_by_harness"]["build"] == ["docs/live-build-2.md"]
        assert len(serialized["approvals_pending"]) == 1


class TestSessionLifecycleStatePermissions:
    """Tests for SessionLifecycleState permission helper methods."""

    @pytest.fixture
    def locked_state(self):
        """Create a session with locked permissions."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset(),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-2",
            session_name="Build 3",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-3.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.POLLING,
            worktree_path="/worktree/build-3",
            branch_name="main",
            current_task_id=None,
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=5000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.QUEUE_READ,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    @pytest.fixture
    def unlocked_state(self):
        """Create a session with unlocked permissions."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-1",
            session_name="Build 2",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.POLLING,
            worktree_path="/worktree/build-2",
            branch_name="main",
            current_task_id=None,
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=5000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.QUEUE_READ,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_is_permission_locked_true(self, locked_state):
        """Test is_permission_locked returns true for locked state."""
        assert locked_state.is_permission_locked()

    def test_is_permission_locked_false(self, unlocked_state):
        """Test is_permission_locked returns false for unlocked state."""
        assert not unlocked_state.is_permission_locked()

    def test_requires_approval_branch_move_unlocked(self, unlocked_state):
        """Test requires_approval_for_operation when approved."""
        assert not unlocked_state.requires_approval_for_operation(OperationScope.BRANCH_MOVE)

    def test_requires_approval_branch_move_locked(self, locked_state):
        """Test requires_approval_for_operation when locked."""
        assert locked_state.requires_approval_for_operation(OperationScope.BRANCH_MOVE)

    def test_can_execute_operation_approved_no_escalation(self, unlocked_state):
        """Test can_execute_operation when approved and no escalation."""
        assert unlocked_state.can_execute_operation(OperationScope.BRANCH_MOVE)

    def test_can_execute_operation_not_approved(self, locked_state):
        """Test can_execute_operation when not approved."""
        assert not locked_state.can_execute_operation(OperationScope.BRANCH_MOVE)
