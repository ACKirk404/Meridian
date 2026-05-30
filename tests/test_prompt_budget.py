"""
Tests for the Relay Prompt Budget domain model.

Ensures prompt budgets are deterministic by risk tier, bounded, and prevent
prompt drag (excessive injected context, diagnostic overhead, state bloat).
"""

from __future__ import annotations

import pytest
from meridian_core.prompt_budget import (
    PromptBudgetPlan,
    PromptBudgetTier,
    prompt_budget_for_risk_tier,
)
from meridian_core.risk import RiskTier


class TestPromptBudgetTier:
    """PromptBudgetTier enum values and semantics."""

    def test_tier_enum_values(self):
        assert PromptBudgetTier.MINIMAL.value == "minimal"
        assert PromptBudgetTier.FOCUSED.value == "focused"
        assert PromptBudgetTier.BOUNDED.value == "bounded"
        assert PromptBudgetTier.EXPLAINED.value == "explained"

    def test_tier_count(self):
        assert len(list(PromptBudgetTier)) == 4


class TestPromptBudgetPlan:
    """PromptBudgetPlan dataclass — the planning artifact."""

    def test_plan_includes_all_fields(self):
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
        plan = PromptBudgetPlan(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=["direct_input"],
            reason="Test",
        )
        assert len(plan.reason) > 0

    def test_plan_is_immutable(self):
        plan = PromptBudgetPlan(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=["direct_input"],
            reason="test",
        )
        with pytest.raises((AttributeError, TypeError)):
            plan.max_context_tokens = 99999  # type: ignore[misc]

    def test_allowed_sources_is_copied_on_construction(self):
        sources = ["direct_input"]
        plan = PromptBudgetPlan(
            tier=PromptBudgetTier.MINIMAL,
            max_context_tokens=500,
            allowed_sources=sources,
            reason="test",
        )
        sources.append("injected")
        assert len(plan.allowed_sources) == 1


class TestPromptBudgetForRiskTier:
    """prompt_budget_for_risk_tier() — int and RiskTier enum inputs."""

    def test_tier_0_minimal_budget(self):
        plan = prompt_budget_for_risk_tier(0)
        assert plan.tier == PromptBudgetTier.MINIMAL
        assert plan.max_context_tokens <= 1000
        assert plan.reason

    def test_tier_1_minimal_budget(self):
        plan = prompt_budget_for_risk_tier(1)
        assert plan.tier == PromptBudgetTier.MINIMAL
        assert plan.max_context_tokens <= 1500
        assert plan.reason

    def test_tier_2_focused_budget(self):
        plan = prompt_budget_for_risk_tier(2)
        assert plan.tier == PromptBudgetTier.FOCUSED
        assert 1500 <= plan.max_context_tokens <= 3000
        assert plan.reason

    def test_tier_3_bounded_budget(self):
        plan = prompt_budget_for_risk_tier(3)
        assert plan.tier == PromptBudgetTier.BOUNDED
        assert 3000 <= plan.max_context_tokens <= 7000
        assert plan.reason

    def test_tier_4_explained_budget(self):
        plan = prompt_budget_for_risk_tier(4)
        assert plan.tier == PromptBudgetTier.EXPLAINED
        assert plan.max_context_tokens <= 10000
        assert plan.reason

    def test_accepts_risk_tier_enum(self):
        plan_int = prompt_budget_for_risk_tier(2)
        plan_enum = prompt_budget_for_risk_tier(RiskTier.TIER_2)
        assert plan_enum.tier == plan_int.tier
        assert plan_enum.max_context_tokens == plan_int.max_context_tokens
        assert plan_enum.reason == plan_int.reason

    def test_accepts_all_risk_tier_enum_values(self):
        for rt in RiskTier:
            plan = prompt_budget_for_risk_tier(rt)
            assert isinstance(plan, PromptBudgetPlan)

    def test_tier_0_vs_tier_3_budget(self):
        assert prompt_budget_for_risk_tier(0).max_context_tokens < prompt_budget_for_risk_tier(3).max_context_tokens

    def test_tier_3_vs_tier_4_budget(self):
        assert prompt_budget_for_risk_tier(4).max_context_tokens >= prompt_budget_for_risk_tier(3).max_context_tokens

    def test_tier_progression_increases_budget(self):
        tokens = [prompt_budget_for_risk_tier(i).max_context_tokens for i in range(5)]
        assert tokens[0] <= tokens[2]
        assert tokens[2] <= tokens[3]
        assert tokens[3] <= tokens[4]

    def test_all_plans_have_reasons(self):
        for tier in range(5):
            plan = prompt_budget_for_risk_tier(tier)
            assert len(plan.reason) > 0

    def test_invalid_tier_raises_error(self):
        with pytest.raises(ValueError, match="Unknown risk tier"):
            prompt_budget_for_risk_tier(5)
        with pytest.raises(ValueError, match="Unknown risk tier"):
            prompt_budget_for_risk_tier(-1)

    def test_deterministic_output(self):
        plan_a = prompt_budget_for_risk_tier(2)
        plan_b = prompt_budget_for_risk_tier(2)
        assert plan_a.tier == plan_b.tier
        assert plan_a.max_context_tokens == plan_b.max_context_tokens
        assert plan_a.reason == plan_b.reason

    def test_no_mutable_list_leakage(self):
        plan_a = prompt_budget_for_risk_tier(2)
        original_count = len(plan_a.allowed_sources)
        plan_a.allowed_sources.append("injected_garbage")
        plan_b = prompt_budget_for_risk_tier(2)
        assert len(plan_b.allowed_sources) == original_count
