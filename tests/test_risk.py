"""Tests for the Risk Tier Engine (meridian_core/risk.py)."""

from __future__ import annotations

import pytest

from meridian_core.intention import RiskTier
from meridian_core.risk import RiskAssessment, RiskMode, RiskRequirement, assess_tier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(assessment: RiskAssessment, label: str) -> RiskRequirement | None:
    for r in assessment.requirements:
        if r.label == label:
            return r
    return None


def _active(assessment: RiskAssessment, label: str) -> bool:
    r = _req(assessment, label)
    assert r is not None, f"Requirement '{label}' not found in assessment"
    return r.active


# ---------------------------------------------------------------------------
# Tier 0 — Deterministic
# ---------------------------------------------------------------------------


class TestTier0:
    def test_mode(self):
        assert assess_tier(0).mode is RiskMode.DETERMINISTIC

    def test_tier_number(self):
        assert assess_tier(0).tier == 0

    def test_no_dual_lane(self):
        assert assess_tier(0).requires_dual_lane is False

    def test_no_aegis_proof(self):
        assert assess_tier(0).requires_aegis_proof is False

    def test_no_human_gate(self):
        assert assess_tier(0).requires_human_gate is False

    def test_deterministic_requirement_active(self):
        assert _active(assess_tier(0), "Deterministic logic") is True

    def test_single_lane_inactive(self):
        assert _active(assess_tier(0), "Single-lane cognition") is False

    def test_dual_lane_inactive(self):
        assert _active(assess_tier(0), "Dual-lane cognition") is False

    def test_aegis_inactive(self):
        assert _active(assess_tier(0), "Aegis proof") is False

    def test_human_gate_inactive(self):
        assert _active(assess_tier(0), "Human gate") is False

    def test_has_escalation_triggers(self):
        assert len(assess_tier(0).escalation_triggers) > 0

    def test_reason_not_empty(self):
        assert assess_tier(0).reason


# ---------------------------------------------------------------------------
# Tier 1 — Single-lane cognition
# ---------------------------------------------------------------------------


class TestTier1:
    def test_mode(self):
        assert assess_tier(1).mode is RiskMode.SINGLE_LANE

    def test_tier_number(self):
        assert assess_tier(1).tier == 1

    def test_no_dual_lane(self):
        assert assess_tier(1).requires_dual_lane is False

    def test_no_aegis_proof(self):
        assert assess_tier(1).requires_aegis_proof is False

    def test_no_human_gate(self):
        assert assess_tier(1).requires_human_gate is False

    def test_single_lane_active(self):
        assert _active(assess_tier(1), "Single-lane cognition") is True

    def test_dual_lane_inactive(self):
        assert _active(assess_tier(1), "Dual-lane cognition") is False

    def test_aegis_inactive(self):
        assert _active(assess_tier(1), "Aegis proof") is False

    def test_human_gate_inactive(self):
        assert _active(assess_tier(1), "Human gate") is False


# ---------------------------------------------------------------------------
# Tier 2 — Dual-lane cognition
# ---------------------------------------------------------------------------


class TestTier2:
    def test_mode(self):
        assert assess_tier(2).mode is RiskMode.DUAL_LANE

    def test_tier_number(self):
        assert assess_tier(2).tier == 2

    def test_requires_dual_lane(self):
        assert assess_tier(2).requires_dual_lane is True

    def test_no_aegis_proof(self):
        assert assess_tier(2).requires_aegis_proof is False

    def test_no_human_gate(self):
        assert assess_tier(2).requires_human_gate is False

    def test_dual_lane_active(self):
        assert _active(assess_tier(2), "Dual-lane cognition") is True

    def test_two_candidate_paths_active(self):
        assert _active(assess_tier(2), "Two candidate paths") is True

    def test_prime_adjudication_active(self):
        assert _active(assess_tier(2), "Prime adjudication") is True

    def test_aegis_inactive(self):
        assert _active(assess_tier(2), "Aegis proof") is False

    def test_human_gate_inactive(self):
        assert _active(assess_tier(2), "Human gate") is False

    def test_has_escalation_triggers(self):
        assert len(assess_tier(2).escalation_triggers) > 0


# ---------------------------------------------------------------------------
# Tier 3 — Dual-lane + Aegis proof
# ---------------------------------------------------------------------------


class TestTier3:
    def test_mode(self):
        assert assess_tier(3).mode is RiskMode.DUAL_LANE_PROOF

    def test_tier_number(self):
        assert assess_tier(3).tier == 3

    def test_requires_dual_lane(self):
        assert assess_tier(3).requires_dual_lane is True

    def test_requires_aegis_proof(self):
        assert assess_tier(3).requires_aegis_proof is True

    def test_no_human_gate(self):
        assert assess_tier(3).requires_human_gate is False

    def test_dual_lane_active(self):
        assert _active(assess_tier(3), "Dual-lane cognition") is True

    def test_aegis_active(self):
        assert _active(assess_tier(3), "Aegis proof") is True

    def test_human_gate_inactive(self):
        assert _active(assess_tier(3), "Human gate") is False

    def test_has_escalation_triggers(self):
        assert len(assess_tier(3).escalation_triggers) > 0


# ---------------------------------------------------------------------------
# Tier 4 — Human gate
# ---------------------------------------------------------------------------


