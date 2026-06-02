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
class PrimeRuntimeContext:
    """Backend context packet Prime consumes before choosing an action."""

    project_id: str
    project_summary: str
    session_state: str
    relay_route_summary: str
    risk_summary: str
    source_refs: tuple[PrimeSourceRef, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projectId": self.project_id,
            "projectSummary": self.project_summary,
            "sessionState": self.session_state,
            "relayRouteSummary": self.relay_route_summary,
            "riskSummary": self.risk_summary,
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
    proof: tuple[PrimeProof, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    visible_to_scott: tuple[str, ...] = field(default_factory=tuple)

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
            "context": self.context.to_dict(),
            "proof": [item.to_dict() for item in self.proof],
            "blockers": list(self.blockers),
            "visibleToScott": list(self.visible_to_scott),
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
    project_id: str = "Meridian",
    risk_summary: str = "Aegis proof/risk gate unavailable; treat as safe read-only until wired.",
) -> PrimeRuntimeContext:
    """Assemble Prime context from backend harness snapshots only."""

    compass_source = str(compass_snapshot.get("source") or "unknown")
    vulcan_source = str(vulcan_snapshot.get("source") or "unknown")
    relay_source = str(relay_snapshot.get("source") or "unknown")

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
        risk_summary=risk_summary,
        source_refs=(
            PrimeSourceRef("Compass", compass_source, "project bounds and scope"),
            PrimeSourceRef("Vulcan", vulcan_source, "session lifecycle state"),
            PrimeSourceRef("Relay", relay_source, "model route and access logic"),
            PrimeSourceRef("Aegis", "pending", "proof/risk gate placeholder"),
        ),
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

    if requires_approval:
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
) -> PrimeDecision:
    """Create a deterministic Prime decision with visible proof."""

    proof = build_prime_proof_packet(owner_harness=owner_harness, context=context)
    final_status = PrimeDecisionStatus.BLOCKED if blockers else status
    return PrimeDecision(
        decision_id="prime-runtime-decision-v1",
        status=final_status,
        owner_harness=owner_harness,
        action=action,
        why=why,
        risk=risk,
        context=context,
        proof=proof,
        blockers=blockers,
        visible_to_scott=(
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
    )


def prime_runtime_snapshot() -> dict[str, Any]:
    """Return the canonical Prime runtime packet for bridge/UI rendering."""

    from meridian_core.compass_logic_snapshot import compass_logic_snapshot
    from meridian_core.relay_logic_snapshot import relay_logic_snapshot
    from meridian_core.vulcan_logic_snapshot import vulcan_logic_snapshot

    context = assemble_prime_runtime_context(
        compass_snapshot=compass_logic_snapshot(),
        vulcan_snapshot=vulcan_logic_snapshot(),
        relay_snapshot=relay_logic_snapshot(),
    )
    decision = resolve_prime_decision(
        context=context,
        intent=PrimeIntentKind.ORCHESTRATION,
        action="inspect_backend_context",
        why="Prime verifies Compass, Vulcan, Relay, and Aegis source refs before any UI-rendered orchestration.",
    )
    return {
        "ok": True,
        "service": "meridian-prime-runtime",
        "version": SNAPSHOT_VERSION,
        "source": SNAPSHOT_SOURCE,
        "harness": "Prime",
        "summary": "Prime owns orchestration only after backend project, session, route, and proof context are assembled visibly.",
        "decision": decision.to_dict(),
        "capabilitySections": [
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
                    {"key": "4 Aegis", "value": "proof/risk gate; placeholder until live gate is wired"},
                    {"key": "5 Prime", "value": "select owner, explain why, block if source proof is missing"},
                ],
            },
            {
                "title": "Executability Logic",
                "summary": "Prime surfaces whether the next action is executable, blocked, needs approval, or needs clarification.",
                "rows": [
                    {"key": "executable", "value": "all required owner sources are available and no gate blocks action"},
                    {"key": "blocked", "value": "required backend source or route proof is missing"},
                    {"key": "needs approval", "value": "human or Aegis gate required before execution"},
                    {"key": "needs clarification", "value": "intent/scope is ambiguous enough to require Scott-facing question"},
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
