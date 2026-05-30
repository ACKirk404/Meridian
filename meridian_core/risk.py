"""
Risk Tier Engine — first-class risk assessment domain.

Risk tier is not display metadata. In Meridian, changing risk tier changes
the decision process: deterministic logic, single-lane cognition, dual-lane
cognition, Aegis proof requirements, and human gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Union


class RiskMode(Enum):
    DETERMINISTIC = "Deterministic logic only"
    SINGLE_LANE = "Single-lane cognition"
    DUAL_LANE = "Dual-lane cognition"
    DUAL_LANE_PROOF = "Dual-lane cognition + Aegis proof"
    HUMAN_GATE = "Human gate required"


@dataclass
class RiskRequirement:
    label: str
    active: bool


@dataclass
class RiskAssessment:
    tier: int
    mode: RiskMode
    reason: str
    requirements: list[RiskRequirement] = field(default_factory=list)
    escalation_triggers: list[str] = field(default_factory=list)
    requires_dual_lane: bool = False
    requires_aegis_proof: bool = False
    requires_human_gate: bool = False


# ---------------------------------------------------------------------------
# Tier semantics — the canonical defaults for each tier
# ---------------------------------------------------------------------------

_TIER_SEMANTICS: dict[int, dict] = {
    0: {
        "mode": RiskMode.DETERMINISTIC,
        "reason": "deterministic local logic; no model calls needed",
        "requirements": [
            RiskRequirement("Deterministic logic", True),
            RiskRequirement("Single-lane cognition", False),
            RiskRequirement("Dual-lane cognition", False),
            RiskRequirement("Aegis proof", False),
            RiskRequirement("Human gate", False),
        ],
        "escalation_triggers": [
            "non-deterministic input required",
        ],
        "requires_dual_lane": False,
        "requires_aegis_proof": False,
        "requires_human_gate": False,
    },
    1: {
        "mode": RiskMode.SINGLE_LANE,
        "reason": "low-risk reversible action; single model lane sufficient",
        "requirements": [
            RiskRequirement("Single-lane cognition", True),
            RiskRequirement("Dual-lane cognition", False),
            RiskRequirement("Aegis proof", False),
            RiskRequirement("Human gate", False),
        ],
        "escalation_triggers": [
            "file changes introduced",
            "decision confidence below threshold",
            "meaningful Prime decision required",
        ],
        "requires_dual_lane": False,
        "requires_aegis_proof": False,
        "requires_human_gate": False,
    },
    2: {
        "mode": RiskMode.DUAL_LANE,
        "reason": "meaningful work; dual-lane cognition with Prime adjudication",
        "requirements": [
            RiskRequirement("Dual-lane cognition", True),
            RiskRequirement("Two candidate paths", True),
            RiskRequirement("Prime adjudication", True),
            RiskRequirement("Aegis proof", False),
            RiskRequirement("Human gate", False),
        ],
        "escalation_triggers": [
            "tests fail",
            "lane disagreement is high",
            "release risk detected",
            "proof required",
        ],
        "requires_dual_lane": True,
        "requires_aegis_proof": False,
        "requires_human_gate": False,
    },
    3: {
        "mode": RiskMode.DUAL_LANE_PROOF,
        "reason": "completion or proof claim; dual-lane cognition plus Aegis verification",
        "requirements": [
            RiskRequirement("Dual-lane cognition", True),
            RiskRequirement("Two candidate paths", True),
            RiskRequirement("Prime adjudication", True),
            RiskRequirement("Aegis proof", True),
            RiskRequirement("Human gate", False),
        ],
        "escalation_triggers": [
            "proof check fails",
            "reviewer disagrees with builder",
            "human review requested",
            "irreversible action identified",
        ],
        "requires_dual_lane": True,
        "requires_aegis_proof": True,
        "requires_human_gate": False,
    },
    4: {
        "mode": RiskMode.HUMAN_GATE,
        "reason": (
            "irreversible, public, financial, destructive, account-risking, "
            "policy-sensitive, blocked, or strategic action"
        ),
        "requirements": [
            RiskRequirement("Dual-lane cognition", True),
            RiskRequirement("Aegis proof", True),
            RiskRequirement("Human gate", True),
            RiskRequirement("Prime cannot proceed alone", True),
        ],
        "escalation_triggers": [],  # ceiling tier — no higher tier exists
        "requires_dual_lane": True,
        "requires_aegis_proof": True,
        "requires_human_gate": True,
    },
}


def assess_tier(tier: Union[int, object], reason: str | None = None) -> RiskAssessment:
    """
    Return a RiskAssessment for the given tier number (0–4).

    Accepts an int or any object whose `.value` is an int (e.g. RiskTier enum).
    An optional `reason` overrides the default tier reason.
    Raises ValueError for out-of-range tier numbers.
    """
    tier_num: int = tier.value if hasattr(tier, "value") else int(tier)  # type: ignore[union-attr]

    if tier_num not in _TIER_SEMANTICS:
        raise ValueError(f"Unknown risk tier: {tier_num!r}. Valid range is 0–4.")

    sem = _TIER_SEMANTICS[tier_num]
    return RiskAssessment(
        tier=tier_num,
        mode=sem["mode"],
        reason=reason if reason is not None else sem["reason"],
        requirements=[RiskRequirement(r.label, r.active) for r in sem["requirements"]],
        escalation_triggers=list(sem["escalation_triggers"]),
        requires_dual_lane=sem["requires_dual_lane"],
        requires_aegis_proof=sem["requires_aegis_proof"],
        requires_human_gate=sem["requires_human_gate"],
    )
