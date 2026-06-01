"""
Relay executor — provider-neutral execution boundary for a RelayDispatchPlan.

Executes each lane's model-call through an injected callable. No real model,
vendor, API, or account code lives here. Only the lane payload crosses into
the model-call function; no role, model name, or metadata is passed through.
"""

from __future__ import annotations

from dataclasses import dataclass

from .aegis import (
    AegisEvidence,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceType,
    ProofTrail,
)
from .cognition_policy import evaluate_cognition_policy
from .model_adapter import (
    AdapterRegistry,
    MissingAdapterError,
    ModelAdapter,
    ModelHarnessMetadata,
)
from .prompt_payload_meter import PromptPayloadSnapshot
from .relay import ModelRole
from .relay_dispatch import RelayDispatchPlan


ModelCallFn = ModelAdapter


@dataclass(frozen=True)
class RelayExecutionResult:
    """Successful output for one lane with optional payload snapshot and adapter metadata."""

    role: ModelRole
    preferred_model: str
    output: str
    payload_snapshot: PromptPayloadSnapshot | None = None
    adapter_metadata: ModelHarnessMetadata | None = None


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


def _snapshot_severity(snapshot: PromptPayloadSnapshot) -> EvidenceSeverity:
    """Map payload snapshot status to Aegis evidence severity."""
    from .prompt_payload_meter import PayloadStatus

    status = snapshot.status
    if status == PayloadStatus.DEGRADED:
        return EvidenceSeverity.WARNING
    elif status == PayloadStatus.WATCH:
        return EvidenceSeverity.INFO
    else:
        return EvidenceSeverity.INFO


def relay_execution_summary_to_proof_trail(
    summary: RelayExecutionSummary,
) -> ProofTrail:
    """Convert Relay execution output into Aegis evidence.

    Successful lane outputs become non-blocking BUILD_OUTPUT evidence. Lane
    errors become proof-blocking BUILD_OUTPUT evidence with ERROR severity.
    Payload snapshot evidence is added for lanes with snapshot metadata.
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
        if result.payload_snapshot is not None:
            snapshot = result.payload_snapshot
            trail.add(
                AegisEvidence(
                    id=f"relay-payload-{index}-{role}",
                    evidence_type=EvidenceType.BUILD_OUTPUT,
                    severity=_snapshot_severity(snapshot),
                    status=EvidenceStatus.OPEN,
                    source="relay_executor",
                    target=f"{role}:{result.preferred_model}",
                    summary=f"Payload snapshot: {snapshot.display_label} "
                    f"({snapshot.estimated_tokens} tokens, "
                    f"{snapshot.budget_percent:.1f}% of budget); status: {snapshot.status.value}",
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
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
) -> RelayExecutionSummary:
    """
    Execute every lane in *plan* by calling model_call(lane.payload).

    Only the lane payload is forwarded to model_call — no role, model name,
    or metadata. Exceptions are caught per-lane and converted to
    RelayExecutionError entries; successful outputs become RelayExecutionResult
    entries. Lane order matches plan.lanes.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane
    for inclusion in execution results and proof trail evidence.
    """
    _assert_proof_gate_clear(plan, proof_trail)

    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []
    snapshots = payload_snapshots or tuple(None for _ in plan.lanes)

    for lane, snapshot in zip(plan.lanes, snapshots):
        try:
            output = model_call(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
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


def execute_relay_plan_with_registry(
    plan: RelayDispatchPlan,
    registry: AdapterRegistry,
    proof_trail: ProofTrail | None = None,
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
) -> RelayExecutionSummary:
    """
    Execute a plan with per-lane adapter resolution from the registry.

    Pre-resolves all adapters before any call — raises MissingAdapterError
    before the first model call if any lane's adapter is missing. The Aegis
    proof gate is checked first; blocking evidence prevents resolution.
    Only lane.payload crosses to the adapter; role and metadata are not forwarded.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane
    for inclusion in execution results and proof trail evidence.
    """
    _assert_proof_gate_clear(plan, proof_trail)

    resolved_adapters = [
        registry.resolve(lane.role, lane.preferred_model) for lane in plan.lanes
    ]

    results: list[RelayExecutionResult] = []
    errors: list[RelayExecutionError] = []
    snapshots = payload_snapshots or tuple(None for _ in plan.lanes)

    for lane, adapter, snapshot in zip(plan.lanes, resolved_adapters, snapshots):
        try:
            output = adapter(lane.payload)
            results.append(
                RelayExecutionResult(
                    role=lane.role,
                    preferred_model=lane.preferred_model,
                    output=output,
                    payload_snapshot=snapshot,
                    adapter_metadata=adapter.metadata,
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


def execute_relay_dispatch_plan_with_policy(
    plan: RelayDispatchPlan,
    model_call: ModelCallFn,
    proof_trail: ProofTrail | None = None,
    human_gate_approved: bool = False,
    payload_snapshots: tuple[PromptPayloadSnapshot | None, ...] | None = None,
) -> RelayExecutionSummary:
    """
    Execute a plan after evaluating V2 CognitionPolicy against the risk tier.

    Evaluates cognition_policy for plan.route.risk_tier before any model call.
    If policy blocks dispatch, raises RelayProofGateError with blocking reasons
    before calling model_call. Otherwise delegates to execute_relay_dispatch_plan.

    Optional payload_snapshots tuple provides PromptPayloadSnapshot metadata per lane.
    """
    policy_result = evaluate_cognition_policy(
        plan.route.risk_tier,
        proof_trail=proof_trail,
        human_gate_approved=human_gate_approved,
    )

    if not policy_result.can_dispatch:
        reasons = "; ".join(policy_result.blocking_reasons)
        raise RelayProofGateError(
            f"Relay dispatch blocked by cognition policy: {reasons}"
        )

    return execute_relay_dispatch_plan(
        plan, model_call, proof_trail, payload_snapshots
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
