"""
Relay Prompt Packet domain model.

A PromptPacket is a validated, immutable bundle of prompt data ready for
dispatch to a worker model. Validation happens at build time — the packet
is either valid (proceed to dispatch) or raises PromptPacketValidationError.

Only serialized_prompt is ever sent to the model. All other fields are
metadata for Prime, Metrics, and logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .prompt_budget import PromptBudgetPlan


class PromptPacketValidationError(ValueError):
    """Raised when a PromptPacket fails one or more validation checks."""


@dataclass(frozen=True)
class PromptPacket:
    """
    Validated, immutable bundle of prompt data ready for Relay dispatch.

    Build via build_prompt_packet() — direct construction bypasses validation.
    Only serialized_prompt is sent to the model; all other fields are metadata.
    """

    packet_id: str
    serialized_prompt: str
    prompt_tokens: int
    budget: PromptBudgetPlan
    source_lineage: MappingProxyType  # str -> int, immutable
    construction_time_ms: float


def build_prompt_packet(
    *,
    packet_id: str,
    serialized_prompt: str,
    prompt_tokens: int,
    budget: PromptBudgetPlan,
    source_lineage: dict[str, int],
    construction_time_ms: float,
) -> PromptPacket:
    """
    Build and validate a PromptPacket against its budget constraints.

    Raises PromptPacketValidationError (a ValueError subclass) if any check fails.
    All checks are run before raising so the error message is exhaustive.
    """
    errors: list[str] = []

    if not serialized_prompt:
        errors.append("Prompt is empty or invalid type")

    if prompt_tokens < 0:
        errors.append(f"Prompt tokens {prompt_tokens} is negative")

    if prompt_tokens > budget.max_context_tokens:
        errors.append(
            f"Prompt {prompt_tokens} tokens exceeds budget {budget.max_context_tokens}"
        )

    for source, count in source_lineage.items():
        if source not in budget.allowed_sources:
            errors.append(f"Source '{source}' not in allowed_sources")
        if count < 0:
            errors.append(f"Lineage token count for '{source}' is negative")

    lineage_total = sum(source_lineage.values())
    if lineage_total > prompt_tokens:
        errors.append(
            f"Lineage {lineage_total} exceeds packet {prompt_tokens} tokens"
        )

    if construction_time_ms < 0:
        errors.append(f"Construction time {construction_time_ms} is negative")

    if errors:
        raise PromptPacketValidationError("; ".join(errors))

    return PromptPacket(
        packet_id=packet_id,
        serialized_prompt=serialized_prompt,
        prompt_tokens=prompt_tokens,
        budget=budget,
        source_lineage=MappingProxyType(dict(source_lineage)),
        construction_time_ms=construction_time_ms,
    )
