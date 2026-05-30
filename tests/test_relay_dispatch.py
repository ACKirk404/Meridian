"""Tests for the Relay dispatch plan domain model (meridian_core/relay_dispatch.py)."""

from __future__ import annotations

import pytest

from meridian_core.relay import ModelRole, RelayRoute, RoutingMode, route_from_tier
from meridian_core.relay_dispatch import (
    RelayDispatchLane,
    RelayDispatchPlan,
    build_relay_dispatch_plan,
)
from meridian_core.relay_packet import assemble_relay_packet


_PROMPT = "Evaluate the plan and produce a structured assessment."
_PACKET_ID = "DISPATCH-TEST-PKT"


def _make_route_and_packet(tier: int) -> tuple[RelayRoute, object]:
    route = route_from_tier(tier)
    packet = assemble_relay_packet(
        packet_id=_PACKET_ID,
        serialized_prompt=_PROMPT,
        route=route,
    )
    return route, packet


class TestBuildRelayDispatchPlanBasic:
    def test_returns_relay_dispatch_plan(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert isinstance(plan, RelayDispatchPlan)

    def test_route_stored(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.route is route

    def test_packet_stored(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.packet is packet

    def test_lanes_is_tuple(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert isinstance(plan.lanes, tuple)


class TestBuildRelayDispatchPlanLanes:
    def test_tier0_produces_empty_lanes(self):
        route, packet = _make_route_and_packet(0)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes == ()

    def test_tier1_produces_one_lane(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert len(plan.lanes) == 1

    def test_tier2_produces_two_lanes(self):
        route, packet = _make_route_and_packet(2)
        plan = build_relay_dispatch_plan(route, packet)
        assert len(plan.lanes) == 2

    def test_tier3_produces_three_lanes(self):
        route, packet = _make_route_and_packet(3)
        plan = build_relay_dispatch_plan(route, packet)
        assert len(plan.lanes) == 3

    def test_lane_count_matches_route_lanes(self):
        for tier in range(4):
            route, packet = _make_route_and_packet(tier)
            plan = build_relay_dispatch_plan(route, packet)
            assert len(plan.lanes) == len(route.lanes)

    def test_lane_order_preserved(self):
        route, packet = _make_route_and_packet(3)
        plan = build_relay_dispatch_plan(route, packet)
        for i, lane in enumerate(plan.lanes):
            assert lane.role == route.lanes[i].role

    def test_lane_role_correct(self):
        route, packet = _make_route_and_packet(2)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes[0].role == ModelRole.BUILDER
        assert plan.lanes[1].role == ModelRole.REVIEWER

    def test_lane_preferred_model_correct(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes[0].preferred_model == route.lanes[0].preferred_model

    def test_lane_independent_correct(self):
        route, packet = _make_route_and_packet(2)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes[0].independent == route.lanes[0].independent
        assert plan.lanes[1].independent == route.lanes[1].independent

    def test_lanes_are_relay_dispatch_lane_instances(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert isinstance(plan.lanes[0], RelayDispatchLane)


class TestBuildRelayDispatchPayload:
    def test_payload_is_model_payload(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes[0].payload == packet.model_payload()

    def test_payload_is_serialized_prompt(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert plan.lanes[0].payload == _PROMPT

    def test_payload_does_not_contain_packet_id(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        assert _PACKET_ID not in plan.lanes[0].payload

    def test_all_lanes_share_same_payload(self):
        route, packet = _make_route_and_packet(3)
        plan = build_relay_dispatch_plan(route, packet)
        payloads = {lane.payload for lane in plan.lanes}
        assert len(payloads) == 1

    def test_payload_exactly_equals_model_payload_no_extra(self):
        route, packet = _make_route_and_packet(2)
        plan = build_relay_dispatch_plan(route, packet)
        for lane in plan.lanes:
            assert lane.payload == packet.model_payload()
            assert len(lane.payload) == len(packet.model_payload())


class TestBuildRelayDispatchImmutability:
    def test_plan_is_frozen(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        with pytest.raises((AttributeError, TypeError)):
            plan.route = route_from_tier(2)  # type: ignore[misc]

    def test_lane_is_frozen(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        with pytest.raises((AttributeError, TypeError)):
            plan.lanes[0].payload = "mutated"  # type: ignore[misc]

    def test_lanes_tuple_is_immutable(self):
        route, packet = _make_route_and_packet(1)
        plan = build_relay_dispatch_plan(route, packet)
        with pytest.raises(TypeError):
            plan.lanes[0] = None  # type: ignore[index]

    def test_deterministic_repeated_calls(self):
        route, packet = _make_route_and_packet(2)
        plan1 = build_relay_dispatch_plan(route, packet)
        plan2 = build_relay_dispatch_plan(route, packet)
        assert len(plan1.lanes) == len(plan2.lanes)
        for l1, l2 in zip(plan1.lanes, plan2.lanes):
            assert l1.role == l2.role
            assert l1.payload == l2.payload
