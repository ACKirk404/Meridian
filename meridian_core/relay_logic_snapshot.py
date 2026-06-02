"""Serializable Relay model-routing logic snapshot for UI harnesses."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from .relay import route_from_tier
from .relay_dispatch import build_relay_dispatch_plan
from .relay_packet import assemble_relay_packet


SNAPSHOT_VERSION = "relay-domain-v1"
SNAPSHOT_SOURCE = "meridian_core.relay.route_from_tier"
DISPATCH_SOURCE = "meridian_core.relay_dispatch.build_relay_dispatch_plan"
SNAPSHOT_PROMPT = "Relay dispatch snapshot placeholder."


def _value(item: Any) -> Any:
    if isinstance(item, Enum):
        return item.value
    return item


def _tuple_values(items: tuple[Any, ...]) -> list[Any]:
    return [_value(item) for item in items]


def _lane_snapshot(lane: Any) -> dict[str, Any]:
    return {
        "role": _value(lane.role),
        "preferredModel": lane.preferred_model,
        "independent": lane.independent,
    }


def _prompt_budget_snapshot(route: Any) -> dict[str, Any]:
    budget = route.prompt_budget
    return {
        "tier": _value(budget.tier),
        "maxContextTokens": budget.max_context_tokens,
        "allowedSources": list(budget.allowed_sources),
        "reason": budget.reason,
    }


def _audit_snapshot(route: Any) -> dict[str, Any]:
    audit = route.audit
    return {
        "routeKind": _value(audit.route_kind),
        "routeClass": _value(audit.route_class),
        "sessionAction": _value(audit.session_action),
        "trustState": _value(audit.trust_state),
        "routePrecedence": _tuple_values(audit.route_precedence),
        "alternativesRejected": list(audit.alternatives_rejected),
        "fallbackBlockers": list(audit.fallback_blockers),
        "proofRequired": list(audit.proof_required),
        "telemetryRequired": list(audit.telemetry_required),
    }


def _audit_depth_snapshot(route: Any) -> dict[str, Any]:
    audit = route.audit
    fallback_blockers = list(audit.fallback_blockers)
    alternatives_rejected = list(audit.alternatives_rejected)
    proof_required = list(audit.proof_required)
    telemetry_required = list(audit.telemetry_required)
    return {
        "routeClass": _value(audit.route_class),
        "routeKind": _value(audit.route_kind),
        "sessionAction": _value(audit.session_action),
        "trustState": _value(audit.trust_state),
        "contextHealth": _value(audit.context_health),
        "latencyPosture": _value(audit.latency_posture),
        "privacyLevel": _value(audit.privacy_level),
        "alternativesRejectedCount": len(alternatives_rejected),
        "fallbackBlockerCount": len(fallback_blockers),
        "proofRequiredCount": len(proof_required),
        "telemetryRequiredCount": len(telemetry_required),
        "silentFallbackBlocked": bool(
            fallback_blockers
            or any("rejected" in item for item in alternatives_rejected)
            or audit.trust_state.value in {"blocked", "candidate"}
        ),
        "primaryFallbackBlocker": fallback_blockers[0] if fallback_blockers else "none",
        "primaryProofRequirement": proof_required[0] if proof_required else "none",
    }


def _dispatch_snapshot(route: Any) -> dict[str, Any]:
    packet = assemble_relay_packet(
        packet_id=f"relay-logic-tier-{route.risk_tier}",
        serialized_prompt=SNAPSHOT_PROMPT,
        route=route,
    )
    plan = build_relay_dispatch_plan(route, packet)
    lanes = [
        {
            "role": _value(lane.role),
            "preferredModel": lane.preferred_model,
            "independent": lane.independent,
            "payloadSource": "packet.model_payload",
            "payloadTextVisible": False,
            "payloadEqualsModelPayload": lane.payload == packet.model_payload(),
            "payloadIncludesPacketMetadata": packet.packet_id in lane.payload,
        }
        for lane in plan.lanes
    ]
    return {
        "source": DISPATCH_SOURCE,
        "laneCount": len(plan.lanes),
        "laneOrder": [_value(lane.role) for lane in plan.lanes],
        "payloadPolicy": "model_payload_only",
        "payloadTextVisible": False,
        "lanes": lanes,
    }


def _tier_snapshot(tier: int) -> dict[str, Any]:
    route = route_from_tier(tier)
    return {
        "tier": route.risk_tier,
        "mode": _value(route.mode),
        "reason": route.reason,
        "costPosture": _value(route.cost_posture),
        "requiresIndependence": route.requires_independence,
        "requiresHumanGate": route.requires_human_gate,
        "lanes": [_lane_snapshot(lane) for lane in route.lanes],
        "contextStrategy": _value(route.context_strategy),
        "contextHealth": _value(route.context_health),
        "latencyPosture": _value(route.latency_posture),
        "privacyLevel": _value(route.privacy_level),
        "promptBudget": _prompt_budget_snapshot(route),
        "audit": _audit_snapshot(route),
        "auditDepth": _audit_depth_snapshot(route),
        "dispatch": _dispatch_snapshot(route),
    }


def relay_logic_snapshot() -> dict[str, Any]:
    """Return the canonical Relay logic that visible harnesses should render."""
    tiers = [_tier_snapshot(tier) for tier in range(5)]
    return {
        "ok": True,
        "service": "meridian-relay-logic",
        "version": SNAPSHOT_VERSION,
        "source": SNAPSHOT_SOURCE,
        "dispatchSource": DISPATCH_SOURCE,
        "autoRouting": "disabled_until_prime_relay_contract",
        "routePrecedence": tiers[1]["audit"]["routePrecedence"],
        "tiers": tiers,
    }


def main() -> None:
    print(json.dumps(relay_logic_snapshot(), sort_keys=True))


if __name__ == "__main__":
    main()
