"""Tests for the Relay Routing slice (meridian_core/relay.py)."""

from __future__ import annotations

import pytest

from meridian_core.council import CouncilPlan, CouncilRole
from meridian_core.relay import (
    ContextStrategy,
    CostPosture,
    ModelRole,
    RelayLane,
    RelayRoute,
    RoutingMode,
    route_from_assessment,
    route_from_tier,
)
from meridian_core.risk import RiskTier, assess_tier


# ---------------------------------------------------------------------------
# Tier 0 -- no model lanes
# ---------------------------------------------------------------------------


class TestTier0Route:
    def test_mode_is_no_model(self):
        assert route_from_tier(0).mode is RoutingMode.NO_MODEL

    def test_no_lanes(self):
        assert route_from_tier(0).lanes == []

    def test_no_human_gate(self):
        assert route_from_tier(0).requires_human_gate is False

    def test_no_independence_required(self):
        assert route_from_tier(0).requires_independence is False

    def test_cost_posture_is_minimal(self):
        assert route_from_tier(0).cost_posture is CostPosture.MINIMAL


# ---------------------------------------------------------------------------
# Tier 1 -- one lane
# ---------------------------------------------------------------------------


class TestTier1Route:
    def test_mode_is_single_lane(self):
        assert route_from_tier(1).mode is RoutingMode.SINGLE_LANE

    def test_exactly_one_lane(self):
        assert len(route_from_tier(1).lanes) == 1

    def test_lane_role_is_builder(self):
        assert route_from_tier(1).lanes[0].role is ModelRole.BUILDER

    def test_lane_is_not_independent(self):
        assert route_from_tier(1).lanes[0].independent is False

    def test_no_human_gate(self):
        assert route_from_tier(1).requires_human_gate is False

    def test_no_independence_required(self):
        assert route_from_tier(1).requires_independence is False

    def test_cost_posture_is_minimal(self):
        assert route_from_tier(1).cost_posture is CostPosture.MINIMAL


# ---------------------------------------------------------------------------
# Tier 2 -- two independent lanes
# ---------------------------------------------------------------------------


class TestTier2Route:
    def test_mode_is_dual_lane(self):
        assert route_from_tier(2).mode is RoutingMode.DUAL_LANE

    def test_exactly_two_lanes(self):
        assert len(route_from_tier(2).lanes) == 2

    def test_has_builder_lane(self):
        roles = [l.role for l in route_from_tier(2).lanes]
        assert ModelRole.BUILDER in roles

    def test_has_reviewer_lane(self):
        roles = [l.role for l in route_from_tier(2).lanes]
        assert ModelRole.REVIEWER in roles

    def test_reviewer_lane_is_independent(self):
        reviewer = next(l for l in route_from_tier(2).lanes if l.role is ModelRole.REVIEWER)
        assert reviewer.independent is True

    def test_requires_independence(self):
        assert route_from_tier(2).requires_independence is True

    def test_no_human_gate(self):
        assert route_from_tier(2).requires_human_gate is False

    def test_cost_posture_is_standard(self):
        assert route_from_tier(2).cost_posture is CostPosture.STANDARD


# ---------------------------------------------------------------------------
# Tier 3 -- two lanes plus proof/review posture
# ---------------------------------------------------------------------------


class TestTier3Route:
    def test_mode_is_dual_lane_proof(self):
        assert route_from_tier(3).mode is RoutingMode.DUAL_LANE_PROOF

    def test_has_builder_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.BUILDER in roles

    def test_has_reviewer_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.REVIEWER in roles

    def test_has_verifier_lane(self):
        roles = [l.role for l in route_from_tier(3).lanes]
        assert ModelRole.VERIFIER in roles

    def test_verifier_lane_is_independent(self):
        verifier = next(l for l in route_from_tier(3).lanes if l.role is ModelRole.VERIFIER)
        assert verifier.independent is True

    def test_requires_independence(self):
        assert route_from_tier(3).requires_independence is True

    def test_no_human_gate(self):
        assert route_from_tier(3).requires_human_gate is False

    def test_cost_posture_is_thorough(self):
        assert route_from_tier(3).cost_posture is CostPosture.THOROUGH


# ---------------------------------------------------------------------------
# Tier 4 -- human gate required before execution
# ---------------------------------------------------------------------------


class TestTier4Route:
    def test_mode_is_human_gate(self):
        assert route_from_tier(4).mode is RoutingMode.HUMAN_GATE

    def test_requires_human_gate(self):
        assert route_from_tier(4).requires_human_gate is True

    def test_has_explainer_lane(self):
        roles = [l.role for l in route_from_tier(4).lanes]
        assert ModelRole.EXPLAINER in roles

    def test_no_builder_lane(self):
        roles = [l.role for l in route_from_tier(4).lanes]
        assert ModelRole.BUILDER not in roles

    def test_risk_tier_is_4(self):
        assert route_from_tier(4).risk_tier == 4


# ---------------------------------------------------------------------------
# Default context strategy is focused packet
# ---------------------------------------------------------------------------


