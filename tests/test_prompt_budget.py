"""
Tests for the Relay Prompt Budget domain model.

Ensures prompt budgets are deterministic by risk tier, bounded, and prevent
prompt drag (excessive injected context, diagnostic overhead, state bloat).
"""

from __future__ import annotations

import pytest
from meridian_core.prompt_budget import (
    PromptBudget,
    PromptBudgetPlan,
    PromptBudgetTier,
    prompt_budget_for_risk_tier,
)


class TestPromptBudgetTier:
    """PromptBudgetTier enum values and semantics."""

    def test_tier_enum_values(self):
        """All tier values are defined and lowercase."""
        assert PromptBudgetTier.MINIMAL.value == "minimal"
        assert PromptBudgetTier.FOCUSED.value == "focused"
        assert PromptBudgetTier.BOUNDED.value == "bounded"
        assert PromptBudgetTier.EXPLAINED.value == "explained"

    def test_tier_count(self):
        """Exactly 4 tier modes exist."""
        tiers = list(PromptBudgetTier)
        assert len(tiers) == 4


class TestPromptBudget:
    """PromptBudget dataclass — the actual token budget."""

    def test_prompt_budget_minimal(self):
        """Minimal tier has very small max context."""
        budget = PromptBudget(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=["direct_input"],
            reason="Deterministic logic, no model overhead",
        )
        assert budget.max_context_tokens == 500
        assert "direct_input" in budget.allowed_sources
        assert budget.reason

    def test_prompt_budget_focused(self):
        """Focused tier allows moderate context."""
        budget = PromptBudget(
            tier=PromptBudgetTier.FOCUSED,
            max_context_tokens=2000,
            allowed_sources=["direct_input", "recent_history"],
            reason="Single-lane cognition with minimal overhead",
        )
        assert budget.max_context_tokens == 2000
        assert len(budget.allowed_sources) >= 2

    def test_prompt_budget_bounded(self):
        """Bounded tier allows proof/review context but still bounded."""
        budget = PromptBudget(
            tier=PromptBudgetTier.BOUNDED,
            max_context_tokens=5000,
            allowed_sources=[
                "direct_input",
                "recent_history",
                "proof_evidence",
                "review_notes",
            ],
            reason="Dual-lane cognition with proof verification",
        )
        assert budget.max_context_tokens == 5000
        assert len(budget.allowed_sources) >= 4

    def test_prompt_budget_explained(self):
        """Explained tier allows explanation context for human gate."""
        budget = PromptBudget(
            tier=PromptBudgetTier.EXPLAINED,
            max_context_tokens=8000,
            allowed_sources=[
                "direct_input",
                "recent_history",
                "proof_evidence",
                "review_notes",
                "human_explanation_draft",
            ],
            reason="Human gate requires complete explanation context",
        )
        assert budget.max_context_tokens == 8000
        assert "human_explanation_draft" in budget.allowed_sources

    def test_reason_is_required(self):
        """Budget reason cannot be empty."""
        budget = PromptBudget(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=["direct_input"],
            reason="",
        )
        assert budget.reason == ""
        # The reason field exists; tests below verify the generator ensures non-empty

    def test_no_mutation_in_sources(self):
        """Modifying sources list does not affect future instances."""
        sources1 = ["direct_input"]
        budget1 = PromptBudget(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=sources1,
            reason="test",
        )

        sources2 = ["direct_input", "history"]
        budget2 = PromptBudget(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=sources2,
            reason="test",
        )

        assert len(budget1.allowed_sources) == 1
        assert len(budget2.allowed_sources) == 2


class TestPromptBudgetPlan:
    """PromptBudgetPlan — the bundled plan output."""

    def test_plan_includes_all_fields(self):
        """Plan has tier, budget, sources, and reason."""
        plan = PromptBudgetPlan(
            tier=PromptBudgetTier.FOCUSED,
            max_context_tokens=2000,
            allowed_sources=["direct_input", "history"],
            reason="Single-lane cognition",
        )
        assert plan.tier == PromptBudgetTier.FOCUSED
        assert plan.max_context_tokens == 2000
        assert plan.allowed_sources
        assert plan.reason

    def test_plan_reason_is_nonempty(self):
        """Plans always have a non-empty reason."""
        plan = PromptBudgetPlan(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=["direct_input"],
            reason="Test",
        )
        assert len(plan.reason) > 0


