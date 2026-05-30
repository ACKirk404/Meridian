"""Tests for the Prompt Packet domain model (meridian_core/prompt_packet.py)."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from meridian_core.prompt_budget import PromptBudgetPlan, PromptBudgetTier
from meridian_core.prompt_packet import (
    PromptPacket,
    PromptPacketValidationError,
    build_prompt_packet,
)


def _budget(max_tokens: int = 500) -> PromptBudgetPlan:
    return PromptBudgetPlan(
        tier=PromptBudgetTier.FOCUSED,
        max_context_tokens=max_tokens,
        allowed_sources=("direct_input", "task_context"),
        reason="test budget",
    )


def _kwargs(**overrides) -> dict:
    defaults: dict = dict(
        packet_id="pkt-001",
        serialized_prompt="Build a unit test for the payment service.",
        prompt_tokens=10,
        budget=_budget(),
        source_lineage={"direct_input": 6, "task_context": 4},
        construction_time_ms=12.5,
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Construction — valid packets
# ---------------------------------------------------------------------------


class TestPromptPacketConstruction:
    def test_valid_packet_builds(self):
        pkt = build_prompt_packet(**_kwargs())
        assert isinstance(pkt, PromptPacket)

    def test_fields_are_set_correctly(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.packet_id == "pkt-001"
        assert pkt.serialized_prompt == "Build a unit test for the payment service."
        assert pkt.prompt_tokens == 10
        assert pkt.construction_time_ms == 12.5

    def test_budget_is_attached(self):
        budget = _budget()
        pkt = build_prompt_packet(**_kwargs(budget=budget))
        assert pkt.budget is budget

    def test_source_lineage_is_mapping_proxy(self):
        pkt = build_prompt_packet(**_kwargs())
        assert isinstance(pkt.source_lineage, MappingProxyType)

    def test_packet_is_frozen(self):
        pkt = build_prompt_packet(**_kwargs())
        with pytest.raises((AttributeError, TypeError)):
            pkt.prompt_tokens = 99  # type: ignore[misc]

    def test_source_lineage_is_immutable(self):
        pkt = build_prompt_packet(**_kwargs())
        with pytest.raises(TypeError):
            pkt.source_lineage["injected"] = 99  # type: ignore[index]

    def test_input_lineage_dict_not_aliased(self):
        lineage = {"direct_input": 5}
        pkt = build_prompt_packet(**_kwargs(source_lineage=lineage, prompt_tokens=5))
        lineage["injected"] = 99
        assert "injected" not in pkt.source_lineage

    def test_tokens_equal_budget_ceiling_is_valid(self):
        pkt = build_prompt_packet(**_kwargs(
            prompt_tokens=500,
            source_lineage={"direct_input": 500},
        ))
        assert pkt.prompt_tokens == 500

    def test_zero_construction_time_is_valid(self):
        pkt = build_prompt_packet(**_kwargs(construction_time_ms=0.0))
        assert pkt.construction_time_ms == 0.0

    def test_empty_lineage_is_valid(self):
        pkt = build_prompt_packet(**_kwargs(source_lineage={}, prompt_tokens=10))
        assert pkt.source_lineage == MappingProxyType({})

    def test_lineage_values_accessible(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.source_lineage["direct_input"] == 6
        assert pkt.source_lineage["task_context"] == 4


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestPromptPacketValidation:
    def test_empty_prompt_raises(self):
        with pytest.raises(PromptPacketValidationError, match="empty"):
            build_prompt_packet(**_kwargs(serialized_prompt=""))

    def test_negative_tokens_raises(self):
        with pytest.raises(PromptPacketValidationError, match="negative"):
            build_prompt_packet(**_kwargs(prompt_tokens=-1))

    def test_tokens_exceed_budget_raises(self):
        with pytest.raises(PromptPacketValidationError, match="exceeds budget"):
            build_prompt_packet(**_kwargs(prompt_tokens=501))

    def test_unknown_source_raises(self):
        with pytest.raises(PromptPacketValidationError, match="not in allowed_sources"):
            build_prompt_packet(**_kwargs(source_lineage={"debug_logs": 5}))

    def test_negative_lineage_token_count_raises(self):
        with pytest.raises(PromptPacketValidationError, match="negative"):
            build_prompt_packet(**_kwargs(source_lineage={"direct_input": -1}))

    def test_lineage_total_exceeds_prompt_tokens_raises(self):
        with pytest.raises(PromptPacketValidationError, match=r"Lineage .* exceeds packet"):
            build_prompt_packet(**_kwargs(
                source_lineage={"direct_input": 15},
                prompt_tokens=10,
            ))

    def test_negative_construction_time_raises(self):
        with pytest.raises(PromptPacketValidationError, match="negative"):
            build_prompt_packet(**_kwargs(construction_time_ms=-1.0))

    def test_error_is_value_error_subclass(self):
        with pytest.raises(ValueError):
            build_prompt_packet(**_kwargs(serialized_prompt=""))

    def test_multiple_errors_reported_together(self):
        with pytest.raises(PromptPacketValidationError) as exc_info:
            build_prompt_packet(**_kwargs(serialized_prompt="", prompt_tokens=-5))
        msg = str(exc_info.value)
        assert "empty" in msg
        assert "negative" in msg


# ---------------------------------------------------------------------------
# Metadata hygiene — packet metadata never leaks into serialized_prompt
# ---------------------------------------------------------------------------


class TestPromptPacketMetadata:
    def test_packet_id_not_in_serialized_prompt(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.packet_id not in pkt.serialized_prompt

    def test_construction_time_not_in_serialized_prompt(self):
        pkt = build_prompt_packet(**_kwargs())
        assert str(pkt.construction_time_ms) not in pkt.serialized_prompt

    def test_different_packet_ids_are_distinct(self):
        pkt1 = build_prompt_packet(**_kwargs(packet_id="pkt-001"))
        pkt2 = build_prompt_packet(**_kwargs(packet_id="pkt-002"))
        assert pkt1.packet_id != pkt2.packet_id


# ---------------------------------------------------------------------------
# Budget integration — real PromptBudgetPlan from prompt_budget_for_risk_tier
# ---------------------------------------------------------------------------


class TestPromptPacketBudgetIntegration:
    def test_packet_respects_real_tier_budget(self):
        from meridian_core.prompt_budget import prompt_budget_for_risk_tier

        budget = prompt_budget_for_risk_tier(2)
        pkt = build_prompt_packet(
            packet_id="pkt-tier2",
            serialized_prompt="Analyze the risk tier mapping.",
            prompt_tokens=100,
            budget=budget,
            source_lineage={"direct_input": 60, "task_context": 40},
            construction_time_ms=5.0,
        )
        assert pkt.budget.max_context_tokens == 2500
        assert pkt.prompt_tokens <= pkt.budget.max_context_tokens

    def test_packet_rejects_oversized_prompt_against_real_budget(self):
        from meridian_core.prompt_budget import prompt_budget_for_risk_tier

        budget = prompt_budget_for_risk_tier(0)
        with pytest.raises(PromptPacketValidationError, match="exceeds budget"):
            build_prompt_packet(
                packet_id="pkt-overflow",
                serialized_prompt="x" * 10,
                prompt_tokens=budget.max_context_tokens + 1,
                budget=budget,
                source_lineage={},
                construction_time_ms=1.0,
            )
