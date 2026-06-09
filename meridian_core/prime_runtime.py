"""Prime runtime decision contract and context assembly.

This module is backend-only. It defines the typed packet Prime can expose to
Bifrost later without letting the UI invent orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

SNAPSHOT_VERSION = "prime-runtime-v1"
SNAPSHOT_SOURCE = "meridian_core.prime_runtime.resolve_prime_decision"
PRIME_DIRECTIVES = (
    {
        "name": "Logic, not rules",
        "logic": "Prime reasons from purpose, evidence, context, constraints, and consequences before choosing an action.",
    },
    {
        "name": "Context precedes meaningful action",
        "logic": "Prime verifies mission, project, source, and harness context before performing meaningful work.",
    },
    {
        "name": "Intention must be visible before execution",
        "logic": "Prime exposes the intended action, reason, scope, and expected effect before execution.",
    },
)
PRIME_DIRECTIVE_PROOFS = (
    {
        "question": "What reasoning connects the current context, evidence, constraints, and desired outcome to this action?",
        "proves": "logic-first action selection",
    },
    {
        "question": "What mission/context/source state was read or verified before deciding this action was appropriate?",
        "proves": "context before meaningful action",
    },
    {
        "question": "Was the intended action, reason, scope, and expected effect made visible to the user before execution?",
        "proves": "visible intention before execution",
    },
)



class PrimeDecisionStatus(Enum):
    """Executable state for Prime's next runtime decision."""

    EXECUTABLE = "executable"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"
    NEEDS_CLARIFICATION = "needs_clarification"


class PrimeIntentKind(Enum):
    """High-level intent Prime resolves to a single owning harness."""

    PROJECT_CONTEXT = "project_context"
    SESSION_LIFECYCLE = "session_lifecycle"
    MODEL_ROUTE = "model_route"
    PROOF_RISK = "proof_risk"
    ORCHESTRATION = "orchestration"
    UNKNOWN = "unknown"


OWNER_BY_INTENT = {
    PrimeIntentKind.PROJECT_CONTEXT: "Compass",
    PrimeIntentKind.SESSION_LIFECYCLE: "Vulcan",
    PrimeIntentKind.MODEL_ROUTE: "Relay",
    PrimeIntentKind.PROOF_RISK: "Aegis",
    PrimeIntentKind.ORCHESTRATION: "Prime",
}


@dataclass(frozen=True)
class PrimeSourceRef:
    """A backend source Prime used to assemble its decision context."""

    harness: str
    source: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "harness": self.harness,
            "source": self.source,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class PrimeProof:
    """Visible proof item for Prime's no-drift audit trail."""

    question: str
    answer: str
    source: str
    invalidates_when: str

    def to_dict(self) -> dict[str, str]:
        return {
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
            "invalidatesWhen": self.invalidates_when,
        }


@dataclass(frozen=True)
class PrimeExecutability:
    """Executable gate result for a Prime decision."""

    status: PrimeDecisionStatus
    blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "blockers": list(self.blockers),
            "executable": self.status == PrimeDecisionStatus.EXECUTABLE and not self.blockers,
        }


@dataclass(frozen=True)
class PrimeDriftAudit:
    """No-drift audit for a Prime decision packet."""

    status: str
    checks: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()

    def is_clean(self) -> bool:
        return self.status == "clean" and not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": list(self.checks),
            "failures": list(self.failures),
            "clean": self.is_clean(),
        }


