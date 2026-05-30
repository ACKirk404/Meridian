"""
Council cognition -- structured internal positions for Prime deliberation.

The Council is not a multi-agent runtime in this slice. It is a deterministic
domain model that tells Prime which cognitive positions should be considered
for a given risk tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .risk import RiskAssessment, RiskTier, assess_tier


class CouncilRole(Enum):
    ANALYST = "analyst"
    DEVILS_ADVOCATE = "devils_advocate"
    PRAGMATIST = "pragmatist"
    CONTRARIAN = "contrarian"
    EXPANSIONIST = "expansionist"
    CHAIRMAN = "chairman"


@dataclass(frozen=True)
class CouncilPosition:
    role: CouncilRole
    name: str
    purpose: str
    question: str


@dataclass(frozen=True)
class CouncilPlan:
    risk_tier: int
    roles: list[CouncilRole]
    positions: list[CouncilPosition]
    reason: str
    requires_full_council: bool = False

    def includes(self, role: CouncilRole) -> bool:
        """True when the plan includes the requested Council role."""
        return role in self.roles


_DEFAULT_POSITIONS: dict[CouncilRole, CouncilPosition] = {
    CouncilRole.ANALYST: CouncilPosition(
        role=CouncilRole.ANALYST,
        name="Analyst",
        purpose="Evidence-based, skeptical reasoning.",
        question="What do we actually know, and what supports it?",
    ),
    CouncilRole.DEVILS_ADVOCATE: CouncilPosition(
        role=CouncilRole.DEVILS_ADVOCATE,
        name="Devil's Advocate",
        purpose="Challenge assumptions and find flaws in the prevalent view.",
        question="What assumption could make this plan fail?",
    ),
    CouncilRole.PRAGMATIST: CouncilPosition(
        role=CouncilRole.PRAGMATIST,
        name="Pragmatist",
        purpose="Focus on what is realistic, actionable, timely, and cost-aware.",
        question="What is the next useful action we can actually take?",
    ),
    CouncilRole.CONTRARIAN: CouncilPosition(
        role=CouncilRole.CONTRARIAN,
        name="Contrarian",
        purpose="Push back against the answer that seems most obvious or agreeable.",
        question="What if the obvious answer is wrong?",
    ),
    CouncilRole.EXPANSIONIST: CouncilPosition(
        role=CouncilRole.EXPANSIONIST,
        name="Expansionist",
        purpose="Find possibilities, upside, and paths the current frame is missing.",
        question="What opportunity are we not seeing yet?",
    ),
    CouncilRole.CHAIRMAN: CouncilPosition(
        role=CouncilRole.CHAIRMAN,
        name="Chairman",
        purpose="Weigh the Council voices and decide what Prime presents or does.",
        question="Which voice matters most for this moment?",
    ),
}


_ROLE_PLAN_BY_TIER: dict[int, tuple[list[CouncilRole], str]] = {
    0: (
        [CouncilRole.CHAIRMAN],
        "deterministic local logic; Chairman confirms no structured deliberation is needed",
    ),
    1: (
        [CouncilRole.PRAGMATIST, CouncilRole.CHAIRMAN],
        "low-risk reversible action; Pragmatist checks actionability",
    ),
    2: (
        [
            CouncilRole.ANALYST,
            CouncilRole.DEVILS_ADVOCATE,
            CouncilRole.PRAGMATIST,
            CouncilRole.CHAIRMAN,
        ],
        "meaningful Prime decision; evidence, assumptions, and actionability should be checked",
    ),
    3: (
        list(CouncilRole),
        "proof-sensitive work; full Council deliberation should precede Aegis gating",
    ),
    4: (
        list(CouncilRole),
        "human-gated work; full Council deliberation should prepare the gate for Scott",
    ),
}


def default_council_positions() -> list[CouncilPosition]:
    """Return all canonical Council positions in stable order."""
    return [_DEFAULT_POSITIONS[role] for role in CouncilRole]


def council_plan_for_tier(tier: int | RiskTier | RiskAssessment) -> CouncilPlan:
    """Return the Council roles Prime should invoke for a risk tier."""
    assessment = tier if isinstance(tier, RiskAssessment) else assess_tier(tier)
    roles, reason = _ROLE_PLAN_BY_TIER[assessment.tier]
    role_copy = list(roles)
    return CouncilPlan(
        risk_tier=assessment.tier,
        roles=role_copy,
        positions=[_DEFAULT_POSITIONS[role] for role in role_copy],
        reason=reason,
        requires_full_council=len(role_copy) == len(CouncilRole),
    )
