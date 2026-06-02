"""Prime Autonomy domain model for next-action decisions.

Frozen dataclasses and helpers for representing Prime's next deterministic action,
independent of UI/runtime integration. Used for decision logging, audit trails,
and deterministic fallback action selection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, FrozenSet

from meridian_core.session_lifecycle import (
    FindingType,
    OperationScope,
    PrimeAutonomyInput as SessionPrimeAutonomyInput,
    ReviewCadenceState,
    SessionStatus,
)


class PrimeActionType(Enum):
    """Type of action Prime can direct."""
    POLL_SESSION = "poll_session"  # Check session state
    ADVISE_SESSION_RECOVERY = "advise_session_recovery"  # Stage recovery advice only
    ADVANCE_COGNITION = "advance_cognition"  # Run cognition policy evaluation
    RUN_WORKFLOW = "run_workflow"  # Execute workflow sub-agent
    PAUSE_AND_WAIT = "pause_and_wait"  # Wait for human input or external signal
    ESCALATE_ERROR = "escalate_error"  # Report blocker or error state
    NO_OP = "no_op"  # Safe default: do nothing


class PrimeActionConfidence(Enum):
    """Confidence in action selection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FALLBACK = "fallback"  # Default safe action when uncertain


class PrimeActionRiskTier(Enum):
    """Risk level of the action."""
    SAFE = "safe"  # Read-only, no state changes
    LOW = "low"  # Minor state changes, easily reversible
    MEDIUM = "medium"  # Significant changes, requires audit trail
    HIGH = "high"  # Major changes, human gate required


class PrimeActionSource(Enum):
    """Source of the action decision."""
    COGNITION_POLICY = "cognition_policy"
    WORKFLOW_RESULT = "workflow_result"
    SESSION_STATE = "session_state"
    ERROR_RECOVERY = "error_recovery"
    HUMAN_OVERRIDE = "human_override"


@dataclass(frozen=True)
class PrimeNextAction:
    """Immutable representation of Prime's next deterministic action.

    Fields define the action type, target scope, decision quality, risk level,
    blockers, human-gate requirement, rationale, and evidence references.
    """

    action_type: PrimeActionType
    confidence: PrimeActionConfidence
    risk_tier: PrimeActionRiskTier
    source: PrimeActionSource

    # Target scope: which harness/lane/project this action targets
    target_harness: Optional[str] = None  # e.g., "Echo", "Atlas", "Relay"
    target_lane: Optional[str] = None      # e.g., "cognition", "workflow"
    target_project: Optional[str] = None   # e.g., "Meridian", external

    # Decision context
    rationale: str = ""  # Why this action was chosen
    evidence: FrozenSet[str] = field(default_factory=frozenset)  # References to proof/audit log entries

    # Constraints
    human_gate_required: bool = False  # Must wait for human approval before executing
    blockers: FrozenSet[str] = field(default_factory=frozenset)  # Blocking conditions preventing execution

    def is_blocked(self) -> bool:
        """Return True if any blockers prevent execution."""
        return bool(self.blockers)

    def is_executable(self) -> bool:
        """Return True only when no blocker or pending human gate prevents execution."""
        return not self.is_blocked() and not self.human_gate_required