@dataclass(frozen=True)
class PrimeAegisRiskInput:
    """Aegis proof/risk state Prime can consume without calling Aegis internals."""

    source: str
    highest_severity: str
    aggregate_action: str
    evidence_required: tuple[str, ...] = ()
    blocked_gates: tuple[str, ...] = ()
    demoted_gates: tuple[str, ...] = ()
    approvals_present: tuple[str, ...] = ()
    waivers_present: tuple[str, ...] = ()

    def is_blocking(self) -> bool:
        return "blocked" in self.aggregate_action or bool(self.blocked_gates)

    def requires_approval(self) -> bool:
        return self.highest_severity == "error" or self.is_blocking()

    def summary(self) -> str:
        return (
            f"Aegis {self.aggregate_action}; severity={self.highest_severity}; "
            f"evidence={len(self.evidence_required)}; blocked={len(self.blocked_gates)}"
        )

    def blockers(self) -> tuple[str, ...]:
        return tuple(f"Aegis gate blocked: {gate}" for gate in self.blocked_gates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "highestSeverity": self.highest_severity,
            "aggregateAction": self.aggregate_action,
            "evidenceRequired": list(self.evidence_required),
            "blockedGates": list(self.blocked_gates),
            "demotedGates": list(self.demoted_gates),
            "approvalsPresent": list(self.approvals_present),
            "waiversPresent": list(self.waivers_present),
            "blocking": self.is_blocking(),
            "requiresApproval": self.requires_approval(),
        }


@dataclass(frozen=True)
class PrimeBeaconLivenessInput:
    """Display-safe Beacon liveness state Prime can consume as evidence.

    Beacon remains advisory only here: Prime may read liveness posture, but
    this input never authorizes process control, session control, branch
    movement, or worktree movement.
    """

    source: str
    observed_harnesses: tuple[str, ...]
    statuses: tuple[str, ...]
    blocker_count: int = 0
    current_work_present_count: int = 0
    observation_mode: str = "unknown"
    advisory_families: tuple[str, ...] = ()
    updated_at_latest: str = ""

    def is_degraded(self) -> bool:
        degraded = {"blocked", "failed", "stale"}
        return bool(degraded.intersection(self.statuses)) or self.blocker_count > 0

    def summary(self) -> str:
        status_label = ", ".join(self.statuses) if self.statuses else "none"
        return (
            f"Beacon statuses={status_label}; harnesses={len(self.observed_harnesses)}; "
            f"blockers={self.blocker_count}; advisory_only=True"
        )

    def blockers(self) -> tuple[str, ...]:
        if not self.is_degraded():
            return ()
        return ("Beacon liveness advisory requires review before live control.",)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "observedHarnesses": list(self.observed_harnesses),
            "statuses": list(self.statuses),
            "blockerCount": self.blocker_count,
            "currentWorkPresentCount": self.current_work_present_count,
            "observationMode": self.observation_mode,
            "advisoryFamilies": list(self.advisory_families),
            "updatedAtLatest": self.updated_at_latest,
            "degraded": self.is_degraded(),
            "advisoryOnly": True,
            "executionAuthorized": False,
            "sessionControlAuthorized": False,
            "rawFilesystemPathsVisible": False,
        }


@dataclass(frozen=True)
class PrimeInteractionRequest:
    """Typed per-interaction request Prime resolves into a runtime decision."""

    request_id: str
    intent: PrimeIntentKind
    action: str
    why: str
    project_id: str = "Meridian"
    risk: str = "safe_read_only"
    requires_approval: bool = False
    requires_clarification: bool = False
    visible_prompt_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "intent": self.intent.value,
            "action": self.action,
            "why": self.why,
            "projectId": self.project_id,
            "risk": self.risk,
            "requiresApproval": self.requires_approval,
            "requiresClarification": self.requires_clarification,
            "visiblePromptRef": self.visible_prompt_ref,
        }


@dataclass(frozen=True)
class PrimeRuntimeContext:
    """Backend context packet Prime consumes before choosing an action."""

    project_id: str
    project_summary: str
    session_state: str
    relay_route_summary: str
    risk_summary: str
    aegis_risk: PrimeAegisRiskInput | None = None
    beacon_liveness: PrimeBeaconLivenessInput | None = None
    source_refs: tuple[PrimeSourceRef, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "projectSummary": self.project_summary,
            "sessionState": self.session_state,
            "relayRouteSummary": self.relay_route_summary,
            "riskSummary": self.risk_summary,
            "aegisRisk": self.aegis_risk.to_dict() if self.aegis_risk else None,
            "beaconLiveness": (
                self.beacon_liveness.to_dict() if self.beacon_liveness else None
            ),
            "sourceRefs": [source.to_dict() for source in self.source_refs],
        }


