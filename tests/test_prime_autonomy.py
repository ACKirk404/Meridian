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
    select_next_action_from_command_plan_audit,
    select_next_action_from_session_lifecycle_advisory,
    select_next_action_from_runtime_state_export,
    select_next_action_from_workflow_recovery_summary,
)
from meridian_core.session_lifecycle import (
    CommandIntent,
    HealthState,
    HarnessRole,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionAction,
    SessionCommandPlan,
    SessionLifecycleState,
    SessionStatus,
    export_session_runtime_state_for_workflow_recovery,
    gather_prime_autonomy_input,
    generate_restart_finding,
    generate_resteer_finding,
    summarize_workflow_work_order_recovery,
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
        assert any("review gate" in item for item in action.blockers)

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
        assert any("permission.unlock_expired" in item for item in action.evidence)

    def test_permission_summary_finding_becomes_recovery_advisory(self, advisory_session):
        """Summary-generated stale findings can drive advisory recovery decisions."""
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(advisory_session)
        )

        assert action.action_type == PrimeActionType.ADVISE_SESSION_RECOVERY
        assert action.target_lane == advisory_session.session_id
        assert action.human_gate_required is True
        assert any("finding.restart" in item for item in action.evidence)
        assert any("permission.approved_operations=restart,resteer" in item for item in action.evidence)

    def test_permission_summary_blockers_pause_summary_recovery(self, advisory_session):
        """Summary permission blockers pause recovery even without top-level findings."""
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=datetime.now(timezone.utc) - timedelta(minutes=1),
            task_scope="task-1",
            last_permission_change=datetime.now(timezone.utc),
        )
        blocked_session = SessionLifecycleState(
            **{**advisory_session.__dict__, "permission_context": expired_context}
        )

        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(blocked_session)
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert any("permission.unlock_expired" in item for item in action.blockers)
        assert any("finding.restart" in item for item in action.evidence)

    def test_no_recovery_findings_continues_watch_poll(self, advisory_session):
        """No findings keeps Prime on a safe Session Lifecycle watch path."""
        fresh_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.POLLING,
                "health_state": HealthState.HEALTHY,
                "last_prompt_sent_at": datetime.now(timezone.utc),
            }
        )
        action = select_next_action_from_session_lifecycle_advisory(
            self._advisory_input(fresh_session)
        )

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.is_executable() is True

    def test_none_workflow_recovery_summary_pauses_safely(self):
        """Missing workflow recovery summaries fall back to safe pause."""
        action = select_next_action_from_workflow_recovery_summary(None)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.target_harness == "Session Lifecycle"

    def test_workflow_stale_summary_becomes_recovery_advisory(self, advisory_session):
        """Stale workflow heartbeat summaries advise recovery without execution."""
        observed_at = datetime.now(timezone.utc)
        summary = summarize_workflow_work_order_recovery(
            advisory_session,
            work_order_id="wo-prime-stale",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )

        action = select_next_action_from_workflow_recovery_summary(summary)

        assert action.action_type == PrimeActionType.ADVISE_SESSION_RECOVERY
        assert action.source == PrimeActionSource.WORKFLOW_RESULT
        assert action.target_lane == advisory_session.session_id
        assert action.human_gate_required is True
        assert "workflow.recovery_action=start_new" in action.evidence
        assert any("work_order.id=wo-prime-stale" in item for item in action.evidence)

    def test_workflow_permission_blockers_pause_prime_advisory(self, advisory_session):
        """Workflow summaries with permission blockers pause for human gate."""
        observed_at = datetime.now(timezone.utc)
        expired_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=observed_at - timedelta(minutes=1),
            task_scope="task-1",
            last_permission_change=observed_at,
        )
        blocked_session = SessionLifecycleState(
            **{**advisory_session.__dict__, "permission_context": expired_context}
        )
        summary = summarize_workflow_work_order_recovery(
            blocked_session,
            work_order_id="wo-prime-blocked",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )

        action = select_next_action_from_workflow_recovery_summary(summary)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert "permission.unlock_expired" in action.blockers
        assert "blocker=permission.unlock_expired" in action.evidence

    def test_workflow_fresh_summary_continues_polling(self, advisory_session):
        """Fresh workflow heartbeat summaries keep Prime on watch/poll."""
        observed_at = datetime.now(timezone.utc)
        fresh_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.RUNNING,
                "health_state": HealthState.HEALTHY,
                "last_prompt_sent_at": observed_at,
            }
        )
        summary = summarize_workflow_work_order_recovery(
            fresh_session,
            work_order_id="wo-prime-fresh",
            heartbeat_emitted_at=observed_at - timedelta(seconds=10),
            timestamp=observed_at,
        )

        action = select_next_action_from_workflow_recovery_summary(summary)

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert "workflow.recovery_action=reuse" in action.evidence

    def test_none_runtime_state_export_pauses_safely(self):
        """Missing runtime-state exports fall back to safe pause."""
        action = select_next_action_from_runtime_state_export(None)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.target_harness == "Session Lifecycle"

    def test_runtime_state_export_blockers_pause_prime_advisory(
        self,
        advisory_session,
    ):
        """Runtime exports preserve permission/review blockers for Prime."""
        observed_at = datetime.now(timezone.utc)
        gated_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.REVIEW_GATED,
                "review_cadence_state": ReviewCadenceState.REVIEW_GATED,
            }
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            gated_session,
            work_order_id="wo-runtime-gated",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            gated_session,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        action = select_next_action_from_runtime_state_export(runtime_export)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.source == PrimeActionSource.SESSION_STATE
        assert action.human_gate_required is True
        assert "review_gate.status=review_gated" in action.blockers
        assert "runtime.recovery_action=request_human_gate" in action.evidence
        assert "runtime.command_kind=none" in action.evidence

    def test_runtime_state_export_recovery_remains_advisory(self, advisory_session):
        """Runtime exports can advise recovery but never become executable."""
        observed_at = datetime.now(timezone.utc)
        workflow_summary = summarize_workflow_work_order_recovery(
            advisory_session,
            work_order_id="wo-runtime-prime",
            heartbeat_emitted_at=observed_at - timedelta(minutes=10),
            heartbeat_stale_after_seconds=300,
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            advisory_session,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        action = select_next_action_from_runtime_state_export(runtime_export)

        assert runtime_export.recommended_recovery_action == SessionAction.START_NEW
        assert action.action_type == PrimeActionType.ADVISE_SESSION_RECOVERY
        assert action.target_lane == advisory_session.session_id
        assert action.human_gate_required is True
        assert action.is_executable() is False
        assert "advisory only; runtime-state recovery command plan required" in (
            action.blockers
        )

    def test_runtime_state_export_reuse_continues_polling(self, advisory_session):
        """Runtime exports with reuse advice keep Prime on the safe watch path."""
        observed_at = datetime.now(timezone.utc)
        fresh_session = SessionLifecycleState(
            **{
                **advisory_session.__dict__,
                "status": SessionStatus.RUNNING,
                "health_state": HealthState.HEALTHY,
                "last_prompt_sent_at": observed_at,
            }
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            fresh_session,
            work_order_id="wo-runtime-fresh",
            heartbeat_emitted_at=observed_at - timedelta(seconds=10),
            timestamp=observed_at,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            fresh_session,
            workflow_recovery_summary=workflow_summary,
            timestamp=observed_at,
        )

        action = select_next_action_from_runtime_state_export(runtime_export)

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.is_executable() is True
        assert "runtime.recovery_action=reuse" in action.evidence


class TestCommandPlanAuditAdvisorySelection:
    """Test Prime consumption of SessionCommandPlan audit evidence."""

    @pytest.fixture
    def poll_plan(self):
        """Create an executable command plan with audit evidence."""
        return SessionCommandPlan(
            session_id="session-audit",
            session_name="Build 2 Audit",
            command_intent=CommandIntent.POLL_QUEUE,
            reason="Poll queue after review clearance",
            expected_state_transition=(SessionStatus.POLLING, SessionStatus.POLLING),
            current_state_evidence="typed state snapshot",
            queue_file_evidence="docs/live-build-2.md",
            worktree_evidence="/worktree/build-2",
            review_gate_evidence=None,
            proof_requirement=ProofState.QUEUE_READ,
            queue_file_affected="docs/live-build-2.md",
            worktree_path_affected="/worktree/build-2",
            branch_affected="codex/aligned-build-2-prime-audit",
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=True,
            human_approval_required=False,
            approval_context=None,
            rollback_or_recovery_note="No recovery needed.",
        )

    def test_none_command_audit_pauses_safely(self):
        """Missing audit evidence falls back to safe pause."""
        action = select_next_action_from_command_plan_audit()

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.confidence == PrimeActionConfidence.FALLBACK
        assert action.target_harness == "Session Lifecycle"

    def test_executable_poll_audit_becomes_poll_session(self, poll_plan):
        """Executable poll_queue audit evidence maps to Prime POLL_SESSION."""
        action = select_next_action_from_command_plan_audit(command_plan=poll_plan)

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.risk_tier == PrimeActionRiskTier.SAFE
        assert action.target_lane == poll_plan.session_id
        assert action.is_executable() is True
        assert "plan.action=poll_queue" in action.evidence
        assert "permission.proof=queue_read" in action.evidence

    def test_serialized_audit_evidence_becomes_prime_evidence(self, poll_plan):
        """Serialized audit_evidence is enough for Prime-facing advisory data."""
        action = select_next_action_from_command_plan_audit(
            audit_evidence=poll_plan.to_dict()["audit_evidence"]
        )

        assert action.action_type == PrimeActionType.POLL_SESSION
        assert action.target_lane is None
        assert "plan.reason=Poll queue after review clearance" in action.evidence
        assert "recovery.note=No recovery needed." in action.evidence

    def test_human_gated_audit_blocks_prime_execution(self, poll_plan):
        """Human-gated command audits become blocked Prime pause actions."""
        gated_plan = SessionCommandPlan(
            **{
                **poll_plan.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "reason": "review_gate",
                "review_gate_evidence": "review gate pending",
                "cadence_gate_required": True,
                "cadence_gate_status": ReviewCadenceState.REVIEW_GATED,
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "human review approval required",
            }
        )
        action = select_next_action_from_command_plan_audit(command_plan=gated_plan)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_executable() is False
        assert "blocker=human_approval_required" in action.evidence
        assert "human review approval required" in action.blockers

    def test_permission_boundary_audit_stays_display_safe(self, poll_plan):
        """Permission-boundary audit metadata becomes evidence, not execution."""
        blocked_plan = SessionCommandPlan(
            **{
                **poll_plan.__dict__,
                "command_intent": CommandIntent.REQUEST_HUMAN_GATE,
                "reason": "permission_boundary",
                "proof_requirement": ProofState.PERMISSION_VALIDATED,
                "is_executable_now": False,
                "human_approval_required": True,
                "approval_context": "permission boundary blocks restart",
            }
        )
        action = select_next_action_from_command_plan_audit(
            audit_evidence=blocked_plan.audit_evidence()
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.risk_tier == PrimeActionRiskTier.HIGH
        assert "permission.proof=permission_validated" in action.evidence
        assert "blocker=permission boundary blocks restart" in action.evidence
        assert action.target_harness == "Session Lifecycle"

    def test_permission_operation_evidence_surfaces_to_prime(self, poll_plan):
        """Permission operation metadata becomes Prime advisory evidence."""
        restart_plan = SessionCommandPlan(
            **{
                **poll_plan.__dict__,
                "command_intent": CommandIntent.RESTART,
                "reason": "stale_heartbeat",
                "proof_requirement": ProofState.PERMISSION_VALIDATED,
                "is_executable_now": False,
                "human_approval_required": True,
                "permission_state": PermissionState.UNLOCKED_TEMPORARY,
                "permission_task_scope": "permission-evidence-slice",
                "permission_approved_operations": (OperationScope.RESTART,),
                "permission_operation": OperationScope.RESTART,
                "permission_operation_allowed": True,
                "permission_evidence": "unlocked_temporary:permission-evidence-slice",
            }
        )

        action = select_next_action_from_command_plan_audit(command_plan=restart_plan)

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert "permission.state=unlocked_temporary" in action.evidence
        assert "permission.task_scope=permission-evidence-slice" in action.evidence
        assert "permission.operation=restart" in action.evidence
        assert "permission.operation_allowed=True" in action.evidence
        assert (
            "permission.evidence=unlocked_temporary:permission-evidence-slice"
            in action.evidence
        )

    def test_permission_operation_blocker_surfaces_to_prime(self, poll_plan):
        """Missing movement permission remains a Prime blocker."""
        movement_plan = SessionCommandPlan(
            **{
                **poll_plan.__dict__,
                "command_intent": CommandIntent.SPAWN,
                "reason": "reasoning_shift",
                "permission_state": PermissionState.UNLOCKED_TEMPORARY,
                "permission_task_scope": "permission-evidence-slice",
                "permission_approved_operations": (OperationScope.RESTART,),
                "permission_operation": OperationScope.WORKTREE_CREATE,
                "permission_operation_allowed": False,
                "permission_evidence": "unlocked_temporary:permission-evidence-slice",
            }
        )

        action = select_next_action_from_command_plan_audit(
            audit_evidence=movement_plan.audit_evidence()
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert "permission_required_for_worktree_create" in action.blockers
        assert "blocker=permission_required_for_worktree_create" in action.evidence
        assert "permission.operation_allowed=False" in action.evidence

    def test_malformed_serialized_audit_pauses_safely(self):
        """Malformed serialized audit evidence cannot become executable."""
        action = select_next_action_from_command_plan_audit(
            audit_evidence={"plan": "not-a-dict", "blockers": "not-a-list"}
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.risk_tier == PrimeActionRiskTier.HIGH
        assert action.is_executable() is False
        assert "not_executable_now" in action.blockers
        assert "plan.action=unknown" in action.evidence
        assert "plan.executable=False" in action.evidence

    def test_string_false_executable_does_not_become_true(self):
        """Serialized string booleans are parsed deterministically."""
        action = select_next_action_from_command_plan_audit(
            audit_evidence={
                "plan": {
                    "action": "poll_queue",
                    "reason": "serialized false executable",
                    "is_executable": "false",
                },
                "review_gate": {"human_approval_required": "false"},
            }
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is False
        assert action.is_executable() is False
        assert "not_executable_now" in action.blockers
        assert "plan.executable=False" in action.evidence

    def test_string_true_human_gate_blocks_execution(self):
        """Serialized human-gate truth blocks Prime advisory execution."""
        action = select_next_action_from_command_plan_audit(
            audit_evidence={
                "plan": {
                    "action": "restart",
                    "reason": "review gate",
                    "is_executable": "true",
                },
                "review_gate": {
                    "human_approval_required": "true",
                    "cadence_gate_required": "true",
                    "cadence_gate_status": "review_gated",
                },
                "blockers": ["human_approval_required"],
            }
        )

        assert action.action_type == PrimeActionType.PAUSE_AND_WAIT
        assert action.human_gate_required is True
        assert action.is_executable() is False
        assert "review.required=True" in action.evidence
        assert "blocker=human_approval_required" in action.evidence

    def test_evidence_string_format_is_deterministic(self, poll_plan):
        """Prime evidence strings retain stable order and key formatting."""
        action = select_next_action_from_command_plan_audit(command_plan=poll_plan)

        assert action.evidence == frozenset(
            [
                "plan.action=poll_queue",
                "plan.reason=Poll queue after review clearance",
                "plan.executable=True",
                "permission.proof=queue_read",
                "permission.branch=codex/aligned-build-2-prime-audit",
                "review.required=False",
                "review.status=none",
                "recovery.note=No recovery needed.",
            ]
        )
