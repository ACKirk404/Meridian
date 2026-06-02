"""Tests for Beacon file-backed liveness checks."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from meridian_core.beacon import (
    LivenessTarget,
    check_harness_liveness,
    command_plan_advisory_evidence,
    permission_summary_advisory_evidence,
    runtime_state_advisory_evidence,
    workflow_recovery_advisory_evidence,
)
from meridian_core.models import HeartbeatStatus
from meridian_core.session_lifecycle import (
    CommandIntent,
    HarnessRole,
    HealthState,
    OperationScope,
    PermissionContext,
    PermissionState,
    ProofState,
    ReviewCadenceState,
    SessionCommandPlan,
    SessionLifecycleState,
    SessionStatus,
    export_session_runtime_state_for_workflow_recovery,
    summarize_session_permission_state,
    summarize_workflow_work_order_recovery,
)


def _touch(path: Path, modified_at: datetime) -> None:
    path.write_text("sentinel", encoding="utf-8")
    stamp = modified_at.timestamp()
    os.utime(path, (stamp, stamp))


class TestCheckHarnessLiveness:
    def test_fresh_sentinel_returns_alive_heartbeat(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        sentinel = tmp_path / "live-build-1.md"
        _touch(sentinel, now - timedelta(seconds=30))

        heartbeats = check_harness_liveness(
            [LivenessTarget("build_1", sentinel, stale_after_seconds=60)],
            now=now,
        )

        assert heartbeats[0].status is HeartbeatStatus.ALIVE

    def test_stale_sentinel_returns_stale_heartbeat(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        sentinel = tmp_path / "live-build-1.md"
        _touch(sentinel, now - timedelta(seconds=61))

        heartbeats = check_harness_liveness(
            [LivenessTarget("build_1", sentinel, stale_after_seconds=60)],
            now=now,
        )

        assert heartbeats[0].status is HeartbeatStatus.STALE

    def test_missing_sentinel_returns_failed_heartbeat(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        missing = tmp_path / "missing.md"

        heartbeats = check_harness_liveness(
            [LivenessTarget("build_1", missing)],
            now=now,
        )

        assert heartbeats[0].status is HeartbeatStatus.FAILED

    def test_missing_sentinel_records_blocker(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.md"

        heartbeats = check_harness_liveness([LivenessTarget("build_1", missing)])

        assert "missing sentinel" in heartbeats[0].blockers[0]

    def test_current_work_records_target_path(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        sentinel = tmp_path / "live-build-1.md"
        _touch(sentinel, now)

        heartbeats = check_harness_liveness([LivenessTarget("build_1", sentinel)], now=now)

        assert heartbeats[0].current_work == str(sentinel)

    def test_last_event_records_age(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        sentinel = tmp_path / "live-build-1.md"
        _touch(sentinel, now - timedelta(seconds=45))

        heartbeats = check_harness_liveness([LivenessTarget("build_1", sentinel)], now=now)

        assert "45s ago" in heartbeats[0].last_event

    def test_multiple_targets_return_in_input_order(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0, tzinfo=timezone.utc)
        first = tmp_path / "first.md"
        second = tmp_path / "second.md"
        _touch(first, now)
        _touch(second, now)

        heartbeats = check_harness_liveness(
            [
                LivenessTarget("first", first),
                LivenessTarget("second", second),
            ],
            now=now,
        )

        assert [heartbeat.harness_id for heartbeat in heartbeats] == ["first", "second"]

    def test_naive_now_is_treated_as_utc(self, tmp_path: Path) -> None:
        now = datetime(2026, 5, 30, 20, 0)
        sentinel = tmp_path / "live-build-1.md"
        _touch(sentinel, now.replace(tzinfo=timezone.utc))

        heartbeats = check_harness_liveness([LivenessTarget("build_1", sentinel)], now=now)

        assert heartbeats[0].updated_at.tzinfo is timezone.utc

    def test_negative_stale_threshold_raises(self, tmp_path: Path) -> None:
        target = LivenessTarget("build_1", tmp_path / "x.md", stale_after_seconds=-1)

        with pytest.raises(ValueError):
            check_harness_liveness([target])


class TestCommandPlanAdvisoryEvidence:
    def test_command_plan_permission_evidence_is_display_safe(self) -> None:
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        plan = SessionCommandPlan(
            session_id="build-2",
            session_name="Build 2",
            command_intent=CommandIntent.RESTART,
            reason="stale_heartbeat",
            expected_state_transition=(SessionStatus.STALE, SessionStatus.RUNNING),
            current_state_evidence="SessionLifecycleState:build-2:stale",
            queue_file_evidence="docs/live-build-2.md",
            worktree_evidence="/worktree/build-2",
            review_gate_evidence=None,
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected="docs/live-build-2.md",
            worktree_path_affected="/worktree/build-2",
            branch_affected="codex/aligned-build-2-permission-evidence",
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=False,
            human_approval_required=True,
            approval_context="stale recovery requires human approval",
            rollback_or_recovery_note="Advisory only; no live restart is executed.",
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            permission_task_scope="permission-evidence-slice",
            permission_approved_operations=(OperationScope.RESTART,),
            permission_operation=OperationScope.RESTART,
            permission_operation_allowed=True,
            permission_evidence="unlocked_temporary:permission-evidence-slice",
        )

        evidence = command_plan_advisory_evidence(plan, now=now)

        assert evidence.harness_id == "build-2"
        assert evidence.advisory_type == "restart"
        assert evidence.human_gate_required is True
        assert "permission.operation=restart" in evidence.evidence
        assert "permission.operation_allowed=True" in evidence.evidence
        assert "stale recovery requires human approval" in evidence.blockers

    def test_command_plan_movement_blocker_is_beacon_evidence(self) -> None:
        plan = SessionCommandPlan(
            session_id="build-2",
            session_name="Build 2",
            command_intent=CommandIntent.SPAWN,
            reason="reasoning_shift",
            expected_state_transition=(SessionStatus.STARTING, SessionStatus.POLLING),
            current_state_evidence="SessionLifecycleState:build-2:running",
            queue_file_evidence="docs/live-build-2.md",
            worktree_evidence="/worktree/build-2",
            review_gate_evidence=None,
            proof_requirement=ProofState.COMMAND_STAGED,
            queue_file_affected="docs/live-build-2.md",
            worktree_path_affected="/worktree/build-2",
            branch_affected="codex/aligned-build-2-permission-evidence",
            aegis_gate_result=None,
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=False,
            human_approval_required=True,
            approval_context="new session requires human approval",
            rollback_or_recovery_note="Advisory only; no worktree is created.",
            permission_state=PermissionState.UNLOCKED_TEMPORARY,
            permission_task_scope="permission-evidence-slice",
            permission_approved_operations=(OperationScope.RESTART,),
            permission_operation=OperationScope.WORKTREE_CREATE,
            permission_operation_allowed=False,
            permission_evidence="unlocked_temporary:permission-evidence-slice",
        )

        evidence = command_plan_advisory_evidence(plan)

        assert "permission.operation=worktree_create" in evidence.evidence
        assert "permission.operation_allowed=False" in evidence.evidence
        assert "permission_required_for_worktree_create" in evidence.blockers
        assert evidence.to_dict()["blockers"] == list(evidence.blockers)


class TestPermissionSummaryAdvisoryEvidence:
    def test_permission_summary_recovery_evidence_is_display_safe(self) -> None:
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now - timedelta(minutes=1),
            task_scope="permission-summary",
            last_permission_change=now,
        )
        session = SessionLifecycleState(
            session_id="build-2-summary",
            session_name="Build 2 Summary",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-permission-advisory-binding",
            current_task_id="permission-summary",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )
        summary = summarize_session_permission_state(session, timestamp=now)

        evidence = permission_summary_advisory_evidence(summary, now=now)

        assert evidence.harness_id == "build-2-summary"
        assert evidence.advisory_type == "restart"
        assert evidence.human_gate_required is True
        assert "permission.unlock_expired" in evidence.blockers
        assert "permission.state=unlocked_temporary" in evidence.evidence
        assert any(item.startswith("finding.restart=") for item in evidence.evidence)
        assert any(item.startswith("recovery.rationale=") for item in evidence.evidence)
        assert evidence.to_dict()["advisory_type"] == "restart"


class TestWorkflowRecoveryAdvisoryEvidence:
    def test_workflow_recovery_summary_becomes_beacon_evidence(self) -> None:
        now = datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now - timedelta(minutes=1),
            task_scope="workflow-summary",
            last_permission_change=now,
        )
        session = SessionLifecycleState(
            session_id="build-2-workflow",
            session_name="Build 2 Workflow",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-workflow-advisory-binding",
            current_task_id="workflow-summary",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )
        summary = summarize_workflow_work_order_recovery(
            session,
            work_order_id="wo-beacon-workflow",
            heartbeat_emitted_at=now - timedelta(minutes=10),
            timestamp=now,
        )

        evidence = workflow_recovery_advisory_evidence(summary, now=now)

        assert evidence.harness_id == "build-2-workflow"
        assert evidence.advisory_type == "workflow_request_human_gate"
        assert evidence.human_gate_required is True
        assert "permission.unlock_expired" in evidence.blockers
        assert "workflow.recovery_action=request_human_gate" in evidence.evidence
        assert "work_order.id=wo-beacon-workflow" in evidence.evidence
        assert evidence.to_dict()["blockers"] == list(evidence.blockers)


class TestRuntimeStateAdvisoryEvidence:
    def test_runtime_state_export_becomes_beacon_evidence(self) -> None:
        now = datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc)
        permission_context = PermissionContext(
            approved_by="prime",
            approval_scope=frozenset([OperationScope.RESTART]),
            escalation_gate=False,
            escalation_reason=None,
            branch_permission_state=PermissionState.UNLOCKED_TEMPORARY,
            approved_by_secondary=None,
            unlock_expiry=now + timedelta(hours=1),
            task_scope="runtime-export",
            last_permission_change=now,
        )
        session = SessionLifecycleState(
            session_id="build-2-runtime",
            session_name="Build 2 Runtime",
            project_name="Meridian",
            project_path="/path/to/meridian",
            harness_role=HarnessRole.BUILD,
            assigned_queue_file="docs/live-build-2.md",
            model_provider="anthropic",
            model_name="claude-opus-4-7",
            status=SessionStatus.STALE,
            worktree_path="/worktree/build-2",
            branch_name="codex/rolling-build-2-runtime-export-advisory",
            current_task_id="runtime-export",
            last_queue_read_at=now,
            last_queue_write_at=now,
            last_prompt_sent_at=now - timedelta(minutes=45),
            last_prompt_payload_size=12000,
            review_cadence_state=ReviewCadenceState.NONE,
            proof_state=ProofState.PERMISSION_VALIDATED,
            health_state=HealthState.STALE,
            blocker_summary=None,
            permission_context=permission_context,
        )
        command_plan = SessionCommandPlan(
            session_id=session.session_id,
            session_name=session.session_name,
            command_intent=CommandIntent.RESTART,
            reason="Workflow heartbeat stale",
            expected_state_transition=(SessionStatus.STALE, SessionStatus.RUNNING),
            current_state_evidence="build-2-runtime:stale",
            queue_file_evidence=session.assigned_queue_file,
            worktree_evidence=session.worktree_path,
            review_gate_evidence=None,
            proof_requirement=ProofState.PERMISSION_VALIDATED,
            queue_file_affected=session.assigned_queue_file,
            worktree_path_affected=session.worktree_path,
            branch_affected=session.branch_name,
            aegis_gate_result="pending",
            cadence_gate_required=False,
            cadence_gate_status=ReviewCadenceState.NONE,
            is_executable_now=False,
            human_approval_required=True,
            approval_context="runtime recovery requires command-plan review",
            rollback_or_recovery_note="Advisory restart only.",
        )
        workflow_summary = summarize_workflow_work_order_recovery(
            session,
            work_order_id="wo-beacon-runtime",
            heartbeat_emitted_at=now - timedelta(minutes=10),
            timestamp=now,
        )
        runtime_export = export_session_runtime_state_for_workflow_recovery(
            session,
            command_plan=command_plan,
            workflow_recovery_summary=workflow_summary,
            timestamp=now,
        )

        evidence = runtime_state_advisory_evidence(runtime_export, now=now)

        assert evidence.harness_id == "build-2-runtime"
        assert evidence.advisory_type == "runtime_start_new"
        assert evidence.human_gate_required is True
        assert "runtime recovery requires command-plan review" in evidence.blockers
        assert "runtime.command_kind=restart" in evidence.evidence
        assert "runtime.recovery_action=start_new" in evidence.evidence
        assert "workflow.work_order_id=wo-beacon-runtime" in evidence.evidence
        assert evidence.to_dict()["advisory_type"] == "runtime_start_new"
