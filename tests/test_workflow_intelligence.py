"""Tests for V2.5 display-safe workflow intelligence."""

from __future__ import annotations

from meridian_core.workflow_intelligence import (
    BlockedLaneSummary,
    FailureRecoveryAction,
    FailureRecoveryRecommendation,
    LaneCapacityStatus,
    TaskResultInput,
    TaskResultOutcome,
    TaskResultSummary,
    WorkflowTaskDefinition,
    WorkflowTaskPlan,
    WorkflowTaskReadiness,
    ingest_task_results,
    plan_workflow_tasks,
    recommend_failure_recovery,
)


def test_dependency_ordering_places_prerequisites_first():
    report = plan_workflow_tasks(
        (
            WorkflowTaskDefinition(
                task_id="task:verify",
                lane="proof",
                title="Verify repair",
                depends_on=("task:repair",),
            ),
            WorkflowTaskDefinition(
                task_id="task:repair",
                lane="backend",
                title="Repair workflow",
            ),
        ),
        lane_capacity_limits={"backend": 2, "proof": 2},
    )

    assert tuple(plan.task_ref for plan in report.task_plans) == (
        "task:repair",
        "task:verify",
    )
    assert tuple(plan.sequence for plan in report.task_plans) == (1, 2)
    assert all(plan.readiness is WorkflowTaskReadiness.READY for plan in report.task_plans)


def test_blocked_dependency_stays_unscheduled_and_marks_lane():
    report = plan_workflow_tasks(
        (
            WorkflowTaskDefinition(
                task_id="task:verify",
                lane="proof",
                depends_on=("task:missing-repair",),
            ),
        ),
        lane_capacity_limits={"proof": 1},
    )

    plan = report.task_plans[0]
    assert plan.readiness is WorkflowTaskReadiness.BLOCKED
    assert plan.sequence is None
    assert plan.blocking_refs == ("task:missing-repair",)
    assert plan.reason_tags == ("dependency_blocked",)
    assert report.blocked_lanes[0].to_display_dict() == {
        "lane": "proof",
        "blocked_count": 1,
        "blocking_refs": ("task:missing-repair",),
        "reason_tags": ("dependency_blocked",),
    }


def test_lane_capacity_summary_accounts_for_active_planned_and_blocked_units():
    report = plan_workflow_tasks(
        (
            WorkflowTaskDefinition(task_id="task:a", lane="backend"),
            WorkflowTaskDefinition(task_id="task:b", lane="backend"),
        ),
        lane_capacity_limits={"backend": 2},
        active_units_by_lane={"backend": 1},
    )

    ready = [plan for plan in report.task_plans if plan.readiness is WorkflowTaskReadiness.READY]
    blocked = [plan for plan in report.task_plans if plan.readiness is WorkflowTaskReadiness.BLOCKED]
    assert len(ready) == 1
    assert len(blocked) == 1
    assert blocked[0].reason_tags == ("lane_capacity_exhausted",)

    capacity = report.lane_capacity[0]
    assert capacity.status is LaneCapacityStatus.FULL
    assert capacity.to_display_dict() == {
        "lane": "backend",
        "capacity_limit": 2,
        "active_units": 1,
        "planned_units": 1,
        "available_units": 0,
        "blocked_count": 1,
        "status": "full",
    }


def test_task_result_ingestion_normalizes_status_artifacts_and_retryability():
    summaries = ingest_task_results(
        (
            TaskResultInput(
                task_id="task:repair",
                lane="backend",
                status="ERROR",
                summary="Patch failed validation",
                artifact_refs=("proof:validation", "proof:validation"),
                failure_kind="validation",
            ),
            TaskResultInput(
                task_id="task:verify",
                lane="proof",
                status="completed",
                summary="Verification passed",
            ),
        )
    )

    failed = summaries[0]
    succeeded = summaries[1]
    assert failed.outcome is TaskResultOutcome.FAILED
    assert failed.failure_kind == "validation"
    assert failed.retryable is False
    assert failed.artifact_refs == ("proof:validation",)
    assert succeeded.outcome is TaskResultOutcome.SUCCEEDED