def select_prime_next_action(
    action_type: Optional[PrimeActionType] = None,
    confidence: Optional[PrimeActionConfidence] = None,
    risk_tier: Optional[PrimeActionRiskTier] = None,
    source: Optional[PrimeActionSource] = None,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Deterministic helper to construct a Prime next-action with fallback defaults.

    Any None input falls back to a safe default, ensuring a valid action always returns.
    Returns a frozen immutable PrimeNextAction ready for decision logging.
    """

    # Safe defaults for each field
    final_action_type = action_type or PrimeActionType.PAUSE_AND_WAIT
    final_confidence = confidence or PrimeActionConfidence.FALLBACK
    final_risk_tier = risk_tier or PrimeActionRiskTier.SAFE
    final_source = source or PrimeActionSource.ERROR_RECOVERY

    # Convert lists to frozen sets
    final_evidence = frozenset(evidence or [])
    final_blockers = frozenset(blockers or [])

    return PrimeNextAction(
        action_type=final_action_type,
        confidence=final_confidence,
        risk_tier=final_risk_tier,
        source=final_source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=final_evidence,
        human_gate_required=human_gate_required,
        blockers=final_blockers,
    )


def make_prime_next_action(
    action_type: PrimeActionType,
    confidence: PrimeActionConfidence,
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE,
    source: PrimeActionSource = PrimeActionSource.ERROR_RECOVERY,
    target_harness: Optional[str] = None,
    target_lane: Optional[str] = None,
    target_project: Optional[str] = None,
    rationale: str = "",
    evidence: Optional[List[str]] = None,
    human_gate_required: bool = False,
    blockers: Optional[List[str]] = None,
) -> PrimeNextAction:
    """Strict constructor for Prime next-action: requires action_type and confidence.

    Falls back only on optional fields. Use this when you have explicit action intent.
    """

    return select_prime_next_action(
        action_type=action_type,
        confidence=confidence,
        risk_tier=risk_tier,
        source=source,
        target_harness=target_harness,
        target_lane=target_lane,
        target_project=target_project,
        rationale=rationale,
        evidence=evidence,
        human_gate_required=human_gate_required,
        blockers=blockers,
    )


# Review cadence gate: require Codex review after this many task-changing commits.
_REVIEW_GATE_COMMIT_LIMIT = 3


@dataclass(frozen=True)
class ProjectStateSignal:
    """Plain data snapshot of project/backlog/lane state for the Prime selector.

    All inputs are plain data — no model, Echo, or Atlas calls are made
    inside this class or the selector that consumes it.
    """

    active_task: Optional[str] = None        # current active task ID, or None if queue is idle
    candidate_task: Optional[str] = None     # next candidate task ID, or None
    review_gate_open: bool = True            # False when cadence gate explicitly blocks new work
    commits_since_review: int = 0            # commits since last accepted Codex review
    human_gate_required: bool = False        # must wait for human approval before proceeding
    blockers: FrozenSet[str] = field(default_factory=frozenset)  # active blocking conditions
    lane_id: Optional[str] = None            # which build lane (e.g. "build-1")
    risk_tier: PrimeActionRiskTier = PrimeActionRiskTier.SAFE
    echo_signal: Optional[str] = None        # Echo memory context placeholder (plain data)
    atlas_signal: Optional[str] = None       # Atlas retrieval context placeholder (plain data)


def select_next_action_from_project_state(
    state: Optional[ProjectStateSignal] = None,
) -> PrimeNextAction:
    """Select the next Prime action deterministically from project/backlog/lane state.

    Priority (most restrictive first):
      1. Missing state (None)  → PAUSE_AND_WAIT, FALLBACK confidence
      2. Human gate required   → PAUSE_AND_WAIT, human_gate_required=True
      3. Active blockers       → ESCALATE_ERROR
      4. HIGH risk tier        → PAUSE_AND_WAIT, human_gate_required=True
      5. Review gate tripped   → PAUSE_AND_WAIT (cadence gate or explicit close)
      6. No active task        → POLL_SESSION
      7. Active task present   → ADVANCE_COGNITION

    No model calls, filesystem reads, or network access are performed.
    """
    if state is None:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            rationale="No project state available; cannot determine next action safely.",
        )

    # Priority 2: Human gate
    if state.human_gate_required:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.SESSION_STATE,
            target_lane=state.lane_id,
            rationale="Human gate is required before proceeding.",
            blockers=list(state.blockers),
            human_gate_required=True,
        )

    # Priority 3: Blockers
    if state.blockers:
        return make_prime_next_action(
            action_type=PrimeActionType.ESCALATE_ERROR,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_lane=state.lane_id,
            rationale=f"Blockers prevent execution: {'; '.join(sorted(state.blockers))}",
            blockers=list(state.blockers),
        )

    # Priority 4: HIGH risk tier auto-gates to human approval
    if state.risk_tier == PrimeActionRiskTier.HIGH:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.COGNITION_POLICY,
            target_lane=state.lane_id,
            rationale="High risk tier requires human gate before execution.",
            human_gate_required=True,
        )

    # Priority 5: Review gate (explicit close or commit-count limit)
    review_gate_tripped = (
        not state.review_gate_open
        or state.commits_since_review >= _REVIEW_GATE_COMMIT_LIMIT
    )
    if review_gate_tripped:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.MEDIUM,
            risk_tier=state.risk_tier,
            source=PrimeActionSource.COGNITION_POLICY,
            target_lane=state.lane_id,
            rationale=(
                f"Review gate: {state.commits_since_review} commit(s) since last review, "
                f"gate_open={state.review_gate_open}."
            ),
        )

    # Priority 6: No active task — poll for new assignment
    if state.active_task is None:
        return make_prime_next_action(
            action_type=PrimeActionType.POLL_SESSION,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.SESSION_STATE,
            target_lane=state.lane_id,
            rationale="No active task; polling queue for new assignment.",
        )

    # Priority 7: Active task — advance cognition
    return make_prime_next_action(
        action_type=PrimeActionType.ADVANCE_COGNITION,
        confidence=PrimeActionConfidence.HIGH,
        risk_tier=state.risk_tier,
        source=PrimeActionSource.COGNITION_POLICY,
        target_lane=state.lane_id,
        rationale=f"Active task '{state.active_task}' is ready; advancing cognition.",
    )


def select_next_action_from_session_lifecycle_advisory(
    advisory_input: Optional[SessionPrimeAutonomyInput] = None,
) -> PrimeNextAction:
    """Convert Session Lifecycle Prime/Beacon input into a safe Prime advisory.

    The returned action can advise, pause, or escalate, but it never executes
    restart/resteer control. Live recovery still requires a separate command plan.
    """
    if advisory_input is None:
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.FALLBACK,
            risk_tier=PrimeActionRiskTier.SAFE,
            source=PrimeActionSource.ERROR_RECOVERY,
            target_harness="Session Lifecycle",
            rationale="No Session Lifecycle advisory input available.",
        )

    sessions_by_id = {
        session.session_id: session for session in advisory_input.current_sessions
    }

    if advisory_input.approvals_pending:
        blockers = [
            f"{session_id}: {reason}"
            for session_id, reason in advisory_input.approvals_pending
        ]
        return make_prime_next_action(
            action_type=PrimeActionType.PAUSE_AND_WAIT,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.SESSION_STATE,
            target_harness="Session Lifecycle",
            rationale="Session recovery advisory is waiting on approval.",
            evidence=blockers,
            human_gate_required=True,
            blockers=blockers,
        )

    for session in advisory_input.current_sessions:
        if (
            session.status == SessionStatus.REVIEW_GATED
            or session.review_cadence_state == ReviewCadenceState.REVIEW_GATED
        ):
            evidence = [
                f"{session.session_id}: status={session.status.value}",
                f"{session.session_id}: review={session.review_cadence_state.value}",
            ]
            return make_prime_next_action(
                action_type=PrimeActionType.PAUSE_AND_WAIT,
                confidence=PrimeActionConfidence.HIGH,
                risk_tier=PrimeActionRiskTier.HIGH,
                source=PrimeActionSource.SESSION_STATE,
                target_harness="Session Lifecycle",
                target_lane=session.session_id,
                rationale="Review gate blocks session recovery advice from execution.",
                evidence=evidence,
                human_gate_required=True,
                blockers=["review gate requires human approval"],
            )

    for finding in advisory_input.restart_resteer_findings:
        session = sessions_by_id.get(finding.session_id)
        operation = (
            OperationScope.RESTART
            if finding.finding_type == FindingType.RESTART
            else OperationScope.RESTEER
        )
        evidence = [
            f"{finding.session_id}: finding={finding.finding_type.value}",
            f"{finding.session_id}: stale_seconds={finding.evidence_stale_seconds}",
            f"{finding.session_id}: recommendation={finding.recommended_action}",
        ]

        if session is not None and not session.can_execute_operation(operation):
            blocker = f"{finding.session_id}: permission boundary blocks {operation.value}"
            return make_prime_next_action(
                action_type=PrimeActionType.PAUSE_AND_WAIT,
                confidence=PrimeActionConfidence.HIGH,
                risk_tier=PrimeActionRiskTier.HIGH,
                source=PrimeActionSource.SESSION_STATE,
                target_harness="Session Lifecycle",
                target_lane=finding.session_id,
                rationale="Permission boundary blocks session recovery advice.",
                evidence=evidence,
                human_gate_required=True,
                blockers=[blocker],
            )

        return make_prime_next_action(
            action_type=PrimeActionType.ADVISE_SESSION_RECOVERY,
            confidence=PrimeActionConfidence.HIGH,
            risk_tier=PrimeActionRiskTier.HIGH,
            source=PrimeActionSource.SESSION_STATE,
            target_harness="Session Lifecycle",
            target_lane=finding.session_id,
            rationale=f"Advise {finding.finding_type.value} recovery: {finding.reason}",
            evidence=evidence,
            human_gate_required=True,
            blockers=["advisory only; command plan approval required before execution"],
        )

    session_ids = [session.session_id for session in advisory_input.current_sessions]
    return make_prime_next_action(
        action_type=PrimeActionType.POLL_SESSION,
        confidence=PrimeActionConfidence.MEDIUM,
        risk_tier=PrimeActionRiskTier.SAFE,
        source=PrimeActionSource.SESSION_STATE,
        target_harness="Session Lifecycle",
        rationale="No restart/resteer findings; continue watching session state.",
        evidence=session_ids,
    )