class TestContextStrategy:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_default_is_focused_packet(self, tier):
        assert route_from_tier(tier).context_strategy is ContextStrategy.FOCUSED_PACKET

    def test_context_strategy_override_via_assessment(self):
        assessment = assess_tier(2)
        route = route_from_assessment(assessment, context_strategy=ContextStrategy.REUSE_SESSION)
        assert route.context_strategy is ContextStrategy.REUSE_SESSION

    def test_large_context_accepted(self):
        route = route_from_assessment(assess_tier(3), context_strategy=ContextStrategy.LARGE_CONTEXT)
        assert route.context_strategy is ContextStrategy.LARGE_CONTEXT


# ---------------------------------------------------------------------------
# route_from_assessment and route_from_tier consistency
# ---------------------------------------------------------------------------


class TestRouteFromAssessment:
    def test_matches_route_from_tier(self):
        for tier_num in range(5):
            assessment = assess_tier(tier_num)
            r1 = route_from_assessment(assessment)
            r2 = route_from_tier(tier_num)
            assert r1.mode == r2.mode
            assert r1.requires_human_gate == r2.requires_human_gate
            assert r1.requires_independence == r2.requires_independence
            assert len(r1.lanes) == len(r2.lanes)

    def test_risk_tier_preserved(self):
        for tier_num in range(5):
            assert route_from_tier(tier_num).risk_tier == tier_num

    def test_enum_tier_accepted(self):
        for tier_enum in RiskTier:
            route = route_from_tier(tier_enum)
            assert route.risk_tier == tier_enum.value

    def test_reason_not_empty(self):
        for tier_num in range(5):
            assert route_from_tier(tier_num).reason


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.mark.parametrize("tier", [0, 1, 2, 3, 4])
    def test_identical_calls_produce_identical_routes(self, tier):
        r1 = route_from_tier(tier)
        r2 = route_from_tier(tier)
        assert r1.mode == r2.mode
        assert r1.requires_human_gate == r2.requires_human_gate
        assert r1.requires_independence == r2.requires_independence
        assert r1.cost_posture == r2.cost_posture
        assert r1.context_strategy == r2.context_strategy
        assert [(l.role, l.preferred_model, l.independent) for l in r1.lanes] == \
               [(l.role, l.preferred_model, l.independent) for l in r2.lanes]

    def test_lanes_are_independent_copies(self):
        r1 = route_from_tier(2)
        r2 = route_from_tier(2)
        r1.lanes[0].preferred_model = "mutated"
        assert r2.lanes[0].preferred_model != "mutated"


# ---------------------------------------------------------------------------
# Shape checks
# ---------------------------------------------------------------------------


class TestShape:
    def test_result_is_relay_route(self):
        assert isinstance(route_from_tier(2), RelayRoute)

    def test_lanes_are_relay_lane_instances(self):
        for lane in route_from_tier(3).lanes:
            assert isinstance(lane, RelayLane)

    def test_mode_is_routing_mode_enum(self):
        assert isinstance(route_from_tier(1).mode, RoutingMode)

    def test_context_strategy_is_enum(self):
        assert isinstance(route_from_tier(1).context_strategy, ContextStrategy)

    def test_cost_posture_is_enum(self):
        assert isinstance(route_from_tier(1).cost_posture, CostPosture)


# ---------------------------------------------------------------------------
# Council awareness -- RelayRoute exposes council_plan per tier
# ---------------------------------------------------------------------------


class TestCouncilAwareness:
    def test_council_plan_is_council_plan_instance(self):
        for tier in range(5):
            assert isinstance(route_from_tier(tier).council_plan, CouncilPlan)

    def test_tier0_includes_chairman_only(self):
        plan = route_from_tier(0).council_plan
        assert plan.roles == [CouncilRole.CHAIRMAN]

    def test_tier1_includes_pragmatist_and_chairman(self):
        plan = route_from_tier(1).council_plan
        assert CouncilRole.PRAGMATIST in plan.roles
        assert CouncilRole.CHAIRMAN in plan.roles
        assert len(plan.roles) == 2

    def test_tier2_includes_analyst_devils_advocate_pragmatist_chairman(self):
        plan = route_from_tier(2).council_plan
        assert CouncilRole.ANALYST in plan.roles
        assert CouncilRole.DEVILS_ADVOCATE in plan.roles
        assert CouncilRole.PRAGMATIST in plan.roles
        assert CouncilRole.CHAIRMAN in plan.roles
        assert len(plan.roles) == 4

    def test_tier3_requires_full_council(self):
        plan = route_from_tier(3).council_plan
        assert plan.requires_full_council is True
        assert len(plan.roles) == len(CouncilRole)

    def test_tier4_requires_full_council(self):
        plan = route_from_tier(4).council_plan
        assert plan.requires_full_council is True
        assert len(plan.roles) == len(CouncilRole)

    def test_council_risk_tier_matches_route_risk_tier(self):
        for tier in range(5):
            route = route_from_tier(tier)
            assert route.council_plan.risk_tier == route.risk_tier

    def test_council_plan_populated_via_assessment(self):
        from meridian_core.risk import assess_tier
        assessment = assess_tier(2)
        route = route_from_assessment(assessment)
        assert isinstance(route.council_plan, CouncilPlan)
        assert CouncilRole.ANALYST in route.council_plan.roles
