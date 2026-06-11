"""
Prime/Relay Auto routing evidence.

This module gives Prime a bounded request shape for "Auto" routing while
keeping route selection, prompt packet construction, and dispatch evidence
owned by Relay/Model Harness. It is pure domain logic: no model calls, no UI
bridge routes, no provider transport, and no raw prompt text in evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .relay import RelayRoute, route_from_tier
from .relay_dispatch import RelayDispatchPlan, build_relay_dispatch_plan
from .relay_packet import assemble_relay_packet


_UNSAFE_DISPLAY_PATTERNS = (
    re.compile(r"\b(?:api[_-]?key|secret|credential|password|token)\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/(?:Users|home|mnt|var|tmp)/"),
)


@dataclass(frozen=True)
class PrimeRelayAutoRoutingRequest:
    """Prime-owned intent and constraints for one governed model-call request."""

    request_id: str
    requested_by: str
    prime_intent_ref: str
    call_goal: str
    expected_output_shape: str
    risk_tier: int
    proof_requirement: str
    project_ref: str | None = None
    action_type: str = "EXPLAIN"
    disallowed_outputs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "request_id",
            "requested_by",
            "prime_intent_ref",
            "call_goal",
            "expected_output_shape",
            "proof_requirement",
            "action_type",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} is required")
        if self.risk_tier < 0 or self.risk_tier > 4:
            raise ValueError("risk_tier must be between 0 and 4")
        object.__setattr__(self, "disallowed_outputs", tuple(self.disallowed_outputs))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class PrimeRelayAutoRoutingLaneEvidence:
    """Display-safe evidence for one Relay-selected dispatch lane."""

    lane_id: str
    role: str
    preferred_model: str
    independent: bool
    payload_ref: str

    def to_dict(self) -> dict[str, object]:
        return {
            "lane_id": self.lane_id,
            "role": self.role,
            "preferred_model": self.preferred_model,
            "independent": self.independent,
            "payload_ref": self.payload_ref,
        }


@dataclass(frozen=True)
class PrimeRelayAutoRoutingEvidence:
    """Display-safe BR7 evidence owned by Relay/Model Harness."""

    evidence_id: str
    request_id: str
    requested_by: str
    prime_intent_ref: str
    project_ref: str | None
    action_type: str
    call_goal: str
    expected_output_shape: str
    risk_tier: int
    proof_requirement: str
    route_mode: str
    context_strategy: str
    cost_posture: str
    requires_independence: bool
    requires_human_gate: bool
    route_reason: str
    route_class: str | None
    route_kind: str
    trust_state: str
    prompt_budget_ref: str
    packet_id: str
    packet_hash: str
    prompt_tokens: int
    budget_compliant: bool
    source_lineage_keys: tuple[str, ...]
    source_lineage_compliant: bool
    lane_count: int
    lanes: tuple[PrimeRelayAutoRoutingLaneEvidence, ...]
    proof_required: tuple[str, ...]
    disallowed_outputs: tuple[str, ...]
    upstream_evidence_refs: tuple[str, ...]
    raw_prompt_visible: bool = False
    raw_provider_response_visible: bool = False
    provider_transport_authorized: bool = False
    ui_route_selection_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "request_id": self.request_id,
            "requested_by": self.requested_by,
            "prime_intent_ref": self.prime_intent_ref,
            "project_ref": self.project_ref,
            "action_type": self.action_type,
            "call_goal": self.call_goal,
            "expected_output_shape": self.expected_output_shape,
            "risk_tier": self.risk_tier,
            "proof_requirement": self.proof_requirement,
            "route_mode": self.route_mode,
            "context_strategy": self.context_strategy,
            "cost_posture": self.cost_posture,
            "requires_independence": self.requires_independence,
            "requires_human_gate": self.requires_human_gate,
            "route_reason": self.route_reason,
            "route_class": self.route_class,
            "route_kind": self.route_kind,
            "trust_state": self.trust_state,
            "prompt_budget_ref": self.prompt_budget_ref,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "prompt_tokens": self.prompt_tokens,
            "budget_compliant": self.budget_compliant,
            "source_lineage_keys": self.source_lineage_keys,
            "source_lineage_compliant": self.source_lineage_compliant,
            "lane_count": self.lane_count,
            "lanes": tuple(lane.to_dict() for lane in self.lanes),
            "proof_required": self.proof_required,
            "disallowed_outputs": self.disallowed_outputs,
            "upstream_evidence_refs": self.upstream_evidence_refs,
            "raw_prompt_visible": self.raw_prompt_visible,
            "raw_provider_response_visible": self.raw_provider_response_visible,
            "provider_transport_authorized": self.provider_transport_authorized,
            "ui_route_selection_authorized": self.ui_route_selection_authorized,
        }


@dataclass(frozen=True)
class PrimeRelayAutoRoutingPlan:
    """Relay-owned Auto route plan plus display-safe evidence."""

    request: PrimeRelayAutoRoutingRequest
    route: RelayRoute
    dispatch_plan: RelayDispatchPlan
    evidence: PrimeRelayAutoRoutingEvidence


def build_prime_relay_auto_routing_evidence(
    *,
    request: PrimeRelayAutoRoutingRequest,
    serialized_prompt: str,
    packet_id: str | None = None,
) -> PrimeRelayAutoRoutingPlan:
    """Build a deterministic Relay-owned Auto routing plan and evidence record.

    The serialized prompt is used only to construct Relay's validated
    PromptPacket and lane payloads. It is intentionally excluded from
    PrimeRelayAutoRoutingEvidence.
    """
    _assert_request_display_safe(request, serialized_prompt)
    route = route_from_tier(request.risk_tier)
    resolved_packet_id = packet_id or f"auto-route:{request.request_id}"
    packet = assemble_relay_packet(
        packet_id=resolved_packet_id,
        serialized_prompt=serialized_prompt,
        route=route,
    )
    dispatch_plan = build_relay_dispatch_plan(route, packet)
    assert packet.proof_metadata is not None

    lane_evidence = tuple(
        PrimeRelayAutoRoutingLaneEvidence(
            lane_id=f"{resolved_packet_id}:lane:{idx}",
            role=lane.role.value,
            preferred_model=lane.preferred_model,
            independent=lane.independent,
            payload_ref=f"prompt-packet:{resolved_packet_id}:model-payload",
        )
        for idx, lane in enumerate(dispatch_plan.lanes)
    )

    route_class = route.audit.route_class.value if route.audit.route_class else None
    evidence = PrimeRelayAutoRoutingEvidence(
        evidence_id=f"relay-auto-routing:{request.request_id}",
        request_id=request.request_id,
        requested_by=request.requested_by,
        prime_intent_ref=request.prime_intent_ref,
        project_ref=request.project_ref,
        action_type=request.action_type,
        call_goal=request.call_goal,
        expected_output_shape=request.expected_output_shape,
        risk_tier=request.risk_tier,
        proof_requirement=request.proof_requirement,
        route_mode=route.mode.value,
        context_strategy=route.context_strategy.value,
        cost_posture=route.cost_posture.value,
        requires_independence=route.requires_independence,
        requires_human_gate=route.requires_human_gate,
        route_reason=route.reason,
        route_class=route_class,
        route_kind=route.audit.route_kind.value,
        trust_state=route.audit.trust_state.value,
        prompt_budget_ref=packet.proof_metadata.prompt_budget_ref,
        packet_id=packet.proof_metadata.packet_id,
        packet_hash=packet.proof_metadata.packet_hash,
        prompt_tokens=packet.proof_metadata.prompt_tokens,
        budget_compliant=packet.proof_metadata.budget_compliant,
        source_lineage_keys=packet.proof_metadata.source_lineage_keys,
        source_lineage_compliant=packet.proof_metadata.source_lineage_compliant,
        lane_count=len(lane_evidence),
        lanes=lane_evidence,
        proof_required=tuple(route.audit.proof_required),
        disallowed_outputs=request.disallowed_outputs,
        upstream_evidence_refs=request.evidence_refs,
    )
    return PrimeRelayAutoRoutingPlan(
        request=request,
        route=route,
        dispatch_plan=dispatch_plan,
        evidence=evidence,
    )


def _assert_request_display_safe(
    request: PrimeRelayAutoRoutingRequest,
    serialized_prompt: str,
) -> None:
    """Reject request fields that would make BR7 evidence unsafe to render."""
    if not isinstance(serialized_prompt, str) or not serialized_prompt.strip():
        raise ValueError("serialized_prompt is required")
    prompt = serialized_prompt.strip()
    fields = (
        request.request_id,
        request.requested_by,
        request.prime_intent_ref,
        request.project_ref or "",
        request.action_type,
        request.call_goal,
        request.expected_output_shape,
        request.proof_requirement,
        *request.evidence_refs,
        *request.disallowed_outputs,
    )
    for value in fields:
        if not value:
            continue
        if prompt in value.strip():
            raise ValueError("display evidence must not repeat raw prompt text")
        for pattern in _UNSAFE_DISPLAY_PATTERNS:
            if pattern.search(value):
                raise ValueError("display evidence contains unsafe private data")
