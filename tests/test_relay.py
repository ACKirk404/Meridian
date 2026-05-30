"""Tests for Relay Routing (meridian_core/relay.py)."""

from __future__ import annotations

import pytest

from meridian_core.relay import (
    ContextStrategy,
    ModelRole,
    RelayRoute,
    RoutingMode,
    route,
)
from meridian_core.risk import RiskAssessment, RiskTier, assess_tier


# ---------------------------------------------------------------------------
# Tier 0 — no model lanes
# ---------------------------------------------------------------------------


class TestTier0Route:
    def test_mode(self):
        assert route(0).mode is RoutingMode.NO_MODEL

    def test_no_lanes(self):
        assert route(0).lanes == []

    def test_no_human_gate(self):
        assert route(0).requires_human_gate is False

    def test_no_independence_required(self):
        assert route(0).requires_independence is False

    def test_cost_posture(self):
        assert route(0).cost_posture == "none"

    def test_reason_not_empty(self):
        assert route(0).reason


# ---------------------------------------------------------------------------
# Tier 1 — one fast/cheap lane
# ---------------------------------------------------------------------------


class TestTier1Route:
    def test_mode(self):
        assert route(1).mode is RoutingMode.SINGLE_LANE

    def test_one_lane(self):
        assert len(route(1).lanes) == 1

    def test_lane_role_is_builder(self):
        assert route(1).lanes[0].role is ModelRole.BUILDER

    def test_lane_not_independent(self):
        assert route(1).lanes[0].independent is False

    def test_no_human_gate(self):
        assert route(1).requires_human_gate is False

    def test_no_independence_required(self):
        assert route(1).requires_independence is False

    def test_cost_posture(self):
        assert route(1).cost_posture == "minimal"


# ---------------------------------------------------------------------------
# Tier 2 — two independent lanes
# ---------------------------------------------------------------------------


class TestTier2Route:
    def test_mode(self):
        assert route(2).mode is RoutingMode.DUAL_LANE

    def test_two_lanes(self):
        assert len(route(2).lanes) == 2

    def test_builder_lane_exists(self):
        roles = [l.role for l in route(2).lanes]
        assert ModelRole.BUILDER in roles

    def test_reviewer_lane_exists(self):
        roles = [l.role for l in route(2).lanes]
        assert ModelRole.REVIEWER in roles

    def test_reviewer_is_independent(self):
        reviewer = next(l for l in route(2).lanes if l.role is ModelRole.REVIEWER)
        assert reviewer.independent is True

    def test_requires_independence(self):
        assert route(2).requires_independence is True

    def test_no_human_gate(self):
        assert route(2).requires_human_gate is False

    def test_cost_posture(self):
        assert route(2).cost_posture == "moderate"


# ---------------------------------------------------------------------------
# Tier 3 — two lanes plus proof/review posture
# ---------------------------------------------------------------------------


class TestTier3Route:
    def test_mode(self):
        assert route(3).mode is RoutingMode.DUAL_LANE_PROOF

    def test_three_lanes(self):
        assert len(route(3).lanes) == 3

    def test_builder_lane_exists(self):
        roles = [l.role for l in route(3).lanes]
        assert ModelRole.BUILDER in roles

    def test_reviewer_lane_exists(self):
        roles = [l.role for l in route(3).lanes]
        assert ModelRole.REVIEWER in roles

    def test_proof_lane_exists(self):
        roles = [l.role for l in route(3).lanes]
        assert ModelRole.PROOF in roles

    def test_proof_lane_is_independent(self):
        proof = next(l for l in route(3).lanes if l.role is ModelRole.PROOF)
        assert proof.independent is True

    def test_reviewer_is_independent(self):
        reviewer = next(l for l in route(3).lanes if l.role is ModelRole.REVIEWER)
        assert reviewer.independent is True

    def test_requires_independence(self):
        assert route(3).requires_independence is True

    def test_no_human_gate(self):
        assert route(3).requires_human_gate is False

    def test_cost_posture(self):
        assert route(3).cost_posture == "high"


# ---------------------------------------------------------------------------
# Tier 4 — human gate required before execution
# ---------------------------------------------------------------------------