@dataclass(frozen=True)
class PrimeDecision:
    """The single backend decision object Prime exposes per interaction."""

    decision_id: str
    status: PrimeDecisionStatus
    owner_harness: str
    action: str
    why: str
    risk: str
    context: PrimeRuntimeContext
    request: PrimeInteractionRequest | None = None
    proof: tuple[PrimeProof, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    visible_to_user: tuple[str, ...] = field(default_factory=tuple)

    def is_executable(self) -> bool:
        return self.status == PrimeDecisionStatus.EXECUTABLE and not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisionId": self.decision_id,
            "status": self.status.value,
            "ownerHarness": self.owner_harness,
            "action": self.action,
            "why": self.why,
            "risk": self.risk,
            "request": self.request.to_dict() if self.request else None,
            "context": self.context.to_dict(),
            "driftAudit": audit_prime_decision(self).to_dict(),
            "proof": [item.to_dict() for item in self.proof],
            "blockers": list(self.blockers),
            "visibleToUser": list(self.visible_to_user),
            "executable": self.is_executable(),
        }


def _first_section_summary(snapshot: Mapping[str, Any], fallback: str) -> str:
    sections = snapshot.get("capabilitySections")
    if isinstance(sections, list) and sections:
        section = sections[0]
        if isinstance(section, Mapping):
            summary = section.get("summary")
            if isinstance(summary, str) and summary:
                return summary
    summary = snapshot.get("summary")
    return summary if isinstance(summary, str) and summary else fallback


def assemble_prime_runtime_context(
    *,
    compass_snapshot: Mapping[str, Any],
    vulcan_snapshot: Mapping[str, Any],
    relay_snapshot: Mapping[str, Any],
    aegis_risk: PrimeAegisRiskInput | None = None,
    beacon_liveness: PrimeBeaconLivenessInput | None = None,
    project_id: str = "Meridian",
    risk_summary: str = "Aegis proof/risk gate unavailable; treat as safe read-only until wired.",
) -> PrimeRuntimeContext:
    """Assemble Prime context from backend harness snapshots only."""

    compass_source = str(compass_snapshot.get("source") or "unknown")
    vulcan_source = str(vulcan_snapshot.get("source") or "unknown")
    relay_source = str(relay_snapshot.get("source") or "unknown")
    aegis_source = aegis_risk.source if aegis_risk else "pending"
    beacon_source = beacon_liveness.source if beacon_liveness else "pending"
    final_risk_summary = aegis_risk.summary() if aegis_risk else risk_summary
    source_refs = [
        PrimeSourceRef("Compass", compass_source, "project bounds and scope"),
        PrimeSourceRef("Vulcan", vulcan_source, "session lifecycle state"),
        PrimeSourceRef("Relay", relay_source, "model route and access logic"),
        PrimeSourceRef("Aegis", aegis_source, "proof/risk gate state"),
    ]
    if beacon_liveness is not None:
        source_refs.append(
            PrimeSourceRef("Beacon", beacon_source, "heartbeat and liveness posture")
        )

    return PrimeRuntimeContext(
        project_id=project_id,
        project_summary=_first_section_summary(
            compass_snapshot,
            "Compass project context unavailable.",
        ),
        session_state=_first_section_summary(
            vulcan_snapshot,
            "Vulcan session lifecycle unavailable.",
        ),
        relay_route_summary=_first_section_summary(
            relay_snapshot,
            "Relay model route unavailable.",
        ),
        risk_summary=final_risk_summary,
        aegis_risk=aegis_risk,
        beacon_liveness=beacon_liveness,
        source_refs=tuple(source_refs),
    )


