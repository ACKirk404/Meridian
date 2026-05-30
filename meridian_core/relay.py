"""
Relay Routing — deterministic model/session routing from risk tier and task context.

Relay turns a RiskAssessment into a RelayRoute: lane list, roles, context strategy,
cost posture, and independence requirements. No real model calls, provider credentials,
or account automation here — this slice is domain-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from .risk import RiskAssessment, RiskTier, assess_tier


class RoutingMode(Enum):
    NO_MODEL = "no_model"
    SINGLE_LANE = "single_lane"
    DUAL_LANE = "dual_lane"
    DUAL_LANE_PROOF = "dual_lane_proof"
    HUMAN_GATE = "human_gate"


class ModelRole(Enum):
    BUILDER = "builder"
    REVIEWER = "reviewer"
    PROOF = "proof"
    EXPLAINER = "explainer"


class ContextStrategy(Enum):
    FOCUSED_PACKET = "focused_packet"
    REUSE_SESSION = "reuse_session"
    SUMMARIZE_AND_RESET = "summarize_and_reset"
    LARGE_CONTEXT = "large_context"


@dataclass
class RelayLane:
    role: ModelRole
    model_label: str
    independent: bool


@dataclass
class RelayRoute:
    mode: RoutingMode
    lanes: list[RelayLane]
    context_strategy: ContextStrategy
    reason: str
    cost_posture: str
    requires_independence: bool
    requires_human_gate: bool
    assessment: RiskAssessment


# ---------------------------------------------------------------------------
# Routing semantics — deterministic defaults per tier
# ---------------------------------------------------------------------------

_ROUTING_SEMANTICS: dict[int, dict] = {
    0: {
        "mode": RoutingMode.NO_MODEL,
        "lanes": [],
        "cost_posture": "none",
        "requires_independence": False,
        "reason": "deterministic local logic; no model lanes needed",
    },
    1: {
        "mode": RoutingMode.SINGLE_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, model_label="fast/cheap default", independent=False),
        ],
        "cost_posture": "minimal",
        "requires_independence": False,
        "reason": "low-risk reversible action; single fast lane sufficient",
    },
    2: {
        "mode": RoutingMode.DUAL_LANE,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, model_label="primary default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, model_label="independent reviewer", independent=True),
        ],
        "cost_posture": "moderate",
        "requires_independence": True,
        "reason": "meaningful build work; dual-lane cognition with Prime adjudication",
    },
    3: {
        "mode": RoutingMode.DUAL_LANE_PROOF,
        "lanes": [
            RelayLane(role=ModelRole.BUILDER, model_label="primary default", independent=False),
            RelayLane(role=ModelRole.REVIEWER, model_label="independent reviewer", independent=True),
            RelayLane(role=ModelRole.PROOF, model_label="Aegis proof verifier", independent=True),
        ],
        "cost_posture": "high",
        "requires_independence": True,
        "reason": "completion or proof claim; dual-lane cognition plus Aegis verification",
    },
    4: {
        "mode": RoutingMode.HUMAN_GATE,
        "lanes": [
            RelayLane(role=ModelRole.EXPLAINER, model_label="explanation only", independent=False),
        ],
        "cost_posture": "deferred",
        "requires_independence": False,
        "reason": (
            "irreversible, public, financial, destructive, account-risking, "
            "policy-sensitive, blocked, or strategic action; human gate before execution"
        ),
    },
}


def route(
    tier: Union[int, RiskTier, RiskAssessment],
    context_strategy: ContextStrategy = ContextStrategy.FOCUSED_PACKET,
    reason: str | None = None,
) -> RelayRoute:
    """
    Produce a deterministic RelayRoute from a tier number, RiskTier enum, or RiskAssessment.

    context_strategy defaults to FOCUSED_PACKET.
    reason overrides the default routing reason when provided.
    """
    if isinstance(tier, RiskAssessment):
        assessment = tier
    else:
        assessment = assess_tier(tier)

    tier_num = assessment.tier
    sem = _ROUTING_SEMANTICS[tier_num]

    return RelayRoute(
        mode=sem["mode"],
        lanes=[RelayLane(l.role, l.model_label, l.independent) for l in sem["lanes"]],
        context_strategy=context_strategy,
        reason=reason if reason is not None else sem["reason"],
        cost_posture=sem["cost_posture"],
        requires_independence=sem["requires_independence"],
        requires_human_gate=assessment.requires_human_gate,
        assessment=assessment,
    )
