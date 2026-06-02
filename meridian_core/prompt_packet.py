"""
Relay Prompt Packet domain model.

A PromptPacket is a validated, immutable bundle of prompt data ready for
dispatch to a worker model. Validation runs in __post_init__ — invalid
packets cannot be constructed, whether via build_prompt_packet() or directly.

Only serialized_prompt is ever sent to the model. All other fields are
metadata for Prime, Metrics, and logs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType

from .prompt_budget import PromptBudgetPlan


class PromptPacketValidationError(ValueError):
    """Raised when a PromptPacket fails one or more validation checks."""


@dataclass(frozen=True)
class PromptPacketProofMetadata:
    """Safe proof metadata for Relay audit surfaces, never model payload."""

    packet_id: str
    packet_hash: str
    prompt_tokens: int
    budget_tier: str
    prompt_budget_ref: str
    max_context_tokens: int
    allowed_sources: tuple[str, ...]
    source_lineage_keys: tuple[str, ...]
    source_lineage_total_tokens: int
    source_lineage_compliant: bool
    budget_compliant: bool
    proof_required: tuple[str, ...] = ()
    aegis_evidence_ids: tuple[str, ...] = ()
    prompt_payload_snapshot_hash: str | None = None
    snapshot_hash_available: bool = False
    snapshot_hash_gap_tags: tuple[str, ...] = ()
    blocked_tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return deterministic serializable proof metadata for Relay envelopes."""
        return {
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "prompt_tokens": self.prompt_tokens,
            "budget_tier": self.budget_tier,
            "prompt_budget_ref": self.prompt_budget_ref,
            "max_context_tokens": self.max_context_tokens,
            "allowed_sources": self.allowed_sources,
            "source_lineage_keys": self.source_lineage_keys,
            "source_lineage_total_tokens": self.source_lineage_total_tokens,
            "source_lineage_compliant": self.source_lineage_compliant,
            "budget_compliant": self.budget_compliant,
            "proof_required": self.proof_required,
            "aegis_evidence_ids": self.aegis_evidence_ids,
            "prompt_payload_snapshot_hash": self.prompt_payload_snapshot_hash,
            "snapshot_hash_available": self.snapshot_hash_available,
            "snapshot_hash_gap_tags": self.snapshot_hash_gap_tags,
            "blocked_tags": self.blocked_tags,
        }


@dataclass(frozen=True)
class PromptPacket:
    """
    Validated, immutable bundle of prompt data ready for Relay dispatch.

    Validation runs at construction time via __post_init__. source_lineage
    is always stored as an immutable MappingProxyType regardless of input type.
    Only serialized_prompt is sent to the model; all other fields are metadata.
    """

    packet_id: str
    serialized_prompt: str
    prompt_tokens: int
    budget: PromptBudgetPlan
    source_lineage: MappingProxyType  # str -> int, immutable; dict inputs converted
    construction_time_ms: float
    proof_required: tuple[str, ...] = ()
    aegis_evidence_ids: tuple[str, ...] = ()
    proof_metadata: PromptPacketProofMetadata | None = None

    def __post_init__(self) -> None:
        # Convert source_lineage to immutable mapping (accepts dict or MappingProxyType)
        object.__setattr__(
            self,
            "source_lineage",
            MappingProxyType(dict(self.source_lineage)),
        )
        object.__setattr__(self, "proof_required", tuple(self.proof_required))
        object.__setattr__(self, "aegis_evidence_ids", tuple(self.aegis_evidence_ids))

        errors: list[str] = []

        if not self.packet_id:
            errors.append("Packet ID is empty")

        if not isinstance(self.serialized_prompt, str):
            errors.append(
                f"Prompt must be a string, got {type(self.serialized_prompt).__name__}"
            )
        elif not self.serialized_prompt.strip():
            errors.append("Prompt is empty or invalid type")

        if self.prompt_tokens < 0:
            errors.append(f"Prompt tokens {self.prompt_tokens} is negative")

        if self.prompt_tokens > self.budget.max_context_tokens:
            errors.append(
                f"Prompt {self.prompt_tokens} tokens exceeds budget {self.budget.max_context_tokens}"
            )

        for source, count in self.source_lineage.items():
            if source not in self.budget.allowed_sources:
                errors.append(f"Source '{source}' not in allowed_sources")
            if count < 0:
                errors.append(f"Lineage token count for '{source}' is negative")

        lineage_total = sum(self.source_lineage.values())
        if lineage_total > self.prompt_tokens:
            errors.append(
                f"Lineage {lineage_total} exceeds packet {self.prompt_tokens} tokens"
            )

        if self.construction_time_ms < 0:
            errors.append(f"Construction time {self.construction_time_ms} is negative")

        if errors:
            raise PromptPacketValidationError("; ".join(errors))

        if self.proof_metadata is None:
            object.__setattr__(
                self,
                "proof_metadata",
                build_prompt_packet_proof_metadata(
                    self,
                    proof_required=self.proof_required,
                    aegis_evidence_ids=self.aegis_evidence_ids,
                ),
            )

    def model_payload(self) -> str:
        """Return the model-facing prompt payload — only serialized_prompt, no metadata."""
        return self.serialized_prompt