def beacon_liveness_from_snapshot(
    snapshot: Mapping[str, Any],
) -> PrimeBeaconLivenessInput:
    """Convert a display-safe Beacon snapshot into Prime liveness evidence."""
    heartbeats = snapshot.get("heartbeats")
    safe_heartbeats = heartbeats if isinstance(heartbeats, list) else []
    harnesses: list[str] = []
    statuses: list[str] = []
    blocker_count = 0
    current_work_present_count = 0
    latest = ""
    for heartbeat in safe_heartbeats:
        if not isinstance(heartbeat, Mapping):
            continue
        harness_id = heartbeat.get("harness_id")
        status = heartbeat.get("status")
        if isinstance(harness_id, str) and harness_id:
            harnesses.append(harness_id)
        if isinstance(status, str) and status:
            statuses.append(status)
        blockers = heartbeat.get("blockers")
        if isinstance(blockers, list):
            blocker_count += len(blockers)
        if heartbeat.get("current_work_present") is True:
            current_work_present_count += 1
        updated_at = heartbeat.get("updated_at")
        if isinstance(updated_at, str) and updated_at > latest:
            latest = updated_at

    advisory_families = snapshot.get("advisory_families")
    return PrimeBeaconLivenessInput(
        source=str(snapshot.get("source") or "unknown"),
        observed_harnesses=tuple(harnesses),
        statuses=tuple(statuses),
        blocker_count=blocker_count,
        current_work_present_count=current_work_present_count,
        observation_mode=str(snapshot.get("observation_mode") or "unknown"),
        advisory_families=tuple(
            str(item) for item in advisory_families
        )
        if isinstance(advisory_families, list)
        else (),
        updated_at_latest=latest,
    )


def aegis_risk_from_aggregate(
    aggregate: Any,
    *,
    source: str = "meridian_core.aegis.summarize_aggregate_route_gates",
) -> PrimeAegisRiskInput:
    """Convert Aegis aggregate gate summary data into Prime risk input."""

    def field_value(name: str, fallback: Any) -> Any:
        if isinstance(aggregate, Mapping):
            return aggregate.get(name, fallback)
        return getattr(aggregate, name, fallback)

    return PrimeAegisRiskInput(
        source=source,
        highest_severity=str(field_value("highest_severity", "info")),
        aggregate_action=str(field_value("aggregate_action", "route_allowed")),
        evidence_required=tuple(str(item) for item in field_value("evidence_required", ())),
        blocked_gates=tuple(str(item) for item in field_value("blocked_gates", ())),
        demoted_gates=tuple(str(item) for item in field_value("demoted_gates", ())),
        approvals_present=tuple(str(item) for item in field_value("approvals_present", ())),
        waivers_present=tuple(str(item) for item in field_value("waivers_present", ())),
    )


def resolve_prime_owner(intent: PrimeIntentKind | str | None) -> str:
    """Resolve intent to the harness that owns the next decision."""

    if isinstance(intent, str):
        normalized = intent.strip().lower().replace("-", "_").replace(" ", "_")
        intent = PrimeIntentKind._value2member_map_.get(normalized, PrimeIntentKind.UNKNOWN)
    if intent is None:
        intent = PrimeIntentKind.UNKNOWN
    if intent == PrimeIntentKind.UNKNOWN:
        return "Prime"
    return OWNER_BY_INTENT[intent]


def _available_harnesses(context: PrimeRuntimeContext) -> set[str]:
    return {
        source.harness
        for source in context.source_refs
        if source.source not in {"", "unknown", "pending"}
    }


def audit_prime_decision(decision: PrimeDecision) -> PrimeDriftAudit:
    """Audit that visible Prime fields match backend owner/context/proof state."""

    checks = [
        "request_project_matches_context",
        "owner_source_available_or_prime",
        "proof_sources_include_owner_or_prime",
        "aegis_risk_visible_when_source_available",
        "visible_fields_declared",
    ]
    failures: list[str] = []
    available = _available_harnesses(decision.context)
    proof_sources = {item.source for item in decision.proof}

    if decision.request and decision.request.project_id != decision.context.project_id:
        failures.append("request project does not match context project")

    if decision.owner_harness != "Prime" and decision.owner_harness not in available:
        failures.append(f"owner source unavailable: {decision.owner_harness}")

    if decision.owner_harness not in proof_sources and decision.owner_harness != "Prime":
        failures.append(f"proof packet missing owner source: {decision.owner_harness}")

    if "Aegis" in available and decision.context.aegis_risk is None:
        failures.append("Aegis source available but risk packet missing")

    required_visible = {
        "Prime decision status",
        "owning harness",
        "backend source refs",
        "proof questions and answers",
        "blockers before execution",
    }
    if not required_visible.issubset(set(decision.visible_to_user)):
        failures.append("visible field declaration incomplete")

    return PrimeDriftAudit(
        status="drift" if failures else "clean",
        checks=tuple(checks),
        failures=tuple(failures),
    )


