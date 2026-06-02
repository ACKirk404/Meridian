"""Tests for Session Lifecycle domain objects."""

import pytest
from datetime import datetime, timedelta, timezone

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
    gather_prime_autonomy_input,
    generate_restart_finding,
    generate_resteer_finding,
    plan_command_from_session_action,
)


class TestSessionLifecycleState:
    """Tests for SessionLifecycleState dataclass."""

    @pytest.fixture
    def healthy_state(self):
        """Create a healthy session state."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
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
            current_task_id="task-1",
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

    def test_can_accept_work_rejects_out_of_scope_task(self):
        """Test that can_accept_work rejects when current_task_id doesn't match task_scope."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
            last_permission_change=now,
        )
        state = SessionLifecycleState(
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
            current_task_id="task-2",  # Doesn't match task_scope
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
        # Should not be able to accept work when task_id doesn't match task_scope
        assert not state.can_accept_work()

    def test_can_accept_work_accepts_matching_scope_task(self):
        """Test that can_accept_work accepts when current_task_id matches task_scope."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
            last_permission_change=now,
        )
        state = SessionLifecycleState(
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
            current_task_id="task-1",  # Matches task_scope
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
        # Should be able to accept work when task_id matches task_scope
        assert state.can_accept_work()

    def test_heartbeat_stale_fresh(self, healthy_state):
        """Test heartbeat_stale() with recent read."""
        assert not healthy_state.heartbeat_stale(threshold_seconds=1800)

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

    def test_audit_evidence_serializes_plan_action_and_reason(self, poll_command):
        """Test audit evidence exposes display-safe action and reason metadata."""
        audit = poll_command.audit_evidence()

        assert audit["plan"]["action"] == "poll_queue"
        assert audit["plan"]["reason"] == "Check for new tasks in queue"
        assert audit["plan"]["expected_transition"] == ["polling", "polling"]
        assert audit["plan"]["is_executable"] is True

    def test_to_dict_includes_audit_evidence(self, poll_command):
        """Test serialized command plans include audit evidence for Bifrost."""
        serialized = poll_command.to_dict()

        assert serialized["audit_evidence"]["plan"]["action"] == "poll_queue"
        assert serialized["audit_evidence"]["permission"]["proof_requirement"] == "queue_read"
        assert serialized["audit_evidence"]["recovery"]["queue_file_affected"] == (
            "docs/live-build-2.md"
        )

    def test_audit_evidence_records_human_gate_blocker(self, poll_command):
        """Test human-gated plans surface blockers without raw execution data."""
        gated_command = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "review gate pending",
            }
        )

        audit = gated_command.audit_evidence()
        assert audit["review_gate"]["human_approval_required"] is True
        assert "human_approval_required" in audit["blockers"]
        assert "not_executable_now" in audit["blockers"]
        assert "review gate pending" in audit["blockers"]

    def test_audit_evidence_records_permission_metadata(self, poll_command):
        """Test permission-related audit metadata is deterministic and display-safe."""
        permission_command = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "proof_requirement": ProofState.PERMISSION_VALIDATED,
                "branch_affected": "codex/aligned-build-2-command-audit",
                "worktree_path_affected": "/worktree/build-2",
                "aegis_gate_result": "pending",
            }
        )

        audit = permission_command.audit_evidence()
        assert audit["permission"]["proof_requirement"] == "permission_validated"
        assert audit["permission"]["aegis_gate_result"] == "pending"
        assert audit["permission"]["branch_affected"] == (
            "codex/aligned-build-2-command-audit"
        )
        assert audit["permission"]["worktree_path_affected"] == "/worktree/build-2"
        assert audit["permission"]["operation"] is None
        assert audit["permission"]["operation_allowed"] is False

    def test_audit_evidence_records_review_gate_and_recovery(self, poll_command):
        """Test review-gate and recovery metadata survive serialization."""
        recovery_command = poll_command.__class__(
            **{
                **poll_command.__dict__,
                "command_intent": CommandIntent.RESTART,
                "reason": "stale_heartbeat",
                "expected_state_transition": (SessionStatus.STALE, SessionStatus.RUNNING),
                "review_gate_evidence": "review gate pending",
                "cadence_gate_required": True,
                "cadence_gate_status": ReviewCadenceState.REVIEW_GATED,
                "rollback_or_recovery_note": "Restart remains advisory until approved.",
                "is_executable_now": False,
                "human_approval_required": True,
            }
        )

        audit = recovery_command.audit_evidence()
        assert audit["plan"]["action"] == "restart"
        assert audit["review_gate"]["cadence_gate_required"] is True
        assert audit["review_gate"]["cadence_gate_status"] == "review_gated"
        assert audit["recovery"]["rollback_or_recovery_note"] == (
            "Restart remains advisory until approved."
        )

    def test_audit_evidence_is_deterministic(self, poll_command):
        """Test repeated audit evidence calls return identical metadata."""
        assert poll_command.audit_evidence() == poll_command.audit_evidence()

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


class TestSessionCommandPlanEdgeCoverage:
    """Tests for routing-to-command-plan edge decisions."""

    @pytest.fixture
    def running_state(self):
        """Create a running state with valid task-scoped permissions."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset(
                [
                    OperationScope.RESTART,
                    OperationScope.RESTEER,
                    OperationScope.ARCHIVE,
                ]
            ),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="task-1",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-edge",
            session_name="Build 2 Edge",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2",
            branch_name="codex/aligned-build-2-command-plan",
            current_task_id="task-1",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=24000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_summarize_reset_edge_is_executable_steer_plan(self, running_state):
        """Summarize/reset maps to a staged, non-human-gated STEER plan."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.SUMMARIZE_RESET,
            SessionActionReason.PAYLOAD_BUDGET,
            evidence=["payload near limit"],
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.STEER
        assert plan.expected_state_transition == (
            SessionStatus.RUNNING,
            SessionStatus.RUNNING,
        )
        assert plan.is_executable()
        assert not plan.human_approval_required

    def test_transfer_edge_is_human_gated(self, running_state):
        """Transfer stays advisory and requires human/Aegis approval."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.TRANSFER,
            SessionActionReason.DUAL_LANE_NEEDED,
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.TRANSFER
        assert plan.requires_aegis_approval()
        assert plan.human_approval_required
        assert not plan.is_executable()

    def test_start_new_session_edge_is_spawn_advisory(self, running_state):
        """Start-new routing becomes a staged SPAWN advisory, not live launch."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.START_NEW,
            SessionActionReason.REASONING_SHIFT,
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.SPAWN
        assert plan.expected_state_transition == (
            SessionStatus.STARTING,
            SessionStatus.POLLING,
        )
        assert plan.human_approval_required
        assert not plan.is_executable()

    def test_archive_no_session_edge_has_no_plan(self):
        """Archive/no-session does not fabricate a command target."""
        assert (
            plan_command_from_session_action(
                None,
                SessionAction.ARCHIVE,
                SessionActionReason.CONTEXT_FILL,
            )
            is None
        )

    def test_stale_recovery_edge_is_gated_restart(self, running_state):
        """Stale heartbeat recovery maps to gated RESTART command plan."""
        stale_state = SessionLifecycleState(
            **{
                **running_state.__dict__,
                "status": SessionStatus.STALE,
                "health_state": HealthState.STALE,
                "last_prompt_sent_at": datetime.now(timezone.utc) - timedelta(hours=1),
            }
        )
        plan = plan_command_from_session_action(
            stale_state,
            SessionAction.START_NEW,
            SessionActionReason.STALE_HEARTBEAT,
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.RESTART
        assert plan.expected_state_transition == (
            SessionStatus.STALE,
            SessionStatus.RUNNING,
        )
        assert plan.requires_aegis_approval()
        assert not plan.is_executable()

    def test_review_gate_edge_requires_human_gate(self, running_state):
        """Review-gated recovery produces a non-executable human-gate plan."""
        gated_state = SessionLifecycleState(
            **{
                **running_state.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
            }
        )
        plan = plan_command_from_session_action(
            gated_state,
            SessionAction.REQUEST_HUMAN_GATE,
            SessionActionReason.REVIEW_GATE,
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.REQUEST_HUMAN_GATE
        assert plan.cadence_gate_required
        assert plan.review_gate_evidence == "review gate pending"
        assert plan.human_approval_required
        assert not plan.is_executable()

    def test_permission_boundary_edge_blocks_execution(self, running_state):
        """Permission-boundary plans carry permission proof and block execution."""
        locked_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset(),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
            last_permission_change=datetime.now(timezone.utc),
        )
        blocked_state = SessionLifecycleState(
            **{
                **running_state.__dict__,
                "status": SessionStatus.BLOCKED,
                "blocker_summary": "permission boundary",
                "permission_context": locked_context,
            }
        )
        plan = plan_command_from_session_action(
            blocked_state,
            SessionAction.REQUEST_HUMAN_GATE,
            SessionActionReason.PERMISSION_BOUNDARY,
        )

        assert plan is not None
        assert plan.command_intent == CommandIntent.REQUEST_HUMAN_GATE
        assert plan.proof_requirement == ProofState.PERMISSION_VALIDATED
        assert plan.human_approval_required
        assert not blocked_state.can_execute_operation(OperationScope.RESTART)
        assert not plan.is_executable()

    def test_command_plan_audit_records_permission_operation_evidence(self, running_state):
        """Recovery permission state is serialized for advisory consumers."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.START_NEW,
            SessionActionReason.STALE_HEARTBEAT,
        )

        assert plan is not None
        audit = plan.audit_evidence()

        assert audit["permission"]["permission_state"] == "unlocked_temporary"
        assert audit["permission"]["task_scope"] == running_state.current_task_id
        assert audit["permission"]["operation"] == "restart"
        assert audit["permission"]["operation_allowed"] is True
        assert "restart" in audit["permission"]["approved_operations"]

    def test_command_plan_audit_blocks_branch_movement_without_permission(self, running_state):
        """Branch movement stays blocked unless permission explicitly allows it."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.TRANSFER,
            SessionActionReason.DUAL_LANE_NEEDED,
        )

        assert plan is not None
        audit = plan.audit_evidence()

        assert audit["permission"]["operation"] == "branch_move"
        assert audit["permission"]["operation_allowed"] is False
        assert "permission_required_for_branch_move" in audit["blockers"]

    def test_command_plan_audit_blocks_worktree_movement_without_permission(self, running_state):
        """Worktree movement stays blocked unless permission explicitly allows it."""
        plan = plan_command_from_session_action(
            running_state,
            SessionAction.START_NEW,
            SessionActionReason.REASONING_SHIFT,
        )

        assert plan is not None
        audit = plan.audit_evidence()

        assert audit["permission"]["operation"] == "worktree_create"
        assert audit["permission"]["operation_allowed"] is False
        assert "permission_required_for_worktree_create" in audit["blockers"]


class TestRestartResteerRecoveryDecisions:
    """Tests for pure restart/resteer recovery routing and gates."""

    @pytest.fixture
    def recovery_state(self):
        """Create a healthy, task-scoped session for recovery decisions."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset(
                [
                    OperationScope.RESTART,
                    OperationScope.RESTEER,
                    OperationScope.RECOVER_FROM_LIMIT,
                ]
            ),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="restart-resteer-slice",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-recovery",
            session_name="Build 2 Recovery",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2",
            branch_name="codex/aligned-build-2-session-lifecycle",
            current_task_id="restart-resteer-slice",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=16000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    @pytest.fixture
    def base_plan(self, recovery_state):
        """Create a typed, non-live command plan for recovery assertions."""
        return SessionCommandPlan(
            session_id=recovery_state.session_id,
            session_name=recovery_state.session_name,
            command_intent=CommandIntent.WATCH,
            reason="Observe recovery signal",
            expected_state_transition=(SessionStatus.RUNNING, SessionStatus.RUNNING),
            current_state_evidence="typed SessionLifecycleState snapshot",
            queue_file_evidence=recovery_state.assigned_queue_file,
            worktree_evidence=recovery_state.worktree_path,
            review_gate_evidence=None,
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected=recovery_state.assigned_queue_file,
            worktree_path_affected=recovery_state.worktree_path,
            branch_affected=recovery_state.branch_name,
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=True,
            human_approval_required=False,
            approval_context=None,
            rollback_or_recovery_note="No live restart or branch movement is executed.",
        )

    def test_stale_heartbeat_recovery_is_restart_advisory(self, recovery_state, base_plan):
        """Stale heartbeat yields a restart finding and gated restart plan."""
        stale_prompt_at = datetime.now(timezone.utc) - timedelta(minutes=46)
        stale_state = SessionLifecycleState(
            **{
                **recovery_state.__dict__,
                "status": SessionStatus.STALE,
                "health_state": HealthState.STALE,
                "last_prompt_sent_at": stale_prompt_at,
            }
        )
        assert stale_state.heartbeat_stale(threshold_seconds=1800)

        finding = RestartResteerFinding(
            session_id=stale_state.session_id,
            finding_type=FindingType.RESTART,
            reason="Heartbeat exceeded stale threshold",
            evidence_stale_seconds=2760,
            evidence_last_queue_read_at=stale_state.last_queue_read_at,
            evidence_blocker_summary=stale_state.blocker_summary,
            recommended_action="Stage restart recovery for human/Aegis review",
            timestamp=datetime.now(timezone.utc),
        )
        restart_plan = base_plan.__class__(
            **{
                **base_plan.__dict__,
                "command_intent": CommandIntent.RESTART,
                "reason": finding.reason,
                "expected_state_transition": (SessionStatus.STALE, SessionStatus.RUNNING),
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "stale heartbeat recovery requires review",
            }
        )

        assert finding.finding_type == FindingType.RESTART
        assert finding.evidence_last_queue_read_at == stale_state.last_queue_read_at
        assert restart_plan.requires_aegis_approval()
        assert not restart_plan.is_executable()

    def test_context_fill_recovery_stages_summarize_reset(self, recovery_state, base_plan):
        """Context pressure routes to summarize/reset without human approval."""
        action, reason = recovery_state.suggest_routing_action(payload_near_limit=True)
        summarize_plan = base_plan.__class__(
            **{
                **base_plan.__dict__,
                "command_intent": CommandIntent.STEER,
                "reason": "Summarize and reset context before continuing",
                "proof_requirement": ProofState.COMMAND_STAGED,
            }
        )

        assert action == SessionAction.SUMMARIZE_RESET
        assert reason == SessionActionReason.PAYLOAD_BUDGET
        assert summarize_plan.is_executable()
        assert not summarize_plan.requires_aegis_approval()

    def test_reasoning_shift_recovery_can_start_new_or_transfer(self, recovery_state, base_plan):
        """Reasoning changes can start a clean session or transfer to an independent lane."""
        start_action, start_reason = recovery_state.suggest_routing_action(
            reasoning_mode_shifted=True
        )
        transfer_action, transfer_reason = recovery_state.suggest_routing_action(
            tier_3_needs_independence=True
        )
        transfer_plan = base_plan.__class__(
            **{
                **base_plan.__dict__,
                "command_intent": CommandIntent.TRANSFER,
                "reason": "Transfer for independent reasoning lane",
                "expected_state_transition": (SessionStatus.RUNNING, SessionStatus.WAITING),
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "transfer requires independent approval",
            }
        )

        assert start_action == SessionAction.START_NEW
        assert start_reason == SessionActionReason.REASONING_SHIFT
        assert transfer_action == SessionAction.TRANSFER
        assert transfer_reason == SessionActionReason.DUAL_LANE_NEEDED
        assert transfer_plan.requires_aegis_approval()
        assert not transfer_plan.is_executable()

    def test_review_gate_recovery_requires_human_approval(self, recovery_state, base_plan):
        """Review-gated recovery is represented as a blocked human-gate plan."""
        gated_state = SessionLifecycleState(
            **{
                **recovery_state.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
            }
        )
        action, reason = gated_state.suggest_routing_action(review_gate_pending=True)
        gate_plan = base_plan.__class__(
            **{
                **base_plan.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "reason": "Review gate must clear before recovery proceeds",
                "expected_state_transition": (
                    SessionStatus.REVIEW_GATED,
                    SessionStatus.REVIEW_GATED,
                ),
                "review_gate_evidence": "Codex review gate pending",
                "cadence_gate_required": True,
                "cadence_gate_status": ReviewCadenceState.REVIEW_GATED,
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "human review approval required",
            }
        )

        assert action == SessionAction.REQUEST_HUMAN_GATE
        assert reason == SessionActionReason.REVIEW_GATE
        assert not gate_plan.is_executable()
        assert gate_plan.human_approval_required

    def test_permission_boundary_recovery_blocks_without_valid_unlock(self, recovery_state, base_plan):
        """Permission-boundary recovery preserves expiry and task-scope blocking."""
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.RESTEER]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=datetime.now(timezone.utc) - timedelta(minutes=1),
            task_scope="different-task",
            last_permission_change=datetime.now(timezone.utc),
        )
        blocked_state = SessionLifecycleState(
            **{
                **recovery_state.__dict__,
                "status": SessionStatus.BLOCKED,
                "blocker_summary": "permission boundary requires a fresh task-scoped unlock",
                "permission_context": expired_context,
            }
        )
        action, reason = blocked_state.suggest_routing_action(
            permission_boundary_crossed=True
        )
        gate_plan = base_plan.__class__(
            **{
                **base_plan.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "reason": "Permission boundary blocks restart/resteer recovery",
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": blocked_state.blocker_summary,
            }
        )

        assert action == SessionAction.REQUEST_HUMAN_GATE
        assert reason == SessionActionReason.PERMISSION_BOUNDARY
        assert not blocked_state.can_accept_work()
        assert not blocked_state.can_execute_operation(OperationScope.RESTART)
        assert not blocked_state.can_execute_operation(OperationScope.RESTEER)
        assert not gate_plan.is_executable()


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
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
            last_permission_change=now,
        )

    @pytest.fixture
    def unlocked_context(self):
        """Create an unlocked permission context (temporary with expiry and task scope)."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        return PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE, OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
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

    def test_temporary_unlock_requires_expiry(self):
        """Test that UNLOCKED_TEMPORARY requires unlock_expiry."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="UNLOCKED_TEMPORARY requires unlock_expiry"):
            PermissionContext(
                approved_by="scott",
                approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
                escalation_gate=False,
                escalation_reason=None,
                branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
                approved_by_secondary=None,
                unlock_expiry=None,  # Invalid: must be set for temporary unlock
                task_scope="task-1",
                last_permission_change=now,
            )

    def test_temporary_unlock_requires_task_scope(self):
        """Test that UNLOCKED_TEMPORARY requires task_scope."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="UNLOCKED_TEMPORARY requires task_scope"):
            PermissionContext(
                approved_by="scott",
                approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
                escalation_gate=False,
                escalation_reason=None,
                branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
                approved_by_secondary=None,
                unlock_expiry=future,
                task_scope=None,  # Invalid: must be set for temporary unlock
                last_permission_change=now,
            )

    def test_permanent_unlock_requires_secondary_approval(self):
        """Test that UNLOCKED_PERMANENT requires dual approval."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="UNLOCKED_PERMANENT requires approved_by_secondary"):
            PermissionContext(
                approved_by="scott",
                approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
                escalation_gate=False,
                escalation_reason=None,
                branch_permission_state=PermissionState.UNLOCKED_PERMANENT,
                approved_by_secondary=None,  # Invalid: must be set for permanent unlock
                unlock_expiry=None,
                task_scope=None,
                last_permission_change=now,
            )

    def test_can_execute_operation_respects_task_scope_match(self):
        """Test that can_execute_operation rejects when task_scope doesn't match."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
            last_permission_change=now,
        )
        # Operation can execute when task_scope matches
        assert context.can_execute_operation(OperationScope.BRANCH_MOVE, "task-1")
        # Operation cannot execute when task_scope doesn't match
        assert not context.can_execute_operation(OperationScope.BRANCH_MOVE, "task-2")

    def test_can_execute_operation_respects_expiry(self):
        """Test that can_execute_operation rejects when unlock has expired."""
        now = datetime.now(timezone.utc)
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=past,  # Expired
            task_scope="task-1",
            last_permission_change=now,
        )
        # Operation cannot execute when unlock has expired
        assert not context.can_execute_operation(OperationScope.BRANCH_MOVE, "task-1")


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


class TestBeaconPrimeAdvisoryBinding:
    """Tests for pure Beacon findings and Prime advisory input gathering."""

    @pytest.fixture
    def blocked_state(self):
        """Create a blocked session with valid task-scoped recovery permission."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.RESTEER]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-advisory",
            session_name="Build 2 Advisory",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.BLOCKED,
            worktree_path="/worktree/build-2",
            branch_name="codex/aligned-build-2-prime-beacon-advisory",
            current_task_id="task-1",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary="approval needed before recovery",
            permission_context=permission_context,
        )

    def test_generate_restart_finding_from_stale_heartbeat(self, blocked_state):
        """Beacon restart finding records heartbeat evidence without live control."""
        observed_at = datetime.now(timezone.utc)
        finding = generate_restart_finding(
            blocked_state,
            threshold_seconds=1800,
            timestamp=observed_at,
        )

        assert finding is not None
        assert finding.finding_type == FindingType.RESTART
        assert finding.session_id == blocked_state.session_id
        assert finding.evidence_stale_seconds >= 2700
        assert finding.evidence_last_queue_read_at == blocked_state.last_queue_read_at
        assert finding.timestamp == observed_at

    def test_generate_restart_finding_ignores_fresh_heartbeat(self, blocked_state):
        """Fresh sessions do not receive restart advisories."""
        fresh_state = SessionLifecycleState(
            **{
                **blocked_state.__dict__,
                "last_prompt_sent_at": datetime.now(timezone.utc),
            }
        )

        assert generate_restart_finding(fresh_state, threshold_seconds=1800) is None

    def test_generate_resteer_finding_from_blocker(self, blocked_state):
        """Beacon resteer finding records blocker evidence without steering."""
        finding = generate_resteer_finding(blocked_state)

        assert finding is not None
        assert finding.finding_type == FindingType.RESTEER
        assert finding.evidence_blocker_summary == blocked_state.blocker_summary
        assert "resteer" in finding.recommended_action

    def test_gather_prime_autonomy_input_normalizes_mutable_sources(self, blocked_state):
        """Prime advisory input snapshots mutable caller containers as immutable data."""
        queues = {"build": ["docs/live-build-2.md"]}
        approvals = [(blocked_state.session_id, "review gate pending")]
        finding = generate_resteer_finding(blocked_state)
        advisory_input = gather_prime_autonomy_input(
            sessions=[blocked_state],
            queues_by_harness=queues,
            approvals_pending=approvals,
            restart_resteer_findings=[finding],
            recent_completions=["commit-abc123"],
            timestamp=datetime.now(timezone.utc),
        )
        queues["build"].append("docs/live-build-3.md")
        approvals.append(("other", "mutated later"))

        assert advisory_input.current_sessions == (blocked_state,)
        assert advisory_input.approvals_pending == (
            (blocked_state.session_id, "review gate pending"),
        )
        assert dict(advisory_input.queues_by_harness)["build"] == (
            "docs/live-build-2.md",
        )
        assert advisory_input.restart_resteer_findings == (finding,)


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
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
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
            current_sessions=(session,),
            queues_by_harness=frozenset([("build", ("docs/live-build-2.md",))]),
            approvals_pending=(("session-1", "branch merge requires approval"),),
            restart_resteer_findings=(),
            recent_completions=("commit-abc123",),
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
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
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
        """Create a session with unlocked permissions (temporary with expiry and task scope)."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
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
            current_task_id="task-1",
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

    def test_can_execute_operation_rejects_out_of_scope_task(self):
        """Test that can_execute_operation rejects when current_task_id doesn't match task_scope."""
        now = datetime.now(timezone.utc)
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="scott",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=future,
            task_scope="task-1",
            last_permission_change=now,
        )
        state = SessionLifecycleState(
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
            current_task_id="task-2",  # Doesn't match task_scope
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
        # should not be able to execute when task_id doesn't match task_scope
        assert not state.can_execute_operation(OperationScope.BRANCH_MOVE)
