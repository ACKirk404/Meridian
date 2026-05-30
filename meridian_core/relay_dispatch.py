"""
Relay dispatch plan domain model.

A RelayDispatchPlan is a deterministic, immutable mapping from a RelayRoute
and PromptPacket to per-lane model work. No model is called here; this is
pure domain structure for Relay dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass

from .prompt_packet import PromptPacket
from .relay import ModelRole, RelayRoute


@dataclass(frozen=True)
class RelayDispatchLane:
    """One lane's model work specification within a dispatch plan."""

    role: ModelRole
    preferred_model: str
    independent: bool
    payload: str  # always packet.model_payload(); no metadata, lineage, or tokens


@dataclass(frozen=True)
class RelayDispatchPlan:
    """
    Immutable dispatch plan: route + packet mapped to per-lane work.

    lanes preserves order from route.lanes. Tier 0 (NO_MODEL) routes produce
    an empty tuple. Only model_payload() content crosses into lane payloads.
    """

    route: RelayRoute
    packet: PromptPacket
    lanes: tuple[RelayDispatchLane, ...]


def build_relay_dispatch_plan(
    route: RelayRoute,
    packet: PromptPacket,
) -> RelayDispatchPlan:
    """
    Build a deterministic RelayDispatchPlan from a route and a sealed packet.

    Every lane payload is packet.model_payload() — no budget, token counts,
    lineage, or metadata included. Lane order matches route.lanes.
    """
    payload = packet.model_payload()
    lanes = tuple(
        RelayDispatchLane(
            role=lane.role,
            preferred_model=lane.preferred_model,
            independent=lane.independent,
            payload=payload,
        )
        for lane in route.lanes
    )
    return RelayDispatchPlan(route=route, packet=packet, lanes=lanes)
