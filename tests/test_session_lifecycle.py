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
    WorkflowHeartbeatStatus,
    WorkflowResultKind,
    CloseArchiveWriteThroughAction,
    GoalRuntimeCheckpointSurface,
    GoalRuntimeCheckpointCadence,
    GoalRuntimeContinuationState,
    PermissionState,
    OperationScope,
    FindingType,
    PermissionContext,
    RestartResteerFinding,
    PrimeAutonomyInput,
    SessionPermissionSummary,
    WorkflowWorkOrderRecoverySummary,
    SessionRuntimeStateExport,
    SessionLiveStateEvidence,
    SessionLiveStateAdvisoryProjection,
    SessionLiveControlPermissionGate,
    SessionRecoveryReadinessSummary,
    SessionLiveControlCommandPlanStagingRecord,
    SessionCommandStagingReviewPacket,
    SessionCommandPreviewProof,
    SessionCloseArchiveWriteThroughProof,
    V2CommandPlanPreviewProof,
    V3GoalRuntimeCheckpointProofPacket,
    SessionLifecycleState,
    SessionCommandPlan,
    build_session_live_state_evidence,
    build_session_live_state_advisory_projection,
    build_v2_command_plan_preview_proof,
    build_command_staging_review_packet,
    build_command_preview_proof,
    build_close_archive_write_through_proof,
    build_v3_goal_runtime_checkpoint_proof_packet,
    evaluate_live_control_permission_gate,
    export_session_runtime_state_for_workflow_recovery,
    gather_prime_autonomy_input,
    generate_restart_finding,
    generate_resteer_finding,
    plan_command_from_session_action,
    stage_live_control_command_plan_from_readiness,
    summarize_recovery_readiness,
    summarize_session_permission_state,
    summarize_session_permission_states,
    summarize_workflow_work_order_recovery,
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


class TestSessionPermissionSummaryAggregation:
    """Tests for pure Prime/Beacon-safe permission summary aggregation."""

    @pytest.fixture
    def summary_state(self):
        """Create a session with valid task-scoped recovery permission."""
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.RESTEER]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="permission-summary",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-summary",
            session_name="Build 2 Summary",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.BLOCKED,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-permission-summary",
            current_task_id="permission-summary",
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

    def test_permission_summary_records_approved_operations_and_findings(self, summary_state):
        """Summaries include approved operations plus restart/resteer evidence."""
        observed_at = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
        summary = summarize_session_permission_state(
            summary_state,
            approvals_pending=[(summary_state.session_id, "Aegis review pending")],
            timestamp=observed_at,
        )

        assert isinstance(summary, SessionPermissionSummary)
        assert summary.permission_state == PermissionState.UNLOCKED_TEMPORARY
        assert summary.approved_operations == (
            OperationScope.RESTART,
            OperationScope.RESTEER,
        )
        assert summary.approvals_pending == ("Aegis review pending",)
        assert "approval.pending:Aegis review pending" in summary.blockers
        assert [finding.finding_type for finding in summary.restart_resteer_findings] == [
            FindingType.RESTART,
            FindingType.RESTEER,
        ]
        assert "permission.approved_operations=restart,resteer" in summary.evidence
        assert "approval.pending=Aegis review pending" in summary.evidence
        assert any(item.startswith("finding.restart=") for item in summary.evidence)
        assert any(
            item.startswith("finding.restart.recommendation=")
            for item in summary.evidence
        )
        assert summary.timestamp == observed_at

    def test_permission_summary_records_locked_expired_and_out_of_scope_blockers(
        self, summary_state
    ):
        """Locked, expired, and out-of-scope permissions become display-safe blockers."""
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=True,
            escalation_reason="Aegis approval pending",
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now - timedelta(minutes=1),
            task_scope="different-task",
            last_permission_change=now,
        )
        expired_state = SessionLifecycleState(
            **{
                **summary_state.__dict__,
                "current_task_id": "permission-summary",
                "permission_context": expired_context,
            }
        )
        locked_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset(),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
            last_permission_change=now,
        )
        locked_state = SessionLifecycleState(
            **{**summary_state.__dict__, "permission_context": locked_context}
        )

        expired_summary = summarize_session_permission_state(
            expired_state,
            timestamp=now,
        )
        locked_summary = summarize_session_permission_state(locked_state, timestamp=now)

        assert "permission.unlock_expired" in expired_summary.blockers
        assert "permission.out_of_scope" in expired_summary.blockers
        assert "permission.escalation_gate:Aegis approval pending" in (
            expired_summary.blockers
        )
        assert "permission.locked" in locked_summary.blockers
        assert locked_summary.can_accept_work is False

    def test_permission_summary_normalizes_non_utc_aware_expiry(self, summary_state):
        """Non-UTC aware timestamps are converted to UTC before expiry comparison."""
        unlock_expiry = datetime(2026, 6, 2, 7, 0, tzinfo=timezone.utc)
        observed_at = datetime(
            2026,
            6,
            2,
            2,
            0,
            tzinfo=timezone(timedelta(hours=-6)),
        )
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=unlock_expiry,
            task_scope="permission-summary",
            last_permission_change=unlock_expiry,
        )
        session = SessionLifecycleState(
            **{**summary_state.__dict__, "permission_context": permission_context}
        )

        summary = summarize_session_permission_state(session, timestamp=observed_at)

        assert observed_at.astimezone(timezone.utc) > unlock_expiry
        assert "permission.unlock_expired" in summary.blockers
        assert "permission.can_accept_work=False" in summary.evidence

    def test_permission_summary_records_review_gate_blockers(self, summary_state):
        """Review-gated sessions expose review blockers without live control."""
        gated_state = SessionLifecycleState(
            **{
                **summary_state.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
            }
        )

        summary = summarize_session_permission_state(gated_state)

        assert summary.review_gate_blockers == (
            "review_gate.status=review_gated",
            "review_gate.cadence=review_gated",
        )
        assert "review_gate.status=review_gated" in summary.blockers
        assert "review_gate.cadence=review_gated" in summary.evidence

    def test_permission_summary_serializes_display_safe_fields(self, summary_state):
        """Serialized summaries use values, strings, lists, and ISO timestamps."""
        observed_at = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
        summary = summarize_session_permission_state(
            summary_state,
            timestamp=observed_at,
        )

        serialized = summary.to_dict()

        assert serialized["permission_state"] == "unlocked_temporary"
        assert serialized["approved_operations"] == ["restart", "resteer"]
        assert serialized["restart_resteer_findings"][0]["finding_type"] == "restart"
        assert serialized["timestamp"] == observed_at.isoformat()

    def test_permission_summary_aggregation_preserves_session_order(self, summary_state):
        """Aggregate helper emits immutable summaries in input session order."""
        second_state = SessionLifecycleState(
            **{**summary_state.__dict__, "session_id": "session-summary-2"}
        )

        summaries = summarize_session_permission_states([summary_state, second_state])

        assert tuple(summary.session_id for summary in summaries) == (
            "session-summary",
            "session-summary-2",
        )

    def test_gather_prime_autonomy_input_includes_permission_summaries(
        self, summary_state
    ):
        """Prime advisory input includes permission summaries from mutable sources."""
        queues = {"build": ["docs/live-build-2.md"]}
        approvals = [(summary_state.session_id, "review gate pending")]
        advisory_input = gather_prime_autonomy_input(
            sessions=[summary_state],
            queues_by_harness=queues,
            approvals_pending=approvals,
            timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
        )
        queues["build"].append("docs/live-build-3.md")
        approvals.append((summary_state.session_id, "mutated later"))

        assert len(advisory_input.permission_summaries) == 1
        summary = advisory_input.permission_summaries[0]
        assert summary.session_id == summary_state.session_id
        assert summary.approvals_pending == ("review gate pending",)
        assert dict(advisory_input.queues_by_harness)["build"] == (
            "docs/live-build-2.md",
        )
        assert advisory_input.to_dict()["permission_summaries"][0]["session_id"] == (
            summary_state.session_id
        )


class TestWorkflowWorkOrderRecoverySummary:
    """Tests for pure workflow work-order heartbeat/result recovery summaries."""

    @pytest.fixture
    def workflow_state(self):
        """Create a healthy target session for workflow recovery summaries."""
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.RESTEER]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="workflow-summary",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-workflow",
            session_name="Build 2 Workflow",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-workflow-heartbeat-summary",
            current_task_id="workflow-summary",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_stale_work_order_heartbeat_recommends_restart(self, workflow_state):
        """Stale heartbeat recommends restarting the same bounded work order."""
        observed_at = datetime(2026, 6, 2, 8, 10, tzinfo=timezone.utc)
        summary = summarize_workflow_work_order_recovery(
            workflow_state,
            work_order_id="wo-stale",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )

        assert isinstance(summary, WorkflowWorkOrderRecoverySummary)
        assert summary.heartbeat_age_seconds == 600
        assert summary.heartbeat_status == WorkflowHeartbeatStatus.STALE
        assert summary.recovery_action == SessionAction.START_NEW
        assert "heartbeat.status=stale" in summary.evidence
        assert "restart the same work order" in summary.stale_session_recovery_rationale

    def test_successful_work_order_result_recommends_archive(self, workflow_state):
        """Successful typed result summaries can be archived/recorded."""
        observed_at = datetime(2026, 6, 2, 8, 10, tzinfo=timezone.utc)
        summary = summarize_workflow_work_order_recovery(
            workflow_state,
            work_order_id="wo-success",
            heartbeat_emitted_at=observed_at - timedelta(seconds=10),
            result_kind=WorkflowResultKind.SUCCEEDED,
            timestamp=observed_at,
        )

        assert summary.heartbeat_status == WorkflowHeartbeatStatus.FRESH
        assert summary.result_kind == WorkflowResultKind.SUCCEEDED
        assert summary.recovery_action == SessionAction.ARCHIVE
        assert "result.kind=succeeded" in summary.evidence

    def test_resteer_requested_result_recommends_transfer(self, workflow_state):
        """Resteer requests recommend a new bounded work order, not live steering."""
        observed_at = datetime(2026, 6, 2, 8, 10, tzinfo=timezone.utc)
        summary = summarize_workflow_work_order_recovery(
            workflow_state,
            work_order_id="wo-resteer",
            heartbeat_emitted_at=observed_at - timedelta(seconds=30),
            result_kind=WorkflowResultKind.RESTEER_REQUESTED,
            error_kind="input_invalid",
            retry_resteer_recommendation="narrow allowed_paths to docs/",
            timestamp=observed_at,
        )

        assert summary.result_kind == WorkflowResultKind.RESTEER_REQUESTED
        assert summary.recovery_action == SessionAction.TRANSFER
        assert summary.retry_resteer_recommendation == "narrow allowed_paths to docs/"
        assert "error.kind=input_invalid" in summary.evidence
        assert "retry_resteer.recommendation=narrow allowed_paths to docs/" in (
            summary.evidence
        )

    def test_permission_and_review_blockers_force_human_gate(self, workflow_state):
        """Permission/review blockers are surfaced and prevent automatic recovery."""
        observed_at = datetime(2026, 6, 2, 8, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(minutes=1),
            task_scope="workflow-summary",
            last_permission_change=observed_at,
        )
        gated_state = SessionLifecycleState(
            **{
                **workflow_state.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
                "permission_context": expired_context,
            }
        )

        summary = summarize_workflow_work_order_recovery(
            gated_state,
            work_order_id="wo-gated",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )

        assert summary.recovery_action == SessionAction.REQUEST_HUMAN_GATE
        assert "permission.unlock_expired" in summary.permission_blockers
        assert "review_gate.status=review_gated" in summary.review_gate_blockers
        assert "blocker=permission.unlock_expired" in summary.evidence
        assert "blocker=review_gate.status=review_gated" in summary.evidence

    def test_missing_heartbeat_summary_serializes_display_safe_fields(self, workflow_state):
        """Missing heartbeat summaries serialize without raw workflow context."""
        observed_at = datetime(2026, 6, 2, 8, 10, tzinfo=timezone.utc)
        summary = summarize_workflow_work_order_recovery(
            workflow_state,
            work_order_id="wo-missing",
            result_kind=WorkflowResultKind.TIMEOUT,
            error_kind="timeout",
            timestamp=observed_at,
        )

        serialized = summary.to_dict()

        assert serialized["work_order_id"] == "wo-missing"
        assert serialized["target_session_id"] == workflow_state.session_id
        assert serialized["heartbeat_age_seconds"] is None
        assert serialized["heartbeat_status"] == "missing"
        assert serialized["result_kind"] == "timeout"
        assert serialized["recovery_action"] == "start_new"
        assert serialized["timestamp"] == observed_at.isoformat()


