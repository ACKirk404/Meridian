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
    SessionLifecycleState,
    SessionCommandPlan,
)


class TestSessionLifecycleState:
    """Tests for SessionLifecycleState dataclass."""

    @pytest.fixture
    def healthy_state(self):
        """Create a healthy session state."""
        now = datetime.now(timezone.utc)
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
            permission_context={"user": "scott"},
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
