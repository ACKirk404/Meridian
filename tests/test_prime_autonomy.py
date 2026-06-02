"""Tests for Prime Autonomy domain model."""

import pytest
from datetime import datetime, timedelta, timezone

from meridian_core.prime_autonomy import (
    PrimeActionType,
    PrimeActionConfidence,
    PrimeActionRiskTier,
    PrimeActionSource,
    PrimeNextAction,
    ProjectStateSignal,
    select_prime_next_action,
    make_prime_next_action,
    select_next_action_from_project_state,
    select_next_action_from_session_lifecycle_advisory,
)
from meridian_core.session_lifecycle import (
    HealthState,
    HarnessRole,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionLifecycleState,
    SessionStatus,
    gather_prime_autonomy_input,
    generate_restart_finding,
    generate_resteer_finding,
)


class TestPrimeActionEnums:
    """Test enum types are well-formed."""

    def test_action_type_values(self):
        assert PrimeActionType.POLL_SESSION.value == "poll_session"
        assert PrimeActionType.PAUSE_AND_WAIT.value == "pause_and_wait"
        assert PrimeActionType.NO_OP.value == "no_op"

    def test_confidence_values(self):
        assert PrimeActionConfidence.HIGH.value == "high"
        assert PrimeActionConfidence.FALLBACK.value == "fallback"

    def test_risk_tier_values(self):
        assert PrimeActionRiskTier.SAFE.value == "safe"
        assert PrimeActionRiskTier.HIGH.value == "high"

    def test_source_values(self):
        assert PrimeActionSource.COGNITION_POLICY.value == "cognition_policy"
        assert PrimeActionSource.HUMAN_OVERRIDE.value == "human_override"