class TestSessionRuntimeStateExport:
    """Tests for pure runtime-state exports used by advisory recovery views."""

    @pytest.fixture
    def runtime_state(self):
        """Create a review-gated session with scoped restart permission."""
        now = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="runtime-state-export",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-runtime",
            session_name="Build 2 Runtime",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.REVIEW_GATED,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-runtime-state-export",
            current_task_id="runtime-state-export",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.REVIEW_GATED,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary="review gate pending",
            permission_context=permission_context,
        )

    def test_runtime_state_export_combines_command_permission_and_workflow(
        self,
        runtime_state,
    ):
        """Runtime export surfaces only display-safe advisory fields."""
        observed_at = datetime(2026, 6, 2, 9, 10, tzinfo=timezone.utc)
        command_plan = SessionCommandPlan(
            session_id=runtime_state.session_id,
            session_name=runtime_state.session_name,
            command_intent=CommandIntent.RESTART,
            reason="Workflow heartbeat stale",
            expected_state_transition=(SessionStatus.STALE, SessionStatus.RUNNING),
            current_state_evidence="session-runtime:stale",
            queue_file_evidence=runtime_state.assigned_queue_file,
            worktree_evidence=runtime_state.worktree_path,
            review_gate_evidence="review required before restart",
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected=runtime_state.assigned_queue_file,
            worktree_path_affected=runtime_state.worktree_path,
            branch_affected=runtime_state.branch_name,
            aegis_gate_result="pending",
            cadence_gate_required=True,
            cadence_gate_status=ReviewCadenceState.REVIEW_GATED,
            is_executable_now=False,
            human_approval_required=True,
            approval_context="workflow restart requires review",
            rollback_or_recovery_note="Advisory restart only.",
            permission_state=runtime_state.permission_context.branch_permission_state,
            permission_task_scope=runtime_state.permission_context.task_scope,
            permission_unlock_expiry=runtime_state.permission_context.unlock_expiry,
            permission_approved_operations=tuple(
                runtime_state.permission_context.approval_scope
            ),
            permission_operation=OperationScope.RESTART,
            permission_operation_allowed=True,
            permission_evidence="permission validated for restart",
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            runtime_state,
            work_order_id="wo-runtime-stale",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )

        export = export_session_runtime_state_for_workflow_recovery(
            runtime_state,
            command_plan=command_plan,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        serialized = export.to_dict()

        assert isinstance(export, SessionRuntimeStateExport)
        assert serialized["state_id"] == (
            f"{runtime_state.session_id}:review_gated:{observed_at.isoformat()}"
        )
        assert serialized["active_command_kind"] == "restart"
        assert serialized["target_session_id"] == runtime_state.session_id
        assert serialized["recommended_recovery_action"] == "request_human_gate"
        assert serialized["heartbeat_status"] == "stale"
        assert serialized["heartbeat_age_seconds"] == 600
        assert serialized["result_kind"] == "pending"
        assert "review_gate.status=review_gated" in serialized["review_gate_blockers"]
        assert "workflow restart requires review" in serialized["human_gate_blockers"]
        assert "workflow.recovery_action=request_human_gate" in (
            serialized["evidence_refs"]
        )

    def test_runtime_state_export_records_permission_blockers(self, runtime_state):
        """Expired permissions become advisory blockers in the export."""
        observed_at = datetime(2026, 6, 2, 9, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="runtime-state-export",
            last_permission_change=observed_at,
        )
        expired_state = SessionLifecycleState(
            **{**runtime_state.__dict__, "permission_context": expired_context}
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            expired_state,
            work_order_id="wo-runtime-expired",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )

        export = export_session_runtime_state_for_workflow_recovery(
            expired_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        assert export.recommended_recovery_action == SessionAction.REQUEST_HUMAN_GATE
        assert "permission.unlock_expired" in export.permission_blockers
        assert "permission.blocker=permission.unlock_expired" in export.evidence_refs
        assert export.to_dict()["permission_state"] == "unlocked_temporary"

    def test_runtime_state_export_flags_mismatched_command_and_workflow_targets(
        self,
        runtime_state,
    ):
        """Mismatched advisory inputs stay serializable and human-gated."""
        observed_at = datetime(2026, 6, 2, 9, 10, tzinfo=timezone.utc)
        command_plan = SessionCommandPlan(
            session_id="other-session",
            session_name="Other",
            command_intent=CommandIntent.RESTART,
            reason="Mismatched command target",
            expected_state_transition=(SessionStatus.STALE, SessionStatus.RUNNING),
            current_state_evidence="other-session:stale",
            queue_file_evidence=runtime_state.assigned_queue_file,
            worktree_evidence=runtime_state.worktree_path,
            review_gate_evidence=None,
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected=runtime_state.assigned_queue_file,
            worktree_path_affected=runtime_state.worktree_path,
            branch_affected=runtime_state.branch_name,
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=False,
            human_approval_required=True,
            approval_context=None,
            rollback_or_recovery_note=None,
        )
        workflow_summary = WorkflowWorkOrderRecoverySummary(
            work_order_id="wo-other",
            target_session_id="other-session",
            heartbeat_age_seconds=None,
            heartbeat_status=WorkflowHeartbeatStatus.MISSING,
            result_kind=WorkflowResultKind.PENDING,
            error_kind=None,
            retry_resteer_recommendation=None,
            recovery_action=SessionAction.START_NEW,
            permission_blockers=(),
            review_gate_blockers=(),
            stale_session_recovery_rationale="Mismatch fixture.",
            evidence=("work_order.id=wo-other", "target_session.id=other-session"),
            timestamp=observed_at,
        )

        export = export_session_runtime_state_for_workflow_recovery(
            runtime_state,
            command_plan=command_plan,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        assert export.target_session_id == "other-session"
        assert "command.target_session_mismatch" in export.human_gate_blockers
        assert "workflow.target_session_mismatch" in export.human_gate_blockers
        assert "workflow.target_session_mismatch=True" in export.evidence_refs


class TestSessionLiveStateEvidence:
    """Tests for session live state evidence export."""

    @pytest.fixture
    def session_state(self):
        """Create a session with comprehensive lifecycle state."""
        now = datetime(2026, 6, 2, 10, 30, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="coordinator",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE, OperationScope.WORKTREE_CREATE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=2),
            task_scope="live-state-evidence",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-evidence",
            session_name="Build 2 Evidence",
            project_name="Meridian",
            project_path="/home/scott/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-haiku-4-5",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2-session-state-evidence",
            branch_name="codex/build-2-session-state-evidence-20260606",
            current_task_id="live-state-evidence",
            last_queue_read_at=now - timedelta(minutes=5),
            last_queue_write_at=now - timedelta(minutes=3),
            last_prompt_sent_at=now - timedelta(minutes=1),
            last_prompt_payload_size=8500,
            review_cadence_state=ReviewCadenceState.CLEARED,
            proof_state=ProofState.COMMAND_STAGED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_live_state_evidence_captures_all_session_fields(self, session_state):
        """Live state evidence includes queue id/path, worktree, branch, model/provider, timestamps, proof, blocker, project, and evidence refs."""
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(session_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        assert isinstance(evidence, SessionLiveStateEvidence)
        assert evidence.session_id == session_state.session_id
        assert evidence.session_name == session_state.session_name
        assert evidence.project_name == session_state.project_name
        assert evidence.project_path == session_state.project_path
        assert evidence.assigned_queue_file == session_state.assigned_queue_file
        assert evidence.worktree_path == session_state.worktree_path
        assert evidence.branch_name == session_state.branch_name
        assert evidence.model_provider == session_state.model_provider
        assert evidence.model_name == session_state.model_name
        assert evidence.status == session_state.status
        assert evidence.health_state == session_state.health_state
        assert evidence.current_task_id == session_state.current_task_id
        assert evidence.last_queue_read_at == session_state.last_queue_read_at
        assert evidence.last_queue_write_at == session_state.last_queue_write_at
        assert evidence.last_prompt_sent_at == session_state.last_prompt_sent_at
        assert evidence.proof_state == session_state.proof_state
        assert evidence.blocker_summary == session_state.blocker_summary
        assert evidence.timestamp == timestamp

    def test_live_state_evidence_includes_display_safe_evidence_refs(self, session_state):
        """Live state evidence refs are display-safe without raw paths or credentials."""
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(session_state, timestamp=timestamp)

        # Should include safe references
        assert any("session.id=" in ref for ref in evidence.evidence_refs)
        assert any("project.name=" in ref for ref in evidence.evidence_refs)
        assert any("model.provider=" in ref for ref in evidence.evidence_refs)
        assert any("model.name=" in ref for ref in evidence.evidence_refs)
        assert any("branch.name=" in ref for ref in evidence.evidence_refs)
        assert any("proof.state=" in ref for ref in evidence.evidence_refs)
        assert any("queue.file=" in ref for ref in evidence.evidence_refs)

        # Should NOT expose raw filesystem paths
        assert not any(session_state.project_path in ref for ref in evidence.evidence_refs)
        assert not any(session_state.worktree_path in ref for ref in evidence.evidence_refs)

        # Paths should be redacted to safe placeholders
        assert any("worktree.path_safe=" in ref for ref in evidence.evidence_refs)
        assert any("project.path_safe=" in ref for ref in evidence.evidence_refs)

    def test_live_state_evidence_serializes_to_json_safe_dict(self, session_state):
        """Serialized evidence is JSON-safe with ISO timestamp strings."""
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(session_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # All timestamps should be ISO format strings
        assert isinstance(serialized["last_queue_read_at"], str)
        assert isinstance(serialized["last_queue_write_at"], str)
        assert isinstance(serialized["last_prompt_sent_at"], str)
        assert isinstance(serialized["timestamp"], str)

        # All enums should be converted to values
        assert isinstance(serialized["status"], str)
        assert serialized["status"] == "running"
        assert isinstance(serialized["health_state"], str)
        assert serialized["health_state"] == "healthy"
        assert isinstance(serialized["proof_state"], str)
        assert serialized["proof_state"] == "command_staged"

        # Evidence refs should be a list
        assert isinstance(serialized["evidence_refs"], list)
        assert len(serialized["evidence_refs"]) > 0

    def test_live_state_evidence_with_no_blocker(self, session_state):
        """Live state evidence handles sessions with no blockers."""
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(session_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        assert evidence.blocker_summary is None
        assert serialized["blocker_present"] is False
        assert serialized["blocker_summary_label"] == "none"
        assert serialized["blocker_summary_length"] == 0
        assert "blocker_summary" not in serialized
        assert any("blocker_summary=none" in ref for ref in evidence.evidence_refs)

    def test_live_state_evidence_with_blocker(self, session_state):
        """Live state evidence redacts blocker content."""
        blocked_state = SessionLifecycleState(
            **{**session_state.__dict__, "blocker_summary": "Waiting for review gate approval"}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(blocked_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        assert evidence.blocker_summary == blocked_state.blocker_summary
        # Blocker content should be captured but referenced safely in evidence refs
        assert any("blocker_summary=" in ref for ref in evidence.evidence_refs)

    def test_live_state_evidence_with_no_project_path(self, session_state):
        """Live state evidence handles sessions with no project path."""
        no_path_state = SessionLifecycleState(
            **{**session_state.__dict__, "project_path": None}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(no_path_state, timestamp=timestamp)

        assert evidence.project_path is None
        assert any("project.path_safe=none" in ref for ref in evidence.evidence_refs)

    @pytest.mark.parametrize("blank_path", ["", "   ", "\t", "\n"])
    def test_to_dict_treats_blank_project_path_as_absent(self, session_state, blank_path):
        """Regression for Codex Review A: empty/whitespace project_path is absent."""
        blank_state = SessionLifecycleState(
            **{**session_state.__dict__, "project_path": blank_path}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(blank_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # present/label must agree — blank counts as absent
        assert serialized["project_path_present"] is False
        assert serialized["project_path_label"] == "none"
        assert "project.path_safe=none" in evidence.evidence_refs
        assert "project.path_safe=<path>" not in evidence.evidence_refs

    @pytest.mark.parametrize("blank_blocker", ["", "   ", "\t", "\n"])
    def test_to_dict_treats_blank_blocker_summary_as_absent(
        self, session_state, blank_blocker
    ):
        """Regression for Codex Review A: empty/whitespace blocker_summary is absent."""
        blank_state = SessionLifecycleState(
            **{**session_state.__dict__, "blocker_summary": blank_blocker}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(blank_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # present/label/length must all agree — blank counts as absent
        assert serialized["blocker_present"] is False
        assert serialized["blocker_summary_label"] == "none"
        assert serialized["blocker_summary_length"] == 0
        assert "blocker_summary=none" in evidence.evidence_refs
        assert "blocker_summary=<blocker>" not in evidence.evidence_refs

    def test_to_dict_preserves_non_empty_project_path_and_blocker(self, session_state):
        """Legitimate non-empty strings still register as present after the repair."""
        full_state = SessionLifecycleState(
            **{
                **session_state.__dict__,
                "project_path": "/real/project/path",
                "blocker_summary": "Real blocker text",
            }
        )

        evidence = build_session_live_state_evidence(full_state)
        serialized = evidence.to_dict()

        assert serialized["project_path_present"] is True
        assert serialized["project_path_label"] == "<project_path>"
        assert serialized["blocker_present"] is True
        assert serialized["blocker_summary_label"] == "<blocker_summary>"
        assert serialized["blocker_summary_length"] == len("Real blocker text")
        assert "project.path_safe=<path>" in evidence.evidence_refs
        assert "blocker_summary=<blocker>" in evidence.evidence_refs

    def test_to_dict_does_not_leak_raw_project_path(self, session_state):
        """Regression: to_dict() must not serialize raw project_path."""
        sensitive_path = "/home/scott/secret-project/internal"
        sensitive_state = SessionLifecycleState(
            **{**session_state.__dict__, "project_path": sensitive_path}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(sensitive_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # Raw key must not appear in serialized dict
        assert "project_path" not in serialized
        # Raw value must not appear anywhere in serialized dict values
        for key, value in serialized.items():
            if isinstance(value, str):
                assert sensitive_path not in value, (
                    f"Raw project_path leaked in serialized['{key}']"
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        assert sensitive_path not in item, (
                            f"Raw project_path leaked in serialized['{key}'] list"
                        )
        # Presence/label must be bounded and safe
        assert serialized["project_path_present"] is True
        assert serialized["project_path_label"] == "<project_path>"

    def test_to_dict_does_not_leak_raw_worktree_path(self, session_state):
        """Regression: to_dict() must not serialize raw worktree_path."""
        sensitive_worktree = "C:\\Users\\scott\\Code\\Meridian-Worktrees\\secret-build"
        sensitive_state = SessionLifecycleState(
            **{**session_state.__dict__, "worktree_path": sensitive_worktree}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(sensitive_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # Raw key must not appear in serialized dict
        assert "worktree_path" not in serialized
        # Raw value must not appear anywhere in serialized dict values
        for key, value in serialized.items():
            if isinstance(value, str):
                assert sensitive_worktree not in value, (
                    f"Raw worktree_path leaked in serialized['{key}']"
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        assert sensitive_worktree not in item, (
                            f"Raw worktree_path leaked in serialized['{key}'] list"
                        )
        # Presence/label must be bounded and safe
        assert serialized["worktree_path_present"] is True
        assert serialized["worktree_path_label"] == "<worktree_path>"

    def test_to_dict_does_not_leak_raw_blocker_summary(self, session_state):
        """Regression: to_dict() must not serialize raw blocker_summary text."""
        sensitive_blocker = (
            "SECRET_BLOCKER_TEXT: credential rotation failed at /etc/secrets/key.pem"
        )
        sensitive_state = SessionLifecycleState(
            **{**session_state.__dict__, "blocker_summary": sensitive_blocker}
        )
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(sensitive_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # Raw key must not appear in serialized dict
        assert "blocker_summary" not in serialized
        # Raw value must not appear anywhere in serialized dict values
        for key, value in serialized.items():
            if isinstance(value, str):
                assert sensitive_blocker not in value, (
                    f"Raw blocker_summary leaked in serialized['{key}']"
                )
                assert "SECRET_BLOCKER_TEXT" not in value, (
                    f"Raw blocker token leaked in serialized['{key}']"
                )
                assert "/etc/secrets/key.pem" not in value, (
                    f"Raw blocker secret path leaked in serialized['{key}']"
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        assert sensitive_blocker not in item, (
                            f"Raw blocker_summary leaked in serialized['{key}'] list"
                        )
                        assert "SECRET_BLOCKER_TEXT" not in item, (
                            f"Raw blocker token leaked in serialized['{key}'] list"
                        )
        # Presence and length must be bounded and safe
        assert serialized["blocker_present"] is True
        assert serialized["blocker_summary_label"] == "<blocker_summary>"
        assert serialized["blocker_summary_length"] == len(sensitive_blocker)

    def test_to_dict_preserves_useful_bounded_labels(self, session_state):
        """Regression: to_dict() output preserves useful bounded labels for advisory consumers."""
        timestamp = datetime(2026, 6, 2, 10, 35, tzinfo=timezone.utc)

        evidence = build_session_live_state_evidence(session_state, timestamp=timestamp)
        serialized = evidence.to_dict()

        # Useful non-sensitive identifiers must remain
        assert serialized["evidence_id"] == evidence.evidence_id
        assert serialized["session_id"] == session_state.session_id
        assert serialized["session_name"] == session_state.session_name
        assert serialized["project_name"] == session_state.project_name
        assert serialized["assigned_queue_file"] == session_state.assigned_queue_file
        assert serialized["branch_name"] == session_state.branch_name
        assert serialized["model_provider"] == session_state.model_provider
        assert serialized["model_name"] == session_state.model_name
        assert serialized["status"] == "running"
        assert serialized["proof_state"] == "command_staged"
        # Bounded presence/label fields must surface the path/blocker existence
        assert "project_path_present" in serialized
        assert "project_path_label" in serialized
        assert "worktree_path_present" in serialized
        assert "worktree_path_label" in serialized
        assert "blocker_present" in serialized
        assert "blocker_summary_label" in serialized
        assert "blocker_summary_length" in serialized


class TestSessionLiveStateAdvisoryProjection:
    """Tests for Bifrost-ready live-state advisory projection."""

    @pytest.fixture
    def healthy_evidence(self):
        """Build live-state evidence from a healthy running session."""
        now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="coordinator",
            approval_scope=frozenset([OperationScope.BRANCH_MOVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=2),
            task_scope="advisory-projection",
            last_permission_change=now,
        )
        session = SessionLifecycleState(
            session_id="session-projection",
            session_name="Build 2 Projection",
            project_name="Meridian",
            project_path="/home/scott/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2-session-state-evidence",
            branch_name="codex/build-2-session-state-evidence-20260606",
            current_task_id="advisory-projection",
            last_queue_read_at=now - timedelta(minutes=5),
            last_queue_write_at=now - timedelta(minutes=3),
            last_prompt_sent_at=now - timedelta(minutes=1),
            last_prompt_payload_size=8500,
            review_cadence_state=ReviewCadenceState.CLEARED,
            proof_state=ProofState.COMMAND_STAGED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )
        return build_session_live_state_evidence(session, timestamp=now)

    def test_projection_from_healthy_evidence_is_advisory_only(self, healthy_evidence):
        """Fail-closed: a healthy live-state evidence still projects as advisory-only.

        Even with no condition-specific blockers (BLOCKED status, STALE health,
        missing proof, present blocker_summary), the projection must keep
        human_gate_required=True and is_executable_now=False, and must always
        carry the universal advisory_only.requires_human_gate blocker so Prime
        and Beacon never receive an executable live-state action.
        """
        timestamp = datetime(2026, 6, 7, 12, 5, tzinfo=timezone.utc)

        projection = build_session_live_state_advisory_projection(
            healthy_evidence, timestamp=timestamp
        )

        assert isinstance(projection, SessionLiveStateAdvisoryProjection)
        assert projection.session_id == "session-projection"
        assert projection.status == SessionStatus.RUNNING
        assert projection.health_state == HealthState.HEALTHY
        assert projection.blocker_present is False
        # Fail-closed invariants on healthy path
        assert projection.human_gate_required is True
        assert projection.is_executable_now is False
        assert "advisory_only.requires_human_gate" in projection.advisory_blockers
        # No condition-specific blockers on a healthy session
        assert "session.blocker_present" not in projection.advisory_blockers
        assert "session.status=running" not in projection.advisory_blockers
        assert "session.health=healthy" not in projection.advisory_blockers
        assert "session.proof.missing" not in projection.advisory_blockers
        assert projection.timestamp == timestamp

    def test_projection_blocked_session_requires_human_gate(self, healthy_evidence):
        """A BLOCKED status produces advisory blockers and forces human gate."""
        blocked_evidence = SessionLiveStateEvidence(
            **{
                **healthy_evidence.__dict__,
                "status": SessionStatus.BLOCKED,
                "blocker_summary": "Waiting for review approval",
            }
        )
        projection = build_session_live_state_advisory_projection(blocked_evidence)

        assert projection.blocker_present is True
        assert projection.human_gate_required is True
        assert projection.is_executable_now is False
        # Universal advisory blocker plus condition-specific blockers
        assert "advisory_only.requires_human_gate" in projection.advisory_blockers
        assert "session.blocker_present" in projection.advisory_blockers
        assert "session.status=blocked" in projection.advisory_blockers

    def test_projection_stale_health_produces_blocker(self, healthy_evidence):
        """A STALE health_state surfaces an advisory blocker."""
        stale_evidence = SessionLiveStateEvidence(
            **{**healthy_evidence.__dict__, "health_state": HealthState.STALE}
        )
        projection = build_session_live_state_advisory_projection(stale_evidence)

        assert "session.health=stale" in projection.advisory_blockers
        assert projection.human_gate_required is True

    def test_projection_no_proof_produces_blocker(self, healthy_evidence):
        """ProofState.NO_PROOF surfaces an advisory blocker."""
        no_proof_evidence = SessionLiveStateEvidence(
            **{**healthy_evidence.__dict__, "proof_state": ProofState.NO_PROOF}
        )
        projection = build_session_live_state_advisory_projection(no_proof_evidence)

        assert "session.proof.missing" in projection.advisory_blockers
        assert projection.human_gate_required is True

    def test_projection_to_dict_does_not_leak_raw_paths_or_blocker(self, healthy_evidence):
        """Regression: projection.to_dict() must not leak raw paths or blocker text."""
        sensitive_evidence = SessionLiveStateEvidence(
            **{
                **healthy_evidence.__dict__,
                "project_path": "/home/scott/secret/project",
                "worktree_path": "C:\\Users\\scott\\secret-worktree",
                "blocker_summary": "SECRET_BLOCKER_TEXT credentials in /etc/secrets/key.pem",
            }
        )

        projection = build_session_live_state_advisory_projection(sensitive_evidence)
        serialized = projection.to_dict()

        # Raw keys must not appear
        assert "project_path" not in serialized
        assert "worktree_path" not in serialized
        assert "blocker_summary" not in serialized

        # Raw values must not appear anywhere in serialized output
        sensitive_values = [
            "/home/scott/secret/project",
            "C:\\Users\\scott\\secret-worktree",
            "SECRET_BLOCKER_TEXT",
            "/etc/secrets/key.pem",
        ]
        for key, value in serialized.items():
            if isinstance(value, str):
                for sensitive in sensitive_values:
                    assert sensitive not in value, (
                        f"Raw sensitive value '{sensitive}' leaked in serialized['{key}']"
                    )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        for sensitive in sensitive_values:
                            assert sensitive not in item, (
                                f"Raw sensitive value '{sensitive}' leaked in serialized['{key}'] list"
                            )

        # Bounded display-safe labels are present
        assert serialized["project_path_present"] is True
        assert serialized["project_path_label"] == "<project_path>"
        assert serialized["worktree_path_present"] is True
        assert serialized["worktree_path_label"] == "<worktree_path>"
        assert serialized["blocker_present"] is True
        assert serialized["blocker_summary_label"] == "<blocker_summary>"
        assert serialized["blocker_summary_length"] == len(
            "SECRET_BLOCKER_TEXT credentials in /etc/secrets/key.pem"
        )

    def test_projection_to_dict_preserves_useful_view_model_fields(self, healthy_evidence):
        """Projection retains identifiers and bounded labels useful for Bifrost view models."""
        projection = build_session_live_state_advisory_projection(healthy_evidence)
        serialized = projection.to_dict()

        assert serialized["projection_id"].startswith("session-projection:")
        assert serialized["evidence_id"] == healthy_evidence.evidence_id
        assert serialized["session_id"] == "session-projection"
        assert serialized["session_name"] == "Build 2 Projection"
        assert serialized["project_name"] == "Meridian"
        assert serialized["assigned_queue_file"] == "docs/live-build-2.md"
        assert serialized["branch_name"] == "codex/build-2-session-state-evidence-20260606"
        assert serialized["model_provider"] == "anthropic"
        assert serialized["model_name"] == "claude-opus-4-7"
        assert serialized["status"] == "running"
        assert serialized["health_state"] == "healthy"
        assert serialized["proof_state"] == "command_staged"
        # Fail-closed invariants surface in serialized output too
        assert serialized["human_gate_required"] is True
        assert serialized["is_executable_now"] is False
        assert "advisory_only.requires_human_gate" in serialized["advisory_blockers"]
        assert isinstance(serialized["evidence_refs"], list)

    def test_projection_evidence_refs_include_projection_metadata(self, healthy_evidence):
        """Projection refs include inherited evidence refs and projection-specific refs.

        On the healthy path, projection refs must reflect the fail-closed
        contract: human_gate_required=True, is_executable_now=False, and the
        advisory_only=True marker.
        """
        projection = build_session_live_state_advisory_projection(healthy_evidence)

        # Inherited from evidence
        assert any("session.id=session-projection" in ref for ref in projection.evidence_refs)
        # Projection-specific refs reflect fail-closed contract
        assert any("projection.id=session-projection:" in ref for ref in projection.evidence_refs)
        assert any("projection.blocker_present=False" in ref for ref in projection.evidence_refs)
        assert any("projection.human_gate_required=True" in ref for ref in projection.evidence_refs)
        assert any("projection.is_executable_now=False" in ref for ref in projection.evidence_refs)
        assert "projection.advisory_only=True" in projection.evidence_refs
        # Universal advisory blocker surfaces in refs
        assert "projection.blocker=advisory_only.requires_human_gate" in projection.evidence_refs

    def test_projection_fail_closed_across_all_input_states(self, healthy_evidence):
        """Regression: every input state yields an advisory-only projection.

        Cycle through healthy + all blocked statuses + degraded/stale/failed
        health + missing proof + present blocker_summary. In every case
        human_gate_required must be True, is_executable_now must be False,
        and the universal advisory_only.requires_human_gate blocker must be
        present.
        """
        input_variants = [
            {},  # healthy baseline
            {"status": SessionStatus.BLOCKED},
            {"status": SessionStatus.REVIEW_GATED},
            {"status": SessionStatus.STALE},
            {"status": SessionStatus.CAPACITY_LIMITED},
            {"status": SessionStatus.ARCHIVED},
            {"health_state": HealthState.DEGRADED},
            {"health_state": HealthState.STALE},
            {"health_state": HealthState.FAILED},
            {"proof_state": ProofState.NO_PROOF},
            {"blocker_summary": "Waiting for review approval"},
        ]
        for variant in input_variants:
            evidence = SessionLiveStateEvidence(
                **{**healthy_evidence.__dict__, **variant}
            )
            projection = build_session_live_state_advisory_projection(evidence)

            assert projection.human_gate_required is True, (
                f"Fail-closed violated for variant {variant}: "
                f"human_gate_required={projection.human_gate_required}"
            )
            assert projection.is_executable_now is False, (
                f"Fail-closed violated for variant {variant}: "
                f"is_executable_now={projection.is_executable_now}"
            )
            assert "advisory_only.requires_human_gate" in projection.advisory_blockers, (
                f"Universal advisory blocker missing for variant {variant}"
            )

    @pytest.mark.parametrize("blank_blocker", ["", "   ", "\t", "\n"])
    def test_projection_treats_blank_blocker_summary_as_absent(
        self, healthy_evidence, blank_blocker
    ):
        """Regression for Codex Review A: blank blocker_summary is not present.

        The projection must not emit `session.blocker_present` in
        advisory_blockers when the underlying blocker_summary is blank.
        The fail-closed universal blocker still holds — but the phantom
        condition-specific blocker disappears.
        """
        blank_evidence = SessionLiveStateEvidence(
            **{**healthy_evidence.__dict__, "blocker_summary": blank_blocker}
        )

        projection = build_session_live_state_advisory_projection(blank_evidence)

        assert projection.blocker_present is False
        assert projection.blocker_summary_label == "none"
        assert projection.blocker_summary_length == 0
        assert "session.blocker_present" not in projection.advisory_blockers
        # Fail-closed universal blocker still present
        assert (
            "advisory_only.requires_human_gate" in projection.advisory_blockers
        )
        assert projection.human_gate_required is True

    @pytest.mark.parametrize("blank_path", ["", "   ", "\t", "\n"])
    def test_projection_treats_blank_project_path_as_absent(
        self, healthy_evidence, blank_path
    ):
        """Regression for Codex Review A: blank project_path is not present."""
        blank_evidence = SessionLiveStateEvidence(
            **{**healthy_evidence.__dict__, "project_path": blank_path}
        )

        projection = build_session_live_state_advisory_projection(blank_evidence)

        assert projection.project_path_present is False
        assert projection.project_path_label == "none"

    def test_projection_preserves_real_blocker_summary_and_path(self, healthy_evidence):
        """Legitimate non-empty values still produce present/blocker output."""
        real_evidence = SessionLiveStateEvidence(
            **{
                **healthy_evidence.__dict__,
                "project_path": "/real/project/path",
                "blocker_summary": "Real blocker text",
            }
        )

        projection = build_session_live_state_advisory_projection(real_evidence)

        assert projection.project_path_present is True
        assert projection.project_path_label == "<project_path>"
        assert projection.blocker_present is True
        assert projection.blocker_summary_label == "<blocker_summary>"
        assert projection.blocker_summary_length == len("Real blocker text")
        # Real blocker still surfaces the condition-specific blocker
        assert "session.blocker_present" in projection.advisory_blockers


class TestSessionLiveControlPermissionGate:
    """Tests for pure live-control permission readiness advice."""

    @pytest.fixture
    def gate_state(self):
        """Create a stale session with scoped live-control permissions."""
        now = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset(
                [OperationScope.RESTART, OperationScope.RESTEER, OperationScope.ARCHIVE]
            ),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="live-control-gate",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-live-gate",
            session_name="Build 2 Live Gate",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-live-control-permission-gate",
            current_task_id="live-control-gate",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_live_control_gate_clears_ready_restart_advice(self, gate_state):
        """Scoped restart permission can clear future command staging readiness."""
        observed_at = datetime(2026, 6, 2, 10, 10, tzinfo=timezone.utc)
        workflow_summary = summarize_workflow_work_order_recovery(
            gate_state,
            work_order_id="wo-live-restart",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            gate_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        gate = evaluate_live_control_permission_gate(
            gate_state,
            runtime_export,
            timestamp=observed_at,
        )
        serialized = gate.to_dict()

        assert isinstance(gate, SessionLiveControlPermissionGate)
        assert gate.ready_for_execution is True
        assert gate.human_gate_required is False
        assert gate.command_kind == CommandIntent.RESTART
        assert gate.required_operation == OperationScope.RESTART
        assert gate.target_session_id == gate_state.session_id
        assert gate.blockers == ()
        assert serialized["command_kind"] == "restart"
        assert serialized["required_operation"] == "restart"
        assert "gate.ready_for_execution=True" in gate.evidence_refs

    def test_live_control_gate_preserves_permission_and_human_blockers(
        self,
        gate_state,
    ):
        """Expired/out-of-scope permissions remain human-gated advisory blockers."""
        observed_at = datetime(2026, 6, 2, 10, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=True,
            escalation_reason="Aegis approval pending",
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="different-task",
            last_permission_change=observed_at,
        )
        blocked_state = SessionLifecycleState(
            **{**gate_state.__dict__, "permission_context": expired_context}
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            blocked_state,
            work_order_id="wo-live-blocked",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            blocked_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        gate = evaluate_live_control_permission_gate(
            blocked_state,
            runtime_export,
            timestamp=observed_at,
        )

        assert gate.ready_for_execution is False
        assert gate.human_gate_required is True
        assert gate.command_kind is None
        assert "permission.unlock_expired" in gate.blockers
        assert "permission.out_of_scope" in gate.blockers
        assert "permission.escalation_gate:Aegis approval pending" in gate.blockers
        assert "command_kind_missing" in gate.blockers
        assert "gate.blocker=permission.unlock_expired" in gate.evidence_refs

    def test_live_control_gate_flags_target_mismatch(self, gate_state):
        """Target mismatches are preserved as non-executable advisory evidence."""
        observed_at = datetime(2026, 6, 2, 10, 10, tzinfo=timezone.utc)
        runtime_export = SessionRuntimeStateExport(
            state_id=f"other-session:stale:{observed_at.isoformat()}",
            session_id=gate_state.session_id,
            session_name=gate_state.session_name,
            status=gate_state.status,
            health_state=gate_state.health_state,
            current_task_id=gate_state.current_task_id,
            active_command_kind=CommandIntent.RESTART,
            target_session_id="other-session",
            recommended_recovery_action=SessionAction.START_NEW,
            heartbeat_status=WorkflowHeartbeatStatus.STALE,
            heartbeat_age_seconds=600,
            result_kind=WorkflowResultKind.PENDING,
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            permission_blockers=(),
            review_gate_blockers=(),
            human_gate_blockers=(),
            evidence_refs=("workflow.target_session_id=other-session",),
            timestamp=observed_at,
        )

        gate = evaluate_live_control_permission_gate(
            gate_state,
            runtime_export,
            timestamp=observed_at,
        )

        assert gate.target_session_id == "other-session"
        assert gate.ready_for_execution is False
        assert "target_session_mismatch" in gate.blockers
        assert "gate.target_session_id=other-session" in gate.evidence_refs

    def test_live_control_gate_maps_archive_recommendation(self, gate_state):
        """Archive recommendations map to archive permission without execution."""
        observed_at = datetime(2026, 6, 2, 10, 10, tzinfo=timezone.utc)
        workflow_summary = summarize_workflow_work_order_recovery(
            gate_state,
            work_order_id="wo-live-archive",
            heartbeat_emitted_at=observed_at - timedelta(seconds=5),
            result_kind=WorkflowResultKind.SUCCEEDED,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            gate_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        gate = evaluate_live_control_permission_gate(
            gate_state,
            runtime_export,
            timestamp=observed_at,
        )

        assert gate.command_kind == CommandIntent.ARCHIVE
        assert gate.recommended_action == SessionAction.ARCHIVE
        assert gate.required_operation == OperationScope.ARCHIVE
        assert gate.ready_for_execution is True
        assert "gate.required_operation=archive" in gate.evidence_refs


class TestSessionRecoveryReadinessSummary:
    """Tests for composed recovery readiness summaries."""

    @pytest.fixture
    def readiness_state(self):
        """Create a stale session with scoped restart/archive permissions."""
        now = datetime(2026, 6, 2, 11, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.ARCHIVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="recovery-readiness",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-readiness",
            session_name="Build 2 Readiness",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-recovery-readiness-binding",
            current_task_id="recovery-readiness",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_recovery_readiness_summary_combines_ready_export_and_gate(
        self,
        readiness_state,
    ):
        """Ready runtime/gate inputs become one display-safe readiness summary."""
        observed_at = datetime(2026, 6, 2, 11, 10, tzinfo=timezone.utc)
        workflow_summary = summarize_workflow_work_order_recovery(
            readiness_state,
            work_order_id="wo-readiness-ready",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            readiness_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        gate = evaluate_live_control_permission_gate(
            readiness_state,
            runtime_export,
            timestamp=observed_at,
        )

        summary = summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )
        serialized = summary.to_dict()

        assert isinstance(summary, SessionRecoveryReadinessSummary)
        assert summary.readiness_status == "ready"
        assert summary.ready_for_execution is True
        assert summary.human_gate_required is False
        assert summary.command_kind == CommandIntent.RESTART
        assert summary.required_operation == OperationScope.RESTART
        assert summary.recommended_action == SessionAction.START_NEW
        assert summary.blockers == ()
        assert serialized["readiness_status"] == "ready"
        assert "readiness.status=ready" in summary.evidence_refs
        assert "readiness.ready_for_execution=True" in summary.evidence_refs

    def test_recovery_readiness_summary_preserves_blockers(self, readiness_state):
        """Blocked gate inputs stay human-gated in the composed summary."""
        observed_at = datetime(2026, 6, 2, 11, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="recovery-readiness",
            last_permission_change=observed_at,
        )
        blocked_state = SessionLifecycleState(
            **{**readiness_state.__dict__, "permission_context": expired_context}
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            blocked_state,
            work_order_id="wo-readiness-blocked",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            blocked_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        gate = evaluate_live_control_permission_gate(
            blocked_state,
            runtime_export,
            timestamp=observed_at,
        )

        summary = summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )

        assert summary.readiness_status == "blocked"
        assert summary.ready_for_execution is False
        assert summary.human_gate_required is True
        assert "permission.unlock_expired" in summary.blockers
        assert "command_kind_missing" in summary.blockers
        assert "readiness.blocker=permission.unlock_expired" in summary.evidence_refs
        assert summary.human_gate_rationale == gate.human_gate_rationale

    def test_recovery_readiness_summary_flags_input_mismatches(self, readiness_state):
        """Mismatched reviewed inputs become display-safe readiness blockers."""
        observed_at = datetime(2026, 6, 2, 11, 10, tzinfo=timezone.utc)
        runtime_export = SessionRuntimeStateExport(
            state_id=f"{readiness_state.session_id}:stale:{observed_at.isoformat()}",
            session_id=readiness_state.session_id,
            session_name=readiness_state.session_name,
            status=readiness_state.status,
            health_state=readiness_state.health_state,
            current_task_id=readiness_state.current_task_id,
            active_command_kind=CommandIntent.RESTART,
            target_session_id=readiness_state.session_id,
            recommended_recovery_action=SessionAction.START_NEW,
            heartbeat_status=WorkflowHeartbeatStatus.STALE,
            heartbeat_age_seconds=600,
            result_kind=WorkflowResultKind.PENDING,
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            permission_blockers=(),
            review_gate_blockers=(),
            human_gate_blockers=(),
            evidence_refs=("runtime.fixture=restart",),
            timestamp=observed_at,
        )
        gate = SessionLiveControlPermissionGate(
            gate_id=f"other-session:archive:{observed_at.isoformat()}",
            target_session_id="other-session",
            command_kind=CommandIntent.ARCHIVE,
            recommended_action=SessionAction.ARCHIVE,
            required_operation=OperationScope.ARCHIVE,
            ready_for_execution=True,
            human_gate_required=False,
            human_gate_rationale=(
                "Permission gate cleared for future live-control command staging."
            ),
            blockers=(),
            evidence_refs=("gate.fixture=archive",),
            timestamp=observed_at,
        )

        summary = summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )

        assert summary.readiness_status == "blocked"
        assert summary.ready_for_execution is False
        assert "readiness.target_session_mismatch" in summary.blockers
        assert "readiness.recommended_action_mismatch" in summary.blockers
        assert "runtime.fixture=restart" in summary.evidence_refs
        assert "gate.fixture=archive" in summary.evidence_refs


class TestSessionLiveControlCommandPlanStagingRecord:
    """Tests for non-executable live-control command-plan staging."""

    @pytest.fixture
    def staging_state(self):
        """Create a stale session with scoped restart permission."""
        now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="command-plan-staging",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-staging",
            session_name="Build 2 Staging",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-live-control-command-plan-staging",
            current_task_id="command-plan-staging",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def _ready_summary(self, staging_state, observed_at):
        workflow_summary = summarize_workflow_work_order_recovery(
            staging_state,
            work_order_id="wo-staging-ready",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            staging_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        gate = evaluate_live_control_permission_gate(
            staging_state,
            runtime_export,
            timestamp=observed_at,
        )
        return summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )

    def test_stages_ready_readiness_as_non_executable_ui_review(
        self,
        staging_state,
    ):
        """Readiness-cleared recovery still stages as non-executable UI review."""
        observed_at = datetime(2026, 6, 2, 12, 10, tzinfo=timezone.utc)
        readiness = self._ready_summary(staging_state, observed_at)

        staging = stage_live_control_command_plan_from_readiness(
            readiness,
            timestamp=observed_at,
        )
        serialized = staging.to_dict()

        assert isinstance(staging, SessionLiveControlCommandPlanStagingRecord)
        assert staging.target_session_id == staging_state.session_id
        assert staging.command_kind == CommandIntent.RESTART
        assert staging.recommended_action == SessionAction.START_NEW
        assert staging.required_operation == OperationScope.RESTART
        assert staging.permission_state == PermissionState.UNLOCKED_TEMPORARY
        assert staging.ready_for_execution is True
        assert staging.is_executable_now is False
        assert staging.ui_review_required is True
        assert staging.human_gate_required is True
        assert "command_plan.ui_review_required" in staging.blockers
        assert "staging.is_executable_now=False" in staging.evidence_refs
        assert serialized["is_executable_now"] is False

    def test_staging_preserves_blocked_readiness_rationale(self, staging_state):
        """Blocked readiness summaries carry blockers into staging records."""
        observed_at = datetime(2026, 6, 2, 12, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="command-plan-staging",
            last_permission_change=observed_at,
        )
        blocked_state = SessionLifecycleState(
            **{**staging_state.__dict__, "permission_context": expired_context}
        )
        readiness = self._ready_summary(blocked_state, observed_at)

        staging = stage_live_control_command_plan_from_readiness(
            readiness,
            timestamp=observed_at,
        )

        assert staging.ready_for_execution is False
        assert staging.human_gate_rationale == readiness.human_gate_rationale
        assert "permission.unlock_expired" in staging.blockers
        assert "command_plan.ui_review_required" in staging.blockers
        assert "staging.blocker=permission.unlock_expired" in staging.evidence_refs

    def test_staging_flags_non_stageable_command_kind(self, staging_state):
        """Unsupported command kinds remain display-safe non-executable records."""
        observed_at = datetime(2026, 6, 2, 12, 10, tzinfo=timezone.utc)
        readiness = SessionRecoveryReadinessSummary(
            summary_id=f"{staging_state.session_id}:watch:{observed_at.isoformat()}",
            state_id=f"{staging_state.session_id}:running:{observed_at.isoformat()}",
            gate_id=f"{staging_state.session_id}:watch:{observed_at.isoformat()}",
            target_session_id=staging_state.session_id,
            command_kind=CommandIntent.WATCH,
            recommended_action=SessionAction.REUSE,
            required_operation=None,
            readiness_status="watch",
            ready_for_execution=False,
            human_gate_required=False,
            human_gate_rationale=(
                "Recovery readiness advisory is clear for future command staging."
            ),
            heartbeat_status=WorkflowHeartbeatStatus.FRESH,
            result_kind=WorkflowResultKind.PENDING,
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            blockers=(),
            evidence_refs=("readiness.status=watch",),
            timestamp=observed_at,
        )

        staging = stage_live_control_command_plan_from_readiness(
            readiness,
            timestamp=observed_at,
        )

        assert staging.command_kind == CommandIntent.WATCH
        assert staging.is_executable_now is False
        assert "command_plan.command_kind_not_stageable" in staging.blockers
        assert "command_plan.required_operation_missing" in staging.blockers
        assert "staging.command_kind=watch" in staging.evidence_refs


class TestSessionCommandStagingReviewPacket:
    """Tests for display-safe command-staging review packets."""

    @pytest.fixture
    def packet_state(self):
        """Create a stale session with scoped restart permission."""
        now = datetime(2026, 6, 2, 13, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="command-staging-review-packet",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-review-packet",
            session_name="Build 2 Review Packet",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-command-staging-review-packet",
            current_task_id="command-staging-review-packet",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def _staging_record(self, packet_state, observed_at):
        workflow_summary = summarize_workflow_work_order_recovery(
            packet_state,
            work_order_id="wo-review-packet",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            packet_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        gate = evaluate_live_control_permission_gate(
            packet_state,
            runtime_export,
            timestamp=observed_at,
        )
        readiness = summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )
        return stage_live_control_command_plan_from_readiness(
            readiness,
            timestamp=observed_at,
        )

    def test_review_packet_preserves_staging_prime_and_beacon_shapes(
        self,
        packet_state,
    ):
        """Review packets serialize staging plus Prime/Beacon advisory evidence."""
        observed_at = datetime(2026, 6, 2, 13, 10, tzinfo=timezone.utc)
        staging = self._staging_record(packet_state, observed_at)
        prime_advisory = {
            "action_type": "advise_session_recovery",
            "target_harness": "Session Lifecycle",
            "target_lane": staging.target_session_id,
            "human_gate_required": True,
            "blockers": list(staging.blockers),
            "evidence": list(staging.evidence_refs),
            "rationale": "Review non-executable command-plan staging.",
        }
        beacon_evidence = {
            "harness_id": staging.target_session_id,
            "advisory_type": "staging_restart",
            "human_gate_required": True,
            "blockers": list(staging.blockers),
            "evidence": list(staging.evidence_refs),
        }

        packet = build_command_staging_review_packet(
            staging,
            prime_advisory_action=prime_advisory,
            beacon_evidence=beacon_evidence,
            timestamp=observed_at,
        )
        serialized = packet.to_dict()

        assert isinstance(packet, SessionCommandStagingReviewPacket)
        assert packet.target_session_id == packet_state.session_id
        assert packet.command_kind == CommandIntent.RESTART
        assert packet.recommended_action == SessionAction.START_NEW
        assert packet.required_operation == OperationScope.RESTART
        assert packet.ready_for_execution is True
        assert packet.is_executable_now is False
        assert packet.requires_human_ui_review is True
        assert packet.permission_state == PermissionState.UNLOCKED_TEMPORARY
        assert "command_plan.ui_review_required" in packet.blockers
        assert "review_packet.is_executable_now=False" in packet.evidence_refs
        assert packet.prime_advisory_action["action_type"] == (
            "advise_session_recovery"
        )
        assert packet.beacon_evidence["advisory_type"] == "staging_restart"
        assert serialized["is_executable_now"] is False
        assert serialized["requires_human_ui_review"] is True

    def test_review_packet_defaults_missing_prime_and_beacon_shapes(
        self,
        packet_state,
    ):
        """Missing consumer shapes become deterministic display-safe defaults."""
        observed_at = datetime(2026, 6, 2, 13, 10, tzinfo=timezone.utc)
        staging = self._staging_record(packet_state, observed_at)

        packet = build_command_staging_review_packet(staging, timestamp=observed_at)

        assert packet.prime_advisory_action["action_type"] == (
            "advise_session_recovery"
        )
        assert packet.prime_advisory_action["human_gate_required"] is True
        assert packet.beacon_evidence["advisory_type"] == "staging_unknown"
        assert packet.beacon_evidence["human_gate_required"] is True
        assert "review_packet.requires_human_ui_review=True" in packet.evidence_refs

    def test_review_packet_preserves_blocked_staging(self, packet_state):
        """Blocked staging records preserve blocker and rationale metadata."""
        observed_at = datetime(2026, 6, 2, 13, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="command-staging-review-packet",
            last_permission_change=observed_at,
        )
        blocked_state = SessionLifecycleState(
            **{**packet_state.__dict__, "permission_context": expired_context}
        )
        staging = self._staging_record(blocked_state, observed_at)

        packet = build_command_staging_review_packet(staging, timestamp=observed_at)

        assert packet.ready_for_execution is False
        assert packet.human_gate_rationale == staging.human_gate_rationale
        assert "permission.unlock_expired" in packet.blockers
        assert "review_packet.blocker=permission.unlock_expired" in packet.evidence_refs


class TestSessionCommandPreviewProof:
    """Tests for command-preview proof fields for UI review staging."""

    @pytest.fixture
    def preview_state(self):
        """Create a stale session with scoped restart permission."""
        now = datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="command-preview-proof",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-preview-proof",
            session_name="Build 2 Preview Proof",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-command-preview-proof-fields",
            current_task_id="command-preview-proof",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def _review_packet(self, preview_state, observed_at):
        workflow_summary = summarize_workflow_work_order_recovery(
            preview_state,
            work_order_id="wo-preview-proof",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            preview_state,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )
        gate = evaluate_live_control_permission_gate(
            preview_state,
            runtime_export,
            timestamp=observed_at,
        )
        readiness = summarize_recovery_readiness(
            runtime_export,
            gate,
            timestamp=observed_at,
        )
        staging = stage_live_control_command_plan_from_readiness(
            readiness,
            timestamp=observed_at,
        )
        return build_command_staging_review_packet(staging, timestamp=observed_at)

    def test_command_preview_proof_preserves_restart_fields(self, preview_state):
        """Preview proof fields serialize restart context without executability."""
        observed_at = datetime(2026, 6, 2, 14, 10, tzinfo=timezone.utc)
        packet = self._review_packet(preview_state, observed_at)

        proof = build_command_preview_proof(
            preview_state,
            packet,
            reason="Preview restart after stale workflow heartbeat.",
            timestamp=observed_at,
        )
        serialized = proof.to_dict()

        assert isinstance(proof, SessionCommandPreviewProof)
        assert proof.target_session_id == preview_state.session_id
        assert proof.command_kind == CommandIntent.RESTART
        assert proof.recommended_action == SessionAction.START_NEW
        assert proof.required_operation == OperationScope.RESTART
        assert proof.expected_state_transition == (
            SessionStatus.STALE,
            SessionStatus.RUNNING,
        )
        assert proof.queue_file_evidence == preview_state.assigned_queue_file
        assert proof.worktree_evidence == preview_state.worktree_path
        assert proof.branch_affected == preview_state.branch_name
        assert proof.aegis_gate_result == "pending"
        assert proof.aegis_gate_status == "pending_ui_review"
        assert proof.proof_requirement == ProofState.COMMAND_STAGED
        assert proof.is_executable_now is False
        assert proof.requires_human_ui_review is True
        assert proof.permission_state == PermissionState.UNLOCKED_TEMPORARY
        assert "command_plan.ui_review_required" in proof.blockers
        assert "preview.expected_transition=stale->running" in proof.evidence_refs
        assert serialized["is_executable_now"] is False
        assert serialized["expected_state_transition"] == ["stale", "running"]

    def test_command_preview_proof_preserves_blocked_packet(self, preview_state):
        """Blocked packets keep blocker and rollback/recovery proof metadata."""
        observed_at = datetime(2026, 6, 2, 14, 10, tzinfo=timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(seconds=1),
            task_scope="command-preview-proof",
            last_permission_change=observed_at,
        )
        blocked_state = SessionLifecycleState(
            **{**preview_state.__dict__, "permission_context": expired_context}
        )
        packet = self._review_packet(blocked_state, observed_at)

        proof = build_command_preview_proof(
            blocked_state,
            packet,
            timestamp=observed_at,
        )

        assert proof.ready_for_execution is False
        assert proof.is_executable_now is False
        assert "permission.unlock_expired" in proof.blockers
        assert "preview.blocker=permission.unlock_expired" in proof.evidence_refs
        assert proof.rollback_or_recovery_note == (
            "Non-executable command preview only; no live recovery is executed."
        )

    def test_command_preview_proof_holds_unsupported_transition(self, preview_state):
        """Unsupported preview command kinds keep current-state transition."""
        observed_at = datetime(2026, 6, 2, 14, 10, tzinfo=timezone.utc)
        packet = SessionCommandStagingReviewPacket(
            packet_id=f"{preview_state.session_id}:watch:review:{observed_at.isoformat()}",
            staging_id=f"{preview_state.session_id}:watch:{observed_at.isoformat()}",
            target_session_id=preview_state.session_id,
            command_kind=CommandIntent.WATCH,
            recommended_action=SessionAction.REUSE,
            required_operation=None,
            ready_for_execution=False,
            is_executable_now=False,
            requires_human_ui_review=True,
            human_gate_rationale="UI review required before command preview.",
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            blockers=("command_plan.command_kind_not_stageable",),
            evidence_refs=("review_packet.command_kind=watch",),
            prime_advisory_action={},
            beacon_evidence={},
            timestamp=observed_at,
        )

        proof = build_command_preview_proof(
            preview_state,
            packet,
            timestamp=observed_at,
        )

        assert proof.command_kind == CommandIntent.WATCH
        assert proof.expected_state_transition == (
            preview_state.status,
            preview_state.status,
        )
        assert "preview.expected_transition=stale->stale" in proof.evidence_refs


class TestSessionCloseArchiveWriteThroughProof:
    """Tests for close/archive/write-through proof-only metadata."""

    @pytest.fixture
    def close_state(self):
        """Create a running session with scoped archive permission."""
        now = datetime(2026, 6, 2, 17, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.ARCHIVE]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="close-archive-write-through",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-close-proof",
            session_name="Build 2 Close Proof",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.RUNNING,
            worktree_path="/worktree/build-2",
            branch_name="codex/build-2-close-archive-write-through",
            current_task_id="close-archive-write-through",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=9000,
            review_cadence_state=ReviewCadenceState.CLEARED,
            proof_state=ProofState.COMMAND_STAGED,
            health_state=HealthState.HEALTHY,
            blocker_summary=None,
            permission_context=permission_context,
        )

    def test_close_proof_is_non_executable_and_requires_stop_before_close(
        self,
        close_state,
    ):
        """Close proof preserves target and fail-closed stop-before-close blocker."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)

        proof = build_close_archive_write_through_proof(
            close_state,
            CloseArchiveWriteThroughAction.CLOSE,
            write_through_completed=True,
            human_gate_approved=True,
            timestamp=observed_at,
        )
        serialized = proof.to_dict()

        assert isinstance(proof, SessionCloseArchiveWriteThroughProof)
        assert proof.target_session_id == close_state.session_id
        assert proof.intended_action == CloseArchiveWriteThroughAction.CLOSE
        assert proof.required_operation == OperationScope.ARCHIVE
        assert proof.write_through_completed is True
        assert proof.permission_gate_state == "approved"
        assert proof.human_gate_state == "approved"
        assert proof.is_executable_now is False
        assert "close.stop_before_close_required" in proof.blockers
        assert "proof.is_executable_now_false" in proof.blockers
        assert serialized["intended_action"] == "close"
        assert serialized["is_executable_now"] is False

    def test_archive_proof_serializes_write_through_and_visibility(
        self,
        close_state,
    ):
        """Archive proof records durable write-through and visibility metadata."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)
        stopped_state = SessionLifecycleState(
            **{**close_state.__dict__, "status": SessionStatus.STOPPED}
        )

        proof = build_close_archive_write_through_proof(
            stopped_state,
            CloseArchiveWriteThroughAction.ARCHIVE,
            write_through_completed=True,
            human_gate_approved=True,
            timestamp=observed_at,
        )
        serialized = proof.to_dict()

        assert proof.intended_action == CloseArchiveWriteThroughAction.ARCHIVE
        assert proof.blockers == ("proof.is_executable_now_false",)
        assert proof.approval_required is True
        assert proof.failure_visibility == (
            "write_through_verified_for_vulcan_and_session_lifecycle_review"
        )
        assert "Archive requires durable queue/result write-through proof" in (
            proof.required_write_through_condition
        )
        assert "close_archive.intended_action=archive" in proof.evidence_refs
        assert serialized["required_operation"] == "archive"
        assert serialized["permission_state"] == "unlocked_temporary"

    def test_stop_before_close_proof_preserves_state_without_execution(
        self,
        close_state,
    ):
        """Stop-before-close proof is explicit but still non-executable."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)

        proof = build_close_archive_write_through_proof(
            close_state,
            CloseArchiveWriteThroughAction.STOP_BEFORE_CLOSE,
            write_through_completed=True,
            human_gate_approved=True,
            timestamp=observed_at,
        )

        assert proof.intended_action == CloseArchiveWriteThroughAction.STOP_BEFORE_CLOSE
        assert proof.required_operation == OperationScope.ARCHIVE
        assert proof.is_executable_now is False
        assert proof.rollback_or_preservation_note == (
            "Preserve queue, proof, and blocker state before any later close "
            "or archive review."
        )
        assert "close_archive.intended_action=stop_before_close" in proof.evidence_refs

    def test_write_through_failure_visibility_blocks_review(self, close_state):
        """Missing write-through remains visible and blocked."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)

        proof = build_close_archive_write_through_proof(
            close_state,
            CloseArchiveWriteThroughAction.WRITE_THROUGH,
            write_through_completed=False,
            human_gate_approved=True,
            timestamp=observed_at,
        )

        assert proof.intended_action == CloseArchiveWriteThroughAction.WRITE_THROUGH
        assert proof.required_operation is None
        assert proof.failure_visibility == (
            "write_through_failure_visible_to_vulcan_and_session_lifecycle"
        )
        assert "write_through.required" in proof.blockers
        assert "write_through.review_required" in proof.blockers
        assert proof.permission_gate_state == "approved"
        assert proof.is_executable_now is False

    def test_blocked_permission_state_records_gate_blocker(self, close_state):
        """Locked archive permission is surfaced as a proof blocker."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)
        locked_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset(),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.LOCKED_BY_DEFAULT,
            approved_by_secondary=None,
            unlock_expiry=None,
            task_scope=None,
            last_permission_change=observed_at,
        )
        locked_state = SessionLifecycleState(
            **{**close_state.__dict__, "permission_context": locked_context}
        )

        proof = build_close_archive_write_through_proof(
            locked_state,
            CloseArchiveWriteThroughAction.ARCHIVE,
            write_through_completed=True,
            human_gate_approved=True,
            timestamp=observed_at,
        )

        assert proof.permission_state == PermissionState.LOCKED_BY_DEFAULT
        assert proof.permission_gate_state == "blocked"
        assert "permission.archive_required" in proof.blockers
        assert "close_archive.permission_allowed=False" in proof.evidence_refs
        assert proof.is_executable_now is False

    def test_close_archive_proof_excludes_raw_prompt_and_chat_sentinels(
        self,
        close_state,
    ):
        """Caller text is bounded before serialization or evidence refs."""
        observed_at = datetime(2026, 6, 2, 17, 5, tzinfo=timezone.utc)
        raw_worker_chat = "SECRET_WORKER_CHAT: close this UI now"
        raw_prompt = "SECRET_RAW_PROMPT: move branches now"

        proof = build_close_archive_write_through_proof(
            close_state,
            CloseArchiveWriteThroughAction.ARCHIVE,
            write_through_completed=False,
            human_gate_approved=False,
            failure_visibility=raw_worker_chat,
            rollback_or_preservation_note=raw_prompt,
            timestamp=observed_at,
        )
        serialized_text = repr(proof.to_dict())
        evidence_text = repr(proof.evidence_refs)

        assert proof.raw_worker_chat_included is False
        assert proof.raw_prompt_included is False
        assert proof.failure_visibility == "custom_failure_visibility_provided_for_review"
        assert proof.rollback_or_preservation_note == (
            "custom_preservation_note_provided_for_review"
        )
        assert raw_worker_chat not in serialized_text
        assert raw_worker_chat not in evidence_text
        assert raw_prompt not in serialized_text
        assert raw_prompt not in evidence_text
        assert "SECRET_WORKER_CHAT" not in serialized_text
        assert "SECRET_RAW_PROMPT" not in serialized_text


class TestV3GoalRuntimeCheckpointProofPacket:
    """Tests for V3 Goal Runtime checkpoint/update proof metadata."""

    def test_goal_runtime_checkpoint_packet_serializes_non_executable_update(self):
        """Checkpoint proof preserves bounded update metadata."""
        observed_at = datetime(2026, 6, 2, 20, 15, tzinfo=timezone.utc)

        packet = build_v3_goal_runtime_checkpoint_proof_packet(
            checkpoint_id="checkpoint-20260602-001",
            goal_id="goal-runtime-v3-001",
            goal_title="native_goal_runtime",
            owning_lane="prime",
            owning_session_label="build-2-goal-runtime",
            update_surface=GoalRuntimeCheckpointSurface.GIT,
            checkpoint_cadence=GoalRuntimeCheckpointCadence.REGULAR,
            token_budget_summary="tokens_ok",
            time_budget_summary="time_ok",
            latest_git_ref="commit.85dd4714",
            latest_obsidian_ref="obsidian.goal-runtime-proof",
            reviewer_gate_refs=("reviews-a.goal-checkpoint",),
            lease_gate_refs=("lease.prime-goal-runtime",),
            blocker_tags=("v3.not_active_scope",),
            continuation_state=GoalRuntimeContinuationState.READY_FOR_HANDOFF,
            evidence_refs=("v3-parking-lot.native-goal-runtime",),
            timestamp=observed_at,
        )
        serialized = packet.to_dict()

        assert isinstance(packet, V3GoalRuntimeCheckpointProofPacket)
        assert packet.checkpoint_id == "checkpoint-20260602-001"
        assert packet.goal_id == "goal-runtime-v3-001"
        assert packet.goal_title == "native_goal_runtime"
        assert packet.update_surface == GoalRuntimeCheckpointSurface.GIT
        assert packet.checkpoint_cadence == GoalRuntimeCheckpointCadence.REGULAR
        assert packet.token_budget_summary == "tokens_ok"
        assert packet.time_budget_summary == "time_ok"
        assert packet.latest_git_ref == "commit.85dd4714"
        assert packet.latest_obsidian_ref == "obsidian.goal-runtime-proof"
        assert packet.continuation_state == (
            GoalRuntimeContinuationState.READY_FOR_HANDOFF
        )
        assert packet.is_executable_now is False
        assert packet.raw_worker_chat_included is False
        assert packet.raw_prompt_included is False
        assert serialized["update_surface"] == "git"
        assert serialized["checkpoint_cadence"] == "regular"
        assert serialized["is_executable_now"] is False
        assert "v3_goal_checkpoint.update_surface=git" in packet.evidence_refs
        assert "v3_goal_checkpoint.latest_git_ref=commit.85dd4714" in (
            packet.evidence_refs
        )
        assert "v3_goal_checkpoint.evidence_ref=v3-parking-lot.native-goal-runtime" in (
            packet.evidence_refs
        )

    def test_goal_runtime_checkpoint_packet_records_missing_gate_blockers(self):
        """Missing Git/Obsidian and gate refs remain visible as fixed blockers."""
        observed_at = datetime(2026, 6, 2, 20, 15, tzinfo=timezone.utc)

        packet = build_v3_goal_runtime_checkpoint_proof_packet(
            checkpoint_id="checkpoint-20260602-002",
            goal_id="goal-runtime-v3-002",
            goal_title="goal_runtime_checkpoint",
            owning_lane="compass",
            owning_session_label="build-2",
            update_surface=GoalRuntimeCheckpointSurface.REVIEW,
            checkpoint_cadence=GoalRuntimeCheckpointCadence.REVIEW_GATED,
            token_budget_summary="tokens_limited",
            time_budget_summary="time_limited",
            continuation_state=GoalRuntimeContinuationState.PAUSED_FOR_REVIEW,
            timestamp=observed_at,
        )

        assert packet.latest_git_ref == "git_ref_missing"
        assert packet.latest_obsidian_ref == "obsidian_ref_missing"
        assert "goal_checkpoint.git_ref_missing" in packet.blockers
        assert "goal_checkpoint.obsidian_ref_missing" in packet.blockers
        assert "goal_checkpoint.reviewer_gate_refs_missing" in packet.blockers
        assert "goal_checkpoint.lease_gate_refs_missing" in packet.blockers
        assert "goal_checkpoint.is_executable_now_false" in packet.blockers
        assert "v3_goal_checkpoint.blocker=goal_checkpoint.git_ref_missing" in (
            packet.evidence_refs
        )
        assert packet.is_executable_now is False

    def test_goal_runtime_checkpoint_packet_redacts_raw_path_and_movement_text(self):
        """Raw prompt/chat/path/movement strings do not serialize."""
        observed_at = datetime(2026, 6, 2, 20, 15, tzinfo=timezone.utc)
        raw_prompt = "SECRET_RAW_PROMPT: move branches now"
        raw_chat = "SECRET_WORKER_CHAT: write obsidian now"
        path_value = "C:\\Users\\scott\\vault\\goal.md"
        movement_id = "branch_move_request"
        movement_ref = "move_main"

        packet = build_v3_goal_runtime_checkpoint_proof_packet(
            checkpoint_id=movement_id,
            goal_id=movement_ref,
            goal_title=raw_prompt,
            owning_lane="worktree_switch",
            owning_session_label=raw_chat,
            update_surface=GoalRuntimeCheckpointSurface.OBSIDIAN,
            checkpoint_cadence=GoalRuntimeCheckpointCadence.BEFORE_CONTINUATION,
            token_budget_summary=raw_prompt,
            time_budget_summary="stash_pop",
            latest_git_ref="merge_main",
            latest_obsidian_ref=path_value,
            reviewer_gate_refs=("cherry_pick", "reviews-a.safe_ref"),
            lease_gate_refs=("worktree_switch", "lease.safe_ref"),
            blocker_tags=("rebase_main", raw_chat),
            continuation_state=GoalRuntimeContinuationState.BLOCKED,
            evidence_refs=(path_value, raw_prompt),
            timestamp=observed_at,
        )
        serialized_text = repr(packet.to_dict())
        evidence_text = repr(packet.evidence_refs)

        assert packet.checkpoint_id == "checkpoint_id_redacted"
        assert packet.goal_id == "goal_id_redacted"
        assert packet.goal_title == "goal_title_present"
        assert packet.owning_lane == "owning_lane_redacted"
        assert packet.owning_session_label == "owning_session_label_present"
        assert packet.token_budget_summary == "token_budget_summary_present"
        assert packet.time_budget_summary == "time_budget_summary_present"
        assert packet.latest_git_ref == "git_ref_redacted"
        assert packet.latest_obsidian_ref == "obsidian_ref_redacted"
        for unsafe in (
            raw_prompt,
            raw_chat,
            path_value,
            movement_id,
            movement_ref,
            "SECRET_RAW_PROMPT",
            "SECRET_WORKER_CHAT",
            "worktree_switch",
            "stash_pop",
            "merge_main",
            "rebase_main",
            "cherry_pick",
        ):
            assert unsafe not in serialized_text
            assert unsafe not in evidence_text
        assert "v3_goal_checkpoint.reviewer_gate_ref=reviewer_gate_ref_redacted" in (
            packet.evidence_refs
        )
        assert "v3_goal_checkpoint.lease_gate_ref=lease_gate_ref_redacted" in (
            packet.evidence_refs
        )
        assert "v3_goal_checkpoint.evidence_ref=evidence_ref_redacted" in (
            packet.evidence_refs
        )


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


class TestV2CommandPlanPreviewProof:
    """Tests for V2 Session Lifecycle command-plan preview proof."""

    @pytest.fixture
    def session(self):
        now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="coordinator",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="v2-preview",
            last_permission_change=now,
        )
        return SessionLifecycleState(
            session_id="session-v2-preview",
            session_name="Build 2 V2 Preview",
            project_name="Meridian",
            project_path="/home/scott/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2-session-state-evidence",
            branch_name="codex/build-2-session-state-evidence-20260606",
            current_task_id="v2-preview",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now,
            last_prompt_payload_size=8500,
            review_cadence_state=ReviewCadenceState.CLEARED,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )

    @pytest.fixture
    def command_plan(self, session):
        return SessionCommandPlan(
            session_id=session.session_id,
            session_name=session.session_name,
            command_intent=CommandIntent.RESTART,
            reason="Workflow heartbeat stale; advise restart staging",
            expected_state_transition=(SessionStatus.STALE, SessionStatus.RUNNING),
            current_state_evidence="session-v2-preview:stale",
            queue_file_evidence=session.assigned_queue_file,
            worktree_evidence=session.worktree_path,
            review_gate_evidence=None,
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected=session.assigned_queue_file,
            worktree_path_affected=session.worktree_path,
            branch_affected=session.branch_name,
            aegis_gate_result="pending",
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.CLEARED,
            is_executable_now=False,
            human_approval_required=True,
            approval_context="restart staging requires review",
            rollback_or_recovery_note="Advisory restart only; rollback by reverting state",
            permission_state=session.permission_context.branch_permission_state,
            permission_operation=OperationScope.RESTART,
            permission_operation_allowed=True,
        )

    def test_proof_captures_all_required_fields(self, session, command_plan):
        """V2 preview proof carries target, reason, expected transition, queue, worktree, branch, Aegis, executability, human-gate state, rollback, permission, blockers, refs."""
        timestamp = datetime(2026, 6, 7, 12, 5, tzinfo=timezone.utc)

        proof = build_v2_command_plan_preview_proof(
            session, command_plan, timestamp=timestamp
        )

        assert isinstance(proof, V2CommandPlanPreviewProof)
        assert proof.target_session_id == "session-v2-preview"
        assert proof.session_name == "Build 2 V2 Preview"
        assert proof.command_kind == CommandIntent.RESTART
        assert proof.required_operation == OperationScope.RESTART
        assert proof.expected_state_transition == (
            SessionStatus.STALE,
            SessionStatus.RUNNING,
        )
        assert proof.assigned_queue_file == "docs/live-build-2.md"
        assert proof.worktree_path_present is True
        assert proof.worktree_path_label == "<worktree_path>"
        assert proof.branch_name == "codex/build-2-session-state-evidence-20260606"
        assert proof.aegis_gate_result == "pending"
        assert proof.aegis_gate_status == "pending_ui_review"
        assert proof.proof_requirement == ProofState.PERMISSION_VALIDATED
        assert proof.review_cadence_state == ReviewCadenceState.CLEARED
        assert proof.permission_state == PermissionState.UNLOCKED_TEMPORARY
        # Reason and rollback bounded
        assert proof.reason_present is True
        assert proof.reason_label == "<reason>"
        assert proof.reason_length == len(command_plan.reason)
        assert proof.rollback_or_recovery_note_present is True
        assert proof.rollback_or_recovery_note_label == "<rollback_or_recovery_note>"
        assert proof.rollback_or_recovery_note_length == len(
            command_plan.rollback_or_recovery_note
        )
        assert proof.timestamp == timestamp

    def test_proof_is_fail_closed_on_every_path(self, session, command_plan):
        """V2 preview proof is non-executable by contract on every input shape."""
        proof = build_v2_command_plan_preview_proof(session, command_plan)

        assert proof.is_executable_now is False
        assert proof.human_gate_required is True
        assert (
            "v2_command_plan_preview.advisory_only.requires_human_gate"
            in proof.advisory_blockers
        )
        assert "v2_preview.advisory_only=True" in proof.evidence_refs

    def test_proof_universal_blocker_present_even_when_plan_executable(
        self, session, command_plan
    ):
        """Universal advisory blocker still present even if command_plan flagged executable."""
        executable_plan = SessionCommandPlan(
            **{
                **command_plan.__dict__,
                "is_executable_now": True,
                "human_approval_required": False,
            }
        )

        proof = build_v2_command_plan_preview_proof(session, executable_plan)

        # Fail-closed contract overrides plan-level executability hint
        assert proof.is_executable_now is False
        assert proof.human_gate_required is True
        assert (
            "v2_command_plan_preview.advisory_only.requires_human_gate"
            in proof.advisory_blockers
        )

    def test_proof_review_gated_plan_adds_cadence_blocker(self, session, command_plan):
        """Cadence-gate blocker derives from the plan's cadence_gate_status, not the session."""
        gated_plan = SessionCommandPlan(
            **{
                **command_plan.__dict__,
                "cadence_gate_status": ReviewCadenceState.REVIEW_GATED,
            }
        )
        proof = build_v2_command_plan_preview_proof(session, gated_plan)

        assert "review.cadence_gated" in proof.advisory_blockers
        assert proof.review_cadence_state == ReviewCadenceState.REVIEW_GATED

    def test_proof_no_proof_command_plan_adds_proof_missing_blocker(
        self, session, command_plan
    ):
        no_proof_plan = SessionCommandPlan(
            **{**command_plan.__dict__, "proof_requirement": ProofState.NO_PROOF}
        )
        proof = build_v2_command_plan_preview_proof(session, no_proof_plan)

        assert "command_plan.proof.missing" in proof.advisory_blockers

    def test_proof_to_dict_does_not_leak_raw_paths_reason_or_rollback(
        self, session, command_plan
    ):
        """Regression: proof.to_dict() must not leak raw worktree, reason, or rollback text."""
        sensitive_session = SessionLifecycleState(
            **{
                **session.__dict__,
                "project_path": "/home/scott/secret/project",
                "worktree_path": "C:\\Users\\scott\\secret-worktree",
            }
        )
        sensitive_plan = SessionCommandPlan(
            **{
                **command_plan.__dict__,
                "reason": "SECRET_REASON: credentials at /etc/secrets/key.pem",
                "rollback_or_recovery_note": (
                    "SECRET_ROLLBACK: revert SECRET_CHAT prompt text"
                ),
            }
        )

        proof = build_v2_command_plan_preview_proof(sensitive_session, sensitive_plan)
        serialized = proof.to_dict()

        # Raw keys must not appear
        assert "project_path" not in serialized
        assert "worktree_path" not in serialized
        assert "reason" not in serialized
        assert "rollback_or_recovery_note" not in serialized

        sensitive_values = [
            "/home/scott/secret/project",
            "C:\\Users\\scott\\secret-worktree",
            "SECRET_REASON",
            "SECRET_ROLLBACK",
            "SECRET_CHAT",
            "/etc/secrets/key.pem",
        ]
        for key, value in serialized.items():
            if isinstance(value, str):
                for sensitive in sensitive_values:
                    assert sensitive not in value, (
                        f"V2 preview leaked '{sensitive}' in serialized['{key}']"
                    )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        for sensitive in sensitive_values:
                            assert sensitive not in item, (
                                f"V2 preview leaked '{sensitive}' in serialized['{key}'] list"
                            )

        # Bounded labels present
        assert serialized["worktree_path_present"] is True
        assert serialized["worktree_path_label"] == "<worktree_path>"
        assert serialized["reason_present"] is True
        assert serialized["reason_label"] == "<reason>"
        assert serialized["reason_length"] == len(sensitive_plan.reason)
        assert serialized["rollback_or_recovery_note_present"] is True
        assert serialized["rollback_or_recovery_note_label"] == "<rollback_or_recovery_note>"
        assert serialized["rollback_or_recovery_note_length"] == len(
            sensitive_plan.rollback_or_recovery_note
        )

    def test_proof_serializes_to_json_safe_dict(self, session, command_plan):
        proof = build_v2_command_plan_preview_proof(session, command_plan)
        serialized = proof.to_dict()

        assert isinstance(serialized["timestamp"], str)
        assert isinstance(serialized["command_kind"], str)
        assert serialized["command_kind"] == "restart"
        assert isinstance(serialized["expected_state_transition"], list)
        assert serialized["expected_state_transition"] == ["stale", "running"]
        assert isinstance(serialized["advisory_blockers"], list)
        assert isinstance(serialized["evidence_refs"], list)
        assert serialized["is_executable_now"] is False
        assert serialized["human_gate_required"] is True

    def test_proof_handles_no_worktree_no_reason_no_rollback(self, session, command_plan):
        """Bounded fields collapse to 'none' / 0 length when source is empty.

        worktree presence/label derives from the plan's worktree_path_affected,
        not the session.
        """
        empty_plan = SessionCommandPlan(
            **{
                **command_plan.__dict__,
                "reason": "",
                "rollback_or_recovery_note": None,
                "worktree_path_affected": "",
            }
        )

        proof = build_v2_command_plan_preview_proof(session, empty_plan)

        assert proof.worktree_path_present is False
        assert proof.worktree_path_label == "none"
        assert proof.reason_present is False
        assert proof.reason_label == "none"
        assert proof.reason_length == 0
        assert proof.rollback_or_recovery_note_present is False
        assert proof.rollback_or_recovery_note_label == "none"
        assert proof.rollback_or_recovery_note_length == 0
        # Fail-closed invariants still hold
        assert proof.is_executable_now is False
        assert proof.human_gate_required is True

    def test_proof_derives_plan_affected_fields_when_session_disagrees(
        self, session, command_plan
    ):
        """Regression for Codex Review A: preview uses plan-affected fields.

        Builds a session and a plan that deliberately disagree on every
        plan-bound field (queue, worktree, branch, cadence, permission
        state). The preview proof must reflect the plan's values, not the
        session's, because the plan is the audited artifact.
        """
        # Plan targets different resources than current session snapshot.
        divergent_plan = SessionCommandPlan(
            **{
                **command_plan.__dict__,
                "queue_file_affected": "docs/plan-different-queue.md",
                "worktree_path_affected": "/worktree/plan-different-worktree",
                "branch_affected": "codex/plan-different-branch-20260607",
                "cadence_gate_status": ReviewCadenceState.REVIEW_GATED,
                "permission_state": PermissionState.LOCKED_BY_DEFAULT,
            }
        )

        proof = build_v2_command_plan_preview_proof(session, divergent_plan)

        # All plan-bound fields come from the plan, not the session
        assert proof.assigned_queue_file == "docs/plan-different-queue.md"
        assert proof.assigned_queue_file != session.assigned_queue_file
        assert proof.branch_name == "codex/plan-different-branch-20260607"
        assert proof.branch_name != session.branch_name
        assert proof.worktree_path_present is True
        assert proof.worktree_path_label == "<worktree_path>"
        assert proof.review_cadence_state == ReviewCadenceState.REVIEW_GATED
        assert proof.review_cadence_state != session.review_cadence_state
        assert proof.permission_state == PermissionState.LOCKED_BY_DEFAULT
        assert (
            proof.permission_state
            != session.permission_context.branch_permission_state
        )

        # Evidence refs reflect plan values too
        assert (
            "v2_preview.assigned_queue_file=docs/plan-different-queue.md"
            in proof.evidence_refs
        )
        assert (
            "v2_preview.branch_name=codex/plan-different-branch-20260607"
            in proof.evidence_refs
        )
        assert (
            "v2_preview.review_cadence_state=review_gated" in proof.evidence_refs
        )
        assert (
            "v2_preview.permission_state=locked_by_default" in proof.evidence_refs
        )
        # Session values must not surface anywhere in evidence
        assert not any(
            session.assigned_queue_file in ref for ref in proof.evidence_refs
        )
        assert not any(
            session.branch_name in ref for ref in proof.evidence_refs
        )

        # Plan-derived cadence gate produces the cadence-gated blocker
        assert "review.cadence_gated" in proof.advisory_blockers
        # Fail-closed invariants still hold
        assert proof.is_executable_now is False
        assert proof.human_gate_required is True

    def test_proof_permission_state_falls_back_to_session_when_plan_unset(
        self, session, command_plan
    ):
        """When the plan does not carry a permission_state, fall back to session context.

        This preserves backward compatibility with plans that haven't yet
        populated their permission advisory fields, without re-introducing
        a session-derived drift bug for plans that have.
        """
        plan_without_permission = SessionCommandPlan(
            **{**command_plan.__dict__, "permission_state": None}
        )

        proof = build_v2_command_plan_preview_proof(session, plan_without_permission)

        assert (
            proof.permission_state
            == session.permission_context.branch_permission_state
        )