def build_prompt_packet_proof_metadata(
    packet: PromptPacket,
    *,
    proof_required: tuple[str, ...] = (),
    aegis_evidence_ids: tuple[str, ...] = (),
) -> PromptPacketProofMetadata:
    """Build deterministic packet proof metadata from validated packet fields."""
    allowed_sources = tuple(packet.budget.allowed_sources)
    source_keys = tuple(packet.source_lineage.keys())
    lineage_total = sum(packet.source_lineage.values())
    source_lineage_compliant = all(source in allowed_sources for source in source_keys)
    budget_compliant = packet.prompt_tokens <= packet.budget.max_context_tokens
    packet_hash = hashlib.sha256(packet.serialized_prompt.encode("utf-8")).hexdigest()

    blocked_tags: list[str] = []
    if not source_lineage_compliant:
        blocked_tags.append("source_lineage_noncompliant")
    if not budget_compliant:
        blocked_tags.append("prompt_budget_exceeded")

    return PromptPacketProofMetadata(
        packet_id=packet.packet_id,
        packet_hash=packet_hash,
        prompt_tokens=packet.prompt_tokens,
        budget_tier=packet.budget.tier.value,
        prompt_budget_ref=(
            f"prompt-budget:{packet.budget.tier.value}:{packet.budget.max_context_tokens}"
        ),
        max_context_tokens=packet.budget.max_context_tokens,
        allowed_sources=allowed_sources,
        source_lineage_keys=source_keys,
        source_lineage_total_tokens=lineage_total,
        source_lineage_compliant=source_lineage_compliant,
        budget_compliant=budget_compliant,
        proof_required=tuple(proof_required),
        aegis_evidence_ids=tuple(aegis_evidence_ids),
        prompt_payload_snapshot_hash=packet_hash,
        snapshot_hash_available=True,
        snapshot_hash_gap_tags=(),
        blocked_tags=tuple(blocked_tags),
    )


def build_prompt_packet(
    *,
    packet_id: str,
    serialized_prompt: str,
    prompt_tokens: int,
    budget: PromptBudgetPlan,
    source_lineage: dict[str, int],
    construction_time_ms: float,
    proof_required: tuple[str, ...] = (),
    aegis_evidence_ids: tuple[str, ...] = (),
) -> PromptPacket:
    """
    Ergonomic helper to build a validated PromptPacket.

    Accepts a plain dict for source_lineage; the constructor converts it to
    an immutable MappingProxyType. Raises PromptPacketValidationError on
    any constraint violation.
    """
    return PromptPacket(
        packet_id=packet_id,
        serialized_prompt=serialized_prompt,
        prompt_tokens=prompt_tokens,
        budget=budget,
        source_lineage=source_lineage,
        construction_time_ms=construction_time_ms,
        proof_required=proof_required,
        aegis_evidence_ids=aegis_evidence_ids,
    )
