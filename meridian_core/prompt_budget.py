"""
Relay Prompt Budget domain model.

Deterministic, bounded prompt budget planning by risk tier.
Ensures Relay does not become prompt drag—excessive injected context,
diagnostic overhead, or state bloat riding in the model prompt.

This module defines what context sources and token limits each risk tier
can access during Relay dispatch. Budgets are tier-locked, non-negotiable,
and prevent models from receiving uncontrolled context growth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .risk import RiskTier


class PromptBudgetTier(Enum):
    """Prompt budget tier modes mapped to risk tiers."""

    MINIMAL = "minimal"  # Tier 0/1: deterministic, single-lane with no overhead
    FOCUSED = "focused"  # Tier 2: dual-lane cognition with bounded context
    BOUNDED = "bounded"  # Tier 3: proof/review context, still bounded
    EXPLAINED = "explained"  # Tier 4: human-gate explanation, not execution payload


@dataclass(frozen=True)
class PromptBudgetPlan:
    """
    Prompt budget plan for a risk tier.

    Defines max context tokens and allowed context sources for a Relay dispatch.
    Frozen: values are locked after construction.
    """

    tier: PromptBudgetTier
    max_context_tokens: int
    allowed_sources: list[str] = field(default_factory=list)
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_sources", list(self.allowed_sources))


# ---------------------------------------------------------------------------
# Tier semantics — canonical defaults for each risk tier
# ---------------------------------------------------------------------------

_TIER_BUDGETS: dict[int, dict] = {
    0: {
        "tier": PromptBudgetTier.MINIMAL,
        "max_context_tokens": 500,
        "allowed_sources": ["direct_input"],
        "reason": "Deterministic local logic; no model overhead needed",
    },
    1: {
        "tier": PromptBudgetTier.MINIMAL,
        "max_context_tokens": 1000,
        "allowed_sources": ["direct_input", "task_context"],
        "reason": "Low-risk reversible action; single-lane cognition with minimal overhead",
    },
    2: {
        "tier": PromptBudgetTier.FOCUSED,
        "max_context_tokens": 2500,
        "allowed_sources": ["direct_input", "task_context", "recent_history"],
        "reason": "Meaningful work; dual-lane cognition with focused context",
    },
    3: {
        "tier": PromptBudgetTier.BOUNDED,
        "max_context_tokens": 5000,
        "allowed_sources": [
            "direct_input",
            "task_context",
            "recent_history",
            "proof_evidence",
            "review_notes",
        ],
        "reason": "Completion or proof claim; dual-lane cognition with Aegis verification context",
    },
    4: {
        "tier": PromptBudgetTier.EXPLAINED,
        "max_context_tokens": 8000,
        "allowed_sources": [
            "direct_input",
            "task_context",
            "recent_history",
            "proof_evidence",
            "review_notes",
            "human_explanation_draft",
        ],
        "reason": "Irreversible, public, or strategic action; human-gate explanation context allowed",
    },
}


def prompt_budget_for_risk_tier(tier: int | RiskTier) -> PromptBudgetPlan:
    """
    Return a PromptBudgetPlan for the given risk tier (0–4).

    Accepts either an int (0–4) or a RiskTier enum value.

    Tier 0/1 have minimal budgets to prevent deterministic/single-lane overhead.
    Tier 2 allows focused context for dual-lane cognition.
    Tier 3 allows proof and review context, still bounded.
    Tier 4 allows human-gate explanation context.

    Raises ValueError if tier is out of range.
    """
    tier_int = tier.value if isinstance(tier, RiskTier) else tier
    if tier_int not in _TIER_BUDGETS:
        raise ValueError(f"Unknown risk tier: {tier!r}. Valid range is 0–4.")

    budget = _TIER_BUDGETS[tier_int]
    return PromptBudgetPlan(
        tier=budget["tier"],
        max_context_tokens=budget["max_context_tokens"],
        allowed_sources=list(budget["allowed_sources"]),
        reason=budget["reason"],
    )


PromptBudget = PromptBudgetPlan  # Alias for backward compatibility
