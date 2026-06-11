"""Tests for Prime/Relay Auto routing evidence (BR7)."""

from __future__ import annotations

import pytest

from meridian_core.relay import RoutingMode
from meridian_core.relay_auto_routing import (
    PrimeRelayAutoRoutingEvidence,
    PrimeRelayAutoRoutingRequest,
    build_prime_relay_auto_routing_evidence,
)


_PROMPT = "Review the selected Meridian task and return a concise proof plan."


def _request(tier: int = 2) -> PrimeRelayAutoRoutingRequest:
    return PrimeRelayAutoRoutingRequest(
        request_id="prime-auto-001",
        requested_by="prime",
        prime_intent_ref="prime-intent:001",
        project_ref="compass-project:meridian",
        action_type="VERIFY",
        call_goal="Verify whether a backend-only BR7 slice is safe to promote.",
        expected_output_shape="pass-fail-with-evidence",
        risk_tier=tier,
        proof_requirement="Relay route evidence and PromptPacket proof metadata",
        disallowed_outputs=("raw_prompt_text", "provider_credentials"),
        evidence_refs=("aegis-proof:clean", "compass-project:meridian"),
    )


class TestPrimeRelayAutoRoutingRequest:
    def test_requires_request_identity(self):
        with pytest.raises(ValueError, match="request_id is required"):
            PrimeRelayAutoRoutingRequest(
                request_id="",
                requested_by="prime",
                prime_intent_ref="prime-intent:001",
                call_goal="Verify a route",
                expected_output_shape="finding-list",
                risk_tier=1,
                proof_requirement="packet proof",
            )

    def test_rejects_unknown_risk_tier(self):
        with pytest.raises(ValueError, match="risk_tier"):
            _request(5)

    def test_tuple_normalizes_sequences(self):
        request = PrimeRelayAutoRoutingRequest(
            request_id="prime-auto-002",
            requested_by="prime",
            prime_intent_ref="prime-intent:002",
            call_goal="Route a model call",
            expected_output_shape="summary",
            risk_tier=1,
            proof_requirement="packet proof",
            disallowed_outputs=["raw_prompt"],  # type: ignore[arg-type]
            evidence_refs=["aegis-proof:clean"],  # type: ignore[arg-type]
        )
        assert request.disallowed_outputs == ("raw_prompt",)
        assert request.evidence_refs == ("aegis-proof:clean",)