class TestPrimeNextActionImmutability:
    """Test that PrimeNextAction is truly immutable."""

    def test_frozen_dataclass_cannot_modify_field(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            action.action_type = PrimeActionType.NO_OP

    def test_frozen_blockers_set(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.NO_OP,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            blockers=frozenset(["blocker1", "blocker2"]),
        )
        assert isinstance(action.blockers, frozenset)
        with pytest.raises(AttributeError):  # frozenset has no add()
            action.blockers.add("blocker3")

    def test_frozen_evidence_set(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.LOW,
            source=PrimeActionSource.SESSION_STATE,
            evidence=frozenset(["ref1", "ref2"]),
        )
        assert isinstance(action.evidence, frozenset)


class TestSelectPrimeNextActionFallbacks:
    """Test select_prime_next_action fallback behavior."""

    def test_all_none_returns_safe_fallback(self):
        action = select_prime_next_action()
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.source == PrimeActionSource.ERROR_RECOVERY
        assert action.human_gate_required is False
        assert action.blockers == frozenset()
        assert action.evidence == frozenset()

    def test_partial_none_uses_provided_fields(self):
        action = select_prime_next_action(
            action_type=PrimeActionType.ADVANCE_COGNITION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=None,
            source=None,
        )
        assert action.action_type == PrimeActionType.ADVANCE_COGNITION
        assert action.confidence == PrimeActionConfidence.HIGH
        assert action.risk_tier == PrimeActionRiskTier.SAFE  # fallback
        assert action.source == PrimeActionSource.ERROR_RECOVERY  # fallback

    def test_converts_list_to_frozenset(self):
        action = select_prime_next_action(
            evidence=["ref1", "ref2"],
            blockers=["block1"],
        )
        assert action.evidence == frozenset(["ref1", "ref2"])
        assert action.blockers == frozenset(["block1"])

    def test_empty_list_becomes_empty_frozenset(self):
        action = select_prime_next_action(evidence=[], blockers=[])
        assert action.evidence == frozenset()
        assert action.blockers == frozenset()


class TestMakePrimeNextAction:
    """Test make_prime_next_action strict constructor."""

    def test_requires_action_type_and_confidence(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.RUN_WORKFLOW,
            confidence=PrimeActionConfidence.MEDIUM,
        )
        assert action.action_type == PrimeActionType.RUN_WORKFLOW
        assert action.confidence == PrimeActionConfidence.MEDIUM
        assert action.risk_tier == PrimeActionRiskTier.SAFE  # default
        assert action.source == PrimeActionSource.ERROR_RECOVERY  # default

    def test_explicit_optional_fields(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.LOW,
            risk_tier=PrimeActionRiskTier.MEDIUM,
            source=PrimeActionSource.WORKFLOW_RESULT,
            target_harness="Echo",
            target_lane="data-processing",
            rationale="Echo failed to process query",
            evidence=["session_123_error_log"],
            human_gate_required=True,
            blockers=["waiting_for_user_decision"],
        )
        assert action.action_type == PrimeActionType.ESCALATE_ERROR
        assert action.confidence == PrimeActionConfidence.LOW
        assert action.risk_tier == PrimeActionRiskTier.MEDIUM
        assert action.source == PrimeActionSource.WORKFLOW_RESULT
        assert action.target_harness == "Echo"
        assert action.target_lane == "data-processing"
        assert action.rationale == "Echo failed to process query"
        assert action.evidence == frozenset(["session_123_error_log"])
        assert action.human_gate_required is True
        assert action.blockers == frozenset(["waiting_for_user_decision"])


class TestPrimeNextActionBlockerHandling:
    """Test blocker detection and execution checks."""

    def test_is_blocked_with_no_blockers(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            blockers=frozenset(),
        )
        assert action.is_blocked() is False

    def test_is_blocked_with_blockers(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.ADVANCE_COGNITION,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.COGNITION_POLICY,
            blockers=frozenset(["external_service_down"]),
        )
        assert action.is_blocked() is True

    def test_is_executable_unblocked_no_human_gate(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            blockers=frozenset(),
            human_gate_required=False,
        )
        assert action.is_executable() is True

    def test_is_executable_with_blockers(self):
        action = PrimeNextAction(
            action_type=PrimeActionType.RUN_WORKFLOW,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.WORKFLOW_RESULT,
            blockers=frozenset(["precondition_not_met"]),
        )
        assert action.is_executable() is False

    def test_is_executable_with_human_gate_is_not_executable(self):
        """Human-gated actions must wait for approval before execution."""
        action = PrimeNextAction(
            action_type=PrimeActionType.ADVANCE_COGNITION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.COGNITION_POLICY,
            blockers=frozenset(),
            human_gate_required=True,
        )
        assert action.is_executable() is False


class TestPrimeNextActionHumanGateAndRisk:
    """Test human-gate propagation and risk-tier relationships."""

    def test_high_risk_can_have_human_gate(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.RUN_WORKFLOW,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.HIGH,
            human_gate_required=True,
        )
        assert action.risk_tier == PrimeActionRiskTier.HIGH
        assert action.human_gate_required is True
        assert action.is_executable() is False

    def test_safe_action_no_human_gate_by_default(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
        )
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.human_gate_required is False

    def test_human_gate_overrides_to_true_when_set(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.NO_OP,
            confidence=PrimeActionConfidence.FALLBACK,
            human_gate_required=True,
        )
        assert action.human_gate_required is True


class TestPrimeNextActionConfidenceMappings:
    """Test confidence-to-risk mappings and defaults."""

    def test_fallback_confidence_safe_risk(self):
        action = select_prime_next_action(
            confidence=PrimeActionConfidence.FALLBACK
        )
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.risk_tier == PrimeActionRiskTier.SAFE

    def test_high_confidence_with_explicit_risk(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.ADVANCE_COGNITION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
        )
        assert action.confidence == PrimeActionConfidence.HIGH
        assert action.risk_tier == PrimeActionRiskTier.HIGH

    def test_low_confidence_safe_fallback(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.LOW,
        )
        assert action.confidence == PrimeActionConfidence.LOW
        assert action.risk_tier == PrimeActionRiskTier.SAFE


class TestDefaultFallbackAction:
    """Test that select_prime_next_action produces a safe default."""

    def test_fallback_is_pause_and_wait(self):
        action = select_prime_next_action()
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT

    def test_fallback_not_executable_only_if_has_blockers(self):
        action = select_prime_next_action()
        assert action.is_executable() is True  # No blockers by default

    def test_fallback_rationale_empty_by_default(self):
        action = select_prime_next_action()
        assert action.rationale == ""

    def test_fallback_with_custom_rationale(self):
        action = select_prime_next_action(rationale="Custom reason")
        assert action.rationale == "Custom reason"


class TestRoundTripImmutability:
    """Test that actions remain immutable through construction patterns."""

    def test_select_then_read_unchanged(self):
        action = select_prime_next_action(
            action_type=PrimeActionType.RUN_WORKFLOW,
            confidence=PrimeActionConfidence.HIGH,
            blockers=["condition_1"],
        )
        # Reading multiple times should return the same values
        assert action.blockers == frozenset(["condition_1"])
        assert action.action_type == PrimeActionType.RUN_WORKFLOW
        assert action.confidence == PrimeActionConfidence.HIGH

    def test_make_then_read_unchanged(self):
        action = make_prime_next_action(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.MEDIUM,
            evidence=["ref1", "ref2", "ref3"],
        )
        assert action.evidence == frozenset(["ref1", "ref2", "ref3"])
        assert len(action.evidence) == 3


class TestProjectStateSignal:
    """Test ProjectStateSignal construction and immutability."""

    def test_default_state(self):
        state = ProjectStateSignal()
        assert state.active_task is None
        assert state.candidate_task is None
        assert state.review_gate_open is True
        assert state.commits_since_review == 0
        assert state.human_gate_required is False
        assert state.blockers == frozenset()
        assert state.lane_id is None
        assert state.risk_tier == PrimeActionRiskTier.SAFE
        assert state.echo_signal is None
        assert state.atlas_signal is None

    def test_immutable_state(self):
        state = ProjectStateSignal(active_task="task_001")
        with pytest.raises(Exception):
            state.active_task = "task_002"

    def test_with_all_fields(self):
        state = ProjectStateSignal(
            active_task="task_001",
            candidate_task="task_002",
            review_gate_open=False,
            commits_since_review=4,
            human_gate_required=True,
            blockers=frozenset(["blocker_a"]),
            lane_id="build-1",
            risk_tier=PrimeActionRiskTier.HIGH,
            echo_signal="echo context",
            atlas_signal="atlas context",
        )
        assert state.active_task == "task_001"
        assert state.candidate_task == "task_002"
        assert state.lane_id == "build-1"
        assert state.echo_signal == "echo context"
        assert state.atlas_signal == "atlas context"

    def test_blockers_is_frozenset(self):
        state = ProjectStateSignal(blockers=frozenset(["b1", "b2"]))
        assert isinstance(state.blockers, frozenset)


class TestSelectNextActionFromProjectState:
    """Test deterministic priority ordering of project-state selector."""

    def test_none_state_returns_pause_fallback(self):
        """Missing state → PAUSE_AND_WAIT with FALLBACK confidence."""
        action = select_next_action_from_project_state(None)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.source == PrimeActionSource.ERROR_RECOVERY

    def test_no_arg_returns_pause_fallback(self):
        """No argument defaults to None state."""
        action = select_next_action_from_project_state()
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK

    def test_empty_state_polls_session(self):
        """Default state (no active task, gate open) → POLL_SESSION."""
        state = ProjectStateSignal()
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.confidence == PrimeActionConfidence.HIGH

    def test_active_task_advances_cognition(self):
        """Active task with clear state → ADVANCE_COGNITION."""
        state = ProjectStateSignal(active_task="task_001")
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ADVANCE_COGNITION
        assert action.confidence == PrimeActionConfidence.HIGH

    def test_human_gate_returns_pause_not_executable(self):
        """Human gate required → PAUSE_AND_WAIT, not executable."""
        state = ProjectStateSignal(active_task="task_001", human_gate_required=True)
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_executable() is False

    def test_blockers_return_escalate_error(self):
        """Active blockers → ESCALATE_ERROR."""
        state = ProjectStateSignal(
            active_task="task_001",
            blockers=frozenset(["external_service_down"]),
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ESCALATE_ERROR
        assert action.is_blocked() is True

    def test_review_gate_closed_returns_pause(self):
        """Explicitly closed review gate → PAUSE_AND_WAIT."""
        state = ProjectStateSignal(active_task="task_001", review_gate_open=False)
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is False

    def test_commit_limit_exceeded_returns_pause(self):
        """Three commits since review trips cadence gate → PAUSE_AND_WAIT."""
        state = ProjectStateSignal(active_task="task_001", commits_since_review=3)
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT

    def test_two_commits_since_review_still_advances(self):
        """Two commits since review is under the limit → ADVANCE_COGNITION."""
        state = ProjectStateSignal(active_task="task_001", commits_since_review=2)
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ADVANCE_COGNITION

    def test_high_risk_tier_triggers_human_gate(self):
        """HIGH risk tier without explicit human gate → auto-gates, not executable."""
        state = ProjectStateSignal(
            active_task="task_001",
            risk_tier=PrimeActionRiskTier.HIGH,
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_executable() is False

    def test_medium_risk_does_not_auto_gate(self):
        """MEDIUM risk tier does not auto-trigger human gate."""
        state = ProjectStateSignal(
            active_task="task_001",
            risk_tier=PrimeActionRiskTier.MEDIUM,
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ADVANCE_COGNITION
        assert action.human_gate_required is False

    def test_priority_human_gate_before_blockers(self):
        """Human gate takes priority over blockers."""
        state = ProjectStateSignal(
            active_task="task_001",
            human_gate_required=True,
            blockers=frozenset(["something"]),
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True

    def test_priority_blockers_before_review_gate(self):
        """Blockers take priority over review gate."""
        state = ProjectStateSignal(
            active_task="task_001",
            blockers=frozenset(["service_down"]),
            review_gate_open=False,
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ESCALATE_ERROR

    def test_priority_review_gate_before_active_task(self):
        """Review gate takes priority over active task."""
        state = ProjectStateSignal(active_task="task_001", review_gate_open=False)
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT

    def test_priority_high_risk_before_review_gate(self):
        """HIGH risk tier gates before review gate check."""
        state = ProjectStateSignal(
            active_task="task_001",
            risk_tier=PrimeActionRiskTier.HIGH,
            review_gate_open=False,
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True  # came from high-risk, not review-gate

    def test_lane_id_propagated_to_action(self):
        """Lane ID is carried into the selected action."""
        state = ProjectStateSignal(active_task="task_001", lane_id="build-1")
        action = select_next_action_from_project_state(state)
        assert action.target_lane == "build-1"

    def test_active_task_advance_is_executable(self):
        """Normal active task with open gate is executable."""
        state = ProjectStateSignal(active_task="task_001")
        action = select_next_action_from_project_state(state)
        assert action.is_executable() is True

    def test_poll_session_is_executable(self):
        """Poll-session action (no active task) is executable."""
        state = ProjectStateSignal()
        action = select_next_action_from_project_state(state)
        assert action.is_executable() is True

    def test_echo_atlas_signal_fields_accepted(self):
        """Echo/Atlas signal placeholders are accepted without side effects."""
        state = ProjectStateSignal(
            active_task="task_001",
            echo_signal="recent_memory_key",
            atlas_signal="docs/live-build-1.md",
        )
        action = select_next_action_from_project_state(state)
        assert action.action_type == PrimeActionType.ADVANCE_COGNITION

    def test_existing_select_prime_next_action_unaffected(self):
        """Regression: existing select_prime_next_action still returns safe defaults."""
        action = select_prime_next_action()
        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK

    def test_existing_make_prime_next_action_unaffected(self):
        """Regression: existing make_prime_next_action still builds correctly."""
        action = make_prime_next_action(
            action_type=PrimeActionType.RUN_WORKFLOW,
            confidence=PrimeActionConfidence.MEDIUM,
        )
        assert action.action_type == PrimeActionType.RUN_WORKFLOW
        assert action.is_executable() is True


class TestSessionLifecycleAdvisorySelection:
    """Test Prime consumption of Session Lifecycle Prime/Beacon advisory state."""

    @pytest.fixture
    def advisory_session(self):
        """Create a session with valid task-scoped restart/resteer permission."""
        now = datetime.now(timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART, OperationScope.RESTEER]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
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
            status=SessionStatus.STALE,
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
            blocker_summary=None,
            permission_context=permission_context,
        )

    def _advisory_input(self, session, findings=(), approvals=()):
        return gather_prime_autonomy_input(
            sessions=[session],
            queues_by_harness={"build": ["docs/live-build-2.md"]},
            approvals_pending=list(approvals),
            restart_resteer_findings=list(findings),
            timestamp=datetime.now(timezone.utc),
        )

    def test_none_advisory_input_pauses_safely(self):
        """Missing Session Lifecycle advisory state falls back to safe pause."""
        action = select_next_action_from_session_lifecycle_advisory(None)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.target_harness == "Session Lifecycle"

    def test_restart_finding_becomes_human_gated_advisory(self, advisory_session):
        """Restart findings become advisory-only Prime actions, not live control."""
        finding = generate_restart_finding(advisory_session, threshold_seconds=1800)
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(advisory_session, findings=[finding])
        )

        assert action.action_type == PrimeActionType.ADVISE_SESSION_RECOVERY
        assert action.source == PrimeActionSource.SESSION_STATE
        assert action.risk_tier == PrimeActionRiskTier.HIGH
        assert action.human_gate_required is True
        assert action.is_executable() is False
        assert any("restart" in item for item in action.evidence)

    def test_resteer_finding_becomes_human_gated_advisory(self, advisory_session):
        """Resteer findings are consumable by Prime but remain gated."""
        blocked_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.BLOCKED,
                "blocker_summary": "queue assignment no longer matches task",
            }
        )
        finding = generate_resteer_finding(blocked_session)
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(blocked_session, findings=[finding])
        )

        assert action.action_type == PrimeActionType.ADVISE_SESSION_RECOVERY
        assert action.target_lane == blocked_session.session_id
        assert action.human_gate_required is True
        assert any("resteer" in item for item in action.evidence)

    def test_review_gate_blocks_session_recovery_advisory(self, advisory_session):
        """Review-gated sessions force human approval before recovery proceeds."""
        gated_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
            }
        )
        finding = generate_resteer_finding(gated_session, blocker="review gate pending")
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(gated_session, findings=[finding])
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_blocked()
        assert "review gate" in next(iter(action.blockers))

    def test_permission_boundary_blocks_recovery_advisory(self, advisory_session):
        """Expired or out-of-scope permissions block restart/resteer advice."""
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
        blocked_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "permission_context": expired_context,
            }
        )
        finding = generate_restart_finding(blocked_session, threshold_seconds=1800)
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(blocked_session, findings=[finding])
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_executable() is False
        assert any("permission boundary" in item for item in action.blockers)

    def test_no_recovery_findings_continues_watch_poll(self, advisory_session):
        """No findings keeps Prime on a safe Session Lifecycle watch path."""
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(advisory_session)
        )

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.is_executable() is True