def evaluate_prime_executability(
    *,
    context: PrimeRuntimeContext,
    owner_harness: str,
    requires_approval: bool = False,
    requires_clarification: bool = False,
) -> PrimeExecutability:
    """Gate a Prime decision before bridge/UI rendering or execution."""

    blockers: list[str] = []
    available = _available_harnesses(context)

    if owner_harness != "Prime" and owner_harness not in available:
        blockers.append(f"{owner_harness} source unavailable")

    if owner_harness == "Relay" and "Relay" not in available:
        blockers.append("model route proof unavailable")

    if context.aegis_risk and context.aegis_risk.is_blocking():
        blockers.extend(context.aegis_risk.blockers())

    if (
        owner_harness == "Vulcan"
        and context.beacon_liveness
        and context.beacon_liveness.is_degraded()
    ):
        blockers.extend(context.beacon_liveness.blockers())

    if requires_approval or (context.aegis_risk and context.aegis_risk.requires_approval()):
        return PrimeExecutability(
            status=PrimeDecisionStatus.NEEDS_APPROVAL,
            blockers=tuple(blockers + ["approval required"]),
        )

    if requires_clarification:
        return PrimeExecutability(
            status=PrimeDecisionStatus.NEEDS_CLARIFICATION,
            blockers=tuple(blockers + ["clarification required"]),
        )

    if blockers:
        return PrimeExecutability(
            status=PrimeDecisionStatus.BLOCKED,
            blockers=tuple(blockers),
        )

    return PrimeExecutability(status=PrimeDecisionStatus.EXECUTABLE)


def build_prime_proof_packet(
    *,
    owner_harness: str,
    context: PrimeRuntimeContext,
) -> tuple[PrimeProof, ...]:
    """Build proof questions for Prime's core no-drift hierarchy."""

    available = _available_harnesses(context)
    return (
        PrimeProof(
            question="Which harness owns the project boundary?",
            answer=(
                "Compass supplies project bounds before Prime selects an action."
                if "Compass" in available
                else "Compass project source is unavailable."
            ),
            source="Compass",
            invalidates_when="Prime acts without a Compass project source ref.",
        ),
        PrimeProof(
            question="Which harness owns runtime session lifecycle?",
            answer=(
                "Vulcan supplies session lifecycle before Prime routes execution."
                if "Vulcan" in available
                else "Vulcan session lifecycle source is unavailable."
            ),
            source="Vulcan",
            invalidates_when="Prime changes session state without a Vulcan source ref.",
        ),
        PrimeProof(
            question="Which harness owns model access and routing?",
            answer=(
                "Relay supplies model route logic before Prime can ask a model."
                if "Relay" in available
                else "Relay model route source is unavailable."
            ),
            source="Relay",
            invalidates_when="Prime selects a model/vendor without Relay evidence.",
        ),
        PrimeProof(
            question="What proof/risk gate did Aegis return?",
            answer=(
                context.aegis_risk.summary()
                if context.aegis_risk
                else "Aegis proof/risk source is unavailable."
            ),
            source="Aegis",
            invalidates_when="Prime executes a gated action without an Aegis risk input.",
        ),
        PrimeProof(
            question="Does the selected owner match the intent?",
            answer=f"{owner_harness} owns this decision after Prime hierarchy resolution.",
            source="Prime",
            invalidates_when="The visible owner differs from backend owner resolution.",
        ),
    )