def test_failure_recovery_recommends_retry_for_retryable_failure():
    result = ingest_task_results(
        (
            TaskResultInput(
                task_id="task:dispatch",
                lane="backend",
                status="failed",
                summary="Worker timed out",
                failure_kind="timeout",
            ),
        )
    )[0]

    recommendation = recommend_failure_recovery(result)

    assert recommendation.action is FailureRecoveryAction.RETRY
    assert recommendation.reason_tags == ("retryable_failure", "timeout")
    assert recommendation.to_display_dict()["message"] == (
        "Retry after preserving the normalized failure summary."
    )


def test_failure_recovery_recommends_dependency_unblock_for_blocked_result():
    result = ingest_task_results(
        (
            TaskResultInput(
                task_id="task:verify",
                lane="proof",
                status="blocked",
                summary="Dependency unavailable",
            ),
        )
    )[0]

    recommendation = recommend_failure_recovery(result)

    assert recommendation.action is FailureRecoveryAction.UNBLOCK_DEPENDENCY
    assert recommendation.reason_tags == ("dependency_blocked",)


def test_display_dicts_do_not_leak_raw_transcripts_logs_or_local_paths():
    report = plan_workflow_tasks(
        (
            WorkflowTaskDefinition(
                task_id=r"C:\Users\scott\Code\Meridian\raw-task.log",
                lane="backend",
                title="raw transcript: token=super-secret-token",
                depends_on=(r"C:\Users\scott\Code\Meridian\dependency.log",),
            ),
        ),
        lane_capacity_limits={"backend": 1},
    )
    result = ingest_task_results(
        (
            TaskResultInput(
                task_id=r"C:\Users\scott\Code\Meridian\raw-task.log",
                lane="backend",
                status="failed",
                summary="raw transcript: token=super-secret-token",
                transcript="full transcript:\nsecret token=abc123",
                log_excerpt=r"Traceback at C:\Users\scott\Code\Meridian\.env",
                artifact_refs=(r"C:\Users\scott\Code\Meridian\result.log",),
                failure_kind="provider response: secret token",
            ),
        )
    )[0]

    display_text = f"{report.to_display_dict()} {result.to_display_dict()}"

    assert "super-secret-token" not in display_text
    assert "abc123" not in display_text
    assert r"C:\Users\scott" not in display_text
    assert "Traceback" not in display_text
    assert "raw transcript" not in display_text
    assert report.to_display_dict()["task_plans"][0]["task_ref"].startswith("task:unsafe:")
    assert result.to_display_dict()["artifact_refs"][0].startswith("artifact:unsafe:")


def test_direct_failure_recovery_recommendation_display_sanitizes_message_and_tags():
    recommendation = FailureRecoveryRecommendation(
        task_ref="task:fine",
        action=FailureRecoveryAction.ESCALATE,
        reason_tags=("provider response: hidden failure reason",),
        message=r"escalation note at C:\Users\scott\private.log",
    )

    display = recommendation.to_display_dict()
    rendered = str(display)

    assert display["message"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]",)
    assert r"C:\Users\scott" not in rendered


def test_direct_workflow_task_plan_display_sanitizes_reason_tags():
    plan = WorkflowTaskPlan(
        task_ref="task:fine",
        lane="lane",
        title="title",
        dependency_refs=(),
        readiness=WorkflowTaskReadiness.BLOCKED,
        sequence=None,
        capacity_units=1,
        blocking_refs=(),
        reason_tags=(r"raw transcript: hidden tag at C:\Users\scott\file",),
    )

    rendered = str(plan.to_display_dict())

    assert plan.to_display_dict()["reason_tags"] == ("[redacted]",)
    assert r"C:\Users\scott" not in rendered


