"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
)
from .relay import ModelRole
from .relay_dispatch import RelayDispatchPlan


class ModelCallFn(Protocol):
    """Callable boundary: receives only the lane payload string, returns text."""

    def __call__(self, payload: str) -> str: ...


@dataclass(frozen=True)
class RelayExecutionResult:
    """Successful output for one lane."""

    role: ModelRole
    preferred_model: str
    output: str


@dataclass(frozen=True)
class RelayExecutionError:
    """Captured exception for one lane."""

    role: ModelRole
    preferred_model: str
    error: str


@dataclass(frozen=True)
class RelayExecutionSummary:
    """Immutable collection of per-lane results and errors from one plan execution."""

    results: tuple[RelayExecutionResult, ...]
    errors: tuple[RelayExecutionError, ...]


class RelayProofGateError(RuntimeError):
    """Raised when Aegis proof blocks a high-risk Relay dispatch."""


def relay_execution_summary_to_proof_trail(
    summary: RelayExecutionSummary,
) -> ProofTrail:
    """Convert Relay execution output into Aegis evidence.

    Successful lane outputs become non-blocking BUILD_OUTPUT evidence. Lane
    errors become proof-blocking BUILD_OUTPUT evidence with ERROR severity.
    Prompt payloads and packet metadata are intentionally not represented here.
    """
    trail = ProofTrail()
    for index, result in enumerate(summary.results):
        role = result.role.value
        trail.add(
            AegisEvidence(
                id=f"relay-result-{index}-{role}",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.INFO,
                status=EvidenceStatus.OPEN,
                source="relay_executor",
                target=f"{role}:{result.preferred_model}",
                summary=f"{role} lane completed; output length {len(result.output)} characters",
            )
        )
    for index, error in enumerate(summary.errors):
        role = error.role.value
        trail.add(
            AegisEvidence(
                id=f"relay-error-{index}-{role}",
                evidence_type=EvidenceType.BUILD_OUTPUT,
                severity=EvidenceSeverity.ERROR,
                status=EvidenceStatus.OPEN,
                source="relay_executor",
                target=f"{role}:{error.preferred_model}",
                summary=f"{role} lane failed: {error.error}",
            )
        )
    return trail


def execute_relay_dispatch_plan(
    plan: RelayDispatchPlan,
    model_call: ModelCallFn,
    proof_trail: ProofTrail | None = None,
) -> RelayExecutionSummary:
    """
    Execute every lane in *plan* by calling model_call(lane.payload).

    Only the lane payload is forwarded to model_call — no role, model name,
    or metadata. Exceptions are caught per-lane and converted to
    RelayExecutionError entries; successful outputs become RelayExecutionResult
    entries. Lane order matches plan.lanes.
    """
    _assert_proof_gate_clear(plan, proof_trail)

    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []

    for lane in plan.lanes:
        try:
            output = model_call(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                RelayExecutionError(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    error=str(exc),
                )
            )

    return RelayExecutionSummary(
        results=tuple(results),
        errors=tuple(errors),
    )


def _assert_proof_gate_clear(
    plan: RelayDispatchPlan,
    proof_trail: ProofTrail | None,
) -> None:
    if proof_trail is None or plan.route.risk_tier < 3:
        return
    blocking = proof_trail.blocking()
    if not blocking:
        return
    evidence_ids = ", ".join(evidence.id for evidence in blocking)
    raise RelayProofGateError(
        f"Relay dispatch blocked by Aegis proof evidence: {evidence_ids}"
    )
