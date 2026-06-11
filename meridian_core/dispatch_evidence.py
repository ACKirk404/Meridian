"""Display-safe Relay/Model dispatch evidence for V2.5.

This module is pure evidence construction. It never calls providers, performs
IO, stores raw prompt bodies, or stores raw provider responses.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol

from .relay import RelayRoute, RouteTrustState, RoutingMode


class RouteConfidenceLabel(Enum):
    NO_MODEL = "no-model"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BLOCKED = "blocked"


class ProviderHealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class TrustExpirationStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    NEVER_EXPIRES = "never-expires"
    UNKNOWN = "unknown"


class DispatchEvidenceValidationStatus(Enum):
    SIMULATED = "simulated"
    VALIDATED = "validated"
    BLOCKED = "blocked"


class _PacketLike(Protocol):
    packet_id: str

    def model_payload(self) -> str: ...


@dataclass(frozen=True)
class PromptPayloadHashRecord:
    """Hash-only proof for a prompt payload; the prompt body is not retained."""

    payload_ref: str
    sha256: str
    byte_length: int
    algorithm: str = "sha256"
    prompt_body_stored: bool = False

    def to_display_dict(self) -> dict[str, object]:
        return {
            "payload_ref": _safe_ref(self.payload_ref, "prompt-payload:redacted"),
            "algorithm": _safe_label(self.algorithm),
            "sha256": _safe_digest(self.sha256),
            "byte_length": self.byte_length,
            "prompt_body_stored": self.prompt_body_stored,
        }


@dataclass(frozen=True)
class ProviderIdentityProof:
    """Display-safe provider identity, capability, health, and trust proof."""

    provider_ref: str
    provider_name: str
    model_name: str
    capability_tier: str
    trust_state: str
    health_status: ProviderHealthStatus
    evidence_refs: tuple[str, ...] = ()
    observed_at_epoch: int | None = None
    expires_at_epoch: int | None = None
    provider_response_stored: bool = False

    def trust_expiration_status(self, *, now_epoch: int | None = None) -> TrustExpirationStatus:
        if self.expires_at_epoch is None:
            return TrustExpirationStatus.NEVER_EXPIRES
        if now_epoch is None:
            return TrustExpirationStatus.UNKNOWN
        if now_epoch >= self.expires_at_epoch:
            return TrustExpirationStatus.EXPIRED
        return TrustExpirationStatus.ACTIVE

    def is_trust_expired(self, *, now_epoch: int) -> bool:
        return self.trust_expiration_status(now_epoch=now_epoch) is TrustExpirationStatus.EXPIRED

    def to_display_dict(self, *, now_epoch: int | None = None) -> dict[str, object]:
        return {
            "provider_ref": _safe_ref(self.provider_ref, "provider:redacted"),
            "provider_name": _safe_label(self.provider_name),
            "model_name": _safe_label(self.model_name),
            "capability_tier": _safe_label(self.capability_tier),
            "trust_state": _safe_label(self.trust_state),
            "health_status": self.health_status.value,
            "evidence_refs": tuple(
                _safe_ref(ref, "evidence:redacted") for ref in self.evidence_refs
            ),
            "observed_at_epoch": self.observed_at_epoch,
            "expires_at_epoch": self.expires_at_epoch,
            "trust_expiration_status": self.trust_expiration_status(
                now_epoch=now_epoch
            ).value,
            "provider_response_stored": self.provider_response_stored,
        }


@dataclass(frozen=True)
class FallbackExplanation:
    """Deterministic explanation of a selected or rejected fallback path."""

    from_route: str
    to_route: str
    reason: str
    blocker_tags: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_display_dict(self) -> dict[str, object]:
        return {
            "from_route": _safe_label(self.from_route),
            "to_route": _safe_label(self.to_route),
            "reason": _safe_label(self.reason),
            "blocker_tags": tuple(_safe_label(tag) for tag in self.blocker_tags),
            "evidence_refs": tuple(
                _safe_ref(ref, "evidence:redacted") for ref in self.evidence_refs
            ),
        }


@dataclass(frozen=True)
class RouteReplayMetadata:
    """Stable replay/debug record that is safe to display."""

    route_ref: str
    route_mode: str
    risk_tier: int
    lane_roles: tuple[str, ...]
    selected_models: tuple[str, ...]
    route_reason_ref: str
    no_provider_call: bool = True

    def to_display_dict(self) -> dict[str, object]:
        return {
            "route_ref": _safe_ref(self.route_ref, "relay-route:redacted"),
            "route_mode": _safe_label(self.route_mode),
            "risk_tier": self.risk_tier,
            "lane_roles": tuple(_safe_label(role) for role in self.lane_roles),
            "selected_models": tuple(_safe_label(model) for model in self.selected_models),
            "route_reason_ref": _safe_ref(self.route_reason_ref, "route-reason:redacted"),
            "no_provider_call": self.no_provider_call,
        }


@dataclass(frozen=True)
class RouteSimulationLane:
    role: str
    preferred_model: str
    independent: bool
    provider_ref: str | None
    provider_health_status: str
    confidence_label: RouteConfidenceLabel
    fallback_explanation: FallbackExplanation | None = None

    def to_display_dict(self) -> dict[str, object]:
        return {
            "role": _safe_label(self.role),
            "preferred_model": _safe_label(self.preferred_model),
            "independent": self.independent,
            "provider_ref": (
                None
                if self.provider_ref is None
                else _safe_ref(self.provider_ref, "provider:redacted")
            ),
            "provider_health_status": _safe_label(self.provider_health_status),
            "confidence_label": self.confidence_label.value,
            "fallback_explanation": (
                self.fallback_explanation.to_display_dict()
                if self.fallback_explanation is not None
                else None
            ),
        }


@dataclass(frozen=True)
class RouteSimulation:
    route_ref: str
    confidence_label: RouteConfidenceLabel
    no_provider_call: bool
    lanes: tuple[RouteSimulationLane, ...]
    fallback_explanations: tuple[FallbackExplanation, ...]
    replay_metadata: RouteReplayMetadata

    def to_display_dict(self) -> dict[str, object]:
        return {
            "route_ref": _safe_ref(self.route_ref, "relay-route:redacted"),
            "confidence_label": self.confidence_label.value,
            "no_provider_call": self.no_provider_call,
            "lanes": tuple(lane.to_display_dict() for lane in self.lanes),
            "fallback_explanations": tuple(
                explanation.to_display_dict()
                for explanation in self.fallback_explanations
            ),
            "replay_metadata": self.replay_metadata.to_display_dict(),
        }


@dataclass(frozen=True)
class DispatchEvidenceChain:
    """Refs linking intent -> payload -> provider -> response -> validation."""

    intent_ref: str
    payload_ref: str
    provider_refs: tuple[str, ...]
    response_ref: str
    validation_ref: str

    def to_display_dict(self) -> dict[str, object]:
        intent_ref = _safe_ref(self.intent_ref, "intent:redacted")
        payload_ref = _safe_ref(self.payload_ref, "prompt-payload:redacted")
        provider_refs = tuple(
            _safe_ref(ref, "provider:redacted") for ref in self.provider_refs
        )
        response_ref = _safe_ref(self.response_ref, "provider-response:redacted")
        validation_ref = _safe_ref(self.validation_ref, "validation:redacted")
        return {
            "intent_ref": intent_ref,
            "payload_ref": payload_ref,
            "provider_refs": provider_refs,
            "response_ref": response_ref,
            "validation_ref": validation_ref,
            "sequence": (
                intent_ref,
                payload_ref,
                *provider_refs,
                response_ref,
                validation_ref,
            ),
        }


@dataclass(frozen=True)
class DispatchEvidence:
    payload_hash: PromptPayloadHashRecord
    route_simulation: RouteSimulation
    provider_proofs: tuple[ProviderIdentityProof, ...]
    evidence_chain: DispatchEvidenceChain
    validation_status: DispatchEvidenceValidationStatus = (
        DispatchEvidenceValidationStatus.SIMULATED
    )
    provider_response_stored: bool = False

    def to_display_dict(self, *, now_epoch: int | None = None) -> dict[str, object]:
        return {
            "payload_hash": self.payload_hash.to_display_dict(),
            "route_simulation": self.route_simulation.to_display_dict(),
            "provider_proofs": tuple(
                proof.to_display_dict(now_epoch=now_epoch)
                for proof in self.provider_proofs
            ),
            "evidence_chain": self.evidence_chain.to_display_dict(),
            "validation_status": self.validation_status.value,
            "provider_response_stored": self.provider_response_stored,
        }


def hash_prompt_payload(packet_or_payload: _PacketLike | str) -> PromptPayloadHashRecord:
    payload = (
        packet_or_payload.model_payload()
        if hasattr(packet_or_payload, "model_payload")
        else str(packet_or_payload)
    )
    payload_ref = _safe_ref(
        f"prompt-payload:{packet_or_payload.packet_id}"
        if hasattr(packet_or_payload, "packet_id")
        else f"prompt-payload:sha256:{_sha256(payload)[:12]}",
        "prompt-payload:redacted",
    )
    return PromptPayloadHashRecord(
        payload_ref=payload_ref,
        sha256=_sha256(payload),
        byte_length=len(payload.encode("utf-8")),
    )


def provider_identity_proof_from_metadata(
    metadata: Any,
    *,
    health_status: ProviderHealthStatus = ProviderHealthStatus.UNKNOWN,
    evidence_refs: tuple[str, ...] = (),
    observed_at_epoch: int | None = None,
    trust_max_age_seconds: int | None = None,
) -> ProviderIdentityProof:
    if trust_max_age_seconds is not None and trust_max_age_seconds < 0:
        raise ValueError("trust_max_age_seconds must be non-negative")
    provider_name = str(getattr(metadata, "provider_name"))
    model_name = str(getattr(metadata, "model_name"))
    expires_at_epoch = (
        observed_at_epoch + trust_max_age_seconds
        if observed_at_epoch is not None and trust_max_age_seconds is not None
        else None
    )
    refs = evidence_refs or (f"model-harness-metadata:{provider_name}:{model_name}",)
    return ProviderIdentityProof(
        provider_ref=f"provider:{provider_name}:{model_name}",
        provider_name=provider_name,
        model_name=model_name,
        capability_tier=str(getattr(metadata, "capability_tier", "unknown")),
        trust_state=str(getattr(metadata, "trust_state", "unknown")),
        health_status=health_status,
        evidence_refs=tuple(refs),
        observed_at_epoch=observed_at_epoch,
        expires_at_epoch=expires_at_epoch,
    )


def simulate_route_dispatch(
    route: RelayRoute,
    *,
    providers_by_model: Mapping[str, Any] | None = None,
    now_epoch: int | None = None,
) -> RouteSimulation:
    """Simulate dispatch route evidence without invoking provider callables."""
    providers = providers_by_model or {}
    route_ref = _route_ref(route)
    fallback_explanations = tuple(_fallback_explanations(route))
    lane_records: list[RouteSimulationLane] = []

    for lane in route.lanes:
        proof = _proof_for_model(providers, lane.preferred_model)
        lane_confidence = _lane_confidence(route, proof, now_epoch=now_epoch)
        fallback = None
        if proof is None:
            fallback = FallbackExplanation(
                from_route=lane.preferred_model,
                to_route="no-provider-bound",
                reason="provider identity proof missing for lane",
                blocker_tags=("missing_provider_identity_proof",),
            )
        elif proof.health_status in {
            ProviderHealthStatus.DEGRADED,
            ProviderHealthStatus.BLOCKED,
        }:
            fallback = FallbackExplanation(
                from_route=proof.provider_ref,
                to_route="fallback-required",
                reason="provider health is not healthy",
                blocker_tags=(f"provider_health:{proof.health_status.value}",),
                evidence_refs=proof.evidence_refs,
            )

        lane_records.append(
            RouteSimulationLane(
                role=lane.role.value,
                preferred_model=lane.preferred_model,
                independent=lane.independent,
                provider_ref=proof.provider_ref if proof is not None else None,
                provider_health_status=(
                    proof.health_status.value if proof is not None else "missing"
                ),
                confidence_label=lane_confidence,
                fallback_explanation=fallback,
            )
        )

    confidence = _route_confidence(route, tuple(lane_records), fallback_explanations)
    replay = RouteReplayMetadata(
        route_ref=route_ref,
        route_mode=route.mode.value,
        risk_tier=route.risk_tier,
        lane_roles=tuple(lane.role.value for lane in route.lanes),
        selected_models=tuple(lane.preferred_model for lane in route.lanes),
        route_reason_ref=f"route-reason:sha256:{_sha256(route.reason)[:12]}",
    )
    return RouteSimulation(
        route_ref=route_ref,
        confidence_label=confidence,
        no_provider_call=True,
        lanes=tuple(lane_records),
        fallback_explanations=fallback_explanations,
        replay_metadata=replay,
    )


def build_dispatch_evidence(
    *,
    intent_ref: str,
    route: RelayRoute,
    packet: _PacketLike,
    providers_by_model: Mapping[str, Any] | None = None,
    now_epoch: int | None = None,
    response_ref: str | None = None,
    validation_ref: str | None = None,
) -> DispatchEvidence:
    payload_hash = hash_prompt_payload(packet)
    provider_proofs = _provider_proofs_from_mapping(providers_by_model or {})
    simulation = simulate_route_dispatch(
        route,
        providers_by_model={proof.model_name: proof for proof in provider_proofs},
        now_epoch=now_epoch,
    )
    chain = DispatchEvidenceChain(
        intent_ref=intent_ref,
        payload_ref=payload_hash.payload_ref,
        provider_refs=tuple(proof.provider_ref for proof in provider_proofs),
        response_ref=response_ref or "provider-response:not-called",
        validation_ref=validation_ref or f"dispatch-validation:{payload_hash.sha256[:12]}",
    )
    return DispatchEvidence(
        payload_hash=payload_hash,
        route_simulation=simulation,
        provider_proofs=provider_proofs,
        evidence_chain=chain,
        validation_status=(
            DispatchEvidenceValidationStatus.BLOCKED
            if simulation.confidence_label is RouteConfidenceLabel.BLOCKED
            else DispatchEvidenceValidationStatus.SIMULATED
        ),
    )


def _provider_proofs_from_mapping(providers: Mapping[str, Any]) -> tuple[ProviderIdentityProof, ...]:
    proofs: list[ProviderIdentityProof] = []
    for item in providers.values():
        if isinstance(item, ProviderIdentityProof):
            proofs.append(item)
            continue
        metadata = getattr(item, "metadata", item)
        proofs.append(provider_identity_proof_from_metadata(metadata))
    return tuple(proofs)


def _proof_for_model(
    providers: Mapping[str, Any],
    preferred_model: str,
) -> ProviderIdentityProof | None:
    item = providers.get(preferred_model)
    if item is None:
        return None
    if isinstance(item, ProviderIdentityProof):
        return item
    metadata = getattr(item, "metadata", item)
    return provider_identity_proof_from_metadata(metadata)


def _lane_confidence(
    route: RelayRoute,
    proof: ProviderIdentityProof | None,
    *,
    now_epoch: int | None,
) -> RouteConfidenceLabel:
    if route.mode is RoutingMode.NO_MODEL:
        return RouteConfidenceLabel.NO_MODEL
    if route.audit.trust_state is RouteTrustState.BLOCKED:
        return RouteConfidenceLabel.BLOCKED
    if proof is None:
        return RouteConfidenceLabel.LOW
    if now_epoch is not None and proof.is_trust_expired(now_epoch=now_epoch):
        return RouteConfidenceLabel.BLOCKED
    if proof.health_status is ProviderHealthStatus.BLOCKED:
        return RouteConfidenceLabel.BLOCKED
    if proof.health_status is ProviderHealthStatus.DEGRADED:
        return RouteConfidenceLabel.LOW
    if proof.trust_state in {"trusted", "local_only"}:
        return RouteConfidenceLabel.HIGH
    return RouteConfidenceLabel.MEDIUM


def _route_confidence(
    route: RelayRoute,
    lanes: tuple[RouteSimulationLane, ...],
    fallback_explanations: tuple[FallbackExplanation, ...],
) -> RouteConfidenceLabel:
    if route.mode is RoutingMode.NO_MODEL:
        return RouteConfidenceLabel.NO_MODEL
    if any(lane.confidence_label is RouteConfidenceLabel.BLOCKED for lane in lanes):
        return RouteConfidenceLabel.BLOCKED
    if route.requires_human_gate:
        return RouteConfidenceLabel.BLOCKED
    if any(lane.confidence_label is RouteConfidenceLabel.LOW for lane in lanes):
        return RouteConfidenceLabel.LOW
    if fallback_explanations:
        return RouteConfidenceLabel.MEDIUM
    if all(lane.confidence_label is RouteConfidenceLabel.HIGH for lane in lanes):
        return RouteConfidenceLabel.HIGH
    return RouteConfidenceLabel.MEDIUM


def _fallback_explanations(route: RelayRoute) -> list[FallbackExplanation]:
    explanations: list[FallbackExplanation] = []
    if route.audit.fallback_blockers:
        explanations.append(
            FallbackExplanation(
                from_route=route.audit.route_kind.value,
                to_route=(
                    route.audit.route_class.value
                    if route.audit.route_class is not None
                    else "no-model"
                ),
                reason="route audit carries fallback blockers",
                blocker_tags=tuple(route.audit.fallback_blockers),
                evidence_refs=tuple(route.audit.proof_required),
            )
        )
    return explanations


def _route_ref(route: RelayRoute) -> str:
    seed = "|".join(
        (
            route.mode.value,
            str(route.risk_tier),
            ",".join(lane.preferred_model for lane in route.lanes),
        )
    )
    return f"relay-route:{_sha256(seed)[:12]}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_UNSAFE_DISPLAY_PATTERN = re.compile(
    r"(?is)(?:"
    r"[A-Z]:\\|\\\\[^\\\s]+\\[^\\\s]+\\|/(?:Users|home|var|tmp|mnt|Volumes)/|"
    r"\b(?:raw|full|complete)\s+prompt\s*:|"
    r"\b(?:raw|full|complete)\s+transcript\s*:|"
    r"\b(?:provider|model)\s+(?:response|output)\s*:|"
    r"\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]\s*\S{8,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{16,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}"
    r")"
)


def _safe_ref(value: object, fallback: str) -> str:
    text = str(value).strip()
    if not text or _UNSAFE_DISPLAY_PATTERN.search(text):
        return fallback
    return text


def _safe_label(value: object) -> str:
    text = str(value).strip()
    if not text or _UNSAFE_DISPLAY_PATTERN.search(text):
        return "[redacted]"
    return text


def _safe_digest(value: object) -> str:
    text = str(value).strip()
    if not text or _UNSAFE_DISPLAY_PATTERN.search(text):
        return "[redacted]"
    return text
