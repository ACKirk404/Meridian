"""
Relay Routing -- deterministic model/session routing plan from risk tier.

Relay is the Agent / Model Harness. This slice produces a structured
RelayRoute from a RiskAssessment without calling real models or APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .council import CouncilPlan, council_plan_for_tier
from .risk import RiskAssessment, RiskTier, assess_tier


class RoutingMode(Enum):
    NO_MODEL = "no-model"
    SINGLE_LANE = "single-lane"
    DUAL_LANE = "dual-lane"
    DUAL_LANE_PROOF = "dual-lane-proof"
    HUMAN_GATE = "human-gate"


class ModelRole(Enum):
    BUILDER = "builder"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"
    EXPLAINER = "explainer"


class ContextStrategy(Enum):
    FOCUSED_PACKET = "focused_packet"
    REUSE_SESSION = "reuse_session"
    SUMMARIZE_AND_RESET = "summarize_and_reset"
    LARGE_CONTEXT = "large_context"


class CostPosture(Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    THOROUGH = "thorough"


@dataclass
class RelayLane:
    role: ModelRole
    preferred_model: str
    independent: bool = False


@dataclass
class RelayRoute:
    mode: RoutingMode
    lanes: list[RelayLane]
    context_strategy: ContextStrategy
    reason: str
    cost_posture: CostPosture
    requires_independence: bool
    requires_human_gate: bool
    risk_tier: int
    council_plan: CouncilPlan = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Routing table -- deterministic defaults per tier
# ---------------------------------------------------------------------------

_ROUTING_TABLE: dict[int, dict] = {
    0: {
        "mode": RoutingMode.NO_MODEL,
        "lanes": [],
        "reason": "deterministic local logic; no model lanes needed",
        "cost_posture": CostPosture.MINIMAL,
        "requires_independence": False,
        "requires_human_gate": False,
    },
    1: {
        "mode": RoutingMode.SINGLE_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="fast-default", independent=False),
        ],
        "reason": "low-risk reversible action; one fast/cheap lane is sufficient",
        "cost_posture": CostPosture.MINIMAL,
        "requires_independence": False,
        "requires_human_gate": False,
    },
    2: {
        "mode": RoutingMode.DUAL_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="primary-default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, preferred_model="independent-reviewer", independent=True),
        ],
        "reason": "meaningful Prime decision; two independent lanes required for disagreement detection",
        "cost_posture": CostPosture.STANDARD,
        "requires_independence": True,
        "requires_human_gate": False,
    },
    3: {
        "mode": RoutingMode.DUAL_LANE_PROOF,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, preferred_model="primary-default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, preferred_model="independent-reviewer", independent=True),
            RelayLane(role=ModelRole.VERIFIER, preferred_model="proof-verifier", independent=True),
        ],
        "reason": "completion or proof claim; dual-lane plus Aegis verification posture",
        "cost_posture": CostPosture.THOROUGH,
        "requires_independence": True,
        "requires_human_gate": False,
    },
    4: {
        "mode": RoutingMode.HUMAN_GATE,
        "lanes": [
            RelayLane(role=ModelRole.EXPLAINER, preferred_model="primary-default", independent=False),
        ],
        "reason": (
            "irreversible, public, financial, destructive, or strategic action; "
            "no autonomous execution until human gate is cleared"
        ),
        "cost_posture": CostPosture.STANDARD,
        "requires_independence": False,
        "requires_human_gate": True,
    },
}


def route_from_assessment(
    assessment: RiskAssessment,
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
) -> RelayRoute:
    """
    Produce a deterministic RelayRoute from a RiskAssessment.

    context_strategy defaults to FOCUSED_PACKET. Pass an explicit strategy
    when the caller has already decided (e.g. reuse_session after a healthy
    context check).
    """
    row = _ROUTING_TABLE[assessment.tier]
    return RelayRoute(
        mode=row["mode"],
        lanes=[RelayLane(l.role, l.preferred_model, l.independent) for l in row["lanes"]],
        context_strategy=context_strategy,
        reason=row["reason"],
        cost_posture=row["cost_posture"],
        requires_independence=row["requires_independence"],
        requires_human_gate=row["requires_human_gate"],
        risk_tier=assessment.tier,
        council_plan=council_plan_for_tier(assessment),
    )


def route_from_tier(
    tier: int | RiskTier,
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
    reason: str | None = None,
) -> RelayRoute:
    """
    Convenience: produce a RelayRoute directly from a tier number or RiskTier enum.
    """
    assessment = assess_tier(tier, reason=reason)
    return route_from_assessment(assessment, context_strategy=context_strategy)