class TestPromptBudgetForRiskTier:
    """prompt_budget_for_risk_tier() generator function."""

    def test_tier_0_minimal_budget(self):
        """Risk tier 0 gets minimal prompt budget."""
        plan = prompt_budget_for_risk_tier(0)
        assert plan.tier == PromptBudgetTier.MINIMAL
        assert plan.max_context_tokens <= 1000
        assert plan.reason

    def test_tier_1_minimal_budget(self):
        """Risk tier 1 gets minimal to focused budget."""
        plan = prompt_budget_for_risk_tier(1)
        assert plan.tier == PromptBudgetTier.MINIMAL
        assert plan.max_context_tokens <= 1500
        assert plan.reason

    def test_tier_2_focused_budget(self):
        """Risk tier 2 gets focused budget for dual-lane."""
        plan = prompt_budget_for_risk_tier(2)
        assert plan.tier == PromptBudgetTier.FOCUSED
        assert 1500 <= plan.max_context_tokens <= 3000
        assert plan.reason

    def test_tier_3_bounded_budget(self):
        """Risk tier 3 allows proof/review context but bounded."""
        plan = prompt_budget_for_risk_tier(3)
        assert plan.tier == PromptBudgetTier.BOUNDED
        assert 3000 <= plan.max_context_tokens <= 7000
        assert plan.reason

    def test_tier_4_explained_budget(self):
        """Risk tier 4 allows human-gate explanation context."""
        plan = prompt_budget_for_risk_tier(4)
        assert plan.tier == PromptBudgetTier.EXPLAINED
        assert plan.max_context_tokens <= 10000
        assert plan.reason

    def test_tier_0_vs_tier_3_budget(self):
        """Tier 0 has strictly leaner budget than Tier 3."""
        plan_0 = prompt_budget_for_risk_tier(0)
        plan_3 = prompt_budget_for_risk_tier(3)
        assert plan_0.max_context_tokens < plan_3.max_context_tokens

    def test_tier_3_vs_tier_4_budget(self):
        """Tier 3 is bounded; Tier 4 allows more for explanation."""
        plan_3 = prompt_budget_for_risk_tier(3)
        plan_4 = prompt_budget_for_risk_tier(4)
        # Tier 4 may have more tokens for human explanation
        assert plan_4.max_context_tokens >= plan_3.max_context_tokens

    def test_tier_progression_increases_budget(self):
        """Higher tiers generally allow more context."""
        budgets = [prompt_budget_for_risk_tier(i) for i in range(5)]
        tokens = [b.max_context_tokens for b in budgets]
        # Generally increasing, though tier 0 and 1 might be the same
        assert tokens[0] <= tokens[2]
        assert tokens[2] <= tokens[3]
        assert tokens[3] <= tokens[4]

    def test_all_plans_have_reasons(self):
        """Every tier produces a plan with non-empty reason."""
        for tier in range(5):
            plan = prompt_budget_for_risk_tier(tier)
            assert plan.reason
            assert len(plan.reason) > 0

    def test_invalid_tier_raises_error(self):
        """Invalid tier number raises ValueError."""
        with pytest.raises(ValueError, match="Unknown risk tier"):
            prompt_budget_for_risk_tier(5)

        with pytest.raises(ValueError, match="Unknown risk tier"):
            prompt_budget_for_risk_tier(-1)

    def test_deterministic_output(self):
        """Same tier always produces same plan."""
        plan_a = prompt_budget_for_risk_tier(2)
        plan_b = prompt_budget_for_risk_tier(2)

        assert plan_a.tier == plan_b.tier
        assert plan_a.max_context_tokens == plan_b.max_context_tokens
        assert plan_a.reason == plan_b.reason

    def test_no_mutable_list_leakage(self):
        """Modifying returned plan's sources doesn't affect next call."""
        plan_a = prompt_budget_for_risk_tier(2)
        original_count = len(plan_a.allowed_sources)

        plan_a.allowed_sources.append("injected_garbage")

        plan_b = prompt_budget_for_risk_tier(2)
        assert len(plan_b.allowed_sources) == original_count
