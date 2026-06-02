"""Tests for the Relay PromptPacket assembly helper (meridian_core/relay_packet.py)."""

from __future__ import annotations

import pytest

from meridian_core.prompt_packet import PromptPacket, PromptPacketValidationError
from meridian_core.relay import route_from_tier
from meridian_core.relay_packet import assemble_relay_packet
from meridian_core.tokens import count_tokens


_PROMPT = "Analyze this task context and produce a structured plan."


class TestAssembleRelayPacketBasic:
    def test_returns_prompt_packet(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert isinstance(packet, PromptPacket)

    def test_model_payload_returns_prompt(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.model_payload() == _PROMPT

    def test_packet_id_is_preserved(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="relay-test-001", serialized_prompt=_PROMPT, route=route)
        assert packet.packet_id == "relay-test-001"

    def test_budget_comes_from_route(self):
        route = route_from_tier(2)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.budget is route.prompt_budget

    def test_construction_time_defaults_to_zero(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.construction_time_ms == 0.0

    def test_construction_time_can_be_set(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(
            packet_id="pkt-1",
            serialized_prompt=_PROMPT,
            route=route,
            construction_time_ms=42.5,
        )
        assert packet.construction_time_ms == 42.5

    def test_proof_metadata_uses_route_proof_requirements(self):
        route = route_from_tier(3)
        packet = assemble_relay_packet(
            packet_id="pkt-proof",
            serialized_prompt=_PROMPT,
            route=route,
        )

        assert packet.proof_required == tuple(route.audit.proof_required)
        assert packet.proof_metadata.proof_required == tuple(route.audit.proof_required)
        assert packet.proof_metadata.prompt_budget_ref == (
            f"prompt-budget:{route.prompt_budget.tier.value}:"
            f"{route.prompt_budget.max_context_tokens}"
        )

    def test_proof_metadata_does_not_change_model_payload(self):
        route = route_from_tier(3)
        packet = assemble_relay_packet(
            packet_id="pkt-proof",
            serialized_prompt=_PROMPT,
            route=route,
        )

        assert packet.model_payload() == _PROMPT
        assert packet.proof_metadata.packet_hash not in packet.model_payload()


class TestAssembleRelayPacketTokens:
    def test_prompt_tokens_matches_count_tokens(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.prompt_tokens == count_tokens(_PROMPT)

    def test_prompt_tokens_is_non_negative(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.prompt_tokens >= 0

    def test_prompt_tokens_reflects_prompt_length(self):
        route = route_from_tier(2)
        short_prompt = "Hello world."
        long_prompt = "Hello world. " * 20
        short_packet = assemble_relay_packet(packet_id="pkt-s", serialized_prompt=short_prompt, route=route)
        long_packet = assemble_relay_packet(packet_id="pkt-l", serialized_prompt=long_prompt, route=route)
        assert long_packet.prompt_tokens > short_packet.prompt_tokens


class TestAssembleRelayPacketLineage:
    def test_default_lineage_is_direct_input(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert set(packet.source_lineage.keys()) == {"direct_input"}

    def test_default_lineage_token_count_matches_prompt_tokens(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        assert packet.source_lineage["direct_input"] == packet.prompt_tokens

    def test_custom_lineage_is_used(self):
        route = route_from_tier(1)
        tokens = count_tokens(_PROMPT)
        lineage = {"task_context": tokens}
        packet = assemble_relay_packet(
            packet_id="pkt-1",
            serialized_prompt=_PROMPT,
            route=route,
            source_lineage=lineage,
        )
        assert packet.source_lineage["task_context"] == tokens

    def test_lineage_is_immutable(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        with pytest.raises(TypeError):
            packet.source_lineage["new_key"] = 1  # type: ignore[index]


class TestAssembleRelayPacketValidation:
    def test_empty_packet_id_raises(self):
        route = route_from_tier(1)
        with pytest.raises(PromptPacketValidationError):
            assemble_relay_packet(packet_id="", serialized_prompt=_PROMPT, route=route)

    def test_over_budget_prompt_raises(self):
        route = route_from_tier(0)  # max 500 tokens
        long_prompt = " ".join(["word"] * 600)
        with pytest.raises(PromptPacketValidationError):
            assemble_relay_packet(packet_id="pkt-1", serialized_prompt=long_prompt, route=route)

    def test_invalid_lineage_source_raises(self):
        route = route_from_tier(1)  # allowed: direct_input, task_context
        tokens = count_tokens(_PROMPT)
        with pytest.raises(PromptPacketValidationError):
            assemble_relay_packet(
                packet_id="pkt-1",
                serialized_prompt=_PROMPT,
                route=route,
                source_lineage={"disallowed_source": tokens},
            )

    def test_packet_is_frozen(self):
        route = route_from_tier(1)
        packet = assemble_relay_packet(packet_id="pkt-1", serialized_prompt=_PROMPT, route=route)
        with pytest.raises((AttributeError, TypeError)):
            packet.packet_id = "mutated"  # type: ignore[misc]

    def test_whitespace_prompt_raises(self):
        route = route_from_tier(1)
        with pytest.raises(PromptPacketValidationError):
            assemble_relay_packet(packet_id="pkt-1", serialized_prompt="   ", route=route)