class TestTier4Route:
    def test_mode(self):
        assert route(4).mode is RoutingMode.HUMAN_GATE

    def test_requires_human_gate(self):
        assert route(4).requires_human_gate is True

    def test_explainer_lane_exists(self):
        roles = [l.role for l in route(4).lanes]
        assert ModelRole.EXPLAINER in roles

    def test_no_builder_lane(self):
        roles = [l.role for l in route(4).lanes]
        assert ModelRole.BUILDER not in roles

    def test_cost_posture_deferred(self):
        assert route(4).cost_posture == "deferred"

    def test_reason_mentions_human_gate(self):
        assert "human gate" in route(4).reason


# ---------------------------------------------------------------------------
# Context strategy — focused packet is the default
# ---------------------------------------------------------------------------


class TestContextStrategy:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_default_is_focused_packet(self, tier):
        assert route(tier).context_strategy is ContextStrategy.FOCUSED_PACKET

    def test_reuse_session_override(self):
        r = route(2, context_strategy=ContextStrategy.REUSE_SESSION)
        assert r.context_strategy is ContextStrategy.REUSE_SESSION

    def test_summarize_and_reset_override(self):
        r = route(2, context_strategy=ContextStrategy.SUMMARIZE_AND_RESET)
        assert r.context_strategy is ContextStrategy.SUMMARIZE_AND_RESET

    def test_large_context_override(self):
        r = route(3, context_strategy=ContextStrategy.LARGE_CONTEXT)
        assert r.context_strategy is ContextStrategy.LARGE_CONTEXT


# ---------------------------------------------------------------------------
# RiskTier enum input
# ---------------------------------------------------------------------------


class TestRiskTierEnumInput:
    @pytest.mark.parametrize("tier_enum,expected_mode", [
        (RiskTier.TIER_0, RoutingMode.NO_MODEL),
        (RiskTier.TIER_1, RoutingMode.SINGLE_LANE),
        (RiskTier.TIER_2, RoutingMode.DUAL_LANE),
        (RiskTier.TIER_3, RoutingMode.DUAL_LANE_PROOF),
        (RiskTier.TIER_4, RoutingMode.HUMAN_GATE),
    ])
    def test_enum_maps_to_correct_mode(self, tier_enum, expected_mode):
        assert route(tier_enum).mode is expected_mode


# ---------------------------------------------------------------------------
# RiskAssessment input
# ---------------------------------------------------------------------------


class TestRiskAssessmentInput:
    def test_assessment_routes_correctly(self):
        assessment = assess_tier(2)
        r = route(assessment)
        assert r.mode is RoutingMode.DUAL_LANE

    def test_assessment_attached_to_route(self):
        assessment = assess_tier(3)
        r = route(assessment)
        assert r.assessment is assessment

    def test_assessment_human_gate_propagates(self):
        assessment = assess_tier(4)
        r = route(assessment)
        assert r.requires_human_gate is True


# ---------------------------------------------------------------------------
# Custom reason override
# ---------------------------------------------------------------------------


class TestReasonOverride:
    def test_custom_reason_replaces_default(self):
        r = route(2, reason="deploying to staging")
        assert r.reason == "deploying to staging"

    def test_none_reason_uses_default(self):
        r1 = route(2)
        r2 = route(2, reason=None)
        assert r1.reason == r2.reason

    def test_reason_override_does_not_change_mode(self):
        r = route(3, reason="high-stakes deploy")
        assert r.mode is RoutingMode.DUAL_LANE_PROOF


# ---------------------------------------------------------------------------
# Determinism — identical calls return identical results
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_repeated_calls_are_identical(self, tier):
        a = route(tier)
        b = route(tier)
        assert a.mode == b.mode
        assert a.cost_posture == b.cost_posture
        assert a.requires_independence == b.requires_independence
        assert a.requires_human_gate == b.requires_human_gate
        assert a.context_strategy == b.context_strategy
        assert a.reason == b.reason
        assert [(l.role, l.model_label, l.independent) for l in a.lanes] == \
               [(l.role, l.model_label, l.independent) for l in b.lanes]

    def test_lanes_are_independent_copies(self):
        a = route(2)
        b = route(2)
        a.lanes[0].model_label = "mutated"
        assert b.lanes[0].model_label != "mutated"

    def test_assessment_is_fresh_each_call(self):
        a = route(1)
        b = route(1)
        assert a.assessment is not b.assessment
