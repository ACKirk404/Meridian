"""Tests for V2.5 Relay/Model dispatch evidence."""

from __future__ import annotations

import hashlib

from meridian_core.dispatch_evidence import (
    DispatchEvidenceValidationStatus,
    RouteReplayMetadata,
    RouteSimulation,
    RouteSimulationLane,
    ProviderHealthStatus,
    ProviderIdentityProof,
    RouteConfidenceLabel,
    TrustExpirationStatus,
    build_dispatch_evidence,
    hash_prompt_payload,
    provider_identity_proof_from_metadata,
    simulate_route_dispatch,
)
from meridian_core.model_adapter import FakeModelAdapter, ModelHarnessMetadata
from meridian_core.relay import route_from_tier
from meridian_core.relay_packet import assemble_relay_packet


_PROMPT = "raw prompt body that must never appear in display evidence"


def _packet():
    route = route_from_tier(1)
    return assemble_relay_packet(
        packet_id="DISPATCH-EVIDENCE-PACKET",
        serialized_prompt=_PROMPT,
        route=route,
    )


def _metadata(
    *,
    model_name: str = "fast-default",
    trust_state: str = "trusted",
) -> ModelHarnessMetadata:
    return ModelHarnessMetadata(
        provider_name="test-provider",
        model_name=model_name,
        capability_tier="standard",
        context_budget=4096,
        prompt_payload_budget=2048,
        trust_state=trust_state,
        requires_external_review=False,
    )


def test_route_simulation_makes_no_provider_call():
    route = route_from_tier(1)
    adapter = FakeModelAdapter(response="should not be called", metadata=_metadata())

    simulation = simulate_route_dispatch(
        route,
        providers_by_model={"fast-default": adapter},
    )

    assert adapter.received_payloads == []
    assert simulation.no_provider_call is True
    assert simulation.replay_metadata.no_provider_call is True
    assert simulation.lanes[0].provider_ref == "provider:test-provider:fast-default"


def test_payload_hash_contract_never_stores_prompt_body():
    packet = _packet()
    record = hash_prompt_payload(packet)
    display = record.to_display_dict()

    assert record.sha256 == hashlib.sha256(_PROMPT.encode("utf-8")).hexdigest()
    assert display["payload_ref"] == "prompt-payload:DISPATCH-EVIDENCE-PACKET"
    assert display["prompt_body_stored"] is False
    assert _PROMPT not in str(display)
    assert "raw prompt body" not in str(display)


def test_direct_payload_hash_display_sanitizes_unsafe_digest():
    record = hash_prompt_payload("safe payload")
    unsafe = type(record)(
        payload_ref=record.payload_ref,
        sha256="api_key=abcdef1234567890",
        byte_length=record.byte_length,
    )

    display = unsafe.to_display_dict()

    assert display["sha256"] == "[redacted]"
    assert "abcdef1234567890" not in str(display)


def test_trust_state_expiration_blocks_route_confidence():
    route = route_from_tier(1)
    proof = provider_identity_proof_from_metadata(
        _metadata(),
        health_status=ProviderHealthStatus.HEALTHY,
        observed_at_epoch=100,
        trust_max_age_seconds=30,
    )

    assert proof.trust_expiration_status(now_epoch=129) is TrustExpirationStatus.ACTIVE
    assert proof.trust_expiration_status(now_epoch=130) is TrustExpirationStatus.EXPIRED

    simulation = simulate_route_dispatch(
        route,
        providers_by_model={"fast-default": proof},
        now_epoch=130,
    )

    assert simulation.confidence_label is RouteConfidenceLabel.BLOCKED
    assert simulation.lanes[0].confidence_label is RouteConfidenceLabel.BLOCKED


def test_evidence_chain_displays_intent_payload_provider_response_validation_refs():
    route = route_from_tier(1)
    packet = _packet()
    proof = provider_identity_proof_from_metadata(
        _metadata(),
        health_status=ProviderHealthStatus.HEALTHY,
    )

    evidence = build_dispatch_evidence(
        intent_ref="intent:rank-9",
        route=route,
        packet=packet,
        providers_by_model={"fast-default": proof},
        response_ref="provider-response:not-called",
        validation_ref="validation:simulated",
    )

    chain = evidence.evidence_chain.to_display_dict()
    assert chain["sequence"] == (
        "intent:rank-9",
        "prompt-payload:DISPATCH-EVIDENCE-PACKET",
        "provider:test-provider:fast-default",
        "provider-response:not-called",
        "validation:simulated",
    )
    assert evidence.validation_status is DispatchEvidenceValidationStatus.SIMULATED


