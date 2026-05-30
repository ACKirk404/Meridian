"""
Meridian kernel decision loop.

Deterministic, rule-light, and inspectable. Not an LLM planner.
Reads portfolio state and heartbeat; produces next moves, Scott bottlenecks,
decisions, and session injections.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from .events import EventRecorder
from .injections import make_injection
from .models import (
    Decision,
    Heartbeat,
    HeartbeatStatus,
    InjectionMode,
    MoveKind,
    NextMove,
    Portfolio,
    Priority,
    ScottBottleneck,
    SessionInjection,
)


@dataclass
class DecisionResult:
    safe_next_moves: list[NextMove] = field(default_factory=list)
    scott_bottlenecks: list[ScottBottleneck] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    injections: list[SessionInjection] = field(default_factory=list)


def run_decision_loop(
    portfolio: Portfolio,
    heartbeats: list[Heartbeat],
    recorder: Optional[EventRecorder] = None,
) -> DecisionResult:
    """
    Core kernel decision loop.

    Rules applied in order:
    1. Unhealthy harnesses → injection (if blockers known) or bottleneck.
    2. Scott-required next moves → bottleneck, never auto-advanced.
    3. Autonomous moves with unverified proof → verification injection.
    4. Remaining autonomous moves → safe to advance.
    """
    result = DecisionResult()

    _process_heartbeats(heartbeats, result, recorder)
    _process_next_moves(portfolio, result, recorder)

    return result


# ---------------------------------------------------------------------------
# Internal rules
# ---------------------------------------------------------------------------


def _process_heartbeats(
    heartbeats: list[Heartbeat],
    result: DecisionResult,
    recorder: Optional[EventRecorder],
) -> None:
    unhealthy = {HeartbeatStatus.BLOCKED, HeartbeatStatus.STALE, HeartbeatStatus.FAILED}

    for hb in heartbeats:
        if hb.status not in unhealthy:
            continue

        if hb.blockers:
            inj = make_injection(
                target_session_id=hb.harness_id,
                instruction=(
                    f"Harness is {hb.status.value}. "
                    f"Known blockers: {', '.join(hb.blockers)}. "
                    "Investigate and resolve or escalate."
                ),
                reason=f"Automatic response to {hb.status.value} harness with known blockers",
                priority=Priority.HIGH,
                mode=InjectionMode.DIRECTIVE,
                stable_key=f"injection:harness:{hb.harness_id}:{hb.status.value}",
            )
            result.injections.append(inj)

            decision = Decision(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"decision:harness:{hb.harness_id}:{hb.status.value}")),
                next_action=f"inject_directive_to_{hb.harness_id}",
                reason=f"Harness {hb.harness_id!r} is {hb.status.value} with {len(hb.blockers)} known blocker(s)",
                evidence_needed=[f"harness {hb.harness_id!r} resumes alive or busy status"],
                hard_policies_checked=["do_not_edit_another_sessions_worktree"],
            )
            result.decisions.append(decision)

            if recorder:
                recorder.record_decision(decision)
                recorder.record_injection(inj)
        else:
            # No blockers known — escalate to Scott
            bn = ScottBottleneck(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bottleneck:harness:{hb.harness_id}:{hb.status.value}")),
                title=f"Harness {hb.harness_id!r} is {hb.status.value} with no known blockers",
                description=(
                    f"Harness {hb.harness_id!r} reported status {hb.status.value!r} "
                    "but provided no blockers. Scott may need to diagnose or restart it."
                ),
                priority=Priority.MEDIUM,
            )
            result.scott_bottlenecks.append(bn)

            if recorder:
                recorder.record_bottleneck(bn)


def _process_next_moves(
    portfolio: Portfolio,
    result: DecisionResult,
    recorder: Optional[EventRecorder],
) -> None:
    for move in portfolio.all_next_moves():
        if move.kind == MoveKind.SCOTT_REQUIRED:
            _escalate_to_scott(move, result, recorder)
        elif move.proof_required and (move.proof is None or not move.proof.verified):
            _request_verification(move, result, recorder)
        else:
            result.safe_next_moves.append(move)


def _escalate_to_scott(
    move: NextMove,
    result: DecisionResult,
    recorder: Optional[EventRecorder],
) -> None:
    bn = ScottBottleneck(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bottleneck:move:{move.id}")),
        title=f"Scott judgment required: {move.description}",
        description=move.reason or "This next move requires Scott's judgment before Meridian can proceed.",
        priority=Priority.HIGH,
        move_id=move.id,
    )
    result.scott_bottlenecks.append(bn)

    if recorder:
        recorder.record_bottleneck(bn)


def _request_verification(
    move: NextMove,
    result: DecisionResult,
    recorder: Optional[EventRecorder],
) -> None:
    proof_cmd = move.proof.command if move.proof else None
    instruction = (
        f"Verification required before proceeding with: '{move.description}'. "
        + (f"Run: `{proof_cmd}` and return evidence." if proof_cmd else "Run proof check and return evidence.")
    )

    inj = make_injection(
        target_session_id=move.session_id or "agent_harness",
        instruction=instruction,
        reason="Next move is autonomous but proof is required and not yet verified",
        priority=Priority.HIGH,
        mode=InjectionMode.DIRECTIVE,
        stable_key=f"injection:verify:{move.id}",
    )
    result.injections.append(inj)

    if recorder:
        recorder.record_injection(inj)