def make_prime_decision(
    *,
    context: PrimeRuntimeContext,
    owner_harness: str = "Prime",
    action: str = "inspect_context",
    why: str = "Prime can inspect assembled backend context before UI rendering.",
    risk: str = "safe_read_only",
    status: PrimeDecisionStatus = PrimeDecisionStatus.EXECUTABLE,
    blockers: tuple[str, ...] = (),
    request: PrimeInteractionRequest | None = None,
) -> PrimeDecision:
    """Create a deterministic Prime decision with visible proof."""

    proof = build_prime_proof_packet(owner_harness=owner_harness, context=context)
    final_status = (
        PrimeDecisionStatus.BLOCKED
        if blockers and status == PrimeDecisionStatus.EXECUTABLE
        else status
    )
    return PrimeDecision(
        decision_id="prime-runtime-decision-v1",
        status=final_status,
        owner_harness=owner_harness,
        action=action,
        why=why,
        risk=risk,
        context=context,
        request=request,
        proof=proof,
        blockers=blockers,
        visible_to_user=(
            "Prime decision status",
            "owning harness",
            "backend source refs",
            "proof questions and answers",
            "blockers before execution",
        ),
    )


def resolve_prime_decision(
    *,
    context: PrimeRuntimeContext,
    intent: PrimeIntentKind | str | None,
    action: str,
    why: str,
    risk: str = "safe_read_only",
    requires_approval: bool = False,
    requires_clarification: bool = False,
    request: PrimeInteractionRequest | None = None,
) -> PrimeDecision:
    """Resolve owner, gate executability, and return the visible Prime decision."""

    owner = resolve_prime_owner(intent)
    gate = evaluate_prime_executability(
        context=context,
        owner_harness=owner,
        requires_approval=requires_approval,
        requires_clarification=requires_clarification,
    )
    return make_prime_decision(
        context=context,
        owner_harness=owner,
        action=action,
        why=why,
        risk=risk,
        status=gate.status,
        blockers=gate.blockers,
        request=request,
    )


def resolve_prime_interaction(
    *,
    context: PrimeRuntimeContext,
    request: PrimeInteractionRequest,
) -> PrimeDecision:
    """Resolve a typed Prime interaction request into the visible decision packet."""

    return resolve_prime_decision(
        context=context,
        intent=request.intent,
        action=request.action,
        why=request.why,
        risk=request.risk,
        requires_approval=request.requires_approval,
        requires_clarification=request.requires_clarification,
        request=request,
    )


