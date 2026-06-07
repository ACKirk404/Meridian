"""Provider-neutral model adapter boundary for the Model Harness.

Adapters receive only approved prompt payload text. Provider credentials,
models, account/session details, and transport concerns stay inside the
adapter implementation and outside Relay's dispatch payload.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from .relay import ModelRole


class ModelAdapterConfigError(RuntimeError):
    """Raised when a live model adapter is missing required configuration."""


class DeepSeekValidationLevel(Enum):
    """Validation gate levels for DeepSeek direct-provider authority.

    Each level gates progressively more dangerous operations.
    Levels are ordered: only clear when prior level is satisfied.
    """

    METADATA_ONLY = "level-0:metadata-only"
    VALIDATION_CLEARED = "level-1:validation-cleared"
    REVIEW_CLEARANCE = "level-2:review-clearance"
    BRANCH_MOVEMENT = "level-3:branch-movement"
    AUTONOMOUS_CODING = "level-4:autonomous-coding"


_DEEPSEEK_RESERVED_VALIDATION_LEVELS = frozenset({
    DeepSeekValidationLevel.REVIEW_CLEARANCE,
    DeepSeekValidationLevel.BRANCH_MOVEMENT,
    DeepSeekValidationLevel.AUTONOMOUS_CODING,
})


@dataclass(frozen=True)
class DeepSeekValidationState:
    """Deterministic validation-state object for DeepSeek direct-provider authority.

    Distinguishes metadata-only candidate state from validation-cleared transport state.
    Records which operations are gated by validation levels.

    The `DeepSeekValidationLevel` enum advertises higher gate levels
    (REVIEW_CLEARANCE, BRANCH_MOVEMENT, AUTONOMOUS_CODING) for documentation of
    the gate ladder, but at this slice they are reserved and not constructible.
    Future slices must explicitly extend `__post_init__` to authorize a higher
    level — accidental construction must never grant elevated authority.
    """

    current_level: DeepSeekValidationLevel
    can_receive_prompt_payloads: bool
    can_clear_reviews: bool
    can_move_branches: bool
    can_enable_autonomous_coding: bool
    blocked_operations: tuple[str, ...]
    validation_ref: str

    def __post_init__(self) -> None:
        if self.current_level == DeepSeekValidationLevel.METADATA_ONLY:
            if (
                self.can_receive_prompt_payloads
                or self.can_clear_reviews
                or self.can_move_branches
                or self.can_enable_autonomous_coding
            ):
                raise ModelAdapterConfigError(
                    "metadata-only validation level cannot grant any operational authority"
                )
        elif self.current_level == DeepSeekValidationLevel.VALIDATION_CLEARED:
            if not self.can_receive_prompt_payloads:
                raise ModelAdapterConfigError(
                    "validation-cleared level must grant prompt payload authority"
                )
            if (
                self.can_clear_reviews
                or self.can_move_branches
                or self.can_enable_autonomous_coding
            ):
                raise ModelAdapterConfigError(
                    "validation-cleared level cannot grant review/branch/autonomous authority"
                )
        elif self.current_level in _DEEPSEEK_RESERVED_VALIDATION_LEVELS:
            raise ModelAdapterConfigError(
                f"DeepSeek validation level {self.current_level.value} is reserved "
                "and not constructible at this slice (no autonomy by accident)"
            )
        else:
            raise ModelAdapterConfigError(
                f"Unknown DeepSeek validation level: {self.current_level!r}"
            )


def deepseek_validation_state_from_preset(preset: ModelCandidateRoutePreset) -> DeepSeekValidationState:
    """Derive the validation state from a DeepSeek candidate preset.

    Ensures consistency between preset authority bits and validation levels.
    """
    if preset.provider_name != "deepseek" or preset.dispatch_model != DEEPSEEK_DIRECT_MODEL:
        raise ModelAdapterConfigError(
            "validation state is only for direct DeepSeek dispatch (deepseek-chat)"
        )

    validation_ref = preset.validation_evidence_ref or "deepseek-validation:level-0:metadata-only"

    if validation_ref.startswith("deepseek-validation:level-0"):
        return DeepSeekValidationState(
            current_level=DeepSeekValidationLevel.METADATA_ONLY,
            can_receive_prompt_payloads=False,
            can_clear_reviews=False,
            can_move_branches=False,
            can_enable_autonomous_coding=False,
            blocked_operations=(
                "prompt_payload_dispatch",
                "review_clearance",
                "branch_movement",
                "autonomous_coding",
            ),
            validation_ref=validation_ref,
        )
    elif validation_ref.startswith("deepseek-validation:level-1"):
        return DeepSeekValidationState(
            current_level=DeepSeekValidationLevel.VALIDATION_CLEARED,
            can_receive_prompt_payloads=True,
            can_clear_reviews=False,
            can_move_branches=False,
            can_enable_autonomous_coding=False,
            blocked_operations=(
                "review_clearance",
                "branch_movement",
                "autonomous_coding",
            ),
            validation_ref=validation_ref,
        )
    else:
        raise ModelAdapterConfigError(
            f"Unknown DeepSeek validation reference: {validation_ref}"
        )


@dataclass(frozen=True)
class DeepSeekValidationDisposition:
    """Bounded Relay-facing disposition for DeepSeek validation-state metadata.

    Exposes validation level, direct dispatch id, variant labels, transport-cleared
    state, blocked-authority tags, and evidence refs as bounded metadata only.

    All autonomous authority bits are hard-coded False at this slice: this
    disposition never grants autonomous implementation, review-clearing,
    branch/worktree movement, live coding authority, or unsafe Relay bypass.
    Validation-cleared transport state is represented as transport metadata only.
    """

    validation_level: str
    direct_dispatch_id: str
    variant_labels: tuple[str, ...]
    transport_cleared: bool
    blocked_authority_tags: tuple[str, ...]
    validation_evidence_ref: str
    direct_endpoint_evidence_ref: str | None = None
    external_review_evidence_ref: str | None = None
    autonomous_implementation_authorized: bool = False
    review_clearing_authorized: bool = False
    branch_movement_authorized: bool = False
    live_coding_authority_authorized: bool = False
    relay_bypass_authorized: bool = False
    serialization_only: bool = True

    def __post_init__(self) -> None:
        if self.direct_dispatch_id != DEEPSEEK_DIRECT_MODEL:
            raise ModelAdapterConfigError(
                "DeepSeek disposition direct_dispatch_id must be deepseek-chat"
            )
        for label in self.variant_labels:
            if label == self.direct_dispatch_id:
                raise ModelAdapterConfigError(
                    "DeepSeek variant labels must not masquerade as the dispatch model"
                )
        if (
            self.autonomous_implementation_authorized
            or self.review_clearing_authorized
            or self.branch_movement_authorized
            or self.live_coding_authority_authorized
            or self.relay_bypass_authorized
        ):
            raise ModelAdapterConfigError(
                "DeepSeek disposition must not grant autonomous authority at this slice"
            )
        if not self.serialization_only:
            raise ModelAdapterConfigError(
                "DeepSeek disposition is serialization-only"
            )

    def to_dict(self) -> dict[str, object]:
        """Return display-safe disposition for Relay envelope handoff."""
        return {
            "validation_level": self.validation_level,
            "direct_dispatch_id": self.direct_dispatch_id,
            "variant_labels": self.variant_labels,
            "transport_cleared": self.transport_cleared,
            "blocked_authority_tags": self.blocked_authority_tags,
            "validation_evidence_ref": self.validation_evidence_ref,
            "direct_endpoint_evidence_ref": self.direct_endpoint_evidence_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "autonomous_implementation_authorized": self.autonomous_implementation_authorized,
            "review_clearing_authorized": self.review_clearing_authorized,
            "branch_movement_authorized": self.branch_movement_authorized,
            "live_coding_authority_authorized": self.live_coding_authority_authorized,
            "relay_bypass_authorized": self.relay_bypass_authorized,
            "serialization_only": self.serialization_only,
        }


def bind_deepseek_validation_disposition(
    adapter_metadata: "ModelHarnessMetadata | None",
) -> DeepSeekValidationDisposition | None:
    """Bind reviewed DeepSeek validation-state into a bounded Relay disposition.

    Returns None when metadata is missing, not DeepSeek direct dispatch, or
    carries no candidate validation state. Returns a serialization-only
    disposition otherwise. Never grants autonomous authority.
    """
    if adapter_metadata is None:
        return None
    if adapter_metadata.provider_name != "deepseek":
        return None
    if adapter_metadata.model_name != DEEPSEEK_DIRECT_MODEL:
        return None
    candidate_state = adapter_metadata.deepseek_candidate_state
    if candidate_state is None:
        return None
    validation_ref = candidate_state.get("validation_evidence_ref", "") or ""
    if not validation_ref:
        return None

    if validation_ref.startswith("deepseek-validation:level-0"):
        validation_level = "level-0:metadata-only"
        transport_cleared = False
    elif validation_ref.startswith("deepseek-validation:level-1"):
        validation_level = "level-1:validation-cleared"
        transport_cleared = True
    else:
        validation_level = "level-unknown"
        transport_cleared = False

    blocked_authority_tags = tuple(
        tag.strip()
        for tag in (candidate_state.get("blocked_authorities") or "").split(",")
        if tag.strip()
    )
    variant_label = (candidate_state.get("variant_label") or "").strip()
    variant_labels = (variant_label,) if variant_label else ()
    direct_endpoint_ref = (
        candidate_state.get("direct_endpoint_evidence_ref") or ""
    ).strip() or None
    external_review_ref = (
        candidate_state.get("external_review_evidence_ref") or ""
    ).strip() or None

    return DeepSeekValidationDisposition(
        validation_level=validation_level,
        direct_dispatch_id=DEEPSEEK_DIRECT_MODEL,
        variant_labels=variant_labels,
        transport_cleared=transport_cleared,
        blocked_authority_tags=blocked_authority_tags,
        validation_evidence_ref=validation_ref,
        direct_endpoint_evidence_ref=direct_endpoint_ref,
        external_review_evidence_ref=external_review_ref,
    )


class DeepSeekValidationProofState(Enum):
    """Validation-gate proof state for DeepSeek direct-provider transport.

    Drives fail-closed transport authority. Any state other than
    PROOF_VERIFIED (with both human and Prime authority gates satisfied)
    blocks transport. Even PROOF_VERIFIED never extends authority beyond
    transport: autonomous implementation, review clearing, branch movement,
    live coding, and Relay bypass remain hard-blocked regardless.
    """

    NONE = "none"
    CANDIDATE_METADATA_ONLY = "candidate-metadata-only"
    PROOF_SUBMITTED_PENDING_REVIEW = "proof-submitted-pending-review"
    PROOF_STALE = "proof-stale"
    PROOF_PARTIAL = "proof-partial"
    PROOF_REVOKED = "proof-revoked"
    PROOF_VERIFIED = "proof-verified"


class DeepSeekTransportAuthorityStatus(Enum):
    """Transport-authority status for DeepSeek direct-provider dispatch.

    Only AUTHORIZED_TRANSPORT_ONLY permits transport; every other value is a
    fail-closed blocker. AUTHORIZED_TRANSPORT_ONLY explicitly does NOT grant
    autonomous implementation, review clearing, branch movement, live coding,
    or Relay bypass.
    """

    BLOCKED_NO_PROOF = "blocked:no-proof"
    BLOCKED_CANDIDATE_ONLY = "blocked:candidate-only"
    BLOCKED_PROOF_PARTIAL = "blocked:proof-partial"
    BLOCKED_PROOF_STALE = "blocked:proof-stale"
    BLOCKED_PROOF_REVOKED = "blocked:proof-revoked"
    BLOCKED_PROOF_PENDING_REVIEW = "blocked:proof-pending-review"
    BLOCKED_HUMAN_GATE_REQUIRED = "blocked:human-gate-required"
    BLOCKED_PRIME_AUTHORITY_REQUIRED = "blocked:prime-authority-required"
    AUTHORIZED_TRANSPORT_ONLY = "authorized:transport-only"


_DEEPSEEK_PROOF_STATE_TO_BLOCKER: Mapping[
    DeepSeekValidationProofState, tuple[DeepSeekTransportAuthorityStatus, str]
] = MappingProxyType({
    DeepSeekValidationProofState.NONE: (
        DeepSeekTransportAuthorityStatus.BLOCKED_NO_PROOF,
        "deepseek_proof_missing",
    ),
    DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY: (
        DeepSeekTransportAuthorityStatus.BLOCKED_CANDIDATE_ONLY,
        "deepseek_proof_candidate_only",
    ),
    DeepSeekValidationProofState.PROOF_PARTIAL: (
        DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_PARTIAL,
        "deepseek_proof_partial",
    ),
    DeepSeekValidationProofState.PROOF_STALE: (
        DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_STALE,
        "deepseek_proof_stale",
    ),
    DeepSeekValidationProofState.PROOF_REVOKED: (
        DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_REVOKED,
        "deepseek_proof_revoked",
    ),
    DeepSeekValidationProofState.PROOF_SUBMITTED_PENDING_REVIEW: (
        DeepSeekTransportAuthorityStatus.BLOCKED_PROOF_PENDING_REVIEW,
        "deepseek_proof_pending_review",
    ),
})


_DEEPSEEK_BLOCKED_AUTHORITY_TAGS: tuple[str, ...] = (
    "autonomous_implementation",
    "review_clearance",
    "branch_movement",
    "live_coding",
    "relay_bypass",
)


@dataclass(frozen=True)
class DeepSeekValidationGateProof:
    """Bounded validation-gate proof record for DeepSeek direct-provider transport.

    Carries only proof state plus display-safe evidence references. Never
    stores raw credentials, raw provider responses, or transcripts. Staleness
    and partial-proof are first-class blockers, not optional warnings.
    """

    proof_state: DeepSeekValidationProofState
    proof_evidence_refs: tuple[str, ...] = ()
    review_evidence_ref: str | None = None
    proof_observed_at: str | None = None
    proof_max_age_seconds: int | None = None
    human_gate_satisfied: bool = False
    prime_authority_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.proof_max_age_seconds is not None and self.proof_max_age_seconds < 0:
            raise ModelAdapterConfigError(
                "proof_max_age_seconds must be non-negative if provided"
            )

    def to_dict(self) -> dict[str, object]:
        """Return display-safe proof metadata for Relay/Bifrost handoff."""
        return {
            "proof_state": self.proof_state.value,
            "proof_evidence_refs": list(self.proof_evidence_refs),
            "review_evidence_ref": self.review_evidence_ref,
            "proof_observed_at": self.proof_observed_at,
            "proof_max_age_seconds": self.proof_max_age_seconds,
            "human_gate_satisfied": self.human_gate_satisfied,
            "prime_authority_satisfied": self.prime_authority_satisfied,
        }


@dataclass(frozen=True)
class DeepSeekTransportAuthority:
    """Bounded transport-authority record for DeepSeek direct-provider dispatch.

    Combines validation-gate proof + authority gates into a single fail-closed
    transport-authority status. Authority NEVER extends beyond transport: the
    five autonomous-authority bits are hard-coded False, the dispatch identity
    is hard-coded to ``deepseek-chat``, and ``transport_authorized`` must
    match the ``status == AUTHORIZED_TRANSPORT_ONLY`` invariant.
    """

    direct_dispatch_id: str
    proof: DeepSeekValidationGateProof
    status: DeepSeekTransportAuthorityStatus
    transport_authorized: bool
    blocker_tags: tuple[str, ...]
    blocked_authority_tags: tuple[str, ...]
    autonomous_implementation_authorized: bool = False
    review_clearing_authorized: bool = False
    branch_movement_authorized: bool = False
    live_coding_authority_authorized: bool = False
    relay_bypass_authorized: bool = False
    serialization_only: bool = True

    def __post_init__(self) -> None:
        if self.direct_dispatch_id != DEEPSEEK_DIRECT_MODEL:
            raise ModelAdapterConfigError(
                "DeepSeek transport authority direct_dispatch_id must be deepseek-chat"
            )
        if (
            self.autonomous_implementation_authorized
            or self.review_clearing_authorized
            or self.branch_movement_authorized
            or self.live_coding_authority_authorized
            or self.relay_bypass_authorized
        ):
            raise ModelAdapterConfigError(
                "DeepSeek transport authority must not grant autonomous authority"
            )
        if not self.serialization_only:
            raise ModelAdapterConfigError(
                "DeepSeek transport authority is serialization-only"
            )
        expected_authorized = (
            self.status == DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        )
        if self.transport_authorized != expected_authorized:
            raise ModelAdapterConfigError(
                "transport_authorized must equal (status == AUTHORIZED_TRANSPORT_ONLY)"
            )
        for marker in _DEEPSEEK_BLOCKED_AUTHORITY_TAGS:
            if marker not in self.blocked_authority_tags:
                raise ModelAdapterConfigError(
                    f"DeepSeek transport authority must preserve "
                    f"blocked-authority tag: {marker}"
                )

    def to_dict(self) -> dict[str, object]:
        """Return display-safe transport-authority metadata."""
        return {
            "direct_dispatch_id": self.direct_dispatch_id,
            "proof": self.proof.to_dict(),
            "status": self.status.value,
            "transport_authorized": self.transport_authorized,
            "blocker_tags": list(self.blocker_tags),
            "blocked_authority_tags": list(self.blocked_authority_tags),
            "autonomous_implementation_authorized": self.autonomous_implementation_authorized,
            "review_clearing_authorized": self.review_clearing_authorized,
            "branch_movement_authorized": self.branch_movement_authorized,
            "live_coding_authority_authorized": self.live_coding_authority_authorized,
            "relay_bypass_authorized": self.relay_bypass_authorized,
            "serialization_only": self.serialization_only,
        }


def evaluate_deepseek_transport_authority(
    proof: DeepSeekValidationGateProof,
) -> DeepSeekTransportAuthority:
    """Evaluate transport authority from a proof record, fail-closed by default.

    Missing, candidate-only, partial, stale, revoked, or pending-review proof
    always blocks. Only PROOF_VERIFIED with both human and Prime authority
    gates satisfied yields AUTHORIZED_TRANSPORT_ONLY. The five autonomous-
    authority bits remain False in every output.
    """
    blocker_tags: list[str] = []
    if proof.proof_state in _DEEPSEEK_PROOF_STATE_TO_BLOCKER:
        status, marker = _DEEPSEEK_PROOF_STATE_TO_BLOCKER[proof.proof_state]
        blocker_tags.append(marker)
    elif proof.proof_state == DeepSeekValidationProofState.PROOF_VERIFIED:
        if not proof.human_gate_satisfied:
            status = DeepSeekTransportAuthorityStatus.BLOCKED_HUMAN_GATE_REQUIRED
            blocker_tags.append("deepseek_human_gate_required")
        elif not proof.prime_authority_satisfied:
            status = DeepSeekTransportAuthorityStatus.BLOCKED_PRIME_AUTHORITY_REQUIRED
            blocker_tags.append("deepseek_prime_authority_required")
        else:
            status = DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
    else:
        # Fail-closed default for any unknown proof state.
        status = DeepSeekTransportAuthorityStatus.BLOCKED_NO_PROOF
        blocker_tags.append("deepseek_proof_unknown_state")

    return DeepSeekTransportAuthority(
        direct_dispatch_id=DEEPSEEK_DIRECT_MODEL,
        proof=proof,
        status=status,
        transport_authorized=(
            status == DeepSeekTransportAuthorityStatus.AUTHORIZED_TRANSPORT_ONLY
        ),
        blocker_tags=tuple(blocker_tags),
        blocked_authority_tags=_DEEPSEEK_BLOCKED_AUTHORITY_TAGS,
    )


def bind_deepseek_transport_authority(
    adapter_metadata: "ModelHarnessMetadata | None",
) -> DeepSeekTransportAuthority | None:
    """Bind adapter metadata to a fail-closed DeepSeek transport-authority record.

    Returns None only when metadata is missing or not DeepSeek direct dispatch.
    Direct DeepSeek (``deepseek-chat``) metadata with no candidate state emits
    a fail-closed ``blocked:no-proof`` authority rather than a silent None, so
    consumers can distinguish "no DeepSeek record" from "DeepSeek record with
    no proof".

    A ``deepseek-validation:level-1:`` validation evidence reference combined
    with ``human_gate_satisfied`` and ``prime_authority_satisfied`` candidate
    state values that are exactly the lowercase string ``"true"`` (after
    surrounding whitespace is stripped) is the only path to
    AUTHORIZED_TRANSPORT_ONLY. Case variants like ``"True"``, ``"TRUE"``,
    ``"yes"``, or ``"1"`` are treated as unsatisfied and the matching blocker
    (``blocked:human-gate-required`` or ``blocked:prime-authority-required``)
    is emitted by ``evaluate_deepseek_transport_authority``. Any non-level-1
    validation ref — including level-0 metadata-only, blank refs, and unknown
    levels — stays fail-closed as ``CANDIDATE_METADATA_ONLY`` regardless of
    gate flags.
    """
    if adapter_metadata is None:
        return None
    if adapter_metadata.provider_name != "deepseek":
        return None
    if adapter_metadata.model_name != DEEPSEEK_DIRECT_MODEL:
        return None
    candidate_state = adapter_metadata.deepseek_candidate_state
    if candidate_state is None:
        proof = DeepSeekValidationGateProof(
            proof_state=DeepSeekValidationProofState.NONE,
        )
        return evaluate_deepseek_transport_authority(proof)

    validation_ref = (candidate_state.get("validation_evidence_ref") or "").strip()
    review_ref = (candidate_state.get("external_review_evidence_ref") or "").strip() or None
    proof_refs: tuple[str, ...] = (validation_ref,) if validation_ref else ()
    human_gate_satisfied = (
        (candidate_state.get("human_gate_satisfied") or "").strip() == "true"
    )
    prime_authority_satisfied = (
        (candidate_state.get("prime_authority_satisfied") or "").strip() == "true"
    )

    if validation_ref.startswith("deepseek-validation:level-1:"):
        proof = DeepSeekValidationGateProof(
            proof_state=DeepSeekValidationProofState.PROOF_VERIFIED,
            proof_evidence_refs=proof_refs,
            review_evidence_ref=review_ref,
            human_gate_satisfied=human_gate_satisfied,
            prime_authority_satisfied=prime_authority_satisfied,
        )
    else:
        proof = DeepSeekValidationGateProof(
            proof_state=DeepSeekValidationProofState.CANDIDATE_METADATA_ONLY,
            proof_evidence_refs=proof_refs,
            review_evidence_ref=review_ref,
            human_gate_satisfied=False,
            prime_authority_satisfied=False,
        )
    return evaluate_deepseek_transport_authority(proof)


@dataclass(frozen=True)
class ModelHarnessMetadata:
    """Provider-neutral Model Harness metadata for capability and budget tracking."""

    provider_name: str
    model_name: str
    capability_tier: str
    context_budget: int
    prompt_payload_budget: int
    trust_state: str
    requires_external_review: bool
    deepseek_candidate_state: Mapping[str, str] | None = None
    max_output_tokens: int | None = None
    tokenizer_family: str = "unknown"
    supports_completion_tokens: bool = False
    supports_latency_ms: bool = False
    supports_payload_snapshot: bool = False
    supports_response_hash: bool = False

    def __post_init__(self) -> None:
        if self.deepseek_candidate_state is not None:
            object.__setattr__(
                self,
                "deepseek_candidate_state",
                MappingProxyType(dict(self.deepseek_candidate_state)),
            )


@dataclass(frozen=True)
class ModelCandidateRoutePreset:
    """Provider-neutral candidate-route metadata before a live adapter is wired."""

    provider_name: str
    dispatch_model: str
    variant_label: str
    lane: str
    api_mode: str
    trust_state: str
    requires_external_review: bool
    external_review_status: str
    direct_api_endpoint: str
    capability_tier: str
    context_budget: int
    prompt_payload_budget: int
    allowed_task_types: tuple[str, ...]
    blocked_task_types: tuple[str, ...]
    max_risk_tier: int
    q_mode_flat: bool
    can_clear_reviews: bool
    can_move_branches: bool
    bypasses_relay_aegis: bool
    autonomous_coding_allowed: bool
    known_authorities: tuple[str, ...]
    trust_mode: str = "direct"
    proof_strength: str = "weak"
    direct_endpoint_evidence_ref: str | None = None
    external_review_evidence_ref: str | None = None
    validation_evidence_ref: str | None = None
    blocked_authorities: tuple[str, ...] = ()
    prompt_drag_default_status: str = "unknown"
    prompt_drag_warning_tags: tuple[str, ...] = ()
    direct_provider_authority: bool = True
    aggregator_authority: bool = False

    def __post_init__(self) -> None:
        if self.provider_name == "deepseek" and self.dispatch_model != DEEPSEEK_DIRECT_MODEL:
            raise ModelAdapterConfigError(
                "DeepSeek direct candidate presets must dispatch with deepseek-chat"
            )
        if self.variant_label == self.dispatch_model:
            raise ModelAdapterConfigError("variant_label must not masquerade as dispatch_model")
        if self.provider_name == "deepseek" and self.api_mode == "direct":
            if self.direct_api_endpoint != DEEPSEEK_DIRECT_ENDPOINT:
                raise ModelAdapterConfigError(
                    "DeepSeek direct candidate endpoint must match the reviewed endpoint"
                )
            if self.trust_mode != "direct":
                raise ModelAdapterConfigError("DeepSeek direct candidates must declare direct trust")
            if self.aggregator_authority:
                raise ModelAdapterConfigError(
                    "DeepSeek direct candidates must not inherit aggregator authority"
                )

    def to_metadata(self) -> ModelHarnessMetadata:
        """Return the legacy adapter metadata surface for this candidate preset."""
        return ModelHarnessMetadata(
            provider_name=self.provider_name,
            model_name=self.dispatch_model,
            capability_tier=self.capability_tier,
            context_budget=self.context_budget,
            prompt_payload_budget=self.prompt_payload_budget,
            trust_state=self.trust_state,
            requires_external_review=self.requires_external_review,
            max_output_tokens=8192,
            tokenizer_family=self.provider_name,
            supports_completion_tokens=True,
            supports_latency_ms=True,
            supports_payload_snapshot=True,
            supports_response_hash=True,
            deepseek_candidate_state={
                "api_mode": self.api_mode,
                "variant_label": self.variant_label,
                "lane": self.lane,
                "direct_api_endpoint": self.direct_api_endpoint,
                "trust_mode": self.trust_mode,
                "proof_strength": self.proof_strength,
                "external_review_status": self.external_review_status,
                "direct_endpoint_evidence_ref": self.direct_endpoint_evidence_ref or "",
                "external_review_evidence_ref": self.external_review_evidence_ref or "",
                "validation_evidence_ref": self.validation_evidence_ref or "",
                "allowed_task_types": ",".join(self.allowed_task_types),
                "blocked_task_types": ",".join(self.blocked_task_types),
                "blocked_authorities": ",".join(self.blocked_authorities),
                "max_risk_tier": str(self.max_risk_tier),
                "q_mode_flat": str(self.q_mode_flat).lower(),
                "prompt_drag_default_status": self.prompt_drag_default_status,
                "prompt_drag_warning_tags": ",".join(self.prompt_drag_warning_tags),
                "can_clear_reviews": str(self.can_clear_reviews).lower(),
                "can_move_branches": str(self.can_move_branches).lower(),
                "bypasses_relay_aegis": str(self.bypasses_relay_aegis).lower(),
                "autonomous_coding_allowed": str(self.autonomous_coding_allowed).lower(),
                "direct_provider_authority": str(self.direct_provider_authority).lower(),
                "aggregator_authority": str(self.aggregator_authority).lower(),
                "known_authorities": ",".join(self.known_authorities),
            },
        )

    def to_dict(self) -> dict[str, object]:
        """Return stable display-safe preset metadata without transport details."""
        return {
            "provider_name": self.provider_name,
            "dispatch_model": self.dispatch_model,
            "variant_label": self.variant_label,
            "lane": self.lane,
            "api_mode": self.api_mode,
            "trust_mode": self.trust_mode,
            "trust_state": self.trust_state,
            "proof_strength": self.proof_strength,
            "requires_external_review": self.requires_external_review,
            "external_review_status": self.external_review_status,
            "direct_endpoint_evidence_ref": self.direct_endpoint_evidence_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "validation_evidence_ref": self.validation_evidence_ref,
            "capability_tier": self.capability_tier,
            "context_budget": self.context_budget,
            "prompt_payload_budget": self.prompt_payload_budget,
            "allowed_task_types": self.allowed_task_types,
            "blocked_task_types": self.blocked_task_types,
            "blocked_authorities": self.blocked_authorities,
            "max_risk_tier": self.max_risk_tier,
            "q_mode_flat": self.q_mode_flat,
            "prompt_drag_default_status": self.prompt_drag_default_status,
            "prompt_drag_warning_tags": self.prompt_drag_warning_tags,
            "can_clear_reviews": self.can_clear_reviews,
            "can_move_branches": self.can_move_branches,
            "bypasses_relay_aegis": self.bypasses_relay_aegis,
            "autonomous_coding_allowed": self.autonomous_coding_allowed,
            "direct_provider_authority": self.direct_provider_authority,
            "aggregator_authority": self.aggregator_authority,
            "known_authorities": self.known_authorities,
        }


DEEPSEEK_DIRECT_MODEL = "deepseek-chat"
DEEPSEEK_DIRECT_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_CONTEXT_BUDGET = 65536
DEEPSEEK_PROMPT_PAYLOAD_BUDGET = 57344


def deepseek_candidate_route_presets() -> tuple[ModelCandidateRoutePreset, ...]:
    """Return direct-provider DeepSeek candidate presets without creating live calls."""
    shared = {
        "provider_name": "deepseek",
        "dispatch_model": DEEPSEEK_DIRECT_MODEL,
        "api_mode": "direct",
        "trust_mode": "direct",
        "trust_state": "candidate",
        "proof_strength": "weak",
        "requires_external_review": True,
        "external_review_status": "pending",
        "direct_api_endpoint": DEEPSEEK_DIRECT_ENDPOINT,
        "direct_endpoint_evidence_ref": "deepseek-direct-endpoint:https://api.deepseek.com/v1/chat/completions",
        "external_review_evidence_ref": "external-review:deepseek:deepseek-chat:pending",
        "validation_evidence_ref": "deepseek-validation:level-0:metadata-only",
        "context_budget": DEEPSEEK_CONTEXT_BUDGET,
        "prompt_payload_budget": DEEPSEEK_PROMPT_PAYLOAD_BUDGET,
        "allowed_task_types": ("verify", "explain"),
        "blocked_task_types": (
            "build",
            "review",
            "release",
            "destructive",
            "branch_movement",
            "review_clearance",
            "autonomous_coding",
        ),
        "blocked_authorities": (
            "review_clearance",
            "branch_movement",
            "relay_aegis_bypass",
            "autonomous_coding",
            "aggregator_authority",
        ),
        "max_risk_tier": 1,
        "q_mode_flat": True,
        "prompt_drag_default_status": "unknown_until_relay_snapshot",
        "prompt_drag_warning_tags": (
            "prompt_drag_requires_relay_snapshot",
            "q_mode_growth_requires_task_change",
        ),
        "can_clear_reviews": False,
        "can_move_branches": False,
        "bypasses_relay_aegis": False,
        "autonomous_coding_allowed": False,
        "direct_provider_authority": True,
        "aggregator_authority": False,
        "known_authorities": ("deepseek-official-endpoint", "direct-api-only"),
    }
    return (
        ModelCandidateRoutePreset(
            **shared,
            variant_label="deepseek-v4-pro",
            lane="default_quality",
            capability_tier="candidate-quality",
        ),
        ModelCandidateRoutePreset(
            **shared,
            variant_label="deepseek-v4-flash",
            lane="fast",
            capability_tier="candidate-fast",
        ),
    )


def deepseek_candidate_metadata_preset(lane: str = "default_quality") -> ModelHarnessMetadata:
    """Return Model Harness metadata for a named DeepSeek direct candidate lane."""
    for preset in deepseek_candidate_route_presets():
        if preset.lane == lane:
            return preset.to_metadata()
    raise ModelAdapterConfigError(f"Unknown DeepSeek candidate lane: {lane}")


@dataclass(frozen=True)
class ModelRouteMetadataBinding:
    """Provider-neutral route/capability/budget snapshot for Relay evidence."""

    provider_name: str
    model_name: str
    capability_tier: str
    route_risk_tier: int
    route_cost_posture: str
    route_latency_posture: str
    context_budget: int
    prompt_payload_budget: int
    trust_state: str
    requires_external_review: bool
    provider_route_kind: str = "unknown"
    external_review_status: str = "not_required"
    model_metadata_ref: str | None = None
    external_review_evidence_ref: str | None = None
    prompt_payload_status: str | None = None
    prompt_payload_estimated_tokens: int | None = None
    prompt_payload_budget_percent: float | None = None
    prompt_payload_growth_tokens: int | None = None
    prompt_payload_growth_percent: float | None = None

    def __post_init__(self) -> None:
        if self.route_risk_tier < 0:
            raise ModelAdapterConfigError("route_risk_tier must be non-negative")
        if self.context_budget < 0:
            raise ModelAdapterConfigError("context_budget must be non-negative")
        if self.prompt_payload_budget < 0:
            raise ModelAdapterConfigError("prompt_payload_budget must be non-negative")

    def to_dict(self) -> dict[str, object]:
        """Return a stable, serializable shape for Relay/Bifrost evidence."""
        return {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "capability_tier": self.capability_tier,
            "route_risk_tier": self.route_risk_tier,
            "route_cost_posture": self.route_cost_posture,
            "route_latency_posture": self.route_latency_posture,
            "context_budget": self.context_budget,
            "prompt_payload_budget": self.prompt_payload_budget,
            "trust_state": self.trust_state,
            "requires_external_review": self.requires_external_review,
            "provider_route_kind": self.provider_route_kind,
            "external_review_status": self.external_review_status,
            "model_metadata_ref": self.model_metadata_ref,
            "external_review_evidence_ref": self.external_review_evidence_ref,
            "prompt_payload_status": self.prompt_payload_status,
            "prompt_payload_estimated_tokens": self.prompt_payload_estimated_tokens,
            "prompt_payload_budget_percent": self.prompt_payload_budget_percent,
            "prompt_payload_growth_tokens": self.prompt_payload_growth_tokens,
            "prompt_payload_growth_percent": self.prompt_payload_growth_percent,
        }


def _metadata_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _metadata_candidate_value(
    adapter_metadata: ModelHarnessMetadata,
    key: str,
) -> str | None:
    if adapter_metadata.deepseek_candidate_state is None:
        return None
    value = adapter_metadata.deepseek_candidate_state.get(key)
    return str(value) if value is not None else None


def _external_review_status(adapter_metadata: ModelHarnessMetadata) -> str:
    status = _metadata_candidate_value(adapter_metadata, "external_review_status")
    if status:
        return status
    return "required_unknown" if adapter_metadata.requires_external_review else "not_required"


def _model_metadata_ref(adapter_metadata: ModelHarnessMetadata) -> str:
    return f"model-harness-metadata:{adapter_metadata.provider_name}:{adapter_metadata.model_name}"


def _external_review_evidence_ref(adapter_metadata: ModelHarnessMetadata) -> str | None:
    if not adapter_metadata.requires_external_review:
        return None
    return (
        f"external-review:{adapter_metadata.provider_name}:"
        f"{adapter_metadata.model_name}:{_external_review_status(adapter_metadata)}"
    )


def bind_model_route_metadata(
    adapter_metadata: ModelHarnessMetadata,
    *,
    route_risk_tier: int,
    route_cost_posture: Any,
    route_latency_posture: Any,
    payload_snapshot: Any | None = None,
) -> ModelRouteMetadataBinding:
    """Bind adapter capability metadata to a Relay route without vendor branching."""
    return ModelRouteMetadataBinding(
        provider_name=adapter_metadata.provider_name,
        model_name=adapter_metadata.model_name,
        capability_tier=adapter_metadata.capability_tier,
        route_risk_tier=route_risk_tier,
        route_cost_posture=_metadata_value(route_cost_posture),
        route_latency_posture=_metadata_value(route_latency_posture),
        context_budget=adapter_metadata.context_budget,
        prompt_payload_budget=adapter_metadata.prompt_payload_budget,
        trust_state=adapter_metadata.trust_state,
        requires_external_review=adapter_metadata.requires_external_review,
        provider_route_kind=_metadata_candidate_value(adapter_metadata, "api_mode") or "unknown",
        external_review_status=_external_review_status(adapter_metadata),
        model_metadata_ref=_model_metadata_ref(adapter_metadata),
        external_review_evidence_ref=_external_review_evidence_ref(adapter_metadata),
        prompt_payload_status=(
            _metadata_value(payload_snapshot.status)
            if payload_snapshot is not None and hasattr(payload_snapshot, "status")
            else None
        ),
        prompt_payload_estimated_tokens=(
            payload_snapshot.estimated_tokens if payload_snapshot is not None else None
        ),
        prompt_payload_budget_percent=(
            payload_snapshot.budget_percent if payload_snapshot is not None else None
        ),
        prompt_payload_growth_tokens=(
            payload_snapshot.growth_tokens if payload_snapshot is not None else None
        ),
        prompt_payload_growth_percent=(
            payload_snapshot.growth_percent if payload_snapshot is not None else None
        ),
    )


class ModelAdapter(Protocol):
    """Callable boundary: receive approved payload text, return model text."""

    def __call__(self, payload: str) -> str: ...

    @property
    def metadata(self) -> ModelHarnessMetadata:
        """Return Model Harness metadata for this adapter."""
        ...


@dataclass(frozen=True)
class ModelAdapterConfig:
    """Environment-backed configuration for a live provider adapter."""

    provider: str
    model: str
    api_key_env_var: str

    def require_api_key(self, env: Mapping[str, str] | None = None) -> str:
        """Return the configured API key or raise before any live call."""
        source = os.environ if env is None else env
        key = source.get(self.api_key_env_var, "").strip()
        if not key:
            raise ModelAdapterConfigError(
                f"Missing required API key environment variable: {self.api_key_env_var}"
            )
        return key


class FakeModelAdapter:
    """Deterministic test adapter that records payload-only calls."""

    def __init__(
        self,
        response: str = "fake model response",
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self.response = response
        self.received_payloads: list[str] = []
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name="fake",
            model_name="fake-model",
            capability_tier="test",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="test",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        self.received_payloads.append(payload)
        return self.response

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata


class MissingAdapterError(RuntimeError):
    """Raised when no adapter is registered for a lane role or model before any call."""


class AdapterRegistry:
    """Provider-neutral registry: register adapters by exact model or role default.

    Each registration method returns a new registry instance (immutable builder).
    Resolution order: exact model match first, role default second, error if neither.
    """

    def __init__(
        self,
        by_model: Mapping[str, ModelAdapter] | None = None,
        by_role: Mapping[ModelRole, ModelAdapter] | None = None,
    ) -> None:
        self._by_model: Mapping[str, ModelAdapter] = MappingProxyType(dict(by_model or {}))
        self._by_role: Mapping[ModelRole, ModelAdapter] = MappingProxyType(dict(by_role or {}))

    def register_model(self, model: str, adapter: ModelAdapter) -> AdapterRegistry:
        """Return new registry with an exact-model adapter registered."""
        return AdapterRegistry(
            by_model={**self._by_model, model: adapter},
            by_role=dict(self._by_role),
        )

    def register_role_default(self, role: ModelRole, adapter: ModelAdapter) -> AdapterRegistry:
        """Return new registry with a role-default adapter registered."""
        return AdapterRegistry(
            by_model=dict(self._by_model),
            by_role={**self._by_role, role: adapter},
        )

    def resolve(self, role: ModelRole, model: str) -> ModelAdapter:
        """Return the adapter for model (exact) or role (default), or raise MissingAdapterError."""
        if model in self._by_model:
            return self._by_model[model]
        if role in self._by_role:
            return self._by_role[role]
        raise MissingAdapterError(
            f"No adapter registered for model={model!r} or role={role.value!r}"
        )


class EnvConfiguredModelAdapter:
    """Env-safe wrapper for a future live provider transport.

    The transport is injected so this module has no vendor SDK dependency.
    Missing credentials fail before the transport is called.
    """

    def __init__(
        self,
        config: ModelAdapterConfig,
        transport: Callable[[str, ModelAdapterConfig, str], str],
        *,
        env: Mapping[str, str] | None = None,
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self.config = config
        self._transport = transport
        self._env = env
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name=config.provider,
            model_name=config.model,
            capability_tier="standard",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="unknown",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        api_key = self.config.require_api_key(self._env)
        return self._transport(payload, self.config, api_key)

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata


@dataclass(frozen=True)
class HttpModelAdapterConfig:
    """Environment-backed configuration for an HTTP JSON provider adapter."""

    provider: str
    model: str
    api_key_env_var: str
    endpoint_url: str

    def require_api_key(self, env: Mapping[str, str] | None = None) -> str:
        """Return the configured API key or raise before any network call."""
        source = os.environ if env is None else env
        key = source.get(self.api_key_env_var, "").strip()
        if not key:
            raise ModelAdapterConfigError(
                f"Missing required API key environment variable: {self.api_key_env_var}"
            )
        return key

    def require_endpoint(self) -> str:
        """Return the configured endpoint URL or raise before any network call."""
        url = self.endpoint_url.strip()
        if not url:
            raise ModelAdapterConfigError(
                f"Missing required endpoint_url for provider={self.provider!r}"
            )
        return url


def _stdlib_http_post(
    payload: str,
    endpoint: str,
    provider: str,
    model: str,
    api_key: str,
) -> str:
    """POST approved payload to endpoint using only stdlib urllib. No SDK dependency."""
    body = json.dumps(
        {"provider": provider, "model": model, "input": payload}
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode()
    decoded = json.loads(raw)
    if not isinstance(decoded, dict) or not isinstance(decoded.get("text"), str):
        raise ModelAdapterConfigError("HTTP JSON model adapter response missing text")
    return decoded["text"]


class HttpJsonModelAdapter:
    """HTTP JSON adapter for V0 Relay dispatch; validates config before any call.

    Accepts an injectable http_post for testing — no live network calls in tests.
    The request body carries only approved payload text, provider, and model name.
    API key is set as an Authorization header and never echoed into response/error text.
    """

    def __init__(
        self,
        config: HttpModelAdapterConfig,
        *,
        env: Mapping[str, str] | None = None,
        http_post: Callable[[str, str, str, str, str], str] | None = None,
        metadata: ModelHarnessMetadata | None = None,
    ) -> None:
        self._config = config
        self._env = env
        self._http_post = http_post if http_post is not None else _stdlib_http_post
        self._metadata = metadata or ModelHarnessMetadata(
            provider_name=config.provider,
            model_name=config.model,
            capability_tier="standard",
            context_budget=4096,
            prompt_payload_budget=2048,
            trust_state="unknown",
            requires_external_review=False,
        )

    def __call__(self, payload: str) -> str:
        api_key = self._config.require_api_key(self._env)
        endpoint = self._config.require_endpoint()
        return self._http_post(
            payload,
            endpoint,
            self._config.provider,
            self._config.model,
            api_key,
        )

    @property
    def metadata(self) -> ModelHarnessMetadata:
        return self._metadata
