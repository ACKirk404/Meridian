"""
Relay-owned helper: assembles a validated PromptPacket from a RelayRoute.

This is runtime glue internal to Relay dispatch — not a package-root export.
"""

from __future__ import annotations

from .prompt_packet import PromptPacket, build_prompt_packet
from .relay import RelayRoute
from .tokens import count_tokens


def assemble_relay_packet(
    *,
    packet_id: str,
    serialized_prompt: str,
    route: RelayRoute,
    source_lineage: dict[str, int] | None = None,
    construction_time_ms: float = 0.0,
) -> PromptPacket:
    """
    Build a validated PromptPacket from a RelayRoute and a serialized prompt.

    Reads route.prompt_budget for budget constraints. Token count is derived
    from count_tokens(). Source lineage defaults to {"direct_input": prompt_tokens}
    when not supplied.

    Raises PromptPacketValidationError if the resulting packet fails validation.
    """
    prompt_tokens = count_tokens(serialized_prompt)
    if source_lineage is None:
        source_lineage = {"direct_input": prompt_tokens}
    return build_prompt_packet(
        packet_id=packet_id,
        serialized_prompt=serialized_prompt,
        prompt_tokens=prompt_tokens,
        budget=route.prompt_budget,
        source_lineage=source_lineage,
        construction_time_ms=construction_time_ms,
        proof_required=tuple(route.audit.proof_required),
    )
