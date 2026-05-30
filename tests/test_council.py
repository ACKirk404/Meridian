"""Tests for Council cognition domain planning."""

from __future__ import annotations

from meridian_core.council import (
    CouncilPlan,
    CouncilPosition,
    CouncilRole,
    council_plan_for_tier,
    default_council_positions,
)
from meridian_core.risk import RiskTier, assess_tier


def test_default_positions_include_six_roles():
    positions = default_council_positions()
    assert len(positions) == 6
    assert {p.role for p in positions} == set(CouncilRole)


def test_default_positions_are_council_positions():
    assert all(isinstance(p, CouncilPosition) for p in default_council_positions())


def test_chairman_is_always_present():
    for tier in RiskTier:
        assert council_plan_for_tier(tier).includes(CouncilRole.CHAIRMAN)


def test_tier_0_uses_chairman_only():
    plan = council_plan_for_tier(0)
    assert plan.roles == [CouncilRole.CHAIRMAN]
    assert plan.requires_full_council is False


def test_tier_1_uses_pragmatist_and_chairman():
    plan = council_plan_for_tier(RiskTier.TIER_1)
    assert plan.roles == [CouncilRole.PRAGMATIST, CouncilRole.CHAIRMAN]


def test_tier_2_checks_evidence_assumptions_and_actionability():
    plan = council_plan_for_tier(RiskTier.TIER_2)
    assert plan.roles == [
        CouncilRole.ANALYST,
        CouncilRole.DEVILS_ADVOCATE,
        CouncilRole.PRAGMATIST,
        CouncilRole.CHAIRMAN,
    ]


def test_tier_3_uses_full_council():
    plan = council_plan_for_tier(RiskTier.TIER_3)
    assert plan.roles == list(CouncilRole)
    assert plan.requires_full_council is True


def test_tier_4_uses_full_council():
    plan = council_plan_for_tier(RiskTier.TIER_4)
    assert plan.roles == list(CouncilRole)
    assert plan.requires_full_council is True


def test_accepts_risk_assessment():
    assessment = assess_tier(RiskTier.TIER_3)
    plan = council_plan_for_tier(assessment)
    assert plan.risk_tier == 3
    assert plan.requires_full_council is True


def test_positions_match_roles_in_order():
    plan = council_plan_for_tier(RiskTier.TIER_2)
    assert [p.role for p in plan.positions] == plan.roles


def test_plan_is_council_plan():
    assert isinstance(council_plan_for_tier(2), CouncilPlan)


def test_plan_reason_is_human_readable():
    assert council_plan_for_tier(2).reason
