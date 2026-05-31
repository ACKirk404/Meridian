"""Tests for Prime restart/resteer deterministic lane recovery."""

from __future__ import annotations

from meridian_core.restart_resteer import (
    EscalationGate,
    FindingSeverity,
    HealthFindingKind,
    LaneOperatingFrame,
    LaneRole,
    QuotaState,
    RecoveryActionKind,
    RestartDirective,
    RestartKind,
    ResteerDirective,
    ResteerKind,
    choose_recovery_action,
    evaluate_lane_frame,
)


def _frame(**overrides: object) -> LaneOperatingFrame:
    values = {
        "lane_id": "build-1",
        "lane_role": LaneRole.BUILD,
        "assigned_queue_path": "docs/live-build-1.md",
        "current_queue_path": "docs/live-build-1.md",
        "expected_queue_path": "docs/live-build-1.md",
        "worktree_path": "C:/Users/scott/AppData/Local/Temp/meridian-build-1",
        "repo_root_path": "C:/Users/scott/Code/Meridian",
        "allowed_paths": ("meridian_core/", "tests/"),
        "active_task_id": "task-1",
        "next_candidate_id": "task-2",
        "quota_state": QuotaState.AVAILABLE,
    }
    values.update(overrides)
    return LaneOperatingFrame(**values)  # type: ignore[arg-type]


def _kinds(frame: LaneOperatingFrame) -> set[HealthFindingKind]:
    return {finding.kind for finding in evaluate_lane_frame(frame)}


def test_no_findings_for_healthy_lane():
    assert evaluate_lane_frame(_frame()) == ()


def test_empty_queue_produces_resteer_finding():
    findings = evaluate_lane_frame(_frame(active_task_id="", next_candidate_id=""))
    assert findings[0].kind is HealthFindingKind.EMPTY_QUEUE
    assert findings[0].recommended_action is RecoveryActionKind.RESTEER


def test_empty_queue_action_queues_next_task():
    frame = _frame(active_task_id="", next_candidate_id="")
    action = choose_recovery_action(frame, evaluate_lane_frame(frame))
    assert isinstance(action, ResteerDirective)
    assert action.resteer_kind is ResteerKind.QUEUE_NEXT_TASK


def test_empty_review_queue_does_not_trigger_build_runway_finding():
    frame = _frame(
        lane_id="codex-reviews-b",
        lane_role=LaneRole.REVIEW,
        assigned_queue_path="docs/live-codex-reviews-2.md",
        current_queue_path="docs/live-codex-reviews-2.md",
        expected_queue_path="docs/live-codex-reviews-2.md",
        active_task_id="",
        next_candidate_id="",
    )

    assert evaluate_lane_frame(frame) == ()


def test_shared_worktree_escalates():
    frame = _frame()
    peer = _frame(lane_id="build-2", assigned_queue_path="docs/live-build-2.md")
    findings = evaluate_lane_frame(frame, (peer,))
    assert HealthFindingKind.SHARED_WORKTREE in {finding.kind for finding in findings}

    action = choose_recovery_action(frame, findings)
    assert isinstance(action, EscalationGate)
    assert "Scott" in action.default_recommendation


def test_main_worktree_violation_escalates():
    frame = _frame(worktree_path="C:/Users/scott/Code/Meridian")
    findings = evaluate_lane_frame(frame)
    assert findings[0].kind is HealthFindingKind.MAIN_WORKTREE_VIOLATION
    assert findings[0].severity is FindingSeverity.ESCALATE


def test_review_lane_reading_build_queue_restarts_to_review_queue():
    frame = _frame(
        lane_id="codex-reviews-a",
        lane_role=LaneRole.REVIEW,
        assigned_queue_path="docs/live-codex-reviews.md",
        expected_queue_path="docs/live-codex-reviews.md",
        current_queue_path="docs/live-build-1.md",
    )
    findings = evaluate_lane_frame(frame)
    assert findings[0].kind is HealthFindingKind.REVIEW_LANE_READING_BUILD_QUEUE

    action = choose_recovery_action(frame, findings)
    assert isinstance(action, RestartDirective)
    assert action.restart_kind is RestartKind.REANCHOR_QUEUE
    assert action.target_queue_path == "docs/live-codex-reviews.md"


def test_build_lane_reading_review_queue_restarts():
    frame = _frame(current_queue_path="docs/live-codex-reviews-2.md")
    assert HealthFindingKind.BUILD_LANE_READING_REVIEW_QUEUE in _kinds(frame)


def test_wrong_queue_restarts():
    frame = _frame(current_queue_path="docs/live-build-5.md")
    findings = evaluate_lane_frame(frame)
    assert findings[0].kind is HealthFindingKind.WRONG_QUEUE
    assert isinstance(choose_recovery_action(frame, findings), RestartDirective)


def test_cadence_counter_three_routes_review():
    frame = _frame(cadence_counter=3)
    findings = evaluate_lane_frame(frame)
    assert HealthFindingKind.REVIEW_BACKLOG in _kinds(frame)

    action = choose_recovery_action(frame, findings)
    assert isinstance(action, ResteerDirective)
    assert action.resteer_kind is ResteerKind.ROUTE_REVIEW
    assert action.required_review_gate == "Codex review cadence"


def test_quota_blocked_does_not_reissue_same_model_work():
    frame = _frame(quota_state=QuotaState.BLOCKED, model_family="sonnet")
    findings = evaluate_lane_frame(frame)
    assert findings[0].kind is HealthFindingKind.QUOTA_BLOCKED

    action = choose_recovery_action(frame, findings)
    assert isinstance(action, ResteerDirective)
    assert action.resteer_kind is ResteerKind.SWITCH_MODEL_FAMILY
    assert "Do not reissue" in action.new_task_summary


def test_proof_block_beats_empty_queue_throughput():
    frame = _frame(active_task_id="", next_candidate_id="", has_proof_block=True)
    findings = evaluate_lane_frame(frame)
    action = choose_recovery_action(frame, findings)
    assert isinstance(action, ResteerDirective)
    assert action.resteer_kind is ResteerKind.ROUTE_PROOF_REPAIR
    assert action.required_proof == "Aegis proof clearance"


def test_safety_finding_beats_review_and_empty_queue():
    frame = _frame(
        active_task_id="",
        next_candidate_id="",
        cadence_counter=3,
        worktree_path="C:/Users/scott/Code/Meridian",
    )
    action = choose_recovery_action(frame, evaluate_lane_frame(frame))
    assert isinstance(action, EscalationGate)


def test_uncommitted_drift_restarts_with_commit_or_report():
    frame = _frame(has_uncommitted_drift=True)
    action = choose_recovery_action(frame, evaluate_lane_frame(frame))
    assert isinstance(action, RestartDirective)
    assert action.restart_kind is RestartKind.COMMIT_OR_REPORT_DRIFT


def test_launch_popup_restarts_app_frame():
    frame = _frame(has_launch_popup=True)
    action = choose_recovery_action(frame, evaluate_lane_frame(frame))
    assert isinstance(action, RestartDirective)
    assert action.restart_kind is RestartKind.RELAUNCH_APP


def test_obsidian_divergence_routes_memory_update():
    frame = _frame(has_obsidian_divergence=True)
    action = choose_recovery_action(frame, evaluate_lane_frame(frame))
    assert isinstance(action, ResteerDirective)
    assert action.resteer_kind is ResteerKind.UPDATE_MEMORY
