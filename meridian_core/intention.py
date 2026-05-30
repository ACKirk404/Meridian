"""
Progress Intention — Prime stating what work is about to move.

Derives a structured ProgressIntention from portfolio and decision state.
No model calls. No side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .council import CouncilPlan, council_plan_for_tier
from .decisions import DecisionResult
from .models import Heartbeat, HeartbeatStatus, Initiative, MoveKind, Portfolio
from .risk import RiskTier  # noqa: F401 — re-exported for callers that import from here

_BLOCKED_HARNESS_STATUSES: frozenset[HeartbeatStatus] = frozenset(
    {HeartbeatStatus.BLOCKED, HeartbeatStatus.FAILED}
)


class ObjectiveStage(Enum):
    PLAN = "Plan"
    BUILD = "Build"
    REVIEW = "Review"
    VERIFY = "Verify"
    BLOCKED = "Blocked"
    GATE = "Gate"


_STAGE_TO_TIER: dict[ObjectiveStage, RiskTier] = {
    ObjectiveStage.PLAN: RiskTier.TIER_1,
    ObjectiveStage.BUILD: RiskTier.TIER_2,
    ObjectiveStage.REVIEW: RiskTier.TIER_3,
    ObjectiveStage.VERIFY: RiskTier.TIER_3,
    ObjectiveStage.BLOCKED: RiskTier.TIER_4,
    ObjectiveStage.GATE: RiskTier.TIER_4,
}

_STAGE_RISK_REASONS: dict[ObjectiveStage, str] = {
    ObjectiveStage.PLAN: "no active moves yet; planning only",
    ObjectiveStage.BUILD: "autonomous build work in progress",
    ObjectiveStage.REVIEW: "autonomous review work; read-only",
    ObjectiveStage.VERIFY: "proof required before proceeding",
    ObjectiveStage.BLOCKED: "target session blocked or failed; requires escalation",
    ObjectiveStage.GATE: "human judgment required before any action",
}


@dataclass
class MissionObjectiveLine:
    project_name: str
    initiative_title: str
    stage: ObjectiveStage
    risk_tier: RiskTier
    risk_reason: str = ""

    @property
    def council_plan(self) -> CouncilPlan:
        """Council cognition plan for this line's risk tier. Computed on access."""
        return council_plan_for_tier(self.risk_tier)


@dataclass
class ProgressIntention:
    current_stage: str
    initiating_harness: str
    objective_lines: list[MissionObjectiveLine] = field(default_factory=list)
    next_stage: str = ""


def build_progress_intention(
    portfolio: Portfolio,
    decision_result: DecisionResult,
    heartbeats: list[Heartbeat] | None = None,
    current_stage: str = "Mission Boot",
    initiating_harness: str = "Compass",
    next_stage: str = "Intention Engine Bootup",
) -> ProgressIntention:
    """
    Build a ProgressIntention from real portfolio and decision state.
    Deterministic. No model calls.
    """
    bn_move_ids = {bn.move_id for bn in decision_result.scott_bottlenecks if bn.move_id}
    injection_targets = {inj.target_session_id for inj in decision_result.injections}
    safe_move_ids = {m.id for m in decision_result.safe_next_moves}
    blocked_session_ids = {
        hb.harness_id for hb in (heartbeats or [])
        if hb.status in _BLOCKED_HARNESS_STATUSES
    }

    lines: list[MissionObjectiveLine] = []
    seen_initiative_ids: set[str] = set()

    for project_name, initiative in _iter_project_initiatives(portfolio):
        if initiative.id in seen_initiative_ids:
            continue
        seen_initiative_ids.add(initiative.id)

        stage = _derive_stage(initiative, bn_move_ids, injection_targets, safe_move_ids, blocked_session_ids)
        tier = _STAGE_TO_TIER[stage]
        lines.append(
            MissionObjectiveLine(
                project_name=project_name,
                initiative_title=initiative.title,
                stage=stage,
                risk_tier=tier,
                risk_reason=_STAGE_RISK_REASONS[stage],
            )
        )

    return ProgressIntention(
        current_stage=current_stage,
        initiating_harness=initiating_harness,
        objective_lines=lines,
        next_stage=next_stage,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_project_initiatives(portfolio: Portfolio):
    """Yield (project_title, initiative) for all initiatives in the portfolio."""
    seen_project_ids: set[str] = set()
    for venture in portfolio.ventures:
        for project in venture.projects:
            if project.id not in seen_project_ids:
                seen_project_ids.add(project.id)
                for initiative in project.initiatives:
                    yield project.title, initiative
    for project in portfolio.projects:
        if project.id not in seen_project_ids:
            seen_project_ids.add(project.id)
            for initiative in project.initiatives:
                yield project.title, initiative


def _derive_stage(
    initiative: Initiative,
    bn_move_ids: set[str],
    injection_targets: set[str],
    safe_move_ids: set[str],
    blocked_session_ids: set[str],
) -> ObjectiveStage:
    """
    Deterministic stage derivation, evaluated in priority order:
    Gate > Blocked > Verify > Review > Build > Plan
    """
    if not initiative.next_moves:
        return ObjectiveStage.PLAN

    # Gate: any move requires Scott's judgment (bottleneck or SCOTT_REQUIRED kind)
    if any(m.kind == MoveKind.SCOTT_REQUIRED for m in initiative.next_moves):
        return ObjectiveStage.GATE
    if any(m.id in bn_move_ids for m in initiative.next_moves):
        return ObjectiveStage.GATE

    # Blocked: autonomous move targets a harness that is blocked or failed
    if any(
        m.kind == MoveKind.AUTONOMOUS
        and m.session_id is not None
        and m.session_id in blocked_session_ids
        for m in initiative.next_moves
    ):
        return ObjectiveStage.BLOCKED

    # Verify: an autonomous move needs proof and has a target session that received an injection
    if any(
        m.proof_required
        and (m.proof is None or not m.proof.verified)
        and m.session_id is not None
        and m.session_id in injection_targets
        for m in initiative.next_moves
    ):
        return ObjectiveStage.VERIFY

    # Review / Build: safe autonomous moves
    safe_moves = [m for m in initiative.next_moves if m.id in safe_move_ids]
    if safe_moves:
        combined = " ".join(m.description.lower() for m in safe_moves)
        if "review" in combined:
            return ObjectiveStage.REVIEW
        return ObjectiveStage.BUILD

    # Remaining autonomous moves with unresolved proof but no injection target
    return ObjectiveStage.VERIFY
