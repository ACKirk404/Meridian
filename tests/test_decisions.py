import pytest

from meridian_core.decisions import run_decision_loop
from meridian_core.events import EventKind, EventRecorder
from meridian_core.models import HeartbeatStatus, MoveKind
from meridian_core.sample_state import make_sample_heartbeats, make_sample_portfolio


def test_sample_portfolio_has_at_least_three_initiatives():
    portfolio = make_sample_portfolio()
    assert len(portfolio.all_initiatives()) >= 3


def test_blocked_harness_with_blockers_produces_injection():
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()

    blocked_with_blockers = [
        hb for hb in heartbeats
        if hb.status == HeartbeatStatus.BLOCKED and hb.blockers
    ]
    assert blocked_with_blockers, "Sample state must include a blocked harness with known blockers"

    result = run_decision_loop(portfolio, heartbeats)

    blocked_ids = {hb.harness_id for hb in blocked_with_blockers}
    injection_targets = {inj.target_session_id for inj in result.injections}
    assert injection_targets & blocked_ids, "Expected injection targeting the blocked harness"


def test_scott_only_moves_become_bottlenecks_and_are_not_auto_advanced():
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()

    scott_moves = [m for m in portfolio.all_next_moves() if m.kind == MoveKind.SCOTT_REQUIRED]
    assert scott_moves, "Sample state must include at least one scott-required move"

    result = run_decision_loop(portfolio, heartbeats)

    safe_move_ids = {m.id for m in result.safe_next_moves}
    for move in scott_moves:
        assert move.id not in safe_move_ids, f"Move {move.id!r} is SCOTT_REQUIRED but appeared in safe_next_moves"

    bottleneck_move_ids = {bn.move_id for bn in result.scott_bottlenecks}
    for move in scott_moves:
        assert move.id in bottleneck_move_ids, f"Move {move.id!r} has no corresponding ScottBottleneck"


def test_missing_proof_produces_verification_injection():
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()

    needs_proof = [
        m for m in portfolio.all_next_moves()
        if m.kind == MoveKind.AUTONOMOUS
        and m.proof_required
        and (m.proof is None or not m.proof.verified)
    ]
    assert needs_proof, "Sample state must include an autonomous move with unverified proof"

    result = run_decision_loop(portfolio, heartbeats)

    # Each unverified-proof move should produce an injection
    assert len(result.injections) >= len(needs_proof), (
        f"Expected at least {len(needs_proof)} verification injection(s), "
        f"got {len(result.injections)}"
    )
    # At least one injection should mention verification
    assert any(
        "verification" in inj.instruction.lower() or "proof" in inj.instruction.lower()
        or "verify" in inj.reason.lower()
        for inj in result.injections
    )


def test_events_are_recorded_when_recorder_provided():
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()
    recorder = EventRecorder()

    run_decision_loop(portfolio, heartbeats, recorder=recorder)

    events = recorder.all_events()
    assert len(events) > 0

    event_kinds = {e.kind for e in events}
    expected = {EventKind.DECISION_MADE, EventKind.BOTTLENECK_CREATED, EventKind.INJECTION_GENERATED}
    assert event_kinds & expected, f"Expected at least one of {expected}, got {event_kinds}"


def test_no_events_recorded_without_recorder():
    # Confirm the loop runs cleanly without a recorder — no AttributeErrors
    portfolio = make_sample_portfolio()
    heartbeats = make_sample_heartbeats()
    result = run_decision_loop(portfolio, heartbeats, recorder=None)
    assert result is not None
