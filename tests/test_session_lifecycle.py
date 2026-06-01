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
