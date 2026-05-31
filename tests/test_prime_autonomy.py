"""Tests for Prime Autonomy domain model."""

import pytest
from meridian_core.prime_autonomy import (
    PrimeActionType,
    PrimeActionConfidence,
    PrimeActionRiskTier,
    PrimeActionSource,
    PrimeNextAction,
    select_prime_next_action,
    make_prime_next_action,
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