class TestPrimeRelayAutoRoutingEvidence:
    def test_returns_plan_with_display_safe_evidence(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(),
            serialized_prompt=_PROMPT,
        )
        assert isinstance(plan.evidence, PrimeRelayAutoRoutingEvidence)
        assert plan.evidence.evidence_id == "relay-auto-routing:prime-auto-001"

    def test_relay_chooses_route_from_prime_constraints(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(2),
            serialized_prompt=_PROMPT,
        )
        assert plan.route.mode is RoutingMode.DUAL_LANE
        assert plan.evidence.route_mode == "dual-lane"
        assert plan.evidence.risk_tier == 2
        assert plan.evidence.requires_independence is True
        assert plan.evidence.lane_count == 2

    def test_tier_zero_produces_no_model_lanes(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(0),
            serialized_prompt=_PROMPT,
        )
        assert plan.evidence.route_mode == "no-model"
        assert plan.evidence.lane_count == 0
        assert plan.evidence.lanes == ()

    def test_tier_four_preserves_human_gate(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(4),
            serialized_prompt=_PROMPT,
        )
        assert plan.evidence.route_mode == "human-gate"
        assert plan.evidence.requires_human_gate is True
        assert "human_gate_approval" in plan.evidence.proof_required

    def test_packet_proof_metadata_is_exposed_without_prompt_text(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(),
            serialized_prompt=_PROMPT,
            packet_id="packet:auto:001",
        )
        evidence = plan.evidence.to_dict()
        assert evidence["packet_id"] == "packet:auto:001"
        assert evidence["packet_hash"]
        assert evidence["prompt_tokens"] > 0
        assert evidence["budget_compliant"] is True
        assert _PROMPT not in str(evidence)

    def test_provider_transport_and_ui_route_selection_are_not_authorized(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(),
            serialized_prompt=_PROMPT,
        )
        assert plan.evidence.provider_transport_authorized is False
        assert plan.evidence.ui_route_selection_authorized is False
        assert plan.evidence.raw_prompt_visible is False
        assert plan.evidence.raw_provider_response_visible is False

    def test_lane_evidence_uses_payload_refs_not_payload_text(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(3),
            serialized_prompt=_PROMPT,
        )
        assert plan.dispatch_plan.lanes[0].payload == _PROMPT
        lane_dicts = [lane.to_dict() for lane in plan.evidence.lanes]
        assert len(lane_dicts) == 3
        assert all(lane["payload_ref"] for lane in lane_dicts)
        assert _PROMPT not in str(lane_dicts)

    def test_request_intent_and_upstream_refs_are_preserved(self):
        plan = build_prime_relay_auto_routing_evidence(
            request=_request(),
            serialized_prompt=_PROMPT,
        )
        assert plan.evidence.requested_by == "prime"
        assert plan.evidence.prime_intent_ref == "prime-intent:001"
        assert plan.evidence.action_type == "VERIFY"
        assert plan.evidence.upstream_evidence_refs == (
            "aegis-proof:clean",
            "compass-project:meridian",
        )
        assert plan.evidence.disallowed_outputs == (
            "raw_prompt_text",
            "provider_credentials",
        )

    def test_rejects_request_field_that_repeats_raw_prompt(self):
        request = PrimeRelayAutoRoutingRequest(
            request_id="prime-auto-raw",
            requested_by="prime",
            prime_intent_ref="prime-intent:raw",
            call_goal=_PROMPT,
            expected_output_shape="summary",
            risk_tier=1,
            proof_requirement="packet proof",
        )
        with pytest.raises(ValueError, match="raw prompt"):
            build_prime_relay_auto_routing_evidence(
                request=request,
                serialized_prompt=_PROMPT,
            )

    def test_rejects_request_field_that_embeds_raw_prompt(self):
        request = PrimeRelayAutoRoutingRequest(
            request_id="prime-auto-embedded-raw",
            requested_by="prime",
            prime_intent_ref="prime-intent:embedded-raw",
            call_goal=f"Summarize this prompt: {_PROMPT}",
            expected_output_shape="summary",
            risk_tier=1,
            proof_requirement="packet proof",
        )
        with pytest.raises(ValueError, match="raw prompt"):
            build_prime_relay_auto_routing_evidence(
                request=request,
                serialized_prompt=_PROMPT,
            )

    def test_rejects_unsafe_private_data_in_display_evidence(self):
        request = PrimeRelayAutoRoutingRequest(
            request_id="prime-auto-secret",
            requested_by="prime",
            prime_intent_ref="prime-intent:secret",
            project_ref="C:\\Users\\scott\\private",
            call_goal="Route a safe request",
            expected_output_shape="summary",
            risk_tier=1,
            proof_requirement="packet proof",
        )
        with pytest.raises(ValueError, match="unsafe private data"):
            build_prime_relay_auto_routing_evidence(
                request=request,
                serialized_prompt=_PROMPT,
            )

    def test_rejects_unsafe_disallowed_output_entry(self):
        request = PrimeRelayAutoRoutingRequest(
            request_id="prime-auto-disallowed-secret",
            requested_by="prime",
            prime_intent_ref="prime-intent:disallowed-secret",
            call_goal="Route a safe request",
            expected_output_shape="summary",
            risk_tier=1,
            proof_requirement="packet proof",
            disallowed_outputs=("never expose C:\\Users\\scott\\secret.txt",),
        )
        with pytest.raises(ValueError, match="unsafe private data"):
            build_prime_relay_auto_routing_evidence(
                request=request,
                serialized_prompt=_PROMPT,
            )
