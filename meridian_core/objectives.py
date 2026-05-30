"""
Mission Objectives recall layer.

Stable on-demand API for the current mission objectives view.
Designed to be called by the future Compass UI control, the CLI, or any caller.
Reuses the ProgressIntention domain model — does not duplicate it.
"""

from __future__ import annotations

from .decisions import DecisionResult
from .intention import ProgressIntention, build_progress_intention
from .models import Heartbeat, Portfolio


def get_mission_objectives(
    portfolio: Portfolio,
    decision_result: DecisionResult,
    heartbeats: list[Heartbeat] | None = None,
    current_stage: str = "Mission Boot",
    initiating_harness: str = "Compass",
    next_stage: str = "Intention Engine Bootup",
) -> ProgressIntention:
    """
    Return the current mission objectives view, callable on demand.

    This is the stable API surface for the future UI Compass control.
    Independent of wake sequence rendering — safe to call at any time.
    """
    return build_progress_intention(
        portfolio,
        decision_result,
        heartbeats=heartbeats,
        current_stage=current_stage,
        initiating_harness=initiating_harness,
        next_stage=next_stage,
    )


def format_mission_objectives_text(view: ProgressIntention) -> str:
    """
    Render a ProgressIntention as the canonical mission objectives text.

    Suitable for the CLI, non-orchestrator queue display, or any plain-text surface.
    UI rendering uses the structured ProgressIntention object directly.
    """
    lines = [
        f"Stage: {view.current_stage} > {view.initiating_harness} Initiating",
        "",
        "Mission Objectives:",
    ]
    for obj in view.objective_lines:
        plan = obj.council_plan
        council_str = "full council" if plan.requires_full_council else ", ".join(r.value for r in plan.roles)
        lines.append(
            f"  {obj.project_name} - {obj.initiative_title}"
            f" - Stage {obj.stage.value}"
            f" - Risk Tier {obj.risk_tier.value}"
            f" - Council: {council_str}"
        )
    lines.extend(["", f"Next Stage: {view.next_stage}"])
    return "\n".join(lines)
