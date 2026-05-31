"""Prime Autonomy domain model for next-action decisions.

Frozen dataclasses and helpers for representing Prime's next deterministic action,
independent of UI/runtime integration. Used for decision logging, audit trails,
and deterministic fallback action selection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, FrozenSet


class PrimeActionType(Enum):
    """Type of action Prime can direct."""
    POLL_SESSION = "poll_session"  # Check session state
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