def test_fallback_explanation_is_display_safe_and_deterministic():
    route = route_from_tier(2)

    simulation = simulate_route_dispatch(route, providers_by_model={})
    display = simulation.to_display_dict()

    assert simulation.confidence_label is RouteConfidenceLabel.LOW
    assert simulation.fallback_explanations[0].reason == (
        "route audit carries fallback blockers"
    )
    assert "unknown_trust_route" in simulation.fallback_explanations[0].blocker_tags
    assert display == simulation.to_display_dict()
    assert _PROMPT not in str(display)


def test_provider_identity_health_proof_is_display_safe():
    proof = ProviderIdentityProof(
        provider_ref="provider:direct:test-model",
        provider_name="direct",
        model_name="test-model",
        capability_tier="candidate",
        trust_state="candidate",
        health_status=ProviderHealthStatus.DEGRADED,
        evidence_refs=("provider-health:test-model:degraded",),
        observed_at_epoch=10,
        expires_at_epoch=20,
    )

    display = proof.to_display_dict(now_epoch=19)
    assert display["health_status"] == "degraded"
    assert display["trust_expiration_status"] == "active"
    assert display["provider_response_stored"] is False
    assert "provider response:" not in str(display).lower()


def test_dispatch_evidence_display_dict_leaks_no_prompt_or_response_body():
    route = route_from_tier(1)
    packet = _packet()
    response_body = "provider response body that must not leak"
    evidence = build_dispatch_evidence(
        intent_ref="intent:leak-check",
        route=route,
        packet=packet,
        providers_by_model={"fast-default": _metadata()},
    )

    display = evidence.to_display_dict()
    rendered = str(display)

    assert display["provider_response_stored"] is False
    assert display["payload_hash"]["prompt_body_stored"] is False
    assert _PROMPT not in rendered
    assert response_body not in rendered
    assert "provider response body" not in rendered
    assert "sha256" in rendered


def test_dispatch_display_sanitizes_unsafe_refs_and_provider_metadata():
    class UnsafePacket:
        packet_id = r"C:\Users\scott\secret-packet"

        def model_payload(self) -> str:
            return "safe payload body"

    proof = ProviderIdentityProof(
        provider_ref=r"C:\Users\scott\provider",
        provider_name=r"C:\Users\scott\secret-provider",
        model_name="/home/scott/model",
        capability_tier="api_key=abcdef1234567890",
        trust_state="provider response: private body",
        health_status=ProviderHealthStatus.HEALTHY,
        evidence_refs=("token=abcdef1234567890",),
    )
    evidence = build_dispatch_evidence(
        intent_ref=r"C:\Users\scott\intent",
        route=route_from_tier(1),
        packet=UnsafePacket(),
        providers_by_model={"fast-default": proof},
        response_ref="provider response: private body",
        validation_ref="/home/scott/validation",
    )

    rendered = str(evidence.to_display_dict())

    assert r"C:\Users" not in rendered
    assert "/home/scott" not in rendered
    assert "abcdef1234567890" not in rendered
    assert "private body" not in rendered
    assert "provider:redacted" in rendered
    assert "prompt-payload:redacted" in rendered


def test_direct_route_simulation_display_sanitizes_route_ref():
    simulation = RouteSimulation(
        route_ref=r"C:\Users\scott\secret_raw_prompt.txt",
        confidence_label=RouteConfidenceLabel.LOW,
        no_provider_call=True,
        lanes=(
            RouteSimulationLane(
                role="primary",
                preferred_model="fast-default",
                independent=False,
                provider_ref=None,
                provider_health_status="unknown",
                confidence_label=RouteConfidenceLabel.LOW,
            ),
        ),
        fallback_explanations=(),
        replay_metadata=RouteReplayMetadata(
            route_ref="relay-route:safe",
            route_mode="direct",
            risk_tier=1,
            lane_roles=("primary",),
            selected_models=("fast-default",),
            route_reason_ref="route-reason:safe",
        ),
    )

    rendered = str(simulation.to_display_dict())

    assert r"C:\Users" not in rendered
    assert "secret_raw_prompt" not in rendered
    assert simulation.to_display_dict()["route_ref"] == "relay-route:redacted"
