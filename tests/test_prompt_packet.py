"""Tests for the Prompt Packet domain model (meridian_core/prompt_packet.py)."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from meridian_core.prompt_budget import PromptBudgetPlan, PromptBudgetTier
from meridian_core.prompt_packet import (
    PromptPacket,
    PromptPacketProofMetadata,
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

    def test_whitespace_only_prompt_raises(self):
        with pytest.raises(PromptPacketValidationError, match="empty"):
            build_prompt_packet(**_kwargs(serialized_prompt="   "))

    def test_empty_packet_id_raises(self):
        with pytest.raises(PromptPacketValidationError, match="Packet ID is empty"):
            build_prompt_packet(**_kwargs(packet_id=""))

    def test_zero_prompt_tokens_is_valid(self):
        pkt = build_prompt_packet(**_kwargs(
            prompt_tokens=0,
            source_lineage={},
        ))
        assert pkt.prompt_tokens == 0


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


class TestPromptPacketProofMetadata:
    def test_proof_metadata_is_built_from_validated_packet(self):
        pkt = build_prompt_packet(
            **_kwargs(
                proof_required=("unit-test-proof",),
                aegis_evidence_ids=("aegis-1",),
            )
        )

        metadata = pkt.proof_metadata
        assert isinstance(metadata, PromptPacketProofMetadata)
        assert metadata.packet_id == pkt.packet_id
        assert metadata.prompt_tokens == pkt.prompt_tokens
        assert metadata.prompt_budget_ref == "prompt-budget:focused:500"
        assert metadata.source_lineage_compliant is True
        assert metadata.budget_compliant is True
        assert metadata.proof_required == ("unit-test-proof",)
        assert metadata.aegis_evidence_ids == ("aegis-1",)
        assert metadata.blocked_tags == ()

    def test_proof_metadata_hashes_prompt_without_storing_raw_prompt(self):
        pkt = build_prompt_packet(**_kwargs())

        metadata = pkt.proof_metadata
        assert metadata is not None
        assert metadata.packet_hash == metadata.prompt_payload_snapshot_hash
        assert pkt.serialized_prompt not in " ".join(
            str(value) for value in metadata.to_dict().values()
        )

    def test_proof_metadata_to_dict_has_stable_keys(self):
        pkt = build_prompt_packet(**_kwargs())

        metadata_dict = pkt.proof_metadata.to_dict()

        assert metadata_dict == pkt.proof_metadata.to_dict()
        assert tuple(metadata_dict.keys()) == (
            "packet_id",
            "packet_hash",
            "prompt_tokens",
            "budget_tier",
            "prompt_budget_ref",
            "max_context_tokens",
            "allowed_sources",
            "source_lineage_keys",
            "source_lineage_total_tokens",
            "source_lineage_compliant",
            "budget_compliant",
            "proof_required",
            "aegis_evidence_ids",
            "prompt_payload_snapshot_hash",
            "snapshot_hash_available",
            "snapshot_hash_gap_tags",
            "blocked_tags",
        )


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


# ---------------------------------------------------------------------------
# Direct construction — validation must fire even without build_prompt_packet
# ---------------------------------------------------------------------------


class TestPromptPacketDirectConstruction:
    def test_direct_construction_with_valid_data_succeeds(self):
        from types import MappingProxyType
        pkt = PromptPacket(
            packet_id="direct-001",
            serialized_prompt="Direct construction test.",
            prompt_tokens=5,
            budget=_budget(),
            source_lineage={"direct_input": 5},
            construction_time_ms=1.0,
        )
        assert pkt.packet_id == "direct-001"

    def test_direct_construction_with_empty_prompt_raises(self):
        with pytest.raises(PromptPacketValidationError, match="empty"):
            PromptPacket(
                packet_id="bad",
                serialized_prompt="",
                prompt_tokens=0,
                budget=_budget(),
                source_lineage={},
                construction_time_ms=0.0,
            )

    def test_direct_construction_with_non_string_prompt_raises(self):
        with pytest.raises(PromptPacketValidationError, match="string"):
            PromptPacket(
                packet_id="bad",
                serialized_prompt=12345,  # type: ignore[arg-type]
                prompt_tokens=5,
                budget=_budget(),
                source_lineage={},
                construction_time_ms=0.0,
            )

    def test_direct_construction_converts_dict_to_mapping_proxy(self):
        pkt = PromptPacket(
            packet_id="direct-002",
            serialized_prompt="Test.",
            prompt_tokens=1,
            budget=_budget(),
            source_lineage={"direct_input": 1},
            construction_time_ms=0.5,
        )
        assert isinstance(pkt.source_lineage, MappingProxyType)

    def test_direct_construction_input_dict_not_aliased(self):
        lineage = {"direct_input": 3}
        pkt = PromptPacket(
            packet_id="direct-003",
            serialized_prompt="Test.",
            prompt_tokens=3,
            budget=_budget(),
            source_lineage=lineage,
            construction_time_ms=0.5,
        )
        lineage["injected"] = 999
        assert "injected" not in pkt.source_lineage

    def test_helper_still_works_after_refactor(self):
        pkt = build_prompt_packet(**_kwargs())
        assert isinstance(pkt, PromptPacket)
        assert isinstance(pkt.source_lineage, MappingProxyType)


# ---------------------------------------------------------------------------
# Model-dispatch boundary — model_payload() returns only serialized_prompt
# ---------------------------------------------------------------------------


class TestModelDispatchBoundary:
    def test_model_payload_returns_serialized_prompt(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.model_payload() == pkt.serialized_prompt

    def test_model_payload_is_exact_string(self):
        prompt = "Evaluate the risk tier for this action."
        pkt = build_prompt_packet(**_kwargs(serialized_prompt=prompt))
        assert pkt.model_payload() == prompt

    def test_model_payload_excludes_packet_id(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.packet_id not in pkt.model_payload()

    def test_model_payload_excludes_construction_time(self):
        pkt = build_prompt_packet(**_kwargs(construction_time_ms=99.9))
        assert "99.9" not in pkt.model_payload()

    def test_model_payload_excludes_budget_reason(self):
        pkt = build_prompt_packet(**_kwargs())
        assert pkt.budget.reason not in pkt.model_payload()

    def test_model_payload_excludes_source_lineage_keys(self):
        pkt = build_prompt_packet(**_kwargs())
        for source in pkt.source_lineage:
            assert source not in pkt.model_payload()

    def test_model_payload_excludes_prompt_tokens_count(self):
        pkt = build_prompt_packet(**_kwargs(prompt_tokens=10))
        assert str(pkt.prompt_tokens) not in pkt.model_payload()

    def test_model_payload_is_str(self):
        pkt = build_prompt_packet(**_kwargs())
        assert isinstance(pkt.model_payload(), str)

    def test_validation_still_works_with_dispatch_method(self):
        with pytest.raises(PromptPacketValidationError):
            build_prompt_packet(**_kwargs(serialized_prompt=""))