def test_direct_blocked_lane_summary_display_sanitizes_reason_tags():
    summary = BlockedLaneSummary(
        lane="lane",
        blocked_count=1,
        blocking_refs=(),
        reason_tags=("provider response: hidden blocker reason",),
    )

    rendered = str(summary.to_display_dict())

    assert summary.to_display_dict()["reason_tags"] == ("[redacted]",)
    assert "hidden blocker reason" not in rendered


def test_direct_task_result_summary_display_sanitizes_reason_tags():
    summary = TaskResultSummary(
        task_ref="task:fine",
        lane="lane",
        outcome=TaskResultOutcome.FAILED,
        headline="task failed",
        artifact_refs=(),
        failure_kind="unknown",
        retryable=False,
        duration_seconds=None,
        reason_tags=(r"traceback at C:\Users\scott\file",),
    )

    rendered = str(summary.to_display_dict())

    assert summary.to_display_dict()["reason_tags"] == ("[redacted]",)
    assert r"C:\Users\scott" not in rendered


def test_direct_task_result_summary_display_redacts_raw_prompt_failure_kind():
    summary = TaskResultSummary(
        task_ref="task:fine",
        lane="lane",
        outcome=TaskResultOutcome.FAILED,
        headline="task failed",
        artifact_refs=(),
        failure_kind="raw prompt: hidden failure body",
        retryable=False,
        duration_seconds=None,
        reason_tags=("full prompt: another hidden body",),
    )

    display = summary.to_display_dict()
    rendered = str(display)

    assert display["failure_kind"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]",)
    assert "hidden failure body" not in rendered
    assert "another hidden body" not in rendered


def test_direct_task_result_summary_display_redacts_provider_output_reason_tags():
    summary = TaskResultSummary(
        task_ref="task:fine",
        lane="lane",
        outcome=TaskResultOutcome.FAILED,
        headline="task failed",
        artifact_refs=(),
        failure_kind="provider output: hidden body",
        retryable=False,
        duration_seconds=None,
        reason_tags=(
            "model output: hidden body",
            "complete prompt: another hidden body",
        ),
    )

    display = summary.to_display_dict()
    rendered = str(display)

    assert display["failure_kind"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]", "[redacted]")
    assert "hidden body" not in rendered
    assert "another hidden body" not in rendered


def test_direct_failure_recovery_recommendation_redacts_raw_prompt_and_model_output():
    recommendation = FailureRecoveryRecommendation(
        task_ref="task:fine",
        action=FailureRecoveryAction.ESCALATE,
        reason_tags=(
            "raw prompt: hidden reason",
            "model output: another hidden reason",
        ),
        message="complete prompt: hidden escalation note",
    )

    display = recommendation.to_display_dict()
    rendered = str(display)

    assert display["message"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]", "[redacted]")
    assert "hidden reason" not in rendered
    assert "another hidden reason" not in rendered
    assert "hidden escalation note" not in rendered


def test_direct_failure_recovery_recommendation_redacts_github_token_shaped_refs():
    recommendation = FailureRecoveryRecommendation(
        task_ref="task:ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        action=FailureRecoveryAction.ESCALATE,
        reason_tags=("ghs_abcdefghijklmnopqrstuvwxyz0123456789",),
        message="ghp_abcdefghijklmnopqrstuvwxyz0123456789",
    )

    display = recommendation.to_display_dict()
    rendered = str(display)

    assert display["task_ref"].startswith("task:unsafe:")
    assert display["message"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]",)
    for prefix in ("ghp_", "ghs_"):
        assert prefix not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered


def test_direct_failure_recovery_recommendation_redacts_fine_grained_github_pat():
    pat = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    recommendation = FailureRecoveryRecommendation(
        task_ref=f"task:{pat}",
        action=FailureRecoveryAction.ESCALATE,
        reason_tags=(pat,),
        message=pat,
    )

    display = recommendation.to_display_dict()
    rendered = str(display)

    assert display["task_ref"].startswith("task:unsafe:")
    assert display["message"] == "[redacted]"
    assert display["reason_tags"] == ("[redacted]",)
    assert "github_pat_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in rendered