def prime_runtime_snapshot() -> dict[str, Any]:
    """Return the canonical Prime runtime packet for bridge/UI rendering."""

    from meridian_core.compass_logic_snapshot import compass_logic_snapshot
    from meridian_core.aegis import summarize_aggregate_route_gates
    from meridian_core.beacon_liveness_snapshot import beacon_liveness_snapshot
    from meridian_core.relay_logic_snapshot import relay_logic_snapshot
    from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot

    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
        aegis_risk=aegis_risk_from_aggregate(summarize_aggregate_route_gates([])),
        beacon_liveness=beacon_liveness_from_snapshot(beacon_liveness_snapshot()),
    )
    request = PrimeInteractionRequest(
        request_id="prime-runtime-request-v1",
        intent=PrimeIntentKind.ORCHESTRATION,
        action="inspect_backend_context",
        why="Prime verifies Compass, Vulcan, Relay, and Aegis source refs before any UI-rendered orchestration.",
        project_id=context.project_id,
        visible_prompt_ref="visible Prime harness request",
    )
    decision = resolve_prime_interaction(
        context=context,
        request=request,
    )
    return {
        "ok": True,
        "service": "meridian-prime-runtime",
        "version": SNAPSHOT_VERSION,
        "source": SNAPSHOT_SOURCE,
        "harness": "Prime",
        "summary": "Prime owns orchestration only after backend project, session, route, and proof context are assembled visibly.",
        "primeDirectives": list(PRIME_DIRECTIVES),
        "primeDirectiveProofs": list(PRIME_DIRECTIVE_PROOFS),
        "decision": decision.to_dict(),
        "capabilitySections": [
            {
                "title": "Interaction Request",
                "summary": "Prime decisions are driven by typed request fields, not hidden UI interpretation.",
                "rows": [
                    {"key": "request id", "value": request.request_id},
                    {"key": "intent", "value": request.intent.value},
                    {"key": "action", "value": request.action},
                    {"key": "project", "value": request.project_id},
                    {"key": "visible prompt ref", "value": request.visible_prompt_ref},
                ],
            },
            {
                "title": "Prime Job",
                "summary": "Prime decides the next orchestration action without owning project bounds, session lifecycle, model routing, or proof gates.",
                "rows": [
                    {"key": "owns", "value": "orchestration, intent resolution, owner selection, executable status, visible explanation"},
                    {"key": "does not own", "value": "project bounds, session lifecycle, model/vendor access, proof acceptance"},
                    {"key": "no drift guard", "value": "visible Prime harness renders this backend decision packet and source refs"},
                ],
            },
            {
                "title": "Logic Hierarchy",
                "summary": "Prime consumes harness truth in a fixed order before choosing an action.",
                "rows": [
                    {"key": "1 Compass", "value": "project bounds and scope"},
                    {"key": "2 Vulcan", "value": "session lifecycle and runtime target state"},
                    {"key": "3 Relay", "value": "model route, vendor access, route proof, fallback blockers"},
                    {"key": "4 Aegis", "value": "proof/risk aggregate action, severity, evidence, and blockers"},
                    {"key": "5 Prime", "value": "select owner, explain why, block if source proof is missing"},
                ],
            },
            {
                "title": "Executability Logic",
                "summary": "Prime surfaces whether the next action is executable, blocked, needs approval, or needs clarification.",
                "rows": [
                    {"key": "executable", "value": "all required owner sources are available and no gate blocks action"},
                    {"key": "blocked", "value": "required backend source or route proof is missing"},
                    {"key": "needs approval", "value": "human gate or Aegis blocking/error risk requires approval before execution"},
                    {"key": "needs clarification", "value": "intent/scope is ambiguous enough to require user-facing question"},
                ],
            },
            {
                "title": "Aegis Binding",
                "summary": "Prime consumes Aegis aggregate gate state as backend risk truth instead of a placeholder.",
                "rows": [
                    {"key": "source", "value": context.aegis_risk.source if context.aegis_risk else "unavailable"},
                    {"key": "aggregate action", "value": context.aegis_risk.aggregate_action if context.aegis_risk else "unavailable"},
                    {"key": "highest severity", "value": context.aegis_risk.highest_severity if context.aegis_risk else "unavailable"},
                    {"key": "blocking", "value": "yes" if context.aegis_risk and context.aegis_risk.is_blocking() else "no"},
                ],
            },
            {
                "title": "Beacon Binding",
                "summary": "Prime consumes Beacon liveness as advisory evidence without gaining live-control authority.",
                "rows": [
                    {"key": "source", "value": context.beacon_liveness.source if context.beacon_liveness else "unavailable"},
                    {"key": "status", "value": ", ".join(context.beacon_liveness.statuses) if context.beacon_liveness else "unavailable"},
                    {"key": "observed harnesses", "value": str(len(context.beacon_liveness.observed_harnesses)) if context.beacon_liveness else "0"},
                    {"key": "blockers", "value": str(context.beacon_liveness.blocker_count) if context.beacon_liveness else "0"},
                    {"key": "live control authorized", "value": "false"},
                ],
            },
            {
                "title": "No Drift Audit",
                "summary": "Prime checks that request, context, owner, source refs, proof, and visible fields agree.",
                "rows": [
                    {"key": "status", "value": audit_prime_decision(decision).status},
                    {"key": "clean", "value": "yes" if audit_prime_decision(decision).is_clean() else "no"},
                    {"key": "checks", "value": ", ".join(audit_prime_decision(decision).checks)},
                    {"key": "failures", "value": ", ".join(audit_prime_decision(decision).failures) or "none"},
                ],
            },
            {
                "title": "Proof Packet",
                "summary": "Prime exposes the proof questions that must be visible for every orchestration decision.",
                "rows": [
                    {"key": item.question, "value": item.answer}
                    for item in decision.proof
                ],
            },
        ],
    }


def main() -> None:
    import json

    print(json.dumps(prime_runtime_snapshot(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