class TestTier4:
    def test_mode(self):
        assert assess_tier(4).mode is RiskMode.HUMAN_GATE

    def test_tier_number(self):
        assert assess_tier(4).tier == 4

    def test_requires_dual_lane(self):
        assert assess_tier(4).requires_dual_lane is True

    def test_requires_aegis_proof(self):
        assert assess_tier(4).requires_aegis_proof is True

    def test_requires_human_gate(self):
        assert assess_tier(4).requires_human_gate is True

    def test_dual_lane_active(self):
        assert _active(assess_tier(4), "Dual-lane cognition") is True

    def test_aegis_active(self):
        assert _active(assess_tier(4), "Aegis proof") is True

    def test_human_gate_active(self):
        assert _active(assess_tier(4), "Human gate") is True

    def test_prime_cannot_proceed_alone_active(self):
        assert _active(assess_tier(4), "Prime cannot proceed alone") is True

    def test_no_escalation_triggers(self):
        # ceiling tier — no higher tier exists
        assert assess_tier(4).escalation_triggers == []


# ---------------------------------------------------------------------------
# Blocked actions assess as Tier 4
# ---------------------------------------------------------------------------


class TestBlockedActionsTier4:
    def test_risk_tier_enum_tier4_maps_to_human_gate(self):
        result = assess_tier(RiskTier.TIER_4)
        assert result.requires_human_gate is True
        assert result.mode is RiskMode.HUMAN_GATE

    def test_risk_tier_enum_tier4_requires_dual_lane(self):
        result = assess_tier(RiskTier.TIER_4)
        assert result.requires_dual_lane is True

    def test_risk_tier_enum_tier4_requires_aegis_proof(self):
        result = assess_tier(RiskTier.TIER_4)
        assert result.requires_aegis_proof is True

    def test_blocked_reason_override(self):
        result = assess_tier(4, reason="action is blocked by human gate")
        assert result.reason == "action is blocked by human gate"
        assert result.requires_human_gate is True

    def test_blocked_tier_number(self):
        result = assess_tier(RiskTier.TIER_4)
        assert result.tier == 4


# ---------------------------------------------------------------------------
# assess_tier accepts RiskTier enum
# ---------------------------------------------------------------------------


class TestRiskTierEnumInput:
    @pytest.mark.parametrize("tier_enum,expected_tier", [
        (RiskTier.TIER_0, 0),
        (RiskTier.TIER_1, 1),
        (RiskTier.TIER_2, 2),
        (RiskTier.TIER_3, 3),
        (RiskTier.TIER_4, 4),
    ])
    def test_enum_maps_to_correct_tier(self, tier_enum, expected_tier):
        result = assess_tier(tier_enum)
        assert result.tier == expected_tier

    @pytest.mark.parametrize("tier_enum,expected_mode", [
        (RiskTier.TIER_0, RiskMode.DETERMINISTIC),
        (RiskTier.TIER_1, RiskMode.SINGLE_LANE),
        (RiskTier.TIER_2, RiskMode.DUAL_LANE),
        (RiskTier.TIER_3, RiskMode.DUAL_LANE_PROOF),
        (RiskTier.TIER_4, RiskMode.HUMAN_GATE),
    ])
    def test_enum_maps_to_correct_mode(self, tier_enum, expected_mode):
        assert assess_tier(tier_enum).mode is expected_mode


# ---------------------------------------------------------------------------
# Custom reason override
# ---------------------------------------------------------------------------


class TestReasonOverride:
    def test_custom_reason_replaces_default(self):
        result = assess_tier(2, reason="custom reason")
        assert result.reason == "custom reason"

    def test_none_reason_uses_default(self):
        default = assess_tier(2)
        explicit_none = assess_tier(2, reason=None)
        assert default.reason == explicit_none.reason

    def test_reason_override_does_not_change_mode(self):
        result = assess_tier(3, reason="high-stakes deployment")
        assert result.mode is RiskMode.DUAL_LANE_PROOF


# ---------------------------------------------------------------------------
# Determinism — identical calls return identical results
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_repeated_calls_are_identical(self, tier):
        a = assess_tier(tier)
        b = assess_tier(tier)
        assert a.tier == b.tier
        assert a.mode == b.mode
        assert a.reason == b.reason
        assert a.requires_dual_lane == b.requires_dual_lane
        assert a.requires_aegis_proof == b.requires_aegis_proof
        assert a.requires_human_gate == b.requires_human_gate
        assert [(r.label, r.active) for r in a.requirements] == [(r.label, r.active) for r in b.requirements]
        assert a.escalation_triggers == b.escalation_triggers

    def test_requirements_are_independent_copies(self):
        a = assess_tier(2)
        b = assess_tier(2)
        a.requirements[0].active = False
        assert b.requirements[0].active is True  # b is not affected


# ---------------------------------------------------------------------------
# Invalid tier
# ---------------------------------------------------------------------------


class TestInvalidTier:
    def test_negative_tier_raises(self):
        with pytest.raises(ValueError):
            assess_tier(-1)

    def test_tier_5_raises(self):
        with pytest.raises(ValueError):
            assess_tier(5)

    def test_error_message_includes_tier(self):
        with pytest.raises(ValueError, match="99"):
            assess_tier(99)
