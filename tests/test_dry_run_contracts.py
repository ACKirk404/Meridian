"""Tests for V2.5 tool and browser dry-run contracts."""

from __future__ import annotations

import builtins
import subprocess

from meridian_core.dry_run_contracts import (
    BrowserEvidence,
    BrowserNavigationInput,
    DryRunReviewState,
    DryRunSeverity,
    ReversibleActionPlan,
    ReviewAffordanceState,
    SafeNavigationPolicySummary,
    ScreenshotEvidenceInput,
    ScreenshotEvidenceLink,
    ToolActionInput,
    ToolDryRunPlan,
    ToolFailureInput,
    ToolFailureRoutingRecord,
    VisualDiffInput,
    VisualDiffProof,
    VisualDiffStatus,
    build_browser_evidence,
    build_tool_dry_run_plan,
)


def test_tool_dry_run_does_not_execute_tools_io_or_external_mutation(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry-run contracts must not execute side effects")

    monkeypatch.setattr(builtins, "open", fail_if_called)
    monkeypatch.setattr(subprocess, "run", fail_if_called)

    plan = build_tool_dry_run_plan(
        "plan:non-execution",
        (
            ToolActionInput(
                tool_name="shell",
                action_label="would run command",
                target_ref="artifact:repo",
                mutation_kind="write",
                reversible=True,
            ),
        ),
    )

    display = plan.to_display_dict()
    assert display["dry_run_only"] is True
    assert display["reversible_actions"][0]["would_execute"] is False
    assert display["reversible_actions"][0]["external_mutation_blocked"] is True


def test_reversible_action_plan_is_display_ready_with_review_affordance():
    plan = build_tool_dry_run_plan(
        "plan:repair-preview",
        (
            ToolActionInput(
                tool_name="apply_patch",
                action_label="update backend contract",
                target_ref="artifact:dry-run-contract",
                mutation_kind="file_patch",
                reversible=True,
                rollback_plan_ref="rollback:dry-run-contract",
            ),
        ),
    )

    action = plan.reversible_actions[0]
    assert action.reversible is True
    assert action.rollback_plan_ref == "rollback:dry-run-contract"
    assert plan.review.state is DryRunReviewState.READY
    assert plan.review.can_approve is True
    assert plan.review.requires_human_review is False
    assert plan.to_display_dict()["reversible_actions"][0]["mutation_kind"] == "file_patch"


def test_unsafe_navigation_is_blocked_without_echoing_target_url():
    unsafe_url = "javascript:fetch('https://example.test/private?token=super-secret-token-123456')"
    plan = build_tool_dry_run_plan(
        "plan:unsafe-navigation",
        (),
        navigations=(
            BrowserNavigationInput(
                request_id="nav:private-token",
                requested_url=unsafe_url,
            ),
        ),
    )

    display = plan.to_display_dict()
    assert plan.safe_navigation.status is DryRunReviewState.BLOCKED
    assert plan.safe_navigation.blocked_schemes == ("javascript",)
    assert display["safe_navigation"]["warning_count"] == 1
    assert "blocked by dry-run policy" in display["safe_navigation"]["warnings"][0]
    assert "super-secret-token" not in str(display)
    assert "javascript:fetch" not in str(display)


def test_browser_evidence_displays_screenshot_links_and_visual_diff_shape():
    evidence = build_browser_evidence(
        "browser-evidence:checkout",
        navigations=(
            BrowserNavigationInput(
                request_id="nav:checkout",
                requested_url="https://example.test/checkout",
            ),
        ),
        screenshots=(
            ScreenshotEvidenceInput(
                evidence_ref="screenshot:checkout-desktop",
                thumbnail_ref="thumbnail:checkout-desktop",
                viewport_label="desktop",
            ),
        ),
        visual_diff=VisualDiffInput(
            baseline_ref="visual:baseline",
            candidate_ref="visual:candidate",
            diff_ref="visual:diff",
            changed_region_count=2,
            threshold=0.05,
        ),
    )

    display = evidence.to_display_dict()
    assert evidence.dry_run_only is True
    assert display["screenshot_links"][0] == {
        "evidence_ref": "screenshot:checkout-desktop",
        "thumbnail_ref": "thumbnail:checkout-desktop",
        "viewport_label": "desktop",
        "raw_content_available": False,
    }
    assert evidence.visual_diff.status is VisualDiffStatus.CHANGED
    assert display["visual_diff"]["changed_region_count"] == 2
    assert display["review"]["state"] == "needs_review"


def test_tool_failure_routing_record_is_display_safe_and_deterministic():
    plan = build_tool_dry_run_plan(
        "plan:failure-routing",
        (),
        failure_routes=(
            ToolFailureInput(
                route_id="route:model-timeout",
                failure_kind="timeout",
                severity=DryRunSeverity.WARNING,
                retryable=True,
                next_route="retry_then_manual_review",
                evidence_ref="evidence:timeout-summary",
            ),
        ),
    )

    route = plan.failure_routing[0]
    assert route.severity is DryRunSeverity.WARNING
    assert route.retryable is True
    assert route.next_route == "retry_then_manual_review"
    assert route.to_display_dict() == {
        "route_ref": "route:model-timeout",
        "failure_kind": "timeout",
        "severity": "warning",
        "retryable": True,
        "next_route": "retry_then_manual_review",
        "evidence_ref": "evidence:timeout-summary",
    }


def test_display_records_do_not_leak_local_paths_raw_content_or_secret_values():
    raw_path = r"C:\Users\scott\Code\Meridian\.env"
    raw_content = "raw content: provider response includes password=hidden-value-123456"
    browser = build_browser_evidence(
        raw_path,
        screenshots=(
            ScreenshotEvidenceInput(
                evidence_ref=raw_path,
                thumbnail_ref=raw_content,
                viewport_label=raw_content,
            ),
        ),
        visual_diff=VisualDiffInput(
            baseline_ref=raw_path,
            candidate_ref=raw_content,
            diff_ref=r"C:\Users\scott\Code\Meridian\diff.png",
        ),
    )
    plan = build_tool_dry_run_plan(
        raw_path,
        (
            ToolActionInput(
                tool_name=raw_content,
                action_label=raw_content,
                target_ref=raw_path,
                rollback_plan_ref=raw_path,
            ),
        ),
        failure_routes=(
            ToolFailureInput(
                route_id=raw_path,
                failure_kind=raw_content,
                next_route=raw_content,
                evidence_ref=raw_path,
            ),
        ),
    )

    display_text = f"{browser.to_display_dict()} {plan.to_display_dict()}"
    assert r"C:\Users\scott" not in display_text
    assert "provider response" not in display_text
    assert "hidden-value" not in display_text
    assert "password=" not in display_text
    assert "raw content" not in display_text
    assert "browser-evidence:unsafe:" in display_text
    assert "target:unsafe:" in display_text


def test_direct_reversible_action_plan_display_sanitizes_unsafe_fields():
    plan = ReversibleActionPlan(
        action_ref=r"C:\Users\scott\action-id",
        tool_ref=r"C:\Users\scott\tool",
        action_label="raw prompt: hidden label body",
        target_ref="/home/scott/target",
        mutation_kind="provider response: hidden kind",
        reversible=True,
        rollback_plan_ref=r"\\share\path\rollback\\",
        would_execute=False,
        external_mutation_blocked=True,
    )

    display = plan.to_display_dict()
    rendered = str(display)

    assert "action:unsafe:" in str(display["action_ref"])
    assert "tool:unsafe:" in str(display["tool_ref"])
    assert display["action_label"] == "planned action"
    assert "target:unsafe:" in str(display["target_ref"])
    assert display["mutation_kind"] == "mutation"
    assert "rollback:unsafe:" in str(display["rollback_plan_ref"])
    assert r"C:\Users\scott" not in rendered
    assert "hidden label body" not in rendered
    assert "hidden kind" not in rendered


def test_direct_tool_failure_routing_display_sanitizes_unsafe_fields():
    record = ToolFailureRoutingRecord(
        route_ref=r"C:\Users\scott\route",
        failure_kind="raw transcript: private failure body",
        severity=DryRunSeverity.ERROR,
        retryable=False,
        next_route="provider response: hidden next route",
        evidence_ref="/home/scott/evidence",
    )

    display = record.to_display_dict()
    rendered = str(display)

    assert "failure-route:unsafe:" in str(display["route_ref"])
    assert display["failure_kind"] == "tool_failure"
    assert display["next_route"] == "manual_review"
    assert "evidence:unsafe:" in str(display["evidence_ref"])
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_screenshot_evidence_link_display_sanitizes_unsafe_fields():
    link = ScreenshotEvidenceLink(
        evidence_ref=r"C:\Users\scott\screenshot.png",
        thumbnail_ref="/home/scott/thumb.png",
        viewport_label="raw prompt: hidden viewport",
        raw_content_available=False,
    )

    display = link.to_display_dict()
    rendered = str(display)

    assert "screenshot:unsafe:" in str(display["evidence_ref"])
    assert "thumbnail:unsafe:" in str(display["thumbnail_ref"])
    assert display["viewport_label"] == "viewport"
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_visual_diff_proof_display_sanitizes_unsafe_fields():
    proof = VisualDiffProof(
        status=VisualDiffStatus.CHANGED,
        baseline_ref=r"C:\Users\scott\baseline",
        candidate_ref="/home/scott/candidate",
        diff_ref=r"C:\Users\scott\diff",
        changed_region_count=1,
        threshold=0.1,
    )

    display = proof.to_display_dict()
    rendered = str(display)

    assert "visual-baseline:unsafe:" in str(display["baseline_ref"])
    assert "visual-candidate:unsafe:" in str(display["candidate_ref"])
    assert "visual-diff:unsafe:" in str(display["diff_ref"])
    assert r"C:\Users\scott" not in rendered
    assert "/home/scott" not in rendered


def test_direct_review_affordance_state_display_sanitizes_blocked_reason():
    state = ReviewAffordanceState(
        state=DryRunReviewState.BLOCKED,
        can_approve=False,
        can_reject=True,
        requires_human_review=True,
        blocked_reason="provider response: hidden block reason",
    )

    display = state.to_display_dict()
    rendered = str(display)

    assert display["blocked_reason"] == "review_blocked"
    assert "hidden block reason" not in rendered


def test_direct_tool_dry_run_plan_display_sanitizes_plan_ref():
    plan = ToolDryRunPlan(
        plan_ref=r"C:\Users\scott\plan",
        safe_navigation=SafeNavigationPolicySummary(
            status=DryRunReviewState.READY,
            allowed_schemes=(),
            blocked_schemes=(),
            warning_count=0,
            warnings=(),
        ),
        reversible_actions=(),
        failure_routing=(),
        review=ReviewAffordanceState(
            state=DryRunReviewState.READY,
            can_approve=True,
            can_reject=True,
            requires_human_review=False,
        ),
    )

    rendered = str(plan.to_display_dict())

    assert "plan:unsafe:" in rendered
    assert r"C:\Users\scott" not in rendered


def test_direct_browser_evidence_display_sanitizes_evidence_ref():
    evidence = BrowserEvidence(
        evidence_ref=r"C:\Users\scott\evidence",
        safe_navigation=SafeNavigationPolicySummary(
            status=DryRunReviewState.READY,
            allowed_schemes=(),
            blocked_schemes=(),
            warning_count=0,
            warnings=(),
        ),
        screenshot_links=(),
        visual_diff=VisualDiffProof(
            status=VisualDiffStatus.NOT_PROVIDED,
            baseline_ref="",
            candidate_ref="",
            diff_ref="",
            changed_region_count=0,
            threshold=0.0,
        ),
        review=ReviewAffordanceState(
            state=DryRunReviewState.READY,
            can_approve=True,
            can_reject=True,
            requires_human_review=False,
        ),
    )

    rendered = str(evidence.to_display_dict())

    assert "browser-evidence:unsafe:" in rendered
    assert r"C:\Users\scott" not in rendered


def test_direct_reversible_action_plan_redacts_provider_output_mutation_kind():
    plan = ReversibleActionPlan(
        action_ref="action:ok",
        tool_ref="tool:ok",
        action_label="provider output: hidden label",
        target_ref="target:ok",
        mutation_kind="model output: hidden mutation kind",
        reversible=True,
        rollback_plan_ref="rollback:ok",
        would_execute=False,
        external_mutation_blocked=True,
    )

    display = plan.to_display_dict()
    rendered = str(display)

    assert display["action_label"] == "planned action"
    assert display["mutation_kind"] == "mutation"
    assert "hidden label" not in rendered
    assert "hidden mutation kind" not in rendered


def test_direct_tool_failure_routing_redacts_model_output_next_route():
    record = ToolFailureRoutingRecord(
        route_ref="route:ok",
        failure_kind="provider output: hidden failure body",
        severity=DryRunSeverity.ERROR,
        retryable=False,
        next_route="model output: hidden next route",
        evidence_ref="evidence:ok",
    )

    display = record.to_display_dict()
    rendered = str(display)

    assert display["failure_kind"] == "tool_failure"
    assert display["next_route"] == "manual_review"
    assert "hidden failure body" not in rendered
    assert "hidden next route" not in rendered


def test_direct_reversible_action_plan_redacts_full_prompt_label():
    plan = ReversibleActionPlan(
        action_ref="action:ok",
        tool_ref="tool:ok",
        action_label="full prompt: hidden label body",
        target_ref="target:ok",
        mutation_kind="complete prompt: hidden mutation",
        reversible=True,
        rollback_plan_ref="rollback:ok",
        would_execute=False,
        external_mutation_blocked=True,
    )

    display = plan.to_display_dict()
    rendered = str(display)

    assert display["action_label"] == "planned action"
    assert display["mutation_kind"] == "mutation"
    assert "hidden label body" not in rendered
    assert "hidden mutation" not in rendered


def test_direct_safe_navigation_summary_display_sanitizes_unsafe_schemes_and_warnings():
    summary = SafeNavigationPolicySummary(
        status=DryRunReviewState.BLOCKED,
        allowed_schemes=("http",),
        blocked_schemes=("raw prompt: hidden scheme",),
        warning_count=1,
        warnings=(r"navigation at C:\Users\scott\private blocked",),
    )

    display = summary.to_display_dict()
    rendered = str(display)

    assert display["blocked_schemes"] == ("scheme",)
    assert display["warnings"] == ("navigation_warning",)
    assert r"C:\Users\scott" not in rendered
    assert "hidden scheme" not in rendered


def test_tool_dry_run_plan_redacts_github_token_shaped_refs():
    plan = build_tool_dry_run_plan(
        "plan:ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        (
            ToolActionInput(
                tool_name="ghs_abcdefghijklmnopqrstuvwxyz0123456789",
                action_label="would run command",
                target_ref="ghp_abcdefghijklmnopqrstuvwxyz0123456789",
                mutation_kind="write",
                reversible=True,
                rollback_plan_ref="gho_abcdefghijklmnopqrstuvwxyz0123456789",
            ),
        ),
    )

    rendered = str(plan.to_display_dict())

    for prefix in ("ghp_", "gho_", "ghs_"):
        assert prefix not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered


def test_tool_dry_run_plan_redacts_fine_grained_github_pat_refs():
    pat = "github_pat_abcdefghijklmnopqrstuvwxyz0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    plan = build_tool_dry_run_plan(
        f"plan:{pat}",
        (
            ToolActionInput(
                tool_name=pat,
                action_label="would run command",
                target_ref=pat,
                mutation_kind="write",
                reversible=True,
                rollback_plan_ref=pat,
            ),
        ),
    )

    rendered = str(plan.to_display_dict())

    assert "github_pat_" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz0123456789" not in rendered
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in rendered
